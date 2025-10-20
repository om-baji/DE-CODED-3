from fastapi import APIRouter, HTTPException
from database.pinecone import pinecone_manager
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/initialize")
async def initialize_system():
    try:
        pinecone_manager.initialize_indexes()
        return {"status": "success", "message": "Pinecone indexes initialized"}
    except Exception as e:
        logger.error(f"initialize_system failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
