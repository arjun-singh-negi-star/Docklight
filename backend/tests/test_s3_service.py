from app.services.s3_service import S3Service


def test_upload_and_download_file(aws_mock):
    s3 = S3Service()
    s3.ensure_bucket_exists()
    key = s3.upload_file(b"hello world", "user1", "doc1", "hello.txt")
    assert key == "users/user1/documents/doc1/hello.txt"
    assert s3.download_file(key) == b"hello world"


def test_delete_file_is_idempotent(aws_mock):
    s3 = S3Service()
    s3.ensure_bucket_exists()
    key = s3.upload_file(b"data", "user1", "doc2", "note.txt")
    s3.delete_file(key)
    s3.delete_file(key)  # should not raise
