# Implementation Progress

Updated: 2026-09-04

## Current status

The repository has the initial FastAPI, PostgreSQL, Qdrant, embedding, classifier, and infrastructure scaffolding. The implementation is being advanced toward the preprocessing-first architecture in `Architecture.md`.

## Completed

- Documented the target architecture and V1 service boundaries.
- Defined preprocessing as the stage before context construction and the main LLM call.
- Preserved BGE-large-en plus Logistic Regression for intent classification.
- Defined `MemoryService` as the Mem0 adapter and normalized the memory LLM endpoint to port `8003`.
- Added this progress tracker and the project summary.

## Completed in this implementation pass

- Added typed environment settings and FastAPI lifespan resource wiring.
- Added SQLAlchemy session/repository helpers and extended messages with prompt and classifier metadata.
- Added Pydantic API schemas and the preprocessing/chat/document/memory service contracts.
- Registered health, readiness, user, chat, document, and memory routes.
- Implemented BGE embedding reuse and explicit Joblib classifier model loading.
- Implemented preprocessing-first `MemoryService` around Mem0; it receives only the current user prompt.
- Added Qdrant document and memory search/upsert/delete helpers.
- Implemented plain-text, Markdown, CSV, and JSON document ingestion, hashing, chunking, embedding, and indexing.
- Implemented context construction, prompt generation, OpenAI-compatible LLM clients, model routing, and `ChatOrchestrator`.
- Implemented deterministic intent-specific prompt templates driven by classifier outputs; prompt construction does not call another model.
- Fixed routing so all `coding.*` classifier labels use the coding LLM.
- Re-verified the live BGE plus `intent_classifier.pkl` path and corrected the default path to `Backend/models/intent_classifier.pkl`.
- Added `openai`, `mem0ai`, `sentence-transformers`, `email-validator`, and `python-multipart` dependencies.

## Next validation

- Compile every backend Python module. This has passed with `python -m compileall -q Backend/app`.
- Verify FastAPI can import and expose the root route without starting external services. The repository virtual environment can load the classifier artifact; full startup still requires the local databases and model endpoints.
- Run focused service tests with mocked classifier, Qdrant, Mem0, and LLM clients.
- Start PostgreSQL, Qdrant, and the three vLLM services for an end-to-end smoke test.

## Infrastructure prerequisites

- PostgreSQL on `localhost:5432`.
- Qdrant on `localhost:6333`.
- Coding vLLM on `localhost:8000`.
- General vLLM on `localhost:8001`.
- Memory vLLM on `localhost:8003`.
- `.env` values for `POSTGRES_URL`, `QDRANT_URL`, and the LLM URLs.
- Python dependencies from `Backend/requirements.txt`.

## Known limitations

- Authentication and authorization are not implemented; user IDs must not be trusted as identity in production.
- Database migrations are not yet configured; `create_all()` remains a development bootstrap.
- Mem0 and document parser packages may need to be installed depending on the selected deployment environment.
- The local model endpoints and databases are required for full chat, memory, and retrieval behavior.
