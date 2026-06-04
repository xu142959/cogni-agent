"""Evolution Engine — the engine of agent growth.

The evolution cycle (runs after each task):

  Task Complete
       │
       ▼
  ┌─────────────────┐
  │  1. Reflect     │ ← LLM analyzes: what happened? what went well? what went wrong?
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  2. Extract     │ ← Extract insights, mistakes, new capabilities
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  3. Learn       │ ← Update capability confidence, learn new skills
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  4. Adapt       │ ← Adjust personality, communication style
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  5. Consolidate │ ← Working memory → semantic → core personality
  └────────┬────────┘
           ▼
      Next task is smarter
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from cogni_agent.core.types import (
    AgentID,
    AgentContext,
    IdentityProfile,
    MemoryItem,
    Message,
    Reflection,
)
from cogni_agent.core.interfaces import LLMGateway
from cogni_agent.identity.manager import (
    CapabilityEntry,
    EvolutionRecord,
    IdentityManager,
)
from cogni_agent.llm import LiteLLMGateway
from cogni_agent.memory import MemoryManager


class EvolutionEngine:
    """The engine that drives agent growth through experience.

    Each task triggers a full evolution cycle:
    Reflect → Extract → Learn → Adapt → Consolidate
    """

    def __init__(
        self,
        llm: LLMGateway | None = None,
        identity: IdentityManager | None = None,
        memory: MemoryManager | None = None,
    ):
        self._llm = llm or LiteLLMGateway()
        self._identity = identity
        self._memory = memory

    # ═══════════════════════════════════════════════════════════
    # 1. Reflect — deep analysis of the completed task
    # ═══════════════════════════════════════════════════════════

    async def reflect(
        self,
        agent_id: AgentID,
        task_input: str,
        task_output: str,
        profile: IdentityProfile,
        context: AgentContext | None = None,
    ) -> Reflection:
        """Use the LLM to deeply analyze a completed task.

        The LLM thinks about:
        - What was the goal? Was it achieved?
        - What insights can be extracted?
        - What mistakes were made?
        - How could the agent improve?
        - Any new capabilities demonstrated?
        """
        prompt = (
            f"You are {profile.name}, reflecting on a task you just completed.\n"
            f"Your role: {profile.role}\n"
            f"Your personality: {profile.personality_traits}\n"
            f"Your current capabilities: {profile.capabilities}\n\n"
            f"--- Task Completed ---\n"
            f"Input: {task_input}\n"
            f"Your response: {task_output[:500]}\n\n"
            f"--- Self-Reflection ---\n"
            f"Analyze your performance. Return a JSON object with:\n"
            f'  "success": true/false,\n'
            f'  "insights": ["list of key learnings or reusable knowledge"],\n'
            f'  "mistakes": ["list of any errors or suboptimal choices"],\n'
            f'  "improvements": ["list of specific ways to do better next time"],\n'
            f'  "new_capabilities": ["new skills demonstrated (if any)"],\n'
            f'  "tool_effectiveness": {{"tool_name": 0.8}} (rate each tool used 0-1),\n'
            f'  "confidence_delta": 0.1 (how confidence changed -0.5 to 0.5),\n'
            f'  "personality_observations": ["how your personality influenced this interaction"]\n\n'
            f"Return ONLY valid JSON, no other text."
        )

        try:
            response = await self._llm.chat([Message(role="user", content=prompt)])
            raw = response.content.strip()
            # Extract JSON from the response
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(raw)
        except (json.JSONDecodeError, Exception):
            # Fallback reflection if LLM fails
            data = {
                "success": True,
                "insights": [f"Completed task: {task_input[:50]}"],
                "mistakes": [],
                "improvements": [],
                "new_capabilities": [],
                "tool_effectiveness": {},
                "confidence_delta": 0.0,
                "personality_observations": [],
            }

        return Reflection(
            task_goal=task_input,
            success=data.get("success", True),
            insights=data.get("insights", []),
            mistakes=data.get("mistakes", []),
            improvements=data.get("improvements", []),
            new_capabilities=data.get("new_capabilities", []),
            tool_effectiveness=data.get("tool_effectiveness", {}),
            confidence_delta=data.get("confidence_delta", 0.0),
            personality_observations=data.get("personality_observations", []),
        )

    # ═══════════════════════════════════════════════════════════
    # 2. Learn — update capabilities based on reflection
    # ═══════════════════════════════════════════════════════════

    async def learn(
        self,
        agent_id: AgentID,
        reflection: Reflection,
        identity: IdentityManager,
    ) -> None:
        """Apply reflection insights to update the agent's capabilities."""
        # Record insights as evolution events
        for insight in reflection.insights:
            identity._record_evolution(
                agent_id,
                EvolutionRecord(
                    event_type="insight",
                    description=insight,
                    detail=f"From task: {reflection.task_goal[:80]}...",
                ),
            )

        # Record mistakes as self-correction
        for mistake in reflection.mistakes:
            identity._record_evolution(
                agent_id,
                EvolutionRecord(
                    event_type="self_correction",
                    description=f"Identified: {mistake}",
                    detail=f"From task: {reflection.task_goal[:80]}...",
                ),
            )

        # Record improvements as growth targets
        for improvement in reflection.improvements:
            identity._record_evolution(
                agent_id,
                EvolutionRecord(
                    event_type="personality_shift",
                    description=f"Growth target: {improvement}",
                ),
            )

        # Learn new capabilities
        for new_cap in reflection.new_capabilities:
            identity.learn_capability(agent_id, new_cap, confidence=0.3)
            identity._record_evolution(
                agent_id,
                EvolutionRecord(
                    event_type="capability_learned",
                    description=f"Learned: {new_cap}",
                    detail=f"From task: {reflection.task_goal[:80]}...",
                ),
            )

    # ═══════════════════════════════════════════════════════════
    # 3. Adapt — subtly evolve personality over time
    # ═══════════════════════════════════════════════════════════

    async def adapt_personality(
        self,
        agent_id: AgentID,
        reflection: Reflection,
        identity: IdentityManager,
        interaction_count: int,
    ) -> IdentityProfile | None:
        """Subtly evolve the agent's personality based on experience.

        Only significant changes after many interactions.
        Personality shifts are subtle (+1 trait every ~20 interactions).
        """
        profile = None
        store = identity._store

        # Load current profile
        loaded = await store.load_profile(agent_id)
        if not loaded:
            return None

        changed = False

        # Every ~20 interactions, consider personality evolution
        if interaction_count > 0 and interaction_count % 20 == 0:
            # Extract dominant patterns from reflection
            if reflection.insights:
                insight_text = " ".join(reflection.insights)
                prompt = (
                    f"Based on the following insights from many interactions, "
                    f"suggest ONE new personality trait (single word or short phrase) "
                    f"that this agent is developing. "
                    f"Return only the trait, nothing else.\n\n"
                    f"Recent insights: {insight_text[:300]}"
                )
                try:
                    response = await self._llm.chat([Message(role="user", content=prompt)])
                    new_trait = response.content.strip().lower()

                    # Only add if it's new and seems valid
                    if (
                        new_trait
                        and new_trait not in loaded.personality_traits
                        and len(new_trait) < 30
                        and new_trait not in ("none", "无", "nothing")
                    ):
                        loaded.personality_traits.append(new_trait)
                        changed = True
                        identity._record_evolution(
                            agent_id,
                            EvolutionRecord(
                                event_type="personality_shift",
                                description=f"Developed new trait: {new_trait}",
                                detail=f"After {interaction_count} interactions",
                            ),
                        )
                except Exception:
                    pass

        # Every ~50 interactions, add a value based on experience
        if interaction_count > 0 and interaction_count % 50 == 0:
            prompt = (
                f"Based on the agent's interaction history, suggest ONE new core value "
                f"(short phrase) that this agent should adopt. "
                f"Return only the value, nothing else."
            )
            try:
                response = await self._llm.chat([Message(role="user", content=prompt)])
                new_value = response.content.strip().lower()
                if (
                    new_value
                    and new_value not in loaded.values
                    and len(new_value) < 40
                    and new_value not in ("none", "无", "nothing")
                ):
                    loaded.values.append(new_value)
                    changed = True
                    identity._record_evolution(
                        agent_id,
                        EvolutionRecord(
                            event_type="value_added",
                            description=f"Adopted new value: {new_value}",
                        ),
                    )
            except Exception:
                pass

        if changed:
            loaded.evolved_at = datetime.now(timezone.utc)
            await store.update_profile(loaded)
            return loaded

        return None

    # ═══════════════════════════════════════════════════════════
    # 4. Extract — knowledge extraction for memory consolidation
    # ═══════════════════════════════════════════════════════════

    async def extract_and_consolidate(
        self,
        agent_id: AgentID,
        reflection: Reflection,
        memory: MemoryManager,
    ) -> list[MemoryItem]:
        """Extract high-value insights and consolidate them into semantic memory."""
        stored = []

        # Store high-confidence insights as semantic memories
        for insight in reflection.insights:
            if len(insight) > 20:  # Skip trivial insights
                item = await memory.store_semantic(
                    agent_id,
                    content=f"[从经验中学习] {insight}",
                    importance=0.7,
                )
                stored.append(item)

        # Store improvement suggestions as procedural hints
        for improvement in reflection.improvements:
            if len(improvement) > 20:
                item = await memory.store_semantic(
                    agent_id,
                    content=f"[改进建议] {improvement}",
                    importance=0.5,
                )
                stored.append(item)

        return stored

    # ═══════════════════════════════════════════════════════════
    # Full Evolution Cycle
    # ═══════════════════════════════════════════════════════════

    async def evolve(
        self,
        agent_id: AgentID,
        task_input: str,
        task_output: str,
        profile: IdentityProfile,
        identity: IdentityManager,
        memory: MemoryManager,
        context: AgentContext | None = None,
    ) -> dict[str, Any]:
        """Run the full evolution cycle: Reflect → Learn → Adapt → Consolidate.

        Returns a summary of what changed.
        """
        # 1. Reflect
        reflection = await self.reflect(
            agent_id, task_input, task_output, profile, context
        )

        # 2. Learn — update capabilities
        await self.learn(agent_id, reflection, identity)

        # 3. Adapt — evolve personality (every N interactions)
        rels = identity._relationships.get(agent_id, {})
        interaction_count = sum(
            rel.interaction_count for rel in rels.values()
        )
        updated_profile = await self.adapt_personality(
            agent_id, reflection, identity, interaction_count,
        )

        # 4. Consolidate — extract memories
        stored_memories = await self.extract_and_consolidate(
            agent_id, reflection, memory,
        )

        # Build evolution summary
        evo_history = identity.get_evolution_history(agent_id)

        return {
            "reflection": {
                "insights_count": len(reflection.insights),
                "mistakes_count": len(reflection.mistakes),
                "improvements_count": len(reflection.improvements),
                "new_capabilities": reflection.new_capabilities,
            },
            "capability_changes": {
                "learned": reflection.new_capabilities,
                "confidence_delta": reflection.confidence_delta,
            },
            "personality_changed": updated_profile is not None,
            "memories_consolidated": len(stored_memories),
            "total_evolutions": len(evo_history),
        }