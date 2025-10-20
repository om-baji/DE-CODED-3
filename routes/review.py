from fastapi import APIRouter, Form, HTTPException
from datetime import datetime
from database.mongo import mongo_manager
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/queue")
async def get_review_queue():
    try:
        queue = await mongo_manager.db.review_queue.find({}, {"_id": 0}).to_list(1000)
        return {"queue": queue, "count": len(queue)}
    except Exception as e:
        logger.error(f"get_review_queue failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/decision")
async def submit_review_decision(
    proof_id: str = Form(...),
    decision: str = Form(...),
    reviewer_id: str = Form(...),
    notes: str | None = Form(None),
):
    try:
        if decision not in ["VERIFIED", "REJECTED"]:
            raise HTTPException(status_code=400, detail="Invalid decision")
        record = {
            "proof_id": proof_id,
            "decision": decision,
            "reviewer_id": reviewer_id,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        await mongo_manager.db.review_decisions.insert_one(record)
        return {"status": "success", "message": "Review decision recorded"}
    except Exception as e:
        logger.error(f"submit_review_decision failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
