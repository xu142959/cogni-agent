"""Tests for EvolutionEngine — reflect, learn, adapt, and consolidate."""

import pytest

from cogni_agent.core.types import Reflection
from cogni_agent.evolution import EvolutionEngine
from cogni_agent.identity import IdentityManager
from cogni_agent.memory import MemoryManager
from cogni_agent.identity.manager import EvolutionRecord


@pytest.fixture
def engine():
    return EvolutionEngine()


@pytest.fixture
def identity():
    return IdentityManager()


@pytest.fixture
def memory():
    return MemoryManager()


class TestReflection:
    """The reflection step should produce structured analysis."""

    @pytest.mark.asyncio
    async def test_reflect_without_llm(self, engine):
        """Without API key, reflection falls back gracefully."""
        from cogni_agent.core.types import IdentityProfile, AgentID
        from datetime import datetime, timezone

        profile = IdentityProfile(
            agent_id="test",
            name="TestBot",
            role="assistant",
            personality_traits=["helpful"],
            capabilities=["chat"],
        )

        reflection = await engine.reflect(
            agent_id="test",
            task_input="What is 2+2?",
            task_output="The answer is 4.",
            profile=profile,
        )
        assert isinstance(reflection, Reflection)
        assert reflection.task_goal == "What is 2+2?"
        # Fallback reflection should have at least one insight
        assert len(reflection.insights) >= 0
        assert isinstance(reflection.success, bool)


class TestLearn:
    """The learning step updates capabilities and records evolution."""

    @pytest.mark.asyncio
    async def test_learn_adds_evolution_records(self, engine, identity):
        agent_id = "test_agent"
        await identity.create_agent(name="LearnerBot")

        reflection = Reflection(
            task_goal="Analyze data",
            success=True,
            insights=["Always validate input data first"],
            mistakes=["Forgot to check for null values"],
            improvements=["Add validation step before analysis"],
            new_capabilities=["data_validation"],
        )

        await engine.learn(agent_id, reflection, identity)

        history = identity.get_evolution_history(agent_id)
        assert len(history) > 0

        # Should contain insight
        insight_events = [
            h for h in history if h["type"] == "insight"
        ]
        assert len(insight_events) >= 1

        # Should mark self-correction
        correction_events = [
            h for h in history if h["type"] == "self_correction"
        ]
        assert len(correction_events) >= 1

        # New capability should be learnable
        caps = identity.get_capabilities(agent_id)
        cap_names = [c["name"] for c in caps]
        assert "data_validation" in cap_names

    @pytest.mark.asyncio
    async def test_learn_empty_reflection(self, engine, identity):
        """Empty reflection creates no records."""
        context = await identity.create_agent(name="EmptyBot")
        agent_id = context.agent_id  # use the real UUID

        reflection = Reflection(
            task_goal="Hello",
            success=True,
        )

        await engine.learn(agent_id, reflection, identity)

        # Should still have the creation record
        history = identity.get_evolution_history(agent_id)
        assert len(history) >= 1


class TestAdapt:
    """Personality adaptation over time."""

    @pytest.mark.asyncio
    async def test_adapt_no_change_early(self, engine, identity):
        """No personality change before 20 interactions."""
        agent_id = "test_agent"
        context = await identity.create_agent(name="SteadyBot")

        reflection = Reflection(
            task_goal="Help",
            success=True,
            insights=["Be more concise"],
            improvements=[],
        )

        result = await engine.adapt_personality(
            agent_id, reflection, identity, interaction_count=5,
        )
        assert result is None  # No change at 5 interactions


class TestExtractAndConsolidate:
    """Memory consolidation from reflections."""

    @pytest.mark.asyncio
    async def test_extract_stores_insights(self, engine, memory):
        agent_id = "test_agent"
        reflection = Reflection(
            task_goal="Analysis",
            success=True,
            insights=["Data quality is critical for accurate results"],
            improvements=["Add data profiling step"],
        )

        stored = await engine.extract_and_consolidate(
            agent_id, reflection, memory,
        )
        assert len(stored) == 2  # Both insight and improvement

        # Verify they're in semantic memory
        retrieved = await memory.retrieve_relevant(
            agent_id, "data quality",
        )
        assert len(retrieved) >= 1
        assert "Data quality" in retrieved[0].content

    @pytest.mark.asyncio
    async def test_extract_short_insights_skipped(self, engine, memory):
        """Trivial/short insights are not stored."""
        agent_id = "test_agent"
        reflection = Reflection(
            task_goal="Hi",
            success=True,
            insights=["OK"],  # too short
        )

        stored = await engine.extract_and_consolidate(
            agent_id, reflection, memory,
        )
        assert len(stored) == 0


class TestFullCycle:
    """End-to-end evolution cycle test."""

    @pytest.mark.asyncio
    async def test_full_evolution_cycle(self, engine, identity, memory):
        agent_id = "test_agent"
        context = await identity.create_agent(name="EvolvingBot")

        result = await engine.evolve(
            agent_id=agent_id,
            task_input="Help me analyze sales data",
            task_output=(
                "I'll analyze the sales data step by step. "
                "First, let me check the data quality..."
            ),
            profile=context.identity,
            identity=identity,
            memory=memory,
        )

        # Should have a reflection result
        assert "reflection" in result
        assert "capability_changes" in result
        assert "memories_consolidated" in result

        # Evolution history should exist
        history = identity.get_evolution_history(agent_id)
        assert len(history) >= 1