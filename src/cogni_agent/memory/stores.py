"""Memory storage backends — InMemory and ChromaDB."""

from __future__ import annotations

import math
import uuid

from cogni_agent.core.interfaces import MemoryStore
from cogni_agent.core.types import MemoryItem


# ─── InMemory Store ──────────────────────────────────────────

class InMemoryStore(MemoryStore):
    """In-memory vector store for development/testing."""

    def __init__(self):
        self._items: dict[str, list[MemoryItem]] = {}

    async def upsert(self, agent_id: str, item: MemoryItem) -> None:
        if agent_id not in self._items:
            self._items[agent_id] = []
        for i, existing in enumerate(self._items[agent_id]):
            if existing.id == item.id:
                self._items[agent_id][i] = item
                return
        self._items[agent_id].append(item)

    async def search(
        self,
        agent_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[MemoryItem]:
        items = self._items.get(agent_id, [])
        if not items:
            return []

        # Cosine similarity ranking
        scored = []
        for item in items:
            if item.embedding and len(item.embedding) > 1:
                sim = self._cosine_similarity(query_embedding, item.embedding)
                scored.append((sim, item))
            else:
                scored.append((0.0, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    async def delete(self, agent_id: str, item_id: str) -> None:
        if agent_id in self._items:
            self._items[agent_id] = [
                item for item in self._items[agent_id] if item.id != item_id
            ]

    async def clear(self, agent_id: str) -> None:
        self._items[agent_id] = []

    async def count(self, agent_id: str) -> int:
        return len(self._items.get(agent_id, []))

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


# ─── ChromaDB Store ─────────────────────────────────────────

class ChromaDBStore(MemoryStore):
    """Production-grade vector store using ChromaDB."""

    def __init__(self, collection_name: str = "cogni_memories"):
        import chromadb
        self._client = chromadb.Client()  # ephemeral in-memory ChromaDB
        # Use a persistent client in production:
        # chromadb.PersistentClient(path="/path/to/db")
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._collection_name = collection_name

    async def upsert(self, agent_id: str, item: MemoryItem) -> None:
        embedding = item.embedding or [0.0]
        self._collection.upsert(
            ids=[item.id],
            embeddings=[embedding],
            metadatas=[{
                "agent_id": agent_id,
                "memory_type": item.memory_type,
                "importance": item.importance,
                "timestamp": item.timestamp.isoformat(),
            }],
            documents=[item.content],
        )

    async def search(
        self,
        agent_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[MemoryItem]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"agent_id": agent_id},
        )
        if not results["ids"]:
            return []

        items = []
        for i in range(len(results["ids"][0])):
            items.append(MemoryItem(
                id=results["ids"][0][i],
                agent_id=agent_id,
                content=results["documents"][0][i],
                memory_type=results["metadatas"][0][i].get("memory_type", "semantic"),
                importance=results["metadatas"][0][i].get("importance", 0.5),
            ))
        return items

    async def delete(self, agent_id: str, item_id: str) -> None:
        self._collection.delete(ids=[item_id])

    async def clear(self, agent_id: str) -> None:
        # ChromaDB doesn't support delete by metadata filter directly
        all_items = self._collection.get(where={"agent_id": agent_id})
        if all_items["ids"]:
            self._collection.delete(ids=all_items["ids"])

    async def count(self, agent_id: str) -> int:
        items = self._collection.get(where={"agent_id": agent_id})
        return len(items["ids"])
