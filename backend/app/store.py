"""Vector database layer (ChromaDB). One collection per browser session, so
users never see each other's documents."""
import hashlib

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from .config import settings


def _name(session_id: str) -> str:
    # Hash the id so the collection name is always valid and unguessable
    return "s" + hashlib.sha256(session_id.encode()).hexdigest()[:40]


class VectorStore:
    def __init__(self, path: str | None = None):
        self._client = chromadb.PersistentClient(path=path or settings.CHROMA_PATH)
        # Local ONNX embedding model (all-MiniLM-L6-v2): free, no API key needed
        self._embed = DefaultEmbeddingFunction()

    def _collection(self, session_id: str):
        return self._client.get_or_create_collection(
            name=_name(session_id), embedding_function=self._embed,
            metadata={"hnsw:space": "cosine"})

    def add(self, session_id: str, records: list[dict]) -> None:
        if not records:
            return
        self._collection(session_id).upsert(
            ids=[r["id"] for r in records],
            documents=[r["text"] for r in records],
            metadatas=[{"file": r["file"], "page": r["page"]} for r in records],
        )

    def query(self, session_id: str, question: str, k: int) -> list[dict]:
        col = self._collection(session_id)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[question], n_results=min(k, col.count()))
        return [
            {"text": doc, "file": meta["file"], "page": meta["page"], "distance": dist}
            for doc, meta, dist in zip(
                res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]

    def documents(self, session_id: str) -> list[dict]:
        data = self._collection(session_id).get(include=["metadatas"])
        summary: dict[str, dict] = {}
        for meta in data["metadatas"]:
            doc = summary.setdefault(meta["file"], {"name": meta["file"], "pages": 0, "chunks": 0})
            doc["pages"] = max(doc["pages"], meta["page"])
            doc["chunks"] += 1
        return list(summary.values())

    def delete_session(self, session_id: str) -> None:
        try:
            self._client.delete_collection(_name(session_id))
        except Exception:  # collection may not exist yet
            pass
