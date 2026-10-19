"""Stores and retrieves the raw uploaded files in Amazon S3, namespaced per user."""
from app.config import get_settings
from app.services.aws_clients import get_s3_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class S3Service:
    def __init__(self):
        self.settings = get_settings()
        self.client = get_s3_client()
        self.bucket = self.settings.S3_BUCKET_NAME

    def ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            logger.info("Bucket %s not found, creating it.", self.bucket)
            if self.settings.AWS_REGION == "us-east-1":
                self.client.create_bucket(Bucket=self.bucket)
            else:
                self.client.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={"LocationConstraint": self.settings.AWS_REGION},
                )

    def upload_file(self, file_bytes: bytes, user_id: str, doc_id: str, filename: str) -> str:
        key = f"users/{user_id}/documents/{doc_id}/{filename}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=file_bytes)
        return key

    def download_file(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete_file(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
