"""
The actual document ingestion pipeline, run as a Celery task so it never
blocks the HTTP upload request. The logic lives in a plain function so it
can be unit-tested by calling it directly (bypassing the broker entirely) --
see tests/test_tasks.py.
"""
from app.api.routes.metrics import DOCUMENTS_FAILED, DOCUMENTS_INDEXED
from app.celery_app import celery_app
from app.config import get_settings
from app.models.schemas import DocumentStatus
from app.services.document_processor import chunk_text, extract_text
from app.services.dynamodb_service import DynamoDBService
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.services.s3_service import S3Service
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="process_document",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=2,
)
def process_document_task(self, doc_id: str, user_id: str, s3_key: str, filename: str) -> None:
    settings = get_settings()
    db = DynamoDBService()
    try:
        db.update_status(doc_id, DocumentStatus.PROCESSING)

        file_bytes = S3Service().download_file(s3_key)
        text = extract_text(filename, file_bytes)
        chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        if not chunks:
            raise ValueError("No extractable text found in this document.")

        embeddings = EmbeddingService().embed_batch(chunks)

        pinecone_service = PineconeService()
        pinecone_service.ensure_index_exists()
        chunk_ids = pinecone_service.upsert_chunks(doc_id, filename, chunks, embeddings, namespace=user_id)

        db.update_status(doc_id, DocumentStatus.INDEXED, chunk_count=len(chunks), chunk_ids=chunk_ids)
        DOCUMENTS_INDEXED.inc()
        logger.info("Indexed document %s (%d chunks) for user %s", doc_id, len(chunks), user_id)
    except Exception:
        logger.exception("Failed to process document %s", doc_id)
        db.update_status(doc_id, DocumentStatus.FAILED)
        DOCUMENTS_FAILED.inc()
        raise
