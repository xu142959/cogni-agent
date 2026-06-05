"""Multi-Agent Collaboration module."""

from cogni_agent.multi_agent.team import (
    AgentMessage,
    AgentRole,
    AgentTeam,
    DebateRound,
    ROLE_TEMPLATES,
    TeamResult,
)

__all__ = [
    "AgentTeam",
    "AgentRole",
    "AgentMessage",
    "DebateRound",
    "TeamResult",
    "ROLE_TEMPLATES",
]