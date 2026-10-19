from app.models.schemas import DocumentStatus
from app.services.dynamodb_service import DynamoDBService


def test_put_and_list_document(aws_mock):
    db = DynamoDBService()
    db.ensure_table_exists()
    db.put_document("doc1", "user1", "sample.txt", "users/user1/documents/doc1/sample.txt", 100)

    docs = db.list_documents("user1")
    assert len(docs) == 1
    assert docs[0].doc_id == "doc1"
    assert docs[0].status == DocumentStatus.UPLOADED


def test_update_status_and_delete(aws_mock):
    db = DynamoDBService()
    db.ensure_table_exists()
    db.put_document("doc1", "user1", "sample.txt", "key1", 100)

    db.update_status("doc1", DocumentStatus.INDEXED, chunk_count=3, chunk_ids=["a", "b", "c"])
    doc = db.get_document("doc1")
    assert doc["status"] == DocumentStatus.INDEXED.value
    assert doc["chunk_count"] == 3
    assert list(doc["chunk_ids"]) == ["a", "b", "c"]

    db.delete_document("doc1")
    assert db.get_document("doc1") is None


def test_list_documents_is_scoped_per_user(aws_mock):
    db = DynamoDBService()
    db.ensure_table_exists()
    db.put_document("doc1", "userA", "a.txt", "keyA", 10)
    db.put_document("doc2", "userB", "b.txt", "keyB", 20)

    assert [d.doc_id for d in db.list_documents("userA")] == ["doc1"]
    assert [d.doc_id for d in db.list_documents("userB")] == ["doc2"]
