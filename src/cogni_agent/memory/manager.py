"""Memory Manager — structured memory with working, semantic, episodic, procedural layers."""

from __future__ import annotations

import math
from uuid import uuid4

from cogni_agent.core.types import AgentID, MemoryItem, Message
from cogni_agent.core.interfaces import LLMGateway, MemoryStore
from cogni_agent.llm import LiteLLMGateway
from cogni_agent.memory.stores import InMemoryStore


class MemoryManager:
    """Unified memory manager with real embedding and semantic search.

    Layers:
    - Working: current session context (ephemeral, token-aware)
    - Semantic: general knowledge extracted from experience (vector search)
    - Episodic: event memories with timeline (planned)
    - Procedural: how-to knowledge and skill templates (planned)
    """

    EMBEDDING_DIM = 1536  # text-embedding-3-small dimension

    def __init__(
        self,
        llm: LLMGateway | None = None,
        store: MemoryStore | None = None,
        embedding_model: str | None = None,
    ):
        self._llm = llm or LiteLLMGateway()
        self._store = store or InMemoryStore()
        self._embedding_model = embedding_model
        # Working memory is per-agent, in-memory only
        self._working: dict[str, list[MemoryItem]] = {}

    # ─── Working Memory ───────────────────────────────────────

    def push_working(
        self,
        agent_id: AgentID,
        content: str,
        importance: float = 0.1,
        metadata: dict | None = None,
    ) -> MemoryItem:
        """Push a working memory item for the current session."""
        self._working.setdefault(agent_id, [])
        item = MemoryItem(
            id=uuid4().hex,
            agent_id=agent_id,
            content=content,
            memory_type="working",
            importance=importance,
            metadata=metadata or {},
        )
        self._working[agent_id].append(item)
        return item

    def get_working_context(
        self,
        agent_id: AgentID,
        max_count: int = 10,
    ) -> list[MemoryItem]:
        """Get the most recent working memory items."""
        items = self._working.get(agent_id, [])
        return items[-max_count:]

    def clear_working(self, agent_id: AgentID) -> None:
        """Clear working memory for a session."""
        self._working[agent_id] = []

    # ─── Semantic Memory ──────────────────────────────────────

    async def store_semantic(
        self,
        agent_id: AgentID,
        content: str,
        importance: float = 0.5,
    ) -> MemoryItem:
        """Store a piece of semantic knowledge with auto-embedding."""
        embedding = await self._embed(content)
        item = MemoryItem(
            id=uuid4().hex,
            agent_id=agent_id,
            content=content,
            memory_type="semantic",
            importance=importance,
            embedding=embedding,
        )
        await self._store.upsert(agent_id, item)
        return item

    async def retrieve_relevant(
        self,
        agent_id: AgentID,
        query: str,
        top_k: int = 5,
        min_importance: float = 0.0,
    ) -> list[MemoryItem]:
        """Retrieve relevant semantic memories by vector similarity."""
        query_emb = await self._embed(query)
        results = await self._store.search(agent_id, query_emb, top_k=top_k)
        if min_importance > 0.0:
            results = [r for r in results if r.importance >= min_importance]
        return results

    async def count_memories(self, agent_id: AgentID) -> dict[str, int]:
        """Get memory count per type for an agent."""
        total = await self._store.count(agent_id)
        working = len(self._working.get(agent_id, []))
        return {
            "persistent": total,
            "working": working,
            "total": total + working,
        }

    # ─── Memory Extraction ────────────────────────────────────

    async def extract_semantic(
        self,
        agent_id: AgentID,
        conversation_summary: str,
    ) -> MemoryItem | None:
        """Extract reusable knowledge from a conversation turn."""
        prompt = (
            f"Extract a concise, reusable insight or piece of knowledge "
            f"from the following interaction. Return ONLY the insight itself, "
            f"or 'None' if there is nothing worth remembering:\n\n"
            f"{conversation_summary}"
        )
        response = await self._llm.chat([Message(role="user", content=prompt)])
        insight = response.content.strip()

        if not insight or insight.lower() in ("none", "无", "nothing"):
            return None

        return await self.store_semantic(agent_id, insight, importance=0.6)

    # ─── Embedding ───────────────────────────────────────────

    async def _embed(self, text: str) -> list[float]:
        """Generate an embedding vector using the configured embedding model.

        Resolution order:
        1. If embedding_model is set, use litellm to call that model
        2. Otherwise, use a deterministic hash-based fallback
        """
        if self._embedding_model:
            return await self._embed_via_llm(text)
        return self._embed_fallback(text)

    async def _embed_via_llm(self, text: str) -> list[float]:
        """Use an LLM embedding model (e.g. text-embedding-3-small)."""
        from cogni_agent.llm import LiteLLMGateway
        from cogni_agent.core.types import LLMConfig

        embed_llm = LiteLLMGateway(LLMConfig(model=self._embedding_model))
        # litellm handles embedding models via the /embeddings endpoint
        import litellm

        try:
            response = await litellm.aembedding(
                model=self._embedding_model,
                input=text,
            )
            return response.data[0]["embedding"]
        except Exception:
            # Fallback if embedding call fails
            return self._embed_fallback(text)

    @staticmethod
    def _embed_fallback(text: str) -> list[float]:
        """Deterministic fallback embedding based on hash.

        Produces a pseudo-random vector of dimension 128 with
        roughly unit-length magnitude for cosine similarity to work.
        """
        import hashlib

        dim = 128
        text_bytes = text.encode("utf-8")
        vec = []
        for i in range(dim):
            h = hashlib.sha256(text_bytes + str(i).encode()).digest()
            # Convert first 4 bytes to a float in [-1, 1]
            val = int.from_bytes(h[:4], "big") / (2**32) * 2 - 1
            vec.append(val)

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if self._embedding_model:
            import litellm
            try:
                response = await litellm.aembedding(
                    model=self._embedding_model,
                    input=texts,
                )
                return [d["embedding"] for d in response.data]
            except Exception:
                pass
        return [self._embed_fallback(t) for t in texts]

    async def compute_importance(self, content: str, task_context: str | None = None) -> float:
        """Use the LLM to estimate how important a memory is [0, 1]."""
        context_hint = f" (in context: {task_context})" if task_context else ""
        prompt = (
            f"Rate the importance of the following piece of knowledge on a scale "
            f"from 0.0 (forgettable) to 1.0 (critical to remember){context_hint}.\n"
            f"Return ONLY a decimal number, no explanation.\n\n"
            f"Knowledge: {content}"
        )
        response = await self._llm.chat([Message(role="user", content=prompt)])
        try:
            val = float(response.content.strip())
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.5
