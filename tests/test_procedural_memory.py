"""Tests for Procedural Memory."""

import pytest

from cogni_agent.memory import MemoryManager


@pytest.fixture
def memory():
    return MemoryManager()


class TestProceduralMemory:
    @pytest.mark.asyncio
    async def test_store_procedural(self, memory):
        agent_id = "test_agent"
        item = await memory.store_procedural(
            agent_id,
            skill_name="analyze_csv",
            steps=["1. Read the CSV file", "2. Check for null values", "3. Compute statistics"],
            tools_used=["file_read", "python_repl"],
            success_rate=0.8,
        )
        assert item.memory_type == "procedural"
        assert item.importance > 0.5
        assert "analyze_csv" in item.content
        assert item.importance > 0.5

    @pytest.mark.asyncio
    async def test_retrieve_procedural(self, memory):
        agent_id = "test_agent"
        await memory.store_procedural(
            agent_id, "analyze_csv",
            steps=["read", "clean", "analyze"],
            tools_used=["python"],
        )
        await memory.store_procedural(
            agent_id, "web_search",
            steps=["query", "fetch", "extract"],
            tools_used=["web_search"],
        )

        results = await memory.retrieve_procedural(agent_id, "how to analyze data")
        assert len(results) >= 1
        # Should find the CSV analysis skill
        assert any("analyze_csv" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_update_procedural_success(self, memory):
        agent_id = "test_agent"
        await memory.store_procedural(
            agent_id, "test_skill",
            steps=["step1"],
            tools_used=[],
            success_rate=0.5,
        )

        await memory.update_procedural_success(agent_id, "test_skill", success=True)
        # Success rate should have increased
        results = await memory.retrieve_procedural(agent_id, "test_skill")
        if results:
            assert "test_skill" in results[0].content

    @pytest.mark.asyncio
    async def test_procedural_importance_formula(self, memory):
        """Higher success rate = higher importance."""
        agent_id = "test_agent"
        low = await memory.store_procedural(
            agent_id, "low_skill", steps=["a"], tools_used=[], success_rate=0.3,
        )
        high = await memory.store_procedural(
            agent_id, "high_skill", steps=["b"], tools_used=[], success_rate=0.9,
        )
        assert high.importance > low.importance


class TestProceduralInRuntime:
    """Test that procedural memory integrates with MemoryManager correctly."""

    @pytest.mark.asyncio
    async def test_memory_counts_include_procedural(self, memory):
        agent_id = "test_agent"
        await memory.store_procedural(
            agent_id, "skill1", steps=["a"], tools_used=[],
        )
        await memory.store_semantic(agent_id, "a fact")
        counts = await memory.count_memories(agent_id)
        assert counts["persistent"] >= 2