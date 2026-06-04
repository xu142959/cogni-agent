"""Identity storage backends."""

from __future__ import annotations

from cogni_agent.core.interfaces import IdentityStore
from cogni_agent.core.types import IdentityProfile


class InMemoryIdentityStore(IdentityStore):
    """In-memory identity storage (for development/testing)."""

    def __init__(self):
        self._profiles: dict[str, IdentityProfile] = {}

    async def save_profile(self, profile: IdentityProfile) -> None:
        self._profiles[profile.agent_id] = profile

    async def load_profile(self, agent_id: str) -> IdentityProfile | None:
        return self._profiles.get(agent_id)

    async def update_profile(self, profile: IdentityProfile) -> None:
        self._profiles[profile.agent_id] = profile