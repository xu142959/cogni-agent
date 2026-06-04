"""Tests for CogniAgent core types."""

from datetime import datetime

from cogni_agent.core.types import (
    AgentConfig,
    AgentContext,
    IdentityProfile,
    LLMConfig,
    LLMResponse,
    MemoryItem,
    Message,
    SubTask,
    TaskPlan,
    TaskStatus,
)


class TestIdentityProfile:
    def test_default_values(self):
        profile = IdentityProfile(agent_id="test_1", name="TestAgent")
        assert profile.agent_id == "test_1"
        assert profile.name == "TestAgent"
        assert profile.role == "assistant"
        assert profile.personality_traits == []
        assert profile.capabilities == ["chat", "tool_use"]
        assert isinstance(profile.created_at, datetime)

    def test_full_profile(self):
        profile = IdentityProfile(
            agent_id="test_2",
            name="小悟",
            role="数据分析师",
            personality_traits=["严谨", "友善"],
            values=["数据驱动"],
        )
        assert "严谨" in profile.personality_traits
        assert "数据驱动" in profile.values


class TestMessage:
    def test_create_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)

    def test_system_message(self):
        msg = Message(role="system", content="You are a helpful assistant.")
        assert msg.role == "system"


class TestMemoryItem:
    def test_default_importance(self):
        item = MemoryItem(agent_id="test_1", content="test", memory_type="working")
        assert item.importance == 0.0
        assert item.memory_type == "working"

    def test_high_importance(self):
        item = MemoryItem(
            agent_id="test_1",
            content="important insight",
            memory_type="semantic",
            importance=0.9,
        )
        assert item.importance == 0.9


class TestTaskPlan:
    def test_create_plan(self):
        task = SubTask(id="step_1", description="分析数据")
        plan = TaskPlan(
            goal="完成数据分析",
            sub_tasks=[task],
            reasoning_mode="react",
        )
        assert plan.goal == "完成数据分析"
        assert len(plan.sub_tasks) == 1
        assert plan.sub_tasks[0].status == TaskStatus.PENDING


class TestLLMConfig:
    def test_default_config(self):
        config = LLMConfig()
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_custom_config(self):
        config = LLMConfig(
            model="claude-sonnet-4-6",
            temperature=0.3,
            max_tokens=8192,
        )
        assert config.model == "claude-sonnet-4-6"
        assert config.temperature == 0.3


class TestAgentConfig:
    def test_defaults(self):
        config = AgentConfig()
        assert config.max_iterations == 10
        assert config.enable_reflection is True
        assert config.enable_memory is True
