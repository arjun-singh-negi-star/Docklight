"""
Multi-turn chat memory, stored in DynamoDB. Each conversation is one item
with an append-only list of {role, content, ts} turns, so the LLM can be
given recent history for follow-up questions like "what about last month?".
"""
import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.services.aws_clients import get_dynamodb_resource


class ConversationService:
    def __init__(self):
        self.settings = get_settings()
        self.resource = get_dynamodb_resource()
        self.table_name = self.settings.CONVERSATIONS_TABLE_NAME

    @property
    def table(self):
        return self.resource.Table(self.table_name)

    def ensure_table_exists(self) -> None:
        existing = [t.name for t in self.resource.tables.all()]
        if self.table_name in existing:
            return
        table = self.resource.create_table(
            TableName=self.table_name,
            KeySchema=[{"AttributeName": "conversation_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "conversation_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

    def create_conversation(self, user_id: str) -> str:
        self.ensure_table_exists()
        conversation_id = uuid.uuid4().hex[:16]
        self.table.put_item(
            Item={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "turns": [],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return conversation_id

    def append_turn(self, conversation_id: str, role: str, content: str) -> None:
        self.ensure_table_exists()
        turn = {"role": role, "content": content, "ts": datetime.now(timezone.utc).isoformat()}
        self.table.update_item(
            Key={"conversation_id": conversation_id},
            UpdateExpression="SET turns = list_append(if_not_exists(turns, :empty), :t), updated_at = :u",
            ExpressionAttributeValues={":t": [turn], ":u": turn["ts"], ":empty": []},
        )

    def get_recent_turns(self, conversation_id: str, limit: int) -> list[dict]:
        self.ensure_table_exists()
        response = self.table.get_item(Key={"conversation_id": conversation_id})
        item = response.get("Item")
        if not item:
            return []
        turns = item.get("turns", [])
        recent = turns[-limit:] if limit else turns
        return [{"role": t["role"], "content": t["content"]} for t in recent]
