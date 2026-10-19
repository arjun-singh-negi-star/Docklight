from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.routes.chat import _public_error
from app.auth.security import create_access_token
from app.config import Settings
from app.main import app
from app.models.schemas import SourceChunk
from app.services.user_service import UserService

client = TestClient(app)
SOURCE = SourceChunk(doc_id="d1", filename="f.txt", chunk_text="Refunds within 14 days.", score=0.9)


def _headers():
    user = UserService().create_user("testuser@example.com", "password123")
    return {"Authorization": f"Bearer {create_access_token(user['user_id'])}"}


@patch("app.api.routes.chat.LLMService")
@patch("app.api.routes.chat._retrieve_sources", return_value=[SOURCE])
def test_llm_failure_is_reported_as_error_event_not_a_silent_break(_retrieve, mock_llm, aws_mock, fake_redis):
    mock_llm.return_value.generate_answer_stream.side_effect = RuntimeError("model exploded")
    resp = client.post("/api/chat/stream", json={"question": "Refund?"}, headers=_headers())
    assert resp.status_code == 200
    assert "event: error" in resp.text and "model exploded" in resp.text
    assert "event: done" not in resp.text


@patch("app.api.routes.chat._retrieve_sources", side_effect=RuntimeError("pinecone unreachable"))
def test_retrieval_failure_is_reported_as_error_event(_retrieve, aws_mock, fake_redis):
    resp = client.post("/api/chat/stream", json={"question": "Refund?"}, headers=_headers())
    assert resp.status_code == 200
    assert "event: error" in resp.text and "pinecone unreachable" in resp.text


@patch("app.api.routes.chat.LLMService")
@patch("app.api.routes.chat._retrieve_sources", return_value=[SOURCE])
def test_happy_path_still_streams_tokens_and_done(_retrieve, mock_llm, aws_mock, fake_redis):
    mock_llm.return_value.generate_answer_stream.return_value = iter(["14 ", "days"])
    resp = client.post("/api/chat/stream", json={"question": "Refund?"}, headers=_headers())
    assert "event: sources" in resp.text and "event: done" in resp.text
    assert resp.text.count("event: token") == 2 and "event: error" not in resp.text


def test_production_hides_internal_error_details():
    with patch("app.api.routes.chat.get_settings", return_value=Settings(_env_file=None, APP_ENV="production")):
        message = _public_error(RuntimeError("secret internal detail"))
    assert "secret" not in message
    with patch("app.api.routes.chat.get_settings", return_value=Settings(_env_file=None, APP_ENV="development")):
        assert "secret internal detail" in _public_error(RuntimeError("secret internal detail"))


