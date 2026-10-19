"""
Wraps the Pinecone vector index. Every call takes a `namespace` (the user_id)
so each user's vectors are fully isolated inside one shared index -- this is
Pinecone's recommended multi-tenancy pattern and avoids needing a separate
(paid) index per user. Deletion is id-based (see dynamodb_service.py) so it
works the same way regardless of Pinecone plan/index type.
"""
from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.services.secrets_service import load_secrets
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PineconeService:
    def __init__(self):
        self.settings = get_settings()
        secrets = load_secrets()
        api_key = secrets.get("PINECONE_API_KEY") or self.settings.PINECONE_API_KEY
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY is not configured.")
        self.pc = Pinecone(api_key=api_key)
        self.index_name = self.settings.PINECONE_INDEX_NAME

    def ensure_index_exists(self) -> None:
        existing = [idx["name"] for idx in self.pc.list_indexes()]
        if self.index_name in existing:
            return
        logger.info("Pinecone index %s not found, creating it.", self.index_name)
        self.pc.create_index(
            name=self.index_name,
            dimension=self.settings.EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=self.settings.PINECONE_CLOUD, region=self.settings.PINECONE_REGION),
        )

    @property
    def index(self):
        return self.pc.Index(self.index_name)

    def upsert_chunks(
        self, doc_id: str, filename: str, chunks: list[str], embeddings: list[list[float]], namespace: str
    ) -> list[str]:
        ids = [f"{doc_id}::chunk-{i}" for i in range(len(chunks))]
        vectors = [
            {
                "id": ids[i],
                "values": embeddings[i],
                "metadata": {"doc_id": doc_id, "filename": filename, "chunk_text": chunks[i]},
            }
            for i in range(len(chunks))
        ]
        self.index.upsert(vectors=vectors, namespace=namespace)
        return ids

    def query(self, embedding: list[float], top_k: int, namespace: str) -> list[dict]:
        result = self.index.query(vector=embedding, top_k=top_k, include_metadata=True, namespace=namespace)
        return result["matches"]

    def delete_by_ids(self, ids: list[str], namespace: str) -> None:
        if ids:
            self.index.delete(ids=ids, namespace=namespace)
