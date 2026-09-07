from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    mail_id: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class UserResponse(UserCreate):
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class ChatCreate(BaseModel):
    user_id: int
    chat_name: str | None = Field(default=None, max_length=255)


class ChatResponse(BaseModel):
    chat_id: int
    user_id: int
    chat_name: str | None


class ChatMessageRequest(BaseModel):
    user_id: int
    content: str = Field(min_length=1)
    document_ids: list[int] = Field(default_factory=list)
    include_memories: bool = True
    history_limit: int = Field(default=12, ge=0, le=50)


class MessageResponse(BaseModel):
    message_id: int
    chat_id: int
    content: str
    intent: str
    confidence: float = Field(ge=0, le=1)
    model_name: str
    created_at: datetime


class ClassificationResponse(BaseModel):
    intent: str
    confidence: float = Field(ge=0, le=1)


class DocumentResponse(BaseModel):
    doc_id: int
    file_name: str
    file_type: str
    file_size: int
    file_hash: str
    uploaded_at: datetime
    status: str = "indexed"


class DocumentSearchResult(BaseModel):
    doc_id: int
    chunk_id: str
    text: str
    score: float


class MemoryRecord(BaseModel):
    memory_id: str
    user_id: int
    text: str
    memory_type: str = "general"
    score: float | None = None
    created_at: datetime | None = None


class MemorySearchRequest(BaseModel):
    user_id: int
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class ErrorResponse(BaseModel):
    detail: str
    code: str
    request_id: str | None = None
