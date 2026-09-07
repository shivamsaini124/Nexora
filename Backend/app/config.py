import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    postgres_url: str
    qdrant_url: str
    coding_llm_url: str
    general_llm_url: str
    memory_llm_url: str
    llm_api_key: str
    classifier_model_path: str
    embedding_model_name: str
    embedding_dimension: int
    memory_collection: str = "memories"
    document_collection: str = "documents"


def load_settings() -> Settings:
    backend_root = Path(__file__).resolve().parents[1]
    classifier_path = os.getenv(
        "CLASSIFIER_MODEL_PATH",
        str(backend_root / "models" / "intent_classifier.pkl"),
    )
    return Settings(
        postgres_url=os.getenv(
            "POSTGRES_URL",
            "postgresql+psycopg2://app:app_password@localhost:5432/project_db",
        ),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        coding_llm_url=os.getenv("CODING_LLM_URL", "http://localhost:8000/v1"),
        general_llm_url=os.getenv("GENERAL_LLM_URL", "http://localhost:8001/v1"),
        memory_llm_url=os.getenv("MEMORY_LLM_URL", "http://localhost:8003/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", "local"),
        classifier_model_path=classifier_path,
        embedding_model_name=os.getenv(
            "EMBEDDING_MODEL_NAME", "BAAI/bge-large-en"
        ),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")),
    )
