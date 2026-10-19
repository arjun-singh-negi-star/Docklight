"""Pydantic request/response models shared across the API."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    status: DocumentStatus
    chunk_count: int = 0
    uploaded_at: datetime
    size_bytes: int = 0


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: DocumentStatus
    message: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentMetadata]
    count: int


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=10)
    conversation_id: str | None = None


class SourceChunk(BaseModel):
    doc_id: str
    filename: str
    chunk_text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    conversation_id: str


class HealthComponent(BaseModel):
    name: str
    healthy: bool
    detail: str = ""


class HealthResponse(BaseModel):
    status: str
    components: list[HealthComponent]


# ---- Auth ----
class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
