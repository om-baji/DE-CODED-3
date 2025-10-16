from fastapi import FastAPI, APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import base64

# Import verification modules
from pinecone_client import pinecone_manager
from verification_pipeline import verification_pipeline

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="RAG Agent 3 - Proof Verification API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class ComplaintIngestResponse(BaseModel):
    complaint_id: str
    media_id: str
    status: str

class ProofIngestResponse(BaseModel):
    proof_id: str
    status: str
    recycled_flag: bool

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "RAG Agent 3 - Proof Verification System", "version": "1.0.0"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

@api_router.post("/initialize")
async def initialize_system():
    """Initialize Pinecone indexes"""
    try:
        pinecone_manager.initialize_indexes()
        return {"status": "success", "message": "Pinecone indexes initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ingest/complaint", response_model=ComplaintIngestResponse)
async def ingest_complaint(
    complaint_id: str = Form(...),
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: str = Form(...),
    issue_type: Optional[str] = Form("general")
):
    """Ingest a complaint with before-state image"""
    try:
        image_bytes = await image.read()
        
        result = await verification_pipeline.ingest_complaint(
            complaint_id=complaint_id,
            image_bytes=image_bytes,
            lat=latitude,
            lon=longitude,
            ts_iso=timestamp,
            metadata={'issue_type': issue_type}
        )
        
        return ComplaintIngestResponse(**result)
    except Exception as e:
        logging.error(f"Error ingesting complaint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ingest/proof", response_model=ProofIngestResponse)
async def ingest_proof(
    proof_id: str = Form(...),
    complaint_id: str = Form(...),
    worker_id: str = Form(...),
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: str = Form(...)
):
    """Ingest a proof/after-state image"""
    try:
        image_bytes = await image.read()
        
        result = await verification_pipeline.ingest_proof(
            proof_id=proof_id,
            complaint_id=complaint_id,
            worker_id=worker_id,
            image_bytes=image_bytes,
            lat=latitude,
            lon=longitude,
            ts_iso=timestamp
        )
        
        return ProofIngestResponse(**result)
    except Exception as e:
        logging.error(f"Error ingesting proof: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/verify/{proof_id}")
async def verify_proof(proof_id: str):
    """Run verification pipeline on a proof"""
    try:
        result = await verification_pipeline.verify_proof(proof_id)
        return result
    except Exception as e:
        logging.error(f"Error verifying proof: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/review_queue")
async def get_review_queue():
    """Get all QUESTIONABLE cases for human review"""
    try:
        # Query MongoDB for questionable verifications
        queue = await db.review_queue.find({}, {"_id": 0}).to_list(1000)
        return {"queue": queue, "count": len(queue)}
    except Exception as e:
        logging.error(f"Error fetching review queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/review/decision")
async def submit_review_decision(
    proof_id: str = Form(...),
    decision: str = Form(...),
    reviewer_id: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """Submit human reviewer decision"""
    try:
        if decision not in ['VERIFIED', 'REJECTED']:
            raise HTTPException(status_code=400, detail="Decision must be VERIFIED or REJECTED")
        
        review_record = {
            'proof_id': proof_id,
            'decision': decision,
            'reviewer_id': reviewer_id,
            'notes': notes,
            'timestamp': datetime.now().isoformat()
        }
        
        await db.review_decisions.insert_one(review_record)
        
        return {"status": "success", "message": "Review decision recorded"}
    except Exception as e:
        logging.error(f"Error submitting review decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()