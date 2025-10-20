from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from utils.logger import get_logger
from lib.verification_pipeline import verification_pipeline
from database.schema.models import ComplaintIngestResponse, ProofIngestResponse

logger = get_logger(__name__)
router = APIRouter()

@router.post("/complaint", response_model=ComplaintIngestResponse)
async def ingest_complaint(
    complaint_id: str = Form(...),
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: str = Form(...),
    issue_type: str = Form("general"),
):
    try:
        image_bytes = await image.read()
        result = await verification_pipeline.ingest_complaint(
            complaint_id=complaint_id,
            image_bytes=image_bytes,
            lat=latitude,
            lon=longitude,
            ts_iso=timestamp,
            metadata={"issue_type": issue_type},
        )
        return ComplaintIngestResponse(**result)
    except Exception as e:
        logger.error(f"ingest_complaint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proof", response_model=ProofIngestResponse)
async def ingest_proof(
    proof_id: str = Form(...),
    complaint_id: str = Form(...),
    worker_id: str = Form(...),
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: str = Form(...),
):
    try:
        image_bytes = await image.read()
        result = await verification_pipeline.ingest_proof(
            proof_id=proof_id,
            complaint_id=complaint_id,
            worker_id=worker_id,
            image_bytes=image_bytes,
            lat=latitude,
            lon=longitude,
            ts_iso=timestamp,
        )
        return ProofIngestResponse(**result)
    except Exception as e:
        logger.error(f"ingest_proof failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
