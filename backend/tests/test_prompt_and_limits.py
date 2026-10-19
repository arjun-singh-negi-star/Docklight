from unittest.mock import patch

from app.api.routes.chat import _public_error
from app.config import Settings
from app.services.llm_service import SYSTEM_PROMPT, LLMService, _user_message


def test_user_message_ends_with_grounding_reminder_after_the_question():
    msg = _user_message("Capital of France?", ["chunk a", "chunk b"])
    assert "[Source 1]\nchunk a" in msg and "[Source 2]\nchunk b" in msg
    assert msg.index("Question: Capital of France?") < msg.index("Answer only from the Context")


def test_system_prompt_blocks_override_attempts_and_requires_checking_claims():
    # Behavioural effect can only be verified against a live model; this guards the rules
    # from being silently dropped in a future edit.
    for must_have in ("Never use outside or general", "ignore, override or forget", "check it against the numbers"):
        assert must_have in SYSTEM_PROMPT
    assert "[Source 1]" in SYSTEM_PROMPT and "Hinglish" in SYSTEM_PROMPT


@patch("app.services.llm_service.OpenAI")
def test_openai_compatible_client_retries_rate_limits(mock_openai):
    settings = Settings(_env_file=None, LLM_PROVIDER="openai_compatible", LLM_API_KEY="k", LLM_MODEL="m")
    with patch("app.services.llm_service.get_settings", return_value=settings):
        LLMService()
    assert mock_openai.call_args.kwargs["max_retries"] == 5


class RateLimitError(Exception):  # same class name the openai SDK raises on HTTP 429
    pass


def test_rate_limit_errors_get_a_friendly_message_in_every_environment():
    for env in ("development", "production"):
        with patch("app.api.routes.chat.get_settings", return_value=Settings(_env_file=None, APP_ENV=env)):
            message = _public_error(RateLimitError("Error code: 429 ... org_01abc ..."))
        assert "rate-limiting" in message and "org_" not in message


def test_roman_script_question_locks_reply_to_latin_letters():
    assert "never switch to Devanagari" in _user_message("Weighted average salary match karta hai?", ["ctx"])


def test_devanagari_question_is_not_forced_into_latin():
    msg = _user_message("क्या यह सही है?", ["ctx"])
    assert "Devanagari" not in msg and "Answer only from the Context" in msg


import pytest  # noqa: E402

from app.services.llm_service import _dominant_script  # noqa: E402
from app.services.reranker import hybrid_rerank  # noqa: E402


@pytest.mark.parametrize(
    "question, script",
    [
        ("When was TrueMind founded?", "LATIN"),
        ("Kaun se offices India ke bahar hain?", "LATIN"),  # Hinglish
        ("¿Cuándo se fundó la empresa?", "LATIN"),  # Spanish: accents are still Latin
        ("क्या यह सही है?", "DEVANAGARI"),
        ("PDF में कितने employees हैं?", "DEVANAGARI"),  # Hindi with English words: letters decide
        ("TrueMind是什么时候成立的？", "CJK"),
        ("TrueMind는 언제 설립되었나요?", "HANGUL"),
        ("متى تأسست الشركة؟", "ARABIC"),
        ("Когда основана компания?", "CYRILLIC"),
        ("12345 ???", "LATIN"),  # no letters at all -> safe default
        ("What does 成立 mean in the document?", "LATIN"),  # one foreign word inside English
    ],
)
def test_script_detection(question, script):
    assert _dominant_script(question) == script


@pytest.mark.parametrize("question", ["TrueMind是什么时候成立的？", "TrueMind는 언제 설립되었나요?", "क्या यह सही है?"])
def test_non_latin_questions_are_never_forced_into_latin_letters(question):
    msg = _user_message(question, ["ctx"])
    assert "Latin letters only" not in msg
    assert "same language and script as the question" in msg


@pytest.mark.parametrize("question", ["Weighted average match karta hai?", "¿Cuándo se fundó?", "When was it founded?"])
def test_latin_questions_keep_their_own_language_but_never_devanagari(question):
    msg = _user_message(question, ["ctx"])
    assert "Latin letters only" in msg and "never switch to Devanagari" in msg
    assert "Spanish" in msg  # directive must not narrow Latin-script languages to English/Hinglish


def test_empty_context_is_explained_to_the_model_instead_of_dropped():
    assert "No relevant passages were found" in _user_message("Kya yahan kuch hai?", [])


def test_hybrid_rerank_falls_back_to_pure_vector_order_for_chinese_queries():
    # Chinese has no spaces, so BM25 sees one token and matches nothing; the blend must then
    # degrade to the semantic (multilingual-embedding) order instead of scrambling results.
    candidates = [
        {"score": s, "metadata": {"doc_id": "d", "filename": "f", "chunk_text": t}}
        for s, t in [(0.5, "Founded 2010"), (0.9, "Headquarters Bengaluru"), (0.7, "Revenue 72M")]
    ]
    ranked = hybrid_rerank("公司是什么时候成立的", candidates, top_k=3)
    assert [c["score"] for c in ranked] == [0.9, 0.7, 0.5]
