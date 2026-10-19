"""Per-user accounts, stored in DynamoDB. Backs signup/login and multi-tenancy."""
import uuid

from botocore.exceptions import ClientError

from app.auth.security import hash_password, verify_password
from app.config import get_settings
from app.services.aws_clients import get_dynamodb_resource


class UserService:
    def __init__(self):
        self.settings = get_settings()
        self.resource = get_dynamodb_resource()
        self.table_name = self.settings.USERS_TABLE_NAME

    @property
    def table(self):
        return self.resource.Table(self.table_name)

    def ensure_table_exists(self) -> None:
        existing = [t.name for t in self.resource.tables.all()]
        if self.table_name in existing:
            return
        table = self.resource.create_table(
            TableName=self.table_name,
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "email-index",
                    "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

    def get_by_email(self, email: str) -> dict | None:
        response = self.table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :e",
            ExpressionAttributeValues={":e": email},
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def get_by_id(self, user_id: str) -> dict | None:
        try:
            response = self.table.get_item(Key={"user_id": user_id})
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                # Table doesn't exist (e.g. freshly restarted LocalStack): unknown user -> 401, not a 500.
                return None
            raise
        return response.get("Item")

    def create_user(self, email: str, password: str) -> dict:
        self.ensure_table_exists()
        if self.get_by_email(email):
            raise ValueError("An account with this email already exists.")
        user_id = uuid.uuid4().hex[:16]
        item = {"user_id": user_id, "email": email, "password_hash": hash_password(password)}
        self.table.put_item(Item=item)
        return item

    def authenticate(self, email: str, password: str) -> dict | None:
        self.ensure_table_exists()
        user = self.get_by_email(email)
        if not user or not verify_password(password, user["password_hash"]):
            return None
        return user
