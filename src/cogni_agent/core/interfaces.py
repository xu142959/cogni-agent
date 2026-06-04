"""Abstract interfaces for pluggable CogniAgent components."""

from __future__ import annotations

from abc import ABC, abstractmethod

from cogni_agent.core.types import (
    AgentContext,
    IdentityProfile,
    LLMConfig,
    LLMResponse,
    MemoryItem,
    Message,
    Reflection,
    TaskPlan,
    ToolCall,
    ToolResult,
)


# ─── LLM Gateway ───────────────────────────────────────────────

class LLMGateway(ABC):
    """Unified interface for LLM model access."""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        config_override: LLMConfig | None = None,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...


# ─── Reasoning ─────────────────────────────────────────────────

class BaseReasoner(ABC):
    """Base class for all reasoning strategies."""

    @abstractmethod
    async def plan(self, goal: str, context: AgentContext) -> TaskPlan:
        """Decompose a goal into an executable plan."""
        ...

    @abstractmethod
    async def execute(self, plan: TaskPlan, context: AgentContext) -> str:
        """Execute a plan and return the result."""
        ...


# ─── Identity ──────────────────────────────────────────────────

class IdentityStore(ABC):
    """Storage backend for agent identity profiles."""

    @abstractmethod
    async def save_profile(self, profile: IdentityProfile) -> None:
        ...

    @abstractmethod
    async def load_profile(self, agent_id: str) -> IdentityProfile | None:
        ...

    @abstractmethod
    async def update_profile(self, profile: IdentityProfile) -> None:
        ...


# ─── Memory ────────────────────────────────────────────────────

class MemoryStore(ABC):
    """Storage backend for memory items."""

    @abstractmethod
    async def upsert(self, agent_id: str, item: MemoryItem) -> None:
        ...

    @abstractmethod
    async def search(
        self,
        agent_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[MemoryItem]:
        ...

    @abstractmethod
    async def delete(self, agent_id: str, item_id: str) -> None:
        ...


# ─── Tools ─────────────────────────────────────────────────────

class BaseTool(ABC):
    """Base class for all tools."""

    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs) -> str:
        """Execute the tool with given arguments."""
        ...

    def to_openai_tool(self) -> dict:
        """Return the tool definition in OpenAI function calling format."""
        ...


# ─── Reflection / Evolution ────────────────────────────────────

class EvolutionEngine(ABC):
    """Handles post-task reflection and agent evolution."""

    @abstractmethod
    async def reflect(
        self,
        context: AgentContext,
        task_input: str,
        task_output: str,
    ) -> Reflection:
        """Analyze a completed task and produce insights."""
        ...

    @abstractmethod
    async def evolve(
        self,
        context: AgentContext,
        reflection: Reflection,
    ) -> IdentityProfile:
        """Update the agent's identity based on reflection insights."""
        ...
