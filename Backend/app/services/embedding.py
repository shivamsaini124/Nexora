from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-large-en"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        vector = self.model.encode([text], normalize_embeddings=True)[0]
        return vector.tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

def load_embedding_model() -> SentenceTransformer:
    return SentenceTransformer("BAAI/bge-large-en")
