from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.services.embedding_service import PINECONE_EMBED_BATCH, EmbeddingService
from app.services.llm_service import LLMService


def _settings(**kw):
    return Settings(_env_file=None, **kw)


# ---------------- embeddings via Pinecone ----------------
@patch("app.services.embedding_service.load_secrets", return_value={"PINECONE_API_KEY": "k"})
@patch("app.services.embedding_service.Pinecone")
def test_pinecone_embeddings_use_query_vs_passage_and_batch(mock_pc, _secrets):
    mock_pc.return_value.inference.embed.side_effect = lambda model, inputs, parameters: [
        {"values": [float(len(t))] * 3} for t in inputs
    ]
    with patch("app.services.embedding_service.get_settings", return_value=_settings(EMBEDDING_PROVIDER="pinecone")):
        svc = EmbeddingService()
        assert svc.embed_text("hello") == [5.0, 5.0, 5.0]
        assert mock_pc.return_value.inference.embed.call_args.kwargs["parameters"]["input_type"] == "query"

        texts = [f"chunk {i}" for i in range(PINECONE_EMBED_BATCH + 10)]
        vectors = svc.embed_batch(texts)

    assert len(vectors) == len(texts)  # order + count preserved across the 2 batches
    calls = mock_pc.return_value.inference.embed.call_args_list
    assert len(calls) == 3  # 1 query call + 2 passage batches
    assert calls[-1].kwargs["parameters"]["input_type"] == "passage"


def test_default_embedding_provider_is_still_bedrock():
    assert _settings().EMBEDDING_PROVIDER == "bedrock"
    assert _settings().LLM_PROVIDER == "bedrock"


# ---------------- LLM via OpenAI-compatible endpoint ----------------
def _llm(**kw):
    return patch("app.services.llm_service.get_settings", return_value=_settings(LLM_PROVIDER="openai_compatible", **kw))


@patch("app.services.llm_service.OpenAI")
def test_openai_compatible_generate_answer_maps_history_and_system(mock_openai):
    mock_openai.return_value.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="14 days (Source 1)."))]
    )
    with _llm(LLM_API_KEY="k", LLM_MODEL="m", LLM_BASE_URL="http://x/v1"):
        answer = LLMService().generate_answer("Refund?", ["Refunds in 14 days."], [{"role": "user", "content": "Hi"}])

    assert answer == "14 days (Source 1)."
    kwargs = mock_openai.return_value.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "m"
    assert [m["role"] for m in kwargs["messages"]] == ["system", "user", "user"]
    assert mock_openai.call_args.kwargs["base_url"] == "http://x/v1"


@patch("app.services.llm_service.OpenAI")
def test_openai_compatible_stream_skips_empty_chunks(mock_openai):
    def chunk(text):
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])

    mock_openai.return_value.chat.completions.create.return_value = iter(
        [chunk("Hello "), chunk(None), SimpleNamespace(choices=[]), chunk("world")]
    )
    with _llm(LLM_API_KEY="k", LLM_MODEL="m"):
        assert list(LLMService().generate_answer_stream("Hi?", ["ctx"], [])) == ["Hello ", "world"]


def test_openai_compatible_without_key_fails_with_clear_message():
    with _llm(), pytest.raises(RuntimeError, match="LLM_API_KEY"):
        LLMService()


@patch("app.services.llm_service.get_bedrock_runtime_client", return_value=MagicMock())
def test_bedrock_remains_the_default_llm_path(mock_client):
    assert LLMService().provider == "bedrock"


def test_real_openai_client_can_be_constructed():
    # Unmocked on purpose: guards against openai/httpx version drift, which once crashed
    # every chat request with "unexpected keyword argument 'proxies'" inside Docker.
    from openai import OpenAI

    OpenAI(api_key="x", base_url="http://localhost:1/v1")
