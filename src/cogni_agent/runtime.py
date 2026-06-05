"""Agent Runtime — orchestrates all components for a complete agent."""

from __future__ import annotations

from cogni_agent.core.types import (
    AgentConfig,
    AgentContext,
    AgentID,
    IdentityProfile,
    LLMConfig,
    Message,
    Reflection,
)
from cogni_agent.core.interfaces import BaseReasoner, LLMGateway
from cogni_agent.evolution import EvolutionEngine
from cogni_agent.identity import IdentityManager
from cogni_agent.llm import LiteLLMGateway
from cogni_agent.memory import MemoryManager
from cogni_agent.reasoning import ReActReasoner
from cogni_agent.tools import BaseTool, ToolRegistry


class AgentRuntime:
    """The main entry point for interacting with a CogniAgent.

    Coordinates:
    - Identity (self-awareness + capability map + relationships)
    - LLM Gateway (model access)
    - Reasoning Engine (thinking + acting via tools)
    - Memory System (remembering)
    - Tools (acting on the world)
    - Evolution (learning from experience and growing)
    """

    def __init__(
        self,
        context: AgentContext,
        llm: LLMGateway,
        reasoner: BaseReasoner,
        identity: IdentityManager,
        memory: MemoryManager,
        tools: ToolRegistry,
        evolution: EvolutionEngine,
    ):
        self.context = context
        self.llm = llm
        self.reasoner = reasoner
        self.identity = identity
        self.memory = memory
        self.tools = tools
        self.evolution = evolution

    @classmethod
    async def create(
        cls,
        name: str,
        role: str = "assistant",
        personality: list[str] | None = None,
        values: list[str] | None = None,
        model: str = "gpt-4o",
        api_key: str | None = None,
        api_base: str | None = None,
        max_iterations: int = 10,
        enable_memory: bool = True,
        enable_evolution: bool = True,
        verbose: bool = False,
        tools: list[BaseTool] | None = None,
    ) -> AgentRuntime:
        """Factory method — create a fully configured agent in one call.

        Args:
            name: Agent's name (forms its identity).
            role: Agent's role (e.g. "research assistant").
            personality: Personality traits (e.g. ["thorough", "curious"]).
            values: Core values (e.g. ["accuracy", "helpfulness"]).
            model: LLM model identifier (litellm format). Use "openai/..." for custom API base.
            api_key: API key (defaults to env var).
            api_base: Custom API base URL (e.g. for NVIDIA, Ollama, vLLM).
            max_iterations: Max reasoning loop iterations.
            enable_memory: Enable semantic memory.
            enable_evolution: Enable post-task evolution cycle.
            verbose: Enable detailed logging.
            tools: List of BaseTool instances the agent can use.
        """
        llm_cfg = LLMConfig(
            model=model,
            api_key=api_key,
            api_base=api_base,
        )
        llm = LiteLLMGateway(config=llm_cfg)
        config = AgentConfig(
            max_iterations=max_iterations,
            enable_memory=enable_memory,
            verbose=verbose,
        )

        tool_registry = ToolRegistry()
        if tools:
            for tool in tools:
                tool_registry.register(tool)

        identity = IdentityManager()
        context = await identity.create_agent(
            name=name,
            role=role,
            personality=personality,
            values=values,
            config=config,
        )
        reasoner = ReActReasoner(
            llm=llm,
            tool_registry=tool_registry,
            max_iterations=max_iterations,
        )
        memory = MemoryManager(llm=llm)
        evolution = EvolutionEngine(
            llm=llm, identity=identity, memory=memory,
        )

        return cls(
            context=context,
            llm=llm,
            reasoner=reasoner,
            identity=identity,
            memory=memory,
            tools=tool_registry,
            evolution=evolution,
        )

    async def run(self, user_input: str) -> str:
        """Process a user input through the full cognitive pipeline.

        Flow:
        1. Record input + relationship to working memory
        2. Retrieve relevant semantic memories
        3. Inject self-awareness context
        4. Execute reasoning loop (with tool calls)
        5. Post-task reflection → capability update → evolution → memory extraction
        6. Return result
        """
        agent_id = self.context.agent_id

        # 1. Record interaction + relationship
        self.memory.push_working(
            agent_id,
            f"User: {user_input}",
        )
        self.identity.record_interaction(
            agent_id,
            entity_id="user_main",
            entity_name="User",
            role="user",
        )

        # 2. Retrieve relevant semantic memories
        enhanced_input = user_input
        if self.context.config.enable_memory:
            relevant = await self.memory.retrieve_relevant(
                agent_id, query=user_input, top_k=3,
            )
            memory_context = ""
            if relevant:
                memory_context = "\n".join(
                    f"[经验] {item.content}" for item in relevant
                )

            # 3. Inject self-awareness context
            relationship_context = self.identity.get_relationship_context(agent_id)

            context_parts = []
            if memory_context:
                context_parts.append(f"Relevant past experience:\n{memory_context}")
            if relationship_context and len(self.identity._relationships.get(agent_id, {})) > 1:
                context_parts.append(relationship_context)

            if context_parts:
                enhanced_input = (
                    f"{user_input}\n\n"
                    f"--- Internal Context ---\n"
                    f"{chr(10).join(context_parts)}"
                )

        # 4. Plan + Execute (with tool calls)
        plan = await self.reasoner.plan(enhanced_input, self.context)
        result = await self.reasoner.execute(plan, self.context)

        # 5. Post-task processing
        # 5a. Update tool use capabilities
        if plan.sub_tasks and any(t.tool_required for t in plan.sub_tasks):
            for task in plan.sub_tasks:
                if task.tool_required:
                    self.identity.record_capability_use(
                        agent_id, task.tool_required, success=(task.status == "completed")
                    )

        # 5b. Run the full evolution cycle
        if self.context.config.enable_memory:
            evo_result = await self.evolution.evolve(
                agent_id=agent_id,
                task_input=user_input,
                task_output=result,
                profile=self.context.identity,
                identity=self.identity,
                memory=self.memory,
                context=self.context,
            )
            self._last_evolution = evo_result

        # Push result to working memory
        self.memory.push_working(
            agent_id,
            f"{self.context.identity.name}: {result[:200]}",
        )

        return result

    async def chat(self, user_input: str) -> str:
        """Alias for run() — supports conversational use."""
        return await self.run(user_input)

    async def reset_conversation(self) -> None:
        """Reset the conversation, keeping identity, capabilities, and long-term memory."""
        self.context.messages = [
            self.identity._build_system_message(self.context.identity),
        ]
        self.memory.clear_working(self.context.agent_id)

    def get_capability_map(self) -> list[dict]:
        """Return the agent's current capability self-map."""
        return self.identity.get_capabilities(self.context.agent_id)

    def get_evolution_history(self) -> list[dict]:
        """Return the agent's evolution timeline."""
        return self.identity.get_evolution_history(self.context.agent_id)

    def get_last_evolution(self) -> dict | None:
        """Return the last evolution cycle result."""
        return getattr(self, "_last_evolution", None)

    def get_self_summary(self) -> str:
        """Return the agent's full self-awareness report."""
        return self.identity.get_self_summary(self.context.agent_id)

    @property
    def agent_id(self) -> AgentID:
        return self.context.agent_id

    @property
    def profile(self) -> IdentityProfile:
        return self.context.identity

    def __repr__(self) -> str:
        return (
            f"AgentRuntime(name='{self.context.identity.name}', "
            f"role='{self.context.identity.role}', "
            f"id='{self.context.agent_id[:8]}...')"
        )