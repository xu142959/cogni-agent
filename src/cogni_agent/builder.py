"""Agent Builder — fluent API for constructing agents."""

from __future__ import annotations

from cogni_agent.core.types import AgentConfig
from cogni_agent.runtime import AgentRuntime
from cogni_agent.tools import BaseTool


class AgentBuilder:
    """Fluent builder for constructing AgentRuntime instances.

    Usage:
        agent = await (
            AgentBuilder()
            .with_name("小悟")
            .with_role("数据分析助手")
            .with_personality("严谨", "友善")
            .with_values("数据驱动", "保护隐私")
            .with_model("gpt-4o")
            .with_max_iterations(15)
            .with_tools(tool1, tool2)
            .verbose()
            .build()
        )
    """

    def __init__(self):
        self._name: str = "Assistant"
        self._role: str = "assistant"
        self._personality: list[str] = []
        self._values: list[str] = []
        self._model: str = "gpt-4o"
        self._max_iterations: int = 10
        self._enable_memory: bool = True
        self._tools: list[BaseTool] = []
        self._verbose: bool = False

    def with_name(self, name: str) -> AgentBuilder:
        self._name = name
        return self

    def with_role(self, role: str) -> AgentBuilder:
        self._role = role
        return self

    def with_personality(self, *traits: str) -> AgentBuilder:
        self._personality = list(traits)
        return self

    def with_values(self, *values: str) -> AgentBuilder:
        self._values = list(values)
        return self

    def with_model(self, model: str) -> AgentBuilder:
        self._model = model
        return self

    def with_max_iterations(self, n: int) -> AgentBuilder:
        self._max_iterations = n
        return self

    def with_memory(self, enabled: bool = True) -> AgentBuilder:
        self._enable_memory = enabled
        return self

    def with_tools(self, *tools: BaseTool) -> AgentBuilder:
        self._tools = list(tools)
        return self

    def verbose(self, enabled: bool = True) -> AgentBuilder:
        self._verbose = enabled
        return self

    async def build(self) -> AgentRuntime:
        """Construct and return the configured AgentRuntime."""
        return await AgentRuntime.create(
            name=self._name,
            role=self._role,
            personality=self._personality,
            values=self._values,
            model=self._model,
            max_iterations=self._max_iterations,
            enable_memory=self._enable_memory,
            verbose=self._verbose,
            tools=self._tools,
        )


# Shortcut
builder = AgentBuilder