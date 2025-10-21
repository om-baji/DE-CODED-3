# DE-CODED-3 — Proof Verification API

A FastAPI-based verification service for ingesting complaints and proofs (before/after images), running an automated verification pipeline (embedding, pHash, chunking, VLM analysis, scoring) and providing review/status routes and system operations.

## Quick Links (open files / symbols)
- Main app: [main.py](main.py) — [`main.app`](main.py)  
- Configuration: [settings.py](settings.py) — [`settings`](settings.py)  
- Project metadata: [pyproject.toml](pyproject.toml)  
- Start script: [Makefile](Makefile)

Routes
- Ingest endpoints: [routes/ingest.py](routes/ingest.py) — [`routes.ingest.router`](routes/ingest.py)  
- Review endpoints: [routes/review.py](routes/review.py) — [`routes.review.router`](routes/review.py)  
- Status endpoints: [routes/status.py](routes/status.py) — [`routes.status.router`](routes/status.py)  
- System endpoints: [routes/system.py](routes/system.py) — [`routes.system.router`](routes/system.py)

Core libraries and services
- Verification pipeline: [lib/verification_pipeline.py](lib/verification_pipeline.py) — [`lib.verification_pipeline.VerificationPipeline`](lib/verification_pipeline.py) / instance [`lib.verification_pipeline.verification_pipeline`](lib/verification_pipeline.py)  
- Image processing: [lib/image_processor.py](lib/image_processor.py) — [`lib.image_processor.image_processor`](lib/image_processor.py)  
- Manipulation detection: [lib/manipulation_detector.py](lib/manipulation_detector.py) — [`lib.manipulation_detector.manipulation_detector`](lib/manipulation_detector.py)  
- VLM verifier: [lib/vlm_verifier.py](lib/vlm_verifier.py) — [`lib.vlm_verifier.vlm_verifier`](lib/vlm_verifier.py)  
- Embedding service: [services/embedding.py](services/embedding.py) — [`services.embedding.embedding_service`](services/embedding.py)  
- Scoring engine: [services/scoring.py](services/scoring.py) — [`services.scoring.scoring_engine`](services/scoring.py)

Database integrations
- Pinecone manager: [database/pinecone.py](database/pinecone.py) — [`database.pinecone.pinecone_manager`](database/pinecone.py)  
- Mongo manager: [database/mongo.py](database/mongo.py) — [`database.mongo.mongo_manager`](database/mongo.py)  
- Pydantic models: [database/schema/models.py](database/schema/models.py)

Utilities & tests
- Logger: [utils/logger.py](utils/logger.py) — [`utils.logger.get_logger`](utils/logger.py)  
- Unit tests: [tests/unit.py](tests/unit.py)

---

## Features
- Ingest complaint (before image) and proof (after image) endpoints with automatic chunking, thumbnailing, embedding and indexing. See [routes/ingest.py](routes/ingest.py) and the pipeline [`lib.verification_pipeline.ingest_complaint`](lib/verification_pipeline.py) / [`lib.verification_pipeline.ingest_proof`](lib/verification_pipeline.py).
- Review queue and decision submission endpoints in [routes/review.py](routes/review.py).
- Status checks stored via MongoDB in [routes/status.py](routes/status.py) and models in [database/schema/models.py](database/schema/models.py).
- System initialization for Pinecone indexes: [routes/system.py](routes/system.py).
- Detection & verification components:
  - Image processing & similarity: [lib/image_processor.py](lib/image_processor.py)
  - Manipulation detector (ELA + CNN): [lib/manipulation_detector.py](lib/manipulation_detector.py)
  - Vision-Language Model orchestration: [lib/vlm_verifier.py](lib/vlm_verifier.py)
  - Scoring/decision logic: [services/scoring.py](services/scoring.py)
  - Embedding utilities: [services/embedding.py](services/embedding.py)

---

## Requirements & Environment

- Python >= 3.12 (see [.python-version](.python-version))
- Install dependencies from [pyproject.toml](pyproject.toml) (uses poetry/PEP 621 format). Example with pip:
  - pip install -r <(python -c "import tomllib,sys; print('\\n'.join([d.strip('\"') for d in tomllib.loads(open('pyproject.toml','rb').read())['project']['dependencies']]))")

Environment variables (see [settings.py](settings.py)):
- OPENAI_API_KEY — required by VLM/embedding components ([lib/vlm_verifier.py](lib/vlm_verifier.py), [services/embedding.py](services/embedding.py))
- PINECONE_API_KEY — required by Pinecone manager ([database/pinecone.py](database/pinecone.py))
- MONGO_URL — MongoDB connection string used by [`database.mongo.MongoManager`](database/mongo.py)
- DB_NAME — MongoDB database name (defaults in [settings.py](settings.py))

Create a `.env` file in the project root with values:
- OPENAI_API_KEY=...
- PINECONE_API_KEY=...
- MONGO_URL=mongodb://localhost:27017
- DB_NAME=decoded3

---

## Running locally

1. Start MongoDB (or set MONGO_URL to a running instance).  
2. Ensure Pinecone keys / indexes exist or mock pinecone calls for local testing. See [`database.pinecone.PineconeManager.initialize_indexes`](database/pinecone.py).  
3. Run the app:
   - Using Makefile: make start (runs `uvicorn main:app --port 8000`) or
   - Direct: uvicorn main:app --reload --port 8000

API base paths are prefixed in [main.py](main.py):
- Status: /api/status -> implemented in [routes/status.py](routes/status.py)
- Ingest: /api/ingest -> implemented in [routes/ingest.py](routes/ingest.py)
- Review: /api/review -> implemented in [routes/review.py](routes/review.py)
- System: /api/system -> implemented in [routes/system.py](routes/system.py)

Example endpoints:
- POST /api/ingest/complaint — form data + file (see [routes/ingest.py](routes/ingest.py))
- POST /api/ingest/proof — form data + file (see [routes/ingest.py](routes/ingest.py))
- GET /api/review/queue — review queue (see [routes/review.py](routes/review.py))
- POST /api/review/decision — form submission (see [routes/review.py](routes/review.py))
- POST /api/status/ — create status (see [routes/status.py](routes/status.py))
- GET /api/status/ — list status checks (see [routes/status.py](routes/status.py))
- POST /api/system/initialize — initialize Pinecone index checks (see [routes/system.py](routes/system.py))

---

## Testing

Unit tests are located at [tests/unit.py](tests/unit.py) and use FastAPI's TestClient to exercise the routes. The test client imports the app from [main.py](main.py) (`main.app`).

Run tests:
- pytest -q
- pytest tests/unit.py -q

Notes:
- Tests in [tests/unit.py](tests/unit.py) assume a running app and may expect database/pinecone to be available. For reliable CI you should mock:
  - [`database.mongo.mongo_manager`](database/mongo.py)
  - [`database.pinecone.pinecone_manager`](database/pinecone.py)
  - External services like OpenAI via mocking [`lib.vlm_verifier.VLMVerifier`](lib/vlm_verifier.py) and [`services.embedding.EmbeddingService`](services/embedding.py)

---

## Development tips

- Logging: use [`utils.logger.get_logger`](utils/logger.py) for colored, consistent logging across modules.
- Chunking & storage: chunk logic in [`lib.image_processor.ImageProcessor.chunk_image`](lib/image_processor.py) and Pinecone writes happen in [`lib.verification_pipeline.VerificationPipeline`](lib/verification_pipeline.py).
- Scoring & decisions: tweak thresholds or weights in [`services.scoring.ScoringEngine`](services/scoring.py).
- If you need to run parts of the verification pipeline without external services, call the components directly:
  - Embeddings: [`services.embedding.embedding_service.get_clip_embedding`](services/embedding.py)
  - Image similarity: [`lib.image_processor.image_processor.compute_image_similarity`](lib/image_processor.py)
  - Manipulation detection: [`lib.manipulation_detector.manipulation_detector.detect_manipulation`](lib/manipulation_detector.py)
  - Scoring: [`services.scoring.scoring_engine.compute_composite_score`](services/scoring.py)

---

## Troubleshooting

- "Failed to load .env!" — ensure `.env` exists and `python-dotenv` can read it ([settings.py](settings.py)).
- Pinecone errors — ensure `PINECONE_API_KEY` and indexes are present or mock [`database.pinecone.PineconeManager`](database/pinecone.py).
- MongoDB connection issues — check `MONGO_URL` and that MongoDB is running.

---

## Contributing

- Follow the existing module boundaries (routes -> lib -> services -> database).  
- Add unit tests to [tests/unit.py](tests/unit.py) or create new test modules under `tests/`.  
- Keep environment secrets out of the repo — use `.env` and add sensitive files to `.gitignore` (already configured).

---

## File map (high level)
- [main.py](main.py)  
- [settings.py](settings.py)  
- [pyproject.toml](pyproject.toml)  
- [Makefile](Makefile)  
- routes/: [routes/ingest.py](routes/ingest.py), [routes/review.py](routes/review.py), [routes/status.py](routes/status.py), [routes/system.py](routes/system.py)  
- lib/: [lib/verification_pipeline.py](lib/verification_pipeline.py), [lib/image_processor.py](lib/image_processor.py), [lib/manipulation_detector.py](lib/manipulation_detector.py), [lib/vlm_verifier.py](lib/vlm_verifier.py)  
- services/: [services/embedding.py](services/embedding.py), [services/scoring.py](services/scoring.py)  
- database/: [database/mongo.py](database/mongo.py), [database/pinecone.py](database/pinecone.py), [database/schema/models.py](database/schema/models.py)  
- utils/: [utils/logger.py](utils/logger.py)  
- tests/: [tests/unit.py](tests/unit.py)

---