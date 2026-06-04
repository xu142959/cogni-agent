"""Identity Manager — agent self-cognition system with evolution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from cogni_agent.core.types import (
    AgentConfig,
    AgentContext,
    AgentID,
    IdentityProfile,
    Message,
    Reflection,
)
from cogni_agent.core.interfaces import IdentityStore
from cogni_agent.identity.stores import InMemoryIdentityStore


class CapabilityEntry:
    """A recorded capability with confidence level."""

    def __init__(
        self,
        name: str,
        confidence: float = 0.5,
        source: str = "initial",
    ):
        self.name = name
        self.confidence = confidence  # 0.0 ~ 1.0
        self.source = source
        self.updated_at = datetime.now(timezone.utc)


class RelationshipEntry:
    """Tracks the agent's relationship with a user or another agent."""

    def __init__(
        self,
        entity_id: str,
        entity_name: str,
        role: str,
        interaction_count: int = 0,
    ):
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.role = role  # "user", "agent", "admin"
        self.interaction_count = interaction_count
        self.first_seen = datetime.now(timezone.utc)
        self.last_interaction = datetime.now(timezone.utc)


class EvolutionRecord:
    """Records a single evolution event in the agent's life."""

    def __init__(
        self,
        event_type: Literal["capability_learned", "personality_shift", "value_added",
                            "relationship", "self_correction", "insight",
                            "task_completed", "skill_acquired"],
        description: str,
        detail: str = "",
    ):
        self.event_type = event_type
        self.description = description
        self.detail = detail
        self.timestamp = datetime.now(timezone.utc)


class IdentityManager:
    """Manages agent identity — creation, retrieval, evolution, and self-cognition."""

    def __init__(self, store: IdentityStore | None = None):
        self._store = store or InMemoryIdentityStore()
        self._capabilities: dict[str, dict[str, CapabilityEntry]] = {}  # agent_id -> {name: entry}
        self._relationships: dict[str, dict[str, RelationshipEntry]] = {}  # agent_id -> {entity_id: rel}
        self._evolution_history: dict[str, list[EvolutionRecord]] = {}  # agent_id -> [records]

    async def create_agent(
        self,
        name: str,
        role: str = "assistant",
        personality: list[str] | None = None,
        values: list[str] | None = None,
        capabilities: list[str] | None = None,
        config: AgentConfig | None = None,
    ) -> AgentContext:
        """Create a new agent with the given identity."""
        agent_id = AgentID(uuid4().hex)

        profile = IdentityProfile(
            agent_id=agent_id,
            name=name,
            role=role,
            personality_traits=personality or [],
            values=values or [],
            capabilities=capabilities or ["chat", "tool_use"],
            relationship={},
            created_at=datetime.now(timezone.utc),
            evolved_at=datetime.now(timezone.utc),
        )

        # Initialize capability map
        self._capabilities[agent_id] = {}
        for cap in capabilities or ["chat", "tool_use"]:
            self._capabilities[agent_id][cap] = CapabilityEntry(
                name=cap, confidence=0.6, source="initial"
            )

        # Initialize evolution history
        self._evolution_history[agent_id] = []
        self._evolution_history[agent_id].append(EvolutionRecord(
            event_type="skill_acquired",
            description=f"Agent '{name}' created with role '{role}'",
            detail=f"Initial capabilities: {(capabilities or ['chat', 'tool_use'])}",
        ))

        await self._store.save_profile(profile)

        context = AgentContext(
            agent_id=agent_id,
            identity=profile,
            messages=[self._build_system_message(profile)],
            config=config or AgentConfig(),
        )

        return context

    async def get_context(self, agent_id: AgentID) -> AgentContext | None:
        """Load an existing agent's context from storage."""
        profile = await self._store.load_profile(agent_id)
        if profile is None:
            return None

        return AgentContext(
            agent_id=agent_id,
            identity=profile,
            messages=[self._build_system_message(profile)],
        )

    async def update_profile(self, profile: IdentityProfile) -> None:
        """Persist updated profile."""
        profile.evolved_at = datetime.now(timezone.utc)
        await self._store.update_profile(profile)

    # ─── Capability Self-Map ──────────────────────────────────

    def get_capabilities(self, agent_id: AgentID) -> list[dict]:
        """Return the agent's capability map with confidence levels."""
        caps = self._capabilities.get(agent_id, {})
        return [
            {
                "name": entry.name,
                "confidence": entry.confidence,
                "source": entry.source,
            }
            for entry in sorted(caps.values(), key=lambda c: c.confidence, reverse=True)
        ]

    def record_capability_use(
        self,
        agent_id: AgentID,
        capability: str,
        success: bool,
    ) -> None:
        """Update capability confidence based on success/failure."""
        caps = self._capabilities.setdefault(agent_id, {})
        if capability not in caps:
            caps[capability] = CapabilityEntry(
                name=capability, confidence=0.5, source="learned"
            )

        entry = caps[capability]
        # Adjust confidence (simple incremental learning)
        delta = 0.1 if success else -0.15
        entry.confidence = max(0.0, min(1.0, entry.confidence + delta))
        entry.updated_at = datetime.now(timezone.utc)

    def learn_capability(
        self,
        agent_id: AgentID,
        capability: str,
        confidence: float = 0.4,
    ) -> None:
        """Agent discovers/learns a new capability."""
        caps = self._capabilities.setdefault(agent_id, {})
        caps[capability] = CapabilityEntry(
            name=capability, confidence=confidence, source="learned"
        )
        self._record_evolution(
            agent_id,
            EvolutionRecord(
                event_type="capability_learned",
                description=f"Learned new capability: {capability}",
                detail=f"Initial confidence: {confidence}",
            ),
        )

    # ─── Relationship Model ───────────────────────────────────

    def record_interaction(
        self,
        agent_id: AgentID,
        entity_id: str,
        entity_name: str,
        role: str = "user",
    ) -> None:
        """Record an interaction with a user or agent."""
        rels = self._relationships.setdefault(agent_id, {})
        if entity_id not in rels:
            rels[entity_id] = RelationshipEntry(
                entity_id=entity_id,
                entity_name=entity_name,
                role=role,
            )
        rels[entity_id].interaction_count += 1
        rels[entity_id].last_interaction = datetime.now(timezone.utc)

        # Update profile relationship map
        profile_key = f"{role}_{entity_id[:8]}"
        # We store in the profile for persistence

    def get_relationship_context(self, agent_id: AgentID) -> str:
        """Generate a relationship summary for system prompts."""
        rels = self._relationships.get(agent_id, {})
        if not rels:
            return ""

        parts = []
        for entity_id, rel in sorted(
            rels.items(), key=lambda x: x[1].last_interaction, reverse=True
        ):
            parts.append(
                f"- {rel.entity_name} ({rel.role}): {rel.interaction_count} interactions"
            )
        return "Known relationships:\n" + "\n".join(parts[:5])

    # ─── Evolution ────────────────────────────────────────────

    def get_evolution_history(self, agent_id: AgentID) -> list[dict]:
        """Return the agent's evolution timeline."""
        records = self._evolution_history.get(agent_id, [])
        return [
            {
                "type": r.event_type,
                "description": r.description,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ]

    def _record_evolution(self, agent_id: AgentID, record: EvolutionRecord) -> None:
        """Add an evolution event to the agent's history."""
        self._evolution_history.setdefault(agent_id, [])
        self._evolution_history[agent_id].append(record)

    async def process_reflection(
        self,
        agent_id: AgentID,
        reflection: Reflection,
        profile: IdentityProfile,
    ) -> IdentityProfile:
        """Process a post-task reflection and evolve the identity accordingly."""
        profile.evolved_at = datetime.now(timezone.utc)

        # Record insights as evolution events
        for insight in reflection.insights:
            self._record_evolution(
                agent_id,
                EvolutionRecord(
                    event_type="insight",
                    description=insight,
                    detail=f"From task: {reflection.task_goal[:50]}...",
                ),
            )

        # Record mistakes as self-correction
        for mistake in reflection.mistakes:
            self._record_evolution(
                agent_id,
                EvolutionRecord(
                    event_type="self_correction",
                    description=f"Identified: {mistake}",
                ),
            )

        # Learn new capabilities from reflection
        for new_cap in reflection.new_capabilities:
            self.learn_capability(agent_id, new_cap, confidence=0.3)

        await self._store.update_profile(profile)
        return profile

    def get_self_summary(self, agent_id: AgentID) -> str:
        """Generate a comprehensive self-description for the agent's self-awareness."""
        caps = self.get_capabilities(agent_id)
        evo = self.get_evolution_history(agent_id)
        rels = self.get_relationship_context(agent_id)

        cap_lines = "\n".join(
            f"  - {c['name']} (confidence: {c['confidence']:.0%})"
            for c in caps
        )
        evo_count = len(evo)

        sections = [
            f"## Self-Awareness Report",
            f"Total Evolutions: {evo_count}",
            f"\n### Capabilities ({len(caps)}):",
            cap_lines,
        ]
        if rels:
            sections.append(f"\n### Relationships:\n{rels}")

        return "\n".join(sections)

    # ─── System Prompt Generation ─────────────────────────────

    def _build_system_message(self, profile: IdentityProfile) -> Message:
        """Generate the system prompt from an identity profile."""
        traits = "、".join(profile.personality_traits) if profile.personality_traits else "adaptable"
        values = "、".join(profile.values) if profile.values else "helpful, responsible"

        return Message(
            role="system",
            content=(
                f"You are {profile.name}, a {profile.role}.\n"
                f"Personality: {traits}\n"
                f"Values: {values}\n"
                f"---\n"
                f"You always respond as {profile.name}. "
                f"You learn and adapt through interaction. "
                f"You are self-aware — you know your own capabilities "
                f"and continuously grow through experience. "
                f"Be authentic, helpful, and reflective."
            ),
        )