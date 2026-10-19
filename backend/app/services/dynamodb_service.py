"""
Tracks document metadata (owner, filename, status, chunk count, and the exact
Pinecone vector ids created for it) in DynamoDB. Storing vector ids here
means deletion always removes the right vectors by id, regardless of which
Pinecone plan/index type is used. A GSI on user_id lets "list my documents"
run as a cheap indexed query instead of a full table scan.
"""
from datetime import datetime, timezone

from app.config import get_settings
from app.models.schemas import DocumentMetadata, DocumentStatus
from app.services.aws_clients import get_dynamodb_resource
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DynamoDBService:
    def __init__(self):
        self.settings = get_settings()
        self.resource = get_dynamodb_resource()
        self.table_name = self.settings.DYNAMODB_TABLE_NAME

    @property
    def table(self):
        return self.resource.Table(self.table_name)

    def ensure_table_exists(self) -> None:
        existing = [t.name for t in self.resource.tables.all()]
        if self.table_name in existing:
            return
        logger.info("Table %s not found, creating it.", self.table_name)
        table = self.resource.create_table(
            TableName=self.table_name,
            KeySchema=[{"AttributeName": "doc_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "doc_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "user_id-index",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

    def put_document(self, doc_id: str, user_id: str, filename: str, s3_key: str, size_bytes: int) -> dict:
        item = {
            "doc_id": doc_id,
            "user_id": user_id,
            "filename": filename,
            "s3_key": s3_key,
            "status": DocumentStatus.UPLOADED.value,
            "chunk_count": 0,
            "chunk_ids": [],
            "size_bytes": size_bytes,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        self.table.put_item(Item=item)
        return item

    def update_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        chunk_count: int | None = None,
        chunk_ids: list[str] | None = None,
    ) -> None:
        expr_parts = ["#s = :s"]
        values: dict = {":s": status.value}
        names = {"#s": "status"}
        if chunk_count is not None:
            expr_parts.append("chunk_count = :c")
            values[":c"] = chunk_count
        if chunk_ids is not None:
            expr_parts.append("chunk_ids = :ci")
            values[":ci"] = chunk_ids
        self.table.update_item(
            Key={"doc_id": doc_id},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeValues=values,
            ExpressionAttributeNames=names,
        )

    def get_document(self, doc_id: str) -> dict | None:
        response = self.table.get_item(Key={"doc_id": doc_id})
        return response.get("Item")

    def list_documents(self, user_id: str) -> list[DocumentMetadata]:
        response = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression="user_id = :u",
            ExpressionAttributeValues={":u": user_id},
        )
        items = response.get("Items", [])
        return [
            DocumentMetadata(
                doc_id=i["doc_id"],
                filename=i["filename"],
                status=i["status"],
                chunk_count=int(i.get("chunk_count", 0)),
                uploaded_at=i["uploaded_at"],
                size_bytes=int(i.get("size_bytes", 0)),
            )
            for i in items
        ]

    def delete_document(self, doc_id: str) -> None:
        self.table.delete_item(Key={"doc_id": doc_id})
