from fastapi import APIRouter, HTTPException
from datetime import datetime
from database.mongo import mongo_manager
from database.schema.models import StatusCheck, StatusCheckCreate
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    try:
        status_obj = StatusCheck(**input.model_dump())
        await mongo_manager.db.status_checks.insert_one(status_obj.model_dump())
        return status_obj
    except Exception as e:
        logger.error(f"create_status_check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=list[StatusCheck])
async def get_status_checks():
    try:
        records = await mongo_manager.db.status_checks.find({}, {"_id": 0}).to_list(1000)
        for r in records:
            if isinstance(r.get("timestamp"), str):
                r["timestamp"] = datetime.fromisoformat(r["timestamp"])
        return records
    except Exception as e:
        logger.error(f"get_status_checks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
