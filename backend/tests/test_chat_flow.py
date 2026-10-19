from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.main import app
from app.services.user_service import UserService

client = TestClient(app)


@patch("app.api.routes.chat.LLMService")
@patch("app.api.routes.chat.PineconeService")
@patch("app.api.routes.chat.EmbeddingService")
def test_chat_query_end_to_end(mock_embed_cls, mock_pinecone_cls, mock_llm_cls, aws_mock, fake_redis):
    user_service = UserService()
    user = user_service.create_user("testuser@example.com", "password123")
    token = create_access_token(user["user_id"])
    headers = {"Authorization": f"Bearer {token}"}

    mock_embed_cls.return_value.embed_text.return_value = [0.1] * 8
    mock_pinecone_cls.return_value.query.return_value = [
        {"score": 0.9, "metadata": {"doc_id": "d1", "filename": "policy.txt", "chunk_text": "Refunds within 14 days."}}
    ]
    mock_llm_cls.return_value.generate_answer.return_value = "Refunds are processed within 14 days (Source 1)."

    resp = client.post("/api/chat/query", json={"question": "What is the refund window?"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "14 days" in data["answer"]
    assert data["sources"][0]["filename"] == "policy.txt"
    assert data["conversation_id"]


@patch("app.api.routes.chat.LLMService")
@patch("app.api.routes.chat.PineconeService")
@patch("app.api.routes.chat.EmbeddingService")
def test_chat_query_with_no_matches_still_asks_llm_so_reply_is_in_users_language(
    mock_embed_cls, mock_pinecone_cls, mock_llm_cls, aws_mock, fake_redis
):
    user = UserService().create_user("testuser@example.com", "password123")
    headers = {"Authorization": f"Bearer {create_access_token(user['user_id'])}"}

    mock_embed_cls.return_value.embed_text.return_value = [0.1] * 8
    mock_pinecone_cls.return_value.query.return_value = []
    mock_llm_cls.return_value.generate_answer.return_value = "Mere paas documents me iski jaankari nahi hai."

    resp = client.post("/api/chat/query", json={"question": "Kya yahan kuch hai?"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["answer"].startswith("Mere paas")
    assert mock_llm_cls.return_value.generate_answer.call_args.args[1] == []  # empty context, LLM still called
