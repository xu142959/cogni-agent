"""Core type definitions for CogniAgent."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


# ─── Agent Identity ────────────────────────────────────────────

AgentID = str


class IdentityProfile(BaseModel):
    """Agent's self-identity — who the agent believes they are."""

    agent_id: AgentID
    name: str
    role: str = "assistant"
    personality_traits: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=lambda: ["chat", "tool_use"])
    relationship: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evolved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Messages ──────────────────────────────────────────────────

MessageRole = Literal["system", "user", "assistant", "tool", "agent"]


class Message(BaseModel):
    """The fundamental unit of agent communication."""

    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Memory ────────────────────────────────────────────────────

MemoryType = Literal["working", "semantic", "episodic", "procedural"]


class MemoryItem(BaseModel):
    """A single unit of memory."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    agent_id: AgentID
    content: str
    memory_type: MemoryType
    importance: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Reasoning & Planning ──────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(BaseModel):
    """A single step in a decomposed task plan."""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    tool_required: str | None = None
    result: str | None = None
    error: str | None = None


class TaskPlan(BaseModel):
    """A decomposed plan with dependencies."""

    goal: str
    sub_tasks: list[SubTask]
    reasoning_mode: str
    dependencies: dict[str, list[str]] = Field(default_factory=dict)


# ─── LLM ───────────────────────────────────────────────────────

class LLMConfig(BaseModel):
    """Configuration for an LLM model connection."""

    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: str | None = None
    api_base: str | None = None


class LLMResponse(BaseModel):
    """A response from an LLM call."""

    content: str
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    finish_reason: str = "stop"
    model: str
    usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: int = 0


# ─── Tools ─────────────────────────────────────────────────────

class LLMToolCall(BaseModel):
    """A tool call requested by the LLM."""

    id: str
    name: str
    arguments: str  # JSON string, parsed by the tool executor


class ToolCall(BaseModel):
    """A request to call a tool."""

    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """The result of a tool execution."""

    tool_call_id: str
    content: str
    success: bool = True


# ─── Agent Runtime ─────────────────────────────────────────────

class AgentConfig(BaseModel):
    """Runtime configuration for an agent."""

    max_iterations: int = 10
    max_tool_retries: int = 3
    enable_reflection: bool = True
    enable_memory: bool = True
    working_memory_tokens: int = 4000
    verbose: bool = False


class AgentContext(BaseModel):
    """The complete runtime context of an agent."""

    agent_id: AgentID
    identity: IdentityProfile
    messages: list[Message] = Field(default_factory=list)
    working_memory: list[MemoryItem] = Field(default_factory=list)
    current_plan: TaskPlan | None = None
    config: AgentConfig = Field(default_factory=AgentConfig)


# ─── Evolution ─────────────────────────────────────────────────

class Reflection(BaseModel):
    """Output of a post-task reflection cycle."""

    task_goal: str
    success: bool = True
    insights: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    new_capabilities: list[str] = Field(default_factory=list)
    tool_effectiveness: dict[str, float] = Field(default_factory=dict)
    confidence_delta: float = 0.0
    personality_observations: list[str] = Field(default_factory=list)
