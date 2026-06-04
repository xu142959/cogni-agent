"""Tests for MemoryManager — working memory, semantic memory, embeddings, stores."""

import math
import pytest

from cogni_agent.memory import MemoryManager
from cogni_agent.memory.stores import InMemoryStore, ChromaDBStore
from cogni_agent.core.types import MemoryItem


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def memory():
    return MemoryManager()


@pytest.fixture
def agent_id():
    return "test_agent"


# ─── Working Memory ─────────────────────────────────────────

class TestWorkingMemory:
    def test_push_and_get(self, memory):
        agent = "test_agent"
        memory.push_working(agent, "Hello")
        items = memory.get_working_context(agent)
        assert len(items) == 1
        assert items[0].content == "Hello"
        assert items[0].memory_type == "working"

    def test_max_count(self, memory):
        agent = "test_agent"
        for i in range(20):
            memory.push_working(agent, f"Item {i}")
        items = memory.get_working_context(agent, max_count=5)
        assert len(items) == 5
        assert items[-1].content == "Item 19"

    def test_clear(self, memory):
        agent = "test_agent"
        memory.push_working(agent, "test")
        memory.clear_working(agent)
        items = memory.get_working_context(agent)
        assert len(items) == 0


# ─── Semantic Memory ────────────────────────────────────────

@pytest.mark.asyncio
async def test_store_and_retrieve_semantic(memory, agent_id):
    item = await memory.store_semantic(
        agent_id,
        "Important insight about data analysis",
        importance=0.8,
    )
    assert item.agent_id == agent_id
    assert item.memory_type == "semantic"
    assert item.importance == 0.8
    assert item.embedding is not None

    retrieved = await memory.retrieve_relevant(agent_id, "data analysis")
    assert len(retrieved) >= 1


@pytest.mark.asyncio
async def test_retrieve_with_min_importance(memory, agent_id):
    await memory.store_semantic(agent_id, "Low importance fact", importance=0.2)
    await memory.store_semantic(agent_id, "High importance insight", importance=0.9)

    results = await memory.retrieve_relevant(
        agent_id, "fact", min_importance=0.5
    )
    assert all(r.importance >= 0.5 for r in results)


# ─── InMemoryStore ───────────────────────────────────────────

class TestInMemoryStore:
    @pytest.mark.asyncio
    async def test_upsert_and_search(self):
        store = InMemoryStore()
        item = MemoryItem(
            id="1",
            agent_id="test",
            content="test memory",
            memory_type="semantic",
            importance=0.5,
            embedding=[1.0, 0.0, 0.0],
        )
        await store.upsert("test", item)
        results = await store.search("test", [1.0, 0.0, 0.0], top_k=5)
        assert len(results) == 1
        assert results[0].content == "test memory"

    @pytest.mark.asyncio
    async def test_delete(self):
        store = InMemoryStore()
        item = MemoryItem(id="1", agent_id="test", content="x", memory_type="semantic")
        await store.upsert("test", item)
        await store.delete("test", "1")
        results = await store.search("test", [1.0, 0.0], top_k=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_cosine_similarity(self):
        store = InMemoryStore()
        assert store._cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
        assert store._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
        assert store._cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    @pytest.mark.asyncio
    async def test_clear(self):
        store = InMemoryStore()
        await store.upsert("test", MemoryItem(id="1", agent_id="test", content="x", memory_type="semantic"))
        await store.clear("test")
        assert await store.count("test") == 0


# ─── ChromaDBStore ──────────────────────────────────────────

class TestChromaDBStore:
    @pytest.mark.asyncio
    async def test_upsert_and_search(self):
        try:
            store = ChromaDBStore("test_collection")
        except Exception:
            pytest.skip("ChromaDB not available")
        item = MemoryItem(
            id="c1",
            agent_id="test",
            content="chroma test memory",
            memory_type="semantic",
            importance=0.9,
            embedding=[1.0, 0.0, 0.0],
        )
        await store.upsert("test", item)
        results = await store.search("test", [1.0, 0.0, 0.0], top_k=5)
        assert len(results) >= 1
        assert results[0].content == "chroma test memory"

    @pytest.mark.asyncio
    async def test_clear_and_count(self):
        try:
            store = ChromaDBStore("test_count")
        except Exception:
            pytest.skip("ChromaDB not available")
        await store.upsert("test", MemoryItem(id="c2", agent_id="test", content="x", memory_type="semantic", embedding=[0.5, 0.5]))
        assert await store.count("test") >= 1
        await store.clear("test")
        assert await store.count("test") == 0


# ─── Embedding ──────────────────────────────────────────────

class TestEmbedding:
    def test_fallback_embedding_dimension(self, memory):
        vec = memory._embed_fallback("hello world")
        assert len(vec) == 128

    def test_fallback_embedding_normalized(self, memory):
        vec = memory._embed_fallback("test")
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 0.01

    def test_fallback_deterministic(self, memory):
        v1 = memory._embed_fallback("same text")
        v2 = memory._embed_fallback("same text")
        assert v1 == v2

    def test_fallback_different_texts_different(self, memory):
        v1 = memory._embed_fallback("hello")
        v2 = memory._embed_fallback("world")
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_embed_route_no_model(self, memory):
        vec = await memory._embed("test")
        assert len(vec) > 0


# ─── Memory Counts ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_counts(memory, agent_id):
    memory.push_working(agent_id, "working item")
    await memory.store_semantic(agent_id, "semantic item")
    counts = await memory.count_memories(agent_id)
    assert counts["working"] >= 1
    assert counts["persistent"] >= 1
    assert counts["total"] >= 2