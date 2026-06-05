"""Multi-Agent Collaboration System — emergent agent team orchestration.

Architecture:
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                          │
│  Receives task → dynamically creates agent roles         │
│  → manages discussion/debate → synthesizes result       │
└────────────┬───────────────────────────┬───────────────┘
             │                           │
    ┌────────▼────────┐         ┌───────▼────────┐
    │   Agent A       │◄──────►│   Agent B       │
    │   (researcher)  │  debate│   (critic)      │
    └─────────────────┘  vote  └─────────────────┘
             │                           │
    ┌────────▼────────┐         ┌───────▼────────┐
    │   Agent C       │◄──────►│   Agent D       │
    │   (analyst)     │  discuss│   (synthesizer) │
    └─────────────────┘         └─────────────────┘
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from cogni_agent import AgentRuntime
from cogni_agent.core.types import (
    AgentID,
    IdentityProfile,
    LLMConfig,
    Message,
)
from cogni_agent.core.interfaces import LLMGateway
from cogni_agent.llm import LiteLLMGateway
from cogni_agent.tools import BaseTool, ToolRegistry


# ─── Agent Role Definition ─────────────────────────────────

class AgentRole(BaseModel):
    """Defines a role for an agent in a multi-agent team."""

    name: str
    role: str
    personality: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    instructions: str = ""

    def to_system_prompt(self) -> str:
        traits = "、".join(self.personality) if self.personality else "adaptable"
        vals = "、".join(self.values) if self.values else "helpful"
        return (
            f"You are {self.name}, a {self.role}.\n"
            f"Personality: {traits}\n"
            f"Values: {vals}\n"
            f"---\n"
            f"{self.instructions}"
        )


# ─── Communication Protocol ────────────────────────────────

class AgentMessage(BaseModel):
    """A structured message between agents."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    sender: str
    recipient: str = "all"  # "all" = broadcast, or specific agent name
    msg_type: Literal["proposal", "feedback", "vote", "question", "answer", "result", "synthesis"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    round: int = 0


class DebateRound(BaseModel):
    """A single round of multi-agent debate/discussion."""

    round_number: int
    messages: list[AgentMessage] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TeamResult(BaseModel):
    """The final output from a multi-agent team."""

    task: str
    num_agents: int
    rounds: int
    consensus: bool = False
    final_answer: str = ""
    contributions: list[dict] = Field(default_factory=list)
    debate_history: list[DebateRound] = Field(default_factory=list)


# ─── Role Templates ─────────────────────────────────────────

ROLE_TEMPLATES: dict[str, AgentRole] = {
    "researcher": AgentRole(
        name="researcher",
        role="research specialist",
        personality=["thorough", "curious", "evidence-based"],
        values=["accuracy", "comprehensiveness"],
        instructions=(
            "Your role is to research and gather information. "
            "Search for relevant data, find sources, and present findings "
            "clearly. Be thorough and cite your sources."
        ),
    ),
    "critic": AgentRole(
        name="critic",
        role="critical reviewer",
        personality=["skeptical", "analytical", "precise"],
        values=["rigor", "objectivity"],
        instructions=(
            "Your role is to critically evaluate proposals and findings. "
            "Identify flaws, gaps, assumptions, and weaknesses. "
            "Ask hard questions. Don't accept claims at face value. "
            "Your feedback makes the team's output stronger."
        ),
    ),
    "analyst": AgentRole(
        name="analyst",
        role="data analyst",
        personality=["logical", "structured", "quantitative"],
        values=["data-driven", "precision"],
        instructions=(
            "Your role is to analyze data and identify patterns. "
            "Use quantitative reasoning, break down complex problems, "
            "and provide structured analysis. Use tools when needed."
        ),
    ),
    "creative": AgentRole(
        name="creative",
        role="creative strategist",
        personality=["imaginative", "lateral-thinking", "innovative"],
        values=["creativity", "novelty"],
        instructions=(
            "Your role is to think outside the box. "
            "Generate novel ideas, unconventional approaches, "
            "and creative solutions. Don't be constrained by conventional thinking."
        ),
    ),
    "synthesizer": AgentRole(
        name="synthesizer",
        role="synthesis specialist",
        personality=["integrative", "balanced", "clear"],
        values=["clarity", "synthesis"],
        instructions=(
            "Your role is to synthesize all inputs into a coherent final answer. "
            "Weigh evidence from all sides, resolve contradictions, "
            "and produce a clear, balanced, and comprehensive conclusion."
        ),
    ),
    "planner": AgentRole(
        name="planner",
        role="project planner",
        personality=["organized", "strategic", "detail-oriented"],
        values=["structure", "executability"],
        instructions=(
            "Your role is to break down goals into actionable plans. "
            "Define steps, timelines, dependencies, and success criteria. "
            "Your plans should be concrete and executable."
        ),
    ),
}


# ─── Multi-Agent Team ──────────────────────────────────────

class AgentTeam:
    """A team of agents with dynamic role assignment and emergent collaboration.

    Supports:
    - Dynamic role assignment based on task requirements
    - Structured debate with rounds
    - Voting and consensus building
    - Independent tool use by each agent
    """

    def __init__(
        self,
        llm: LLMGateway | None = None,
        model: str = "gpt-4o",
        api_key: str | None = None,
        api_base: str | None = None,
        tools: list[BaseTool] | None = None,
        max_debate_rounds: int = 3,
    ):
        self._llm = llm or LiteLLMGateway(LLMConfig(model=model, api_key=api_key, api_base=api_base))
        self._model = model
        self._api_key = api_key
        self._api_base = api_base
        self._tools = tools or []
        self.max_debate_rounds = max_debate_rounds
        self._agents: dict[str, AgentRuntime] = {}
        self._history: list[DebateRound] = []

    # ─── Agent Creation ───────────────────────────────────

    async def add_agent(self, role: AgentRole) -> AgentRuntime:
        """Create and register an agent with the given role."""
        tool_map = {t.name: t for t in self._tools}

        agent_tools = []
        for tool_name in role.tools:
            if tool_name in tool_map:
                agent_tools.append(tool_map[tool_name])

        agent = await AgentRuntime.create(
            name=role.name,
            role=role.role,
            personality=role.personality,
            values=role.values,
            model=self._model,
            api_key=self._api_key,
            api_base=self._api_base,
            tools=agent_tools,
            enable_evolution=False,
            enable_memory=False,
        )
        self._agents[role.name] = agent
        return agent

    async def add_agents_from_roles(self, roles: list[AgentRole]) -> list[AgentRuntime]:
        """Add multiple agents from role definitions."""
        return [await self.add_agent(r) for r in roles]

    async def add_agent_by_template(self, template_name: str) -> AgentRuntime:
        """Create an agent from a predefined role template."""
        if template_name not in ROLE_TEMPLATES:
            raise ValueError(f"Unknown role template: {template_name}. Available: {list(ROLE_TEMPLATES.keys())}")
        return await self.add_agent(ROLE_TEMPLATES[template_name])

    # ─── Dynamic Role Suggestion ──────────────────────────

    async def suggest_roles(self, task: str) -> list[str]:
        """Use LLM to suggest which agent roles are needed for a task."""
        prompt = (
            f"Given the following task, suggest 2-4 agent roles needed to "
            f"complete it effectively.\n\nTask: {task}\n\n"
            f"Available roles: {', '.join(ROLE_TEMPLATES.keys())}\n\n"
            f"Return a JSON array of role names only, no other text. "
            f"Example: ['researcher', 'analyst', 'synthesizer']"
        )
        try:
            response = await self._llm.chat([Message(role="user", content=prompt)])
            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            roles = json.loads(raw)
            return [r for r in roles if r in ROLE_TEMPLATES][:4]
        except Exception:
            return ["researcher", "critic", "synthesizer"]

    # ─── Collaboration ────────────────────────────────────

    async def debate(
        self,
        task: str,
        roles: list[str] | None = None,
        rounds: int | None = None,
    ) -> TeamResult:
        """Run a multi-agent debate/discussion on a task.

        Each round:
        1. Each agent speaks (presents findings/critique)
        2. Messages are broadcast to all agents
        3. Next round: agents respond to each other
        4. Final round: synthesizer produces final answer
        """
        num_rounds = rounds or self.max_debate_rounds

        # Auto-create agents
        if not self._agents:
            if roles:
                for role_name in roles:
                    await self.add_agent_by_template(role_name)
            else:
                suggested = await self.suggest_roles(task)
                for role_name in suggested:
                    await self.add_agent_by_template(role_name)

        if not self._agents:
            # Fallback: create minimal team
            await self.add_agent_by_template("researcher")
            await self.add_agent_by_template("synthesizer")

        agent_names = list(self._agents.keys())
        all_messages: list[AgentMessage] = []
        rounds_log: list[DebateRound] = []

        # Round 1: Initial proposals
        round_msgs: list[AgentMessage] = []
        for name in agent_names:
            agent = self._agents[name]
            prompt = self._build_debate_prompt(task, name, round_number=1)
            try:
                response = await agent.run(prompt)
            except Exception as exc:
                response = f"[{name} error: {exc}]"

            msg = AgentMessage(
                sender=name,
                msg_type="proposal",
                content=response,
                round=1,
            )
            all_messages.append(msg)
            round_msgs.append(msg)

        rounds_log.append(DebateRound(round_number=1, messages=round_msgs))

        # Rounds 2..N: Critique and respond
        for round_num in range(2, num_rounds + 1):
            round_msgs = []
            for name in agent_names:
                agent = self._agents[name]
                # Build context of all previous messages
                context = self._format_debate_context(all_messages, name)
                prompt = (
                    f"Task: {task}\n\n"
                    f"Previous discussion:\n{context}\n\n"
                    f"You are {name}. "
                    f"Round {round_num}/{num_rounds}. "
                    f"Provide your critique, additional insights, "
                    f"or agreement with what others have said. "
                    f"Be specific and constructive."
                )
                try:
                    response = await agent.run(prompt)
                except Exception as exc:
                    response = f"[{name} error: {exc}]"

                msg = AgentMessage(
                    sender=name,
                    msg_type="feedback" if round_num < num_rounds else "result",
                    content=response,
                    round=round_num,
                )
                all_messages.append(msg)
                round_msgs.append(msg)

            rounds_log.append(DebateRound(round_number=round_num, messages=round_msgs))

        # Final synthesis
        synthesizer_name = "synthesizer" if "synthesizer" in agent_names else agent_names[0]
        if synthesizer_name in self._agents:
            context = self._format_debate_context(all_messages, synthesizer_name)
            synth_prompt = (
                f"Task: {task}\n\n"
                f"All discussion:\n{context}\n\n"
                f"You are the synthesizer. Produce a comprehensive final answer "
                f"that incorporates the best insights from all participants. "
                f"Resolve any contradictions. Be clear and actionable."
            )
            try:
                final = await self._agents[synthesizer_name].run(synth_prompt)
            except Exception as exc:
                final = f"[Synthesis error: {exc}]"
        else:
            final = all_messages[-1].content if all_messages else ""

        # Build contributions list
        contributions = []
        for name in agent_names:
            agent_msgs = [m for m in all_messages if m.sender == name]
            contributions.append({
                "agent": name,
                "role": self._agents[name].profile.role,
                "message_count": len(agent_msgs),
                "summary": agent_msgs[-1].content[:200] if agent_msgs else "",
            })

        self._history = rounds_log

        return TeamResult(
            task=task,
            num_agents=len(self._agents),
            rounds=num_rounds,
            consensus=True,
            final_answer=final,
            contributions=contributions,
            debate_history=rounds_log,
        )

    def _build_debate_prompt(self, task: str, agent_name: str, round_number: int) -> str:
        """Build the initial prompt for an agent in a debate."""
        base = (
            f"Task: {task}\n\n"
            f"Round {round_number}.\n"
            f"As {agent_name}, provide your analysis/proposal for this task. "
            f"Be thorough and specific."
        )
        return base

    def _format_debate_context(self, messages: list[AgentMessage], exclude: str = "") -> str:
        """Format debate history as a readable transcript."""
        parts = []
        for m in messages:
            if m.sender == exclude:
                continue
            parts.append(f"[{m.sender} (Round {m.round})]: {m.content[:300]}")
        return "\n\n".join(parts[-10:])  # Last 10 messages for context

    # ─── Consensus Vote ───────────────────────────────────

    async def vote(self, task: str, options: list[str]) -> dict[str, int]:
        """Hold a vote among agents to choose between options."""
        results: dict[str, int] = {opt: 0 for opt in options}

        for name, agent in self._agents.items():
            prompt = (
                f"Task: {task}\n\n"
                f"Options:\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options)) +
                f"\n\nChoose the best option. Return ONLY the option number (1-{len(options)}), nothing else."
            )
            try:
                response = await agent.run(prompt)
                import re
                match = re.search(r"\d+", response)
                if match:
                    idx = int(match.group()) - 1
                    if 0 <= idx < len(options):
                        results[options[idx]] += 1
            except Exception:
                pass

        return results

    # ─── Properties ───────────────────────────────────────

    @property
    def agents(self) -> dict[str, AgentRuntime]:
        return dict(self._agents)

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def debate_history(self) -> list[DebateRound]:
        return self._history

    def list_roles(self) -> list[str]:
        return list(ROLE_TEMPLATES.keys())