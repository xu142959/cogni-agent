"""Integration tests — end-to-end tests using real LLM APIs.

These tests require API keys:
  OPENAI_API_KEY   — for GPT models
  ANTHROPIC_API_KEY — for Claude models

Run with:
  OPENAI_API_KEY=sk-... pytest tests/integration/ -v
  OPENAI_API_KEY=sk-... pytest tests/integration/test_e2e_basic.py -v

To skip tests that require API keys:
  pytest tests/integration/ -v -k "not needs_api"
"""

import os
import pytest

from cogni_agent import AgentRuntime
from cogni_agent.tools import Calculator, WebSearch


pytestmark = pytest.mark.asyncio


# ─── Helpers ────────────────────────────────────────────────

def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def has_anthropic_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))

needs_api = pytest.mark.skipif(
    not has_openai_key() and not has_anthropic_key(),
    reason="Requires OPENAI_API_KEY or ANTHROPIC_API_KEY",
)


# ─── E2E: Basic Chat ────────────────────────────────────────

@needs_api
class TestBasicChat:
    """Minimal smoke test — create an agent and have a conversation."""

    async def test_simple_response(self):
        """Agent should return a coherent response to a simple question."""
        agent = await AgentRuntime.create(
            name="TestBot",
            role="helpful assistant",
            personality=["concise", "accurate"],
            model="gpt-4o-mini",
            max_iterations=3,
        )
        response = await agent.run("What is 2 + 2?")
        assert "4" in response
        assert len(response) > 0

    async def test_identity_awareness(self):
        """Agent should know its own name."""
        agent = await AgentRuntime.create(
            name="小悟",
            role="数据分析助手",
            personality=["友善"],
        )
        response = await agent.run("What's your name?")
        assert "小悟" in response

    async def test_conversation_memory(self):
        """Agent should remember previous context within a session."""
        agent = await AgentRuntime.create(
            name="MemoryBot", max_iterations=3,
        )
        await agent.run("My name is Alice.")
        response = await agent.run("What's my name?")
        assert "Alice" in response


# ─── E2E: Tool Calling ──────────────────────────────────────

@needs_api
class TestToolCalling:
    """Agent should autonomously decide to use tools."""

    async def test_calculator_tool(self):
        """Agent should use the calculator for math."""
        agent = await AgentRuntime.create(
            name="CalcBot",
            personality=["mathematical"],
            tools=[Calculator()],
            model="gpt-4o-mini",
        )
        response = await agent.run("Calculate (187 + 243) * 15")
        # The agent should call calculator and produce a number
        assert "6450" in response.replace(",", "")

    async def test_web_search_tool(self):
        """Agent should search the web for current information."""
        agent = await AgentRuntime.create(
            name="SearchBot",
            tools=[WebSearch()],
            model="gpt-4o-mini",
        )
        response = await agent.run(
            "Who won the most recent Super Bowl? Search the web."
        )
        assert len(response) > 20  # should return real content

    async def test_tool_selection(self):
        """Agent should pick the right tool from multiple options."""
        agent = await AgentRuntime.create(
            name="ToolBot",
            tools=[Calculator(), WebSearch()],
            model="gpt-4o-mini",
        )
        # This requires calculation — should pick calculator
        response = await agent.run("What is the square root of 144?")
        assert "12" in response


# ─── E2E: Memory Persistence ────────────────────────────────

@needs_api
class TestMemoryPersistence:
    """Agent should extract and retrieve semantic memories."""

    async def test_semantic_memory_across_turns(self):
        """Agent should remember extracted insights."""
        agent = await AgentRuntime.create(
            name="MemoryBot",
            personality=["observant"],
            enable_memory=True,
        )
        # First conversation: extract a memory
        await agent.run("I prefer detailed technical explanations.")
        await agent.run("I work as a data engineer.")

        # Second conversation: should retrieve the memory
        response = await agent.run(
            "What do you remember about my preferences and work?"
        )
        assert "detailed" in response.lower() or "data engineer" in response.lower() or "technical" in response.lower()


# ─── E2E: Non-API Fallback (no LLM) ────────────────────────

class TestLocalFallback:
    """Tests that work without API keys (use fallback behaviors)."""

    async def test_agent_creation(self):
        """Agent creation should never require API keys."""
        agent = await AgentRuntime.create(
            name="LocalBot",
            personality=["quiet"],
        )
        assert agent.profile.name == "LocalBot"
        assert agent.profile.personality_traits == ["quiet"]

    async def test_agent_info_api(self):
        """Self-summary and evolution APIs work without API calls."""
        agent = await AgentRuntime.create(name="InfoBot")
        summary = agent.get_self_summary()
        assert "Self-Awareness Report" in summary
        assert "chat" in summary and "tool_use" in summary

    async def test_tool_definition(self):
        """Tool definitions are available without API calls."""
        agent = await AgentRuntime.create(
            name="ToolBot",
            tools=[Calculator(), WebSearch()],
        )
        assert agent.tools.get("calculator") is not None
        assert agent.tools.get("web_search") is not None
        assert len(agent.tools.list_all()) == 2