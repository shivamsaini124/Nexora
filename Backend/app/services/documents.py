import hashlib
from pathlib import Path

from qdrant_client.models import PointStruct

from ..db.qdrant import delete_document_points, search_documents, upsert_points
from ..db.postgres_models import Document
from ..repositories import DocumentRepository
from ..schemas import DocumentResponse, DocumentSearchResult


class DocumentService:
    def __init__(self, session, qdrant, embeddings, repository: DocumentRepository):
        self.session = session
        self.qdrant = qdrant
        self.embeddings = embeddings
        self.repository = repository

    async def ingest(self, user_id: int, chat_id: int | None, upload) -> DocumentResponse:
        content = await upload.read()
        file_hash = hashlib.sha256(content).hexdigest()
        existing = self.repository.by_hash(self.session, file_hash)
        if existing:
            return self._response(existing)
        text = self.parse(upload.filename or "document.txt", upload.content_type, content)
        chunks = self.chunk(text, 1800, 200)
        if not chunks:
            raise ValueError("Document does not contain readable text")
        document = self.repository.create(
            self.session,
            Document(
                fileName=upload.filename or "document.txt",
                fileType=upload.content_type or "text/plain",
                fileSize=len(content),
                fileHash=file_hash,
            ),
        )
        vectors = self.embeddings.embed_many(chunks)
        points = [
            PointStruct(
                id=f"document:{document.docId}:chunk:{index}",
                vector=vector,
                payload={
                    "doc_id": document.docId,
                    "chunk_id": f"{document.docId}:{index}",
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "file_name": document.fileName,
                    "text": chunk,
                    "chunk_index": index,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        upsert_points(self.qdrant, "documents", points)
        self.session.commit()
        return self._response(document)

    def parse(self, file_name: str, file_type: str | None, content: bytes) -> str:
        extension = Path(file_name).suffix.lower()
        if extension not in {".txt", ".md", ".csv", ".json"} and file_type not in {
            "text/plain",
            "text/markdown",
            "application/json",
            "text/csv",
        }:
            raise ValueError("Only text, Markdown, CSV, and JSON documents are supported")
        return content.decode("utf-8", errors="replace").strip()

    def chunk(self, text: str, max_chars: int = 1800, overlap: int = 200) -> list[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = max(0, end - overlap)
        return chunks

    async def delete(self, document_id: int) -> None:
        document = self.repository.get(self.session, document_id)
        if document is None:
            raise LookupError("Document not found")
        delete_document_points(self.qdrant, document_id)
        self.repository.delete(self.session, document)
        self.session.commit()

    @staticmethod
    def _response(document: Document) -> DocumentResponse:
        return DocumentResponse(
            doc_id=document.docId,
            file_name=document.fileName,
            file_type=document.fileType,
            file_size=document.fileSize,
            file_hash=document.fileHash,
            uploaded_at=document.uploadedAt,
        )


class DocumentSearchService:
    def __init__(self, qdrant, embeddings):
        self.qdrant = qdrant
        self.embeddings = embeddings

    async def search(
        self,
        user_id: int,
        query: str,
        document_ids: list[int],
        limit: int,
    ) -> list[DocumentSearchResult]:
        vector = self.embeddings.embed(query)
        hits = search_documents(self.qdrant, vector, user_id, document_ids, limit)
        return [
            DocumentSearchResult(
                doc_id=int(hit.payload["doc_id"]),
                chunk_id=str(hit.payload["chunk_id"]),
                text=str(hit.payload["text"]),
                score=float(hit.score),
            )
            for hit in hits
        ]
