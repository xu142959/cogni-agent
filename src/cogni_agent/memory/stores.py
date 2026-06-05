"""Memory storage backends — InMemory, ChromaDB, and SQLite persistence."""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

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

    async def search(self, agent_id: str, query_embedding: list[float], top_k: int = 5) -> list[MemoryItem]:
        items = self._items.get(agent_id, [])
        if not items:
            return []
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
            self._items[agent_id] = [item for item in self._items[agent_id] if item.id != item_id]

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
        self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"},
        )

    async def upsert(self, agent_id: str, item: MemoryItem) -> None:
        embedding = item.embedding or [0.0]
        self._collection.upsert(
            ids=[item.id], embeddings=[embedding],
            metadatas=[{"agent_id": agent_id, "memory_type": item.memory_type,
                        "importance": item.importance, "timestamp": str(item.timestamp)}],
            documents=[item.content],
        )

    async def search(self, agent_id: str, query_embedding: list[float], top_k: int = 5) -> list[MemoryItem]:
        results = self._collection.query(
            query_embeddings=[query_embedding], n_results=top_k, where={"agent_id": agent_id},
        )
        if not results["ids"]:
            return []
        items = []
        for i in range(len(results["ids"][0])):
            items.append(MemoryItem(
                id=results["ids"][0][i], agent_id=agent_id,
                content=results["documents"][0][i],
                memory_type=results["metadatas"][0][i].get("memory_type", "semantic"),
                importance=results["metadatas"][0][i].get("importance", 0.5),
            ))
        return items

    async def delete(self, agent_id: str, item_id: str) -> None:
        self._collection.delete(ids=[item_id])

    async def clear(self, agent_id: str) -> None:
        all_items = self._collection.get(where={"agent_id": agent_id})
        if all_items["ids"]:
            self._collection.delete(ids=all_items["ids"])

    async def count(self, agent_id: str) -> int:
        items = self._collection.get(where={"agent_id": agent_id})
        return len(items["ids"])


# ─── SQLite Persistent Store (NEW) ──────────────────────────

class SQLiteStore(MemoryStore):
    """Persistent SQLite-backed memory storage.

    Agents survive restarts — memories are stored on disk.
    Uses JSON for embedding storage (good enough for development).
    Supports cosine similarity search via in-memory loading.

    Usage:
        store = SQLiteStore("data/memories.db")
        manager = MemoryManager(store=store)
    """

    def __init__(self, db_path: str = "cogni_memories.db"):
        self._db_path = str(Path(db_path).expanduser().resolve())
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create the database and table if they don't exist."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL DEFAULT 'semantic',
                    importance REAL NOT NULL DEFAULT 0.0,
                    timestamp TEXT NOT NULL,
                    embedding TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_agent
                ON memories(agent_id)
            """)
            conn.commit()
        finally:
            conn.close()

    async def upsert(self, agent_id: str, item: MemoryItem) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO memories
                (id, agent_id, content, memory_type, importance, timestamp, embedding, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, agent_id, item.content, item.memory_type,
                item.importance, item.timestamp.isoformat(),
                json.dumps(item.embedding) if item.embedding else None,
                json.dumps(item.metadata) if item.metadata else "{}",
            ))
            conn.commit()
        finally:
            conn.close()

    async def search(self, agent_id: str, query_embedding: list[float], top_k: int = 5) -> list[MemoryItem]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM memories WHERE agent_id = ? ORDER BY importance DESC, timestamp DESC",
                (agent_id,),
            ).fetchall()

            items = []
            for row in rows:
                embedding = json.loads(row["embedding"]) if row["embedding"] else None
                item = MemoryItem(
                    id=row["id"], agent_id=row["agent_id"],
                    content=row["content"], memory_type=row["memory_type"],
                    importance=row["importance"],
                    embedding=embedding,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                items.append(item)

            # Score by cosine similarity if we have embeddings
            if query_embedding and len(query_embedding) > 1:
                scored = []
                for item in items:
                    if item.embedding and len(item.embedding) > 1:
                        sim = InMemoryStore._cosine_similarity(query_embedding, item.embedding)
                        scored.append((sim, item))
                    else:
                        scored.append((item.importance, item))
                scored.sort(key=lambda x: x[0], reverse=True)
                items = [item for _, item in scored[:top_k]]
            else:
                items = items[:top_k]

            return items
        finally:
            conn.close()

    async def delete(self, agent_id: str, item_id: str) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("DELETE FROM memories WHERE id = ? AND agent_id = ?", (item_id, agent_id))
            conn.commit()
        finally:
            conn.close()

    async def clear(self, agent_id: str) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("DELETE FROM memories WHERE agent_id = ?", (agent_id,))
            conn.commit()
        finally:
            conn.close()

    async def count(self, agent_id: str) -> int:
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM memories WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    async def get_all(self, agent_id: str) -> list[MemoryItem]:
        """Retrieve all memories for an agent (for inspection/export)."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM memories WHERE agent_id = ? ORDER BY timestamp DESC", (agent_id,)
            ).fetchall()
            return [
                MemoryItem(id=r["id"], agent_id=r["agent_id"], content=r["content"],
                           memory_type=r["memory_type"], importance=r["importance"])
                for r in rows
            ]
        finally:
            conn.close()

    async def vacuum(self) -> None:
        """Reclaim disk space."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("VACUUM")
            conn.commit()
        finally:
            conn.close()

    @property
    def db_path(self) -> str:
        return self._db_path