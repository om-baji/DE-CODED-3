from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
import uuid

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