import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.dependencies import get_current_user
from app.models.schemas import DocumentListResponse, DocumentStatus, UploadResponse
from app.services.dynamodb_service import DynamoDBService
from app.services.pinecone_service import PineconeService
from app.services.s3_service import S3Service
from app.tasks import process_document_task
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = get_logger(__name__)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Stores the raw file in S3 and a metadata row in DynamoDB, then hands off
    to a Celery worker for extraction/chunking/embedding/indexing. Returns
    immediately -- the client polls GET /api/documents to see status move
    UPLOADED -> PROCESSING -> INDEXED (or FAILED).
    """
    user_id = current_user["user_id"]
    s3 = S3Service()
    db = DynamoDBService()

    file_bytes = await file.read()
    doc_id = uuid.uuid4().hex[:12]

    s3.ensure_bucket_exists()
    s3_key = s3.upload_file(file_bytes, user_id, doc_id, file.filename)
    db.ensure_table_exists()
    db.put_document(doc_id, user_id, file.filename, s3_key, len(file_bytes))

    process_document_task.delay(doc_id, user_id, s3_key, file.filename)

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        status=DocumentStatus.UPLOADED,
        message="Queued for background processing.",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(current_user: dict = Depends(get_current_user)):
    db = DynamoDBService()
    db.ensure_table_exists()
    docs = db.list_documents(current_user["user_id"])
    return DocumentListResponse(documents=docs, count=len(docs))


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    db = DynamoDBService()
    doc = db.get_document(doc_id)
    if not doc or doc.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Document not found.")

    S3Service().delete_file(doc["s3_key"])
    PineconeService().delete_by_ids(doc.get("chunk_ids", []), namespace=current_user["user_id"])
    db.delete_document(doc_id)
    return {"message": f"Document {doc_id} deleted."}
