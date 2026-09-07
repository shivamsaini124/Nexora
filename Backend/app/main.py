from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import load_settings
from .db.postgres import Postgres
from .db.postgres_models import Base
from .db.qdrant import connectQdrant
from .repositories import ChatRepository, DocumentRepository
from .routes import router
from .services.chat import ChatOrchestrator, ConversationService
from .services.classifier import Classifier
from .services.context import ContextBuilder
from .services.documents import DocumentSearchService, DocumentService
from .services.embedding import EmbeddingService
from .services.llm import LLMClient, ModelRouter
from .services.memory import MemoryService
from .services.prompts import PromptGenerator


def create_mem0(settings):
    try:
        from mem0 import Memory
    except ImportError:
        return None
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "openai_base_url": settings.memory_llm_url,
                "api_key": settings.llm_api_key,
                "temperature": 0.1,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": settings.embedding_model_name,
                "embedding_dims": settings.embedding_dimension,
                "model_kwargs": {"device": "cpu"},
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": settings.memory_collection,
                "host": "localhost",
                "port": 6333,
                "embedding_model_dims": settings.embedding_dimension,
            },
        },
    }
    return Memory.from_config(config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    postgres = Postgres(settings.postgres_url, Base)
    qdrant = connectQdrant(settings.qdrant_url)
    embeddings = EmbeddingService(settings.embedding_model_name)
    classifier = Classifier(settings.classifier_model_path, embeddings.model)
    memory_service = MemoryService(create_mem0(settings))
    coding_client = LLMClient(
        settings.coding_llm_url,
        settings.llm_api_key,
        "Qwen/Qwen2.5-Coder-0.5B-Instruct-GPTQ-Int4",
    )
    general_client = LLMClient(
        settings.general_llm_url,
        settings.llm_api_key,
        "JunHowie/Qwen3-0.6B-GPTQ-Int4",
    )
    model_router = ModelRouter(coding_client, general_client)
    app.state.settings = settings
    app.state.postgres = postgres
    app.state.qdrant = qdrant
    app.state.encoder = embeddings
    app.state.classifier = classifier
    app.state.memory_service = memory_service
    app.state.chat_service = lambda session: build_chat_service(
        session, app, model_router
    )
    app.state.document_service = lambda session: DocumentService(
        session, qdrant, embeddings, DocumentRepository()
    )
    yield
    await coding_client.close()
    await general_client.close()
    qdrant.close()
    postgres.dispose()


def build_chat_service(session, app: FastAPI, model_router: ModelRouter):
    conversation = ConversationService(session, ChatRepository())
    documents = DocumentSearchService(app.state.qdrant, app.state.encoder)
    context = ContextBuilder(conversation, app.state.memory_service, documents)
    return ChatOrchestrator(
        app.state.classifier,
        app.state.memory_service,
        context,
        PromptGenerator(),
        model_router,
        conversation,
    )


app = FastAPI(title="Private Local AI Backend", lifespan=lifespan)
app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Backend is running"}
