from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from settings import MONGO_URL, DB_NAME, CORS_OROGINS, API_NAME
from utils.logger import get_logger

from routes.status import router as status_router
from routes.ingest import router as ingest_router
from routes.review import router as review_router
from routes.system import router as system_router

logger = get_logger(__name__)

app = FastAPI(title=API_NAME)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_OROGINS.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_router, prefix="/api/status", tags=["Status"])
app.include_router(ingest_router, prefix="/api/ingest", tags=["Ingest"])
app.include_router(review_router, prefix="/api/review", tags=["Review"])
app.include_router(system_router, prefix="/api/system", tags=["System"])

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
