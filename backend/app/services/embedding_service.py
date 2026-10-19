"""
Text embeddings. Provider is chosen by EMBEDDING_PROVIDER:
  - "bedrock"  -> Amazon Titan Embeddings on Bedrock (default)
  - "pinecone" -> Pinecone's hosted embedding models (no AWS needed)
embed_text() is for QUERIES, embed_batch() is for document PASSAGES -- E5-style models
are trained with that distinction, and it measurably improves retrieval.
"""
import json

from pinecone import Pinecone

from app.config import get_settings
from app.services.aws_clients import get_bedrock_runtime_client
from app.services.secrets_service import load_secrets

PINECONE_EMBED_BATCH = 90  # Pinecone's inference endpoint caps inputs per request (96 for E5)


class EmbeddingService:
    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.EMBEDDING_PROVIDER
        if self.provider == "pinecone":
            api_key = load_secrets().get("PINECONE_API_KEY") or self.settings.PINECONE_API_KEY
            if not api_key:
                raise RuntimeError("PINECONE_API_KEY is not configured.")
            self.pc = Pinecone(api_key=api_key)
        else:
            self.client = get_bedrock_runtime_client()

    def _pinecone_embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), PINECONE_EMBED_BATCH):
            result = self.pc.inference.embed(
                model=self.settings.PINECONE_EMBEDDING_MODEL,
                inputs=texts[i : i + PINECONE_EMBED_BATCH],
                parameters={"input_type": input_type, "truncate": "END"},
            )
            vectors.extend(item["values"] for item in result)
        return vectors

    def embed_text(self, text: str) -> list[float]:
        if self.provider == "pinecone":
            return self._pinecone_embed([text], "query")[0]
        body = json.dumps({"inputText": text[:8000]})
        response = self.client.invoke_model(
            modelId=self.settings.BEDROCK_EMBEDDING_MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        return json.loads(response["body"].read())["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "pinecone":
            return self._pinecone_embed(texts, "passage")
        return [self.embed_text(t) for t in texts]
