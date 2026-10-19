from unittest.mock import MagicMock, patch

from app.services.llm_service import LLMService


@patch("app.services.llm_service.get_bedrock_runtime_client")
def test_generate_answer_uses_converse_and_maps_history(mock_get_client):
    client = MagicMock()
    client.converse.return_value = {"output": {"message": {"content": [{"text": "14 days (Source 1)."}]}}}
    mock_get_client.return_value = client

    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    answer = LLMService().generate_answer("Refund window?", ["Refunds within 14 days."], history)

    assert answer == "14 days (Source 1)."
    kwargs = client.converse.call_args.kwargs
    assert [m["role"] for m in kwargs["messages"]] == ["user", "assistant", "user"]
    assert kwargs["messages"][0]["content"] == [{"text": "Hi"}]
    assert "[Source 1]" in kwargs["messages"][-1]["content"][0]["text"]


@patch("app.services.llm_service.get_bedrock_runtime_client")
def test_generate_answer_stream_yields_only_text_deltas(mock_get_client):
    client = MagicMock()
    client.converse_stream.return_value = {
        "stream": [
            {"messageStart": {"role": "assistant"}},
            {"contentBlockDelta": {"delta": {"text": "Hello "}}},
            {"contentBlockDelta": {"delta": {"text": "world"}}},
            {"messageStop": {"stopReason": "end_turn"}},
        ]
    }
    mock_get_client.return_value = client

    tokens = list(LLMService().generate_answer_stream("Hi?", ["ctx"], []))
    assert tokens == ["Hello ", "world"]
