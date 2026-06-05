"""Tests for MCP integration and SQLite persistent storage."""

import os
import tempfile

import pytest

from cogni_agent.tools.mcp import MCPToolset, MCPToolWrapper
from cogni_agent.memory.stores import SQLiteStore
from cogni_agent.core.types import MemoryItem


# ─── MCP Tests ────────────────────────────────────────────

class TestMCPToolWrapper:
    def test_wrapper_creation(self):
        wrapper = MCPToolWrapper(
            name="test_tool",
            description="A test MCP tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
            session=None,
        )
        assert wrapper.name == "test_tool"
        assert wrapper.description == "A test MCP tool"
        assert wrapper.schema is not None

    def test_openai_tool_conversion(self):
        wrapper = MCPToolWrapper(
            name="search",
            description="Search tool",
            input_schema={
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                },
                "required": ["q"],
            },
            session=None,
        )
        ot = wrapper.to_openai_tool()
        assert ot["function"]["name"] == "search"
        assert "q" in ot["function"]["parameters"]["required"]

    def test_mcp_toolset_empty(self):
        toolset = MCPToolset()
        assert toolset.tools == []
        assert toolset.tool_names == []


# ─── SQLite Store Tests ──────────────────────────────────

class TestSQLiteStore:
    @pytest.fixture
    def db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def store(self, db_path):
        return SQLiteStore(db_path)

    @pytest.mark.asyncio
    async def test_upsert_and_search(self, store):
        item = MemoryItem(
            id="test1", agent_id="agent1",
            content="Python is a programming language",
            memory_type="semantic", importance=0.8,
        )
        await store.upsert("agent1", item)

        results = await store.search("agent1", [0.0], top_k=5)
        assert len(results) == 1
        assert results[0].content == "Python is a programming language"

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, store):
        item1 = MemoryItem(id="test1", agent_id="agent1", content="original", memory_type="semantic")
        await store.upsert("agent1", item1)
        item2 = MemoryItem(id="test1", agent_id="agent1", content="updated", memory_type="semantic", importance=0.9)
        await store.upsert("agent1", item2)

        results = await store.search("agent1", [0.0], top_k=5)
        assert len(results) == 1
        assert results[0].content == "updated"

    @pytest.mark.asyncio
    async def test_search_empty(self, store):
        results = await store.search("nonexistent", [0.0], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_delete(self, store):
        item = MemoryItem(id="del1", agent_id="agent1", content="to_delete", memory_type="semantic")
        await store.upsert("agent1", item)
        await store.delete("agent1", "del1")
        results = await store.search("agent1", [0.0], top_k=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_clear(self, store):
        await store.upsert("agent1", MemoryItem(id="c1", agent_id="agent1", content="x", memory_type="semantic"))
        await store.upsert("agent1", MemoryItem(id="c2", agent_id="agent1", content="y", memory_type="semantic"))
        await store.clear("agent1")
        results = await store.search("agent1", [0.0], top_k=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_count(self, store):
        assert await store.count("agent1") == 0
        await store.upsert("agent1", MemoryItem(id="n1", agent_id="agent1", content="a", memory_type="semantic"))
        await store.upsert("agent1", MemoryItem(id="n2", agent_id="agent1", content="b", memory_type="semantic"))
        assert await store.count("agent1") == 2

    @pytest.mark.asyncio
    async def test_get_all(self, store):
        await store.upsert("agent1", MemoryItem(id="g1", agent_id="agent1", content="first", memory_type="semantic"))
        await store.upsert("agent1", MemoryItem(id="g2", agent_id="agent1", content="second", memory_type="semantic"))
        all_items = await store.get_all("agent1")
        assert len(all_items) == 2

    @pytest.mark.asyncio
    async def test_persistence_across_instances(self, db_path):
        """Data survives store recreation (the point of SQLite)."""
        store1 = SQLiteStore(db_path)
        await store1.upsert("agent1", MemoryItem(id="p1", agent_id="agent1", content="persistent!", memory_type="semantic"))
        del store1

        store2 = SQLiteStore(db_path)
        results = await store2.search("agent1", [0.0], top_k=5)
        assert len(results) == 1
        assert results[0].content == "persistent!"

    @pytest.mark.asyncio
    async def test_importance_based_ordering(self, store):
        await store.upsert("agent1", MemoryItem(id="o1", agent_id="agent1", content="low", memory_type="semantic", importance=0.2))
        await store.upsert("agent1", MemoryItem(id="o2", agent_id="agent1", content="high", memory_type="semantic", importance=0.9))
        await store.upsert("agent1", MemoryItem(id="o3", agent_id="agent1", content="medium", memory_type="semantic", importance=0.5))

        results = await store.search("agent1", [0.0], top_k=3)
        assert results[0].importance == 0.9  # high first

    def test_db_path_property(self, db_path):
        store = SQLiteStore(db_path)
        assert store.db_path == db_path

    @pytest.mark.asyncio
    async def test_vacuum(self, store):
        await store.upsert("agent1", MemoryItem(id="v1", agent_id="agent1", content="x", memory_type="semantic"))
        await store.delete("agent1", "v1")
        await store.vacuum()
        # Should not raise
        assert True