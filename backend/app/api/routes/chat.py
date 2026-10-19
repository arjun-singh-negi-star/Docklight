import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.api.routes.metrics import CHAT_CACHE_HITS, CHAT_LATENCY, CHAT_REQUESTS
from app.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk
from app.services.cache_service import get_cached_answer, set_cached_answer
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.pinecone_service import PineconeService
from app.services.rate_limiter import enforce_rate_limit
from app.services.reranker import hybrid_rerank
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = get_logger(__name__)


def _retrieve_sources(question: str, user_id: str, top_k: int) -> list[SourceChunk]:
    settings = get_settings()
    query_embedding = EmbeddingService().embed_text(question)
    candidate_count = top_k * settings.RETRIEVAL_CANDIDATE_MULTIPLIER
    candidates = PineconeService().query(query_embedding, candidate_count, namespace=user_id)
    reranked = hybrid_rerank(question, candidates, top_k, alpha=settings.HYBRID_ALPHA)
    return [
        SourceChunk(
            doc_id=m["metadata"]["doc_id"],
            filename=m["metadata"]["filename"],
            chunk_text=m["metadata"]["chunk_text"],
            score=m["score"],
        )
        for m in reranked
    ]


@router.post("/query", response_model=ChatResponse)
async def query(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Non-streaming Q&A: hybrid retrieval + rerank -> cache check -> LLM -> cache write."""
    settings = get_settings()
    user_id = current_user["user_id"]
    enforce_rate_limit(user_id, settings.RATE_LIMIT_PER_MINUTE)
    CHAT_REQUESTS.inc()

    if request.conversation_id is None:
        cached = get_cached_answer(user_id, request.question)
        if cached:
            CHAT_CACHE_HITS.inc()
            return ChatResponse(**cached)

    with CHAT_LATENCY.time():
        top_k = request.top_k or settings.TOP_K_RESULTS
        sources = _retrieve_sources(request.question, user_id, top_k)

        conv = ConversationService()
        conversation_id = request.conversation_id or conv.create_conversation(user_id)
        history = conv.get_recent_turns(conversation_id, settings.CONVERSATION_HISTORY_TURNS)

        # Even with zero sources the LLM is called, so its "no information" reply is in the user's language.
        answer = LLMService().generate_answer(request.question, [s.chunk_text for s in sources], history)

        conv.append_turn(conversation_id, "user", request.question)
        conv.append_turn(conversation_id, "assistant", answer)

    response = ChatResponse(answer=answer, sources=sources, conversation_id=conversation_id)
    if request.conversation_id is None:
        set_cached_answer(user_id, request.question, response.model_dump(mode="json"), settings.CACHE_TTL_SECONDS)
    return response


def _public_error(exc: Exception) -> str:
    """Details help while developing; in production don't leak internals to the browser."""
    if type(exc).__name__ in ("RateLimitError", "ThrottlingException"):
        return "The AI provider is rate-limiting requests right now. Wait a few seconds and ask again."
    if get_settings().APP_ENV == "production":
        return "The assistant ran into a problem. Please try again."
    return f"{type(exc).__name__}: {str(exc)[:300]}"


@router.post("/stream")
async def stream_query(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Server-Sent-Events version of /query: streams the answer token-by-token
    as the model generates it, for a live "typing" effect in the UI. Events:
      event: sources -> the retrieved source chunks (sent once, up front)
      event: token   -> one chunk of answer text (sent repeatedly)
      event: error   -> something failed mid-request (message is safe to show)
      event: done    -> the conversation_id, signalling the stream is finished
    Rate limiting stays outside the generator so it still returns a real HTTP 429.
    """
    settings = get_settings()
    user_id = current_user["user_id"]
    enforce_rate_limit(user_id, settings.RATE_LIMIT_PER_MINUTE)
    CHAT_REQUESTS.inc()
    top_k = request.top_k or settings.TOP_K_RESULTS

    def event_stream():
        try:
            sources = _retrieve_sources(request.question, user_id, top_k)

            conv = ConversationService()
            conversation_id = request.conversation_id or conv.create_conversation(user_id)
            history = conv.get_recent_turns(conversation_id, settings.CONVERSATION_HISTORY_TURNS)

            yield f"event: sources\ndata: {json.dumps([s.model_dump() for s in sources])}\n\n"

            full_answer: list[str] = []
            for token in LLMService().generate_answer_stream(
                request.question, [s.chunk_text for s in sources], history
            ):
                full_answer.append(token)
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

            conv.append_turn(conversation_id, "user", request.question)
            conv.append_turn(conversation_id, "assistant", "".join(full_answer))
            yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming chat failed")
            yield f"event: error\ndata: {json.dumps({'message': _public_error(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
