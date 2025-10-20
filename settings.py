from dotenv import load_dotenv
import os

_flag = load_dotenv()

if not _flag:
    raise Exception("Failed to load .env!")

API_NAME = "RAG Agent 3 - Proof Verification API"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "decoded3")
CORS_OROGINS = os.getenv("CORS_ORIGINS", "*")
