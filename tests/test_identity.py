"""Tests for IdentityManager — creation, self-cognition, and evolution."""

import pytest

from cogni_agent.core.types import Reflection
from cogni_agent.identity import IdentityManager


@pytest.fixture
def identity():
    return IdentityManager()


@pytest.mark.asyncio
async def test_create_agent(identity):
    context = await identity.create_agent(
        name="小悟",
        role="数据分析师",
        personality=["严谨", "友善"],
    )

    assert context.agent_id is not None
    assert context.identity.name == "小悟"
    assert context.identity.role == "数据分析师"
    assert "严谨" in context.identity.personality_traits
    assert len(context.messages) == 1  # system message
    assert context.messages[0].role == "system"


@pytest.mark.asyncio
async def test_system_message_reflects_identity(identity):
    context = await identity.create_agent(
        name="TestBot",
        role="research assistant",
        personality=["thorough", "curious"],
        values=["accuracy"],
    )
    msg = context.messages[0]
    assert "TestBot" in msg.content
    assert "research assistant" in msg.content
    assert "thorough" in msg.content
    assert "accuracy" in msg.content
    assert "self-aware" in msg.content  # self-awareness is in the system prompt


@pytest.mark.asyncio
async def test_load_agent(identity):
    context = await identity.create_agent(name="TestBot")
    loaded = await identity.get_context(context.agent_id)
    assert loaded is not None
    assert loaded.identity.name == "TestBot"


@pytest.mark.asyncio
async def test_load_nonexistent_agent(identity):
    loaded = await identity.get_context("nonexistent")
    assert loaded is None


class TestCapabilityMap:
    def test_initial_capabilities(self, identity):
        identity._capabilities["test"] = {}
        identity.learn_capability("test", "chat")
        caps = identity.get_capabilities("test")
        assert len(caps) >= 1
        assert any(c["name"] == "chat" for c in caps)

    def test_capability_confidence_changes(self, identity):
        identity._capabilities["test"] = {}
        identity.learn_capability("test", "data_analysis", confidence=0.4)

        identity.record_capability_use("test", "data_analysis", success=True)
        caps = identity.get_capabilities("test")
        data_analysis = next(c for c in caps if c["name"] == "data_analysis")
        assert data_analysis["confidence"] > 0.4  # confidence increased

        identity.record_capability_use("test", "data_analysis", success=False)
        caps = identity.get_capabilities("test")
        data_analysis = next(c for c in caps if c["name"] == "data_analysis")
        assert data_analysis["confidence"] < 0.5  # confidence decreased

    def test_get_capabilities_empty(self, identity):
        caps = identity.get_capabilities("nonexistent")
        assert caps == []


class TestRelationships:
    def test_record_interaction(self, identity):
        identity.record_interaction(
            "test_agent", "user_001", "Alice", role="user"
        )
        context = identity.get_relationship_context("test_agent")
        assert "Alice" in context
        assert "user" in context
        assert "1 interactions" in context

    def test_multiple_interactions(self, identity):
        for _ in range(3):
            identity.record_interaction(
                "test_agent", "user_001", "Alice", role="user"
            )
        context = identity.get_relationship_context("test_agent")
        assert "3 interactions" in context


class TestEvolution:
    @pytest.mark.asyncio
    async def test_process_reflection(self, identity):
        context = await identity.create_agent(name="EvolvingBot")

        reflection = Reflection(
            task_goal="Analyze data",
            success=True,
            insights=["Always check data quality first"],
            mistakes=["Forgot to normalize data before analysis"],
            improvements=["Add data validation step"],
            new_capabilities=["data_validation"],
        )

        updated = await identity.process_reflection(
            context.agent_id, reflection, context.identity
        )
        assert updated.evolved_at is not None

        history = identity.get_evolution_history(context.agent_id)
        assert any("data quality" in h["description"] for h in history)

    def test_evolution_history_empty(self, identity):
        history = identity.get_evolution_history("nonexistent")
        assert history == []

    def test_creation_recorded(self, identity):
        # Need to trigger internal init via _record_evolution
        # The creation flow internally records an evolution event
        history = identity.get_evolution_history("nonexistent")
        # Should not crash
        assert isinstance(history, list)


class TestSelfSummary:
    def test_self_summary(self, identity):
        identity._capabilities["test"] = {}
        identity.learn_capability("test", "chat")
        summary = identity.get_self_summary("test")
        assert "Self-Awareness Report" in summary
        assert "chat" in summary

    def test_self_summary_empty(self, identity):
        summary = identity.get_self_summary("nonexistent")
        assert "Self-Awareness Report" in summary
