"""Tests for AgentBuilder."""

import pytest

from cogni_agent.builder import AgentBuilder
from cogni_agent.tools.builtin import Calculator


@pytest.mark.asyncio
async def test_build_minimal():
    agent = await AgentBuilder().with_name("TestBot").build()
    assert agent.context.identity.name == "TestBot"
    assert agent.context.identity.role == "assistant"


@pytest.mark.asyncio
async def test_build_full():
    agent = await (
        AgentBuilder()
        .with_name("小悟")
        .with_role("data analyst")
        .with_personality("严谨", "友善")
        .with_values("accuracy")
        .with_model("gpt-4o-mini")
        .with_max_iterations(15)
        .with_tools(Calculator())
        .verbose()
        .build()
    )
    assert agent.context.identity.name == "小悟"
    assert agent.context.identity.role == "data analyst"
    assert "严谨" in agent.context.identity.personality_traits
    assert "accuracy" in agent.context.identity.values
    assert agent.context.config.max_iterations == 15
    assert agent.context.config.verbose is True
    assert agent.tools.get("calculator") is not None
