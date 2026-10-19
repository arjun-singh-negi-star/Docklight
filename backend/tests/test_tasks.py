from unittest.mock import patch

from app.models.schemas import DocumentStatus
from app.services.dynamodb_service import DynamoDBService
from app.services.s3_service import S3Service
from app.tasks import process_document_task


@patch("app.tasks.PineconeService")
@patch("app.tasks.EmbeddingService")
def test_process_document_task_success(mock_embed_cls, mock_pinecone_cls, aws_mock):
    db = DynamoDBService()
    db.ensure_table_exists()
    s3 = S3Service()
    s3.ensure_bucket_exists()

    key = s3.upload_file(b"Refunds are processed within 14 days.", "user1", "doc1", "policy.txt")
    db.put_document("doc1", "user1", "policy.txt", key, 40)

    mock_embed_cls.return_value.embed_batch.return_value = [[0.1] * 8]
    mock_pinecone_cls.return_value.upsert_chunks.return_value = ["doc1::chunk-0"]

    process_document_task(doc_id="doc1", user_id="user1", s3_key=key, filename="policy.txt")

    doc = db.get_document("doc1")
    assert doc["status"] == DocumentStatus.INDEXED.value
    assert doc["chunk_count"] == 1
    mock_pinecone_cls.return_value.upsert_chunks.assert_called_once()
    assert mock_pinecone_cls.return_value.upsert_chunks.call_args.kwargs["namespace"] == "user1"


@patch("app.tasks.EmbeddingService")
def test_process_document_task_marks_failed_on_empty_text(mock_embed_cls, aws_mock):
    db = DynamoDBService()
    db.ensure_table_exists()
    s3 = S3Service()
    s3.ensure_bucket_exists()

    key = s3.upload_file(b"   ", "user1", "doc2", "empty.txt")
    db.put_document("doc2", "user1", "empty.txt", key, 3)

    try:
        process_document_task(doc_id="doc2", user_id="user1", s3_key=key, filename="empty.txt")
    except Exception:
        pass  # autoretry re-raises after exhausting retries; we only care about the DB status

    doc = db.get_document("doc2")
    assert doc["status"] == DocumentStatus.FAILED.value
