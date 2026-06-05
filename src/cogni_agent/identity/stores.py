"""Identity storage backends — InMemory and SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


class SQLiteIdentityStore(IdentityStore):
    """SQLite-backed identity storage — Agent 身份持久化，重启不丢失。

    Usage:
        store = SQLiteIdentityStore("data/identities.db")
        manager = IdentityManager(store=store)
    """

    def __init__(self, db_path: str = "cogni_identities.db"):
        self._db_path = str(Path(db_path).expanduser().resolve())
        self._ensure_db()

    def _ensure_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identities (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'assistant',
                    personality_traits TEXT DEFAULT '[]',
                    values TEXT DEFAULT '[]',
                    capabilities TEXT DEFAULT '[]',
                    relationship TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    evolved_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _profile_to_row(self, p: IdentityProfile) -> tuple:
        return (
            p.agent_id, p.name, p.role,
            json.dumps(p.personality_traits),
            json.dumps(p.values),
            json.dumps(p.capabilities),
            json.dumps(p.relationship),
            p.created_at.isoformat() if p.created_at else datetime.now(timezone.utc).isoformat(),
            p.evolved_at.isoformat() if p.evolved_at else datetime.now(timezone.utc).isoformat(),
        )

    def _row_to_profile(self, row: sqlite3.Row) -> IdentityProfile:
        return IdentityProfile(
            agent_id=row["agent_id"],
            name=row["name"],
            role=row["role"],
            personality_traits=json.loads(row["personality_traits"]),
            values=json.loads(row["values"]),
            capabilities=json.loads(row["capabilities"]),
            relationship=json.loads(row["relationship"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            evolved_at=datetime.fromisoformat(row["evolved_at"]),
        )

    async def save_profile(self, profile: IdentityProfile) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO identities
                (agent_id, name, role, personality_traits, values, capabilities,
                 relationship, created_at, evolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, self._profile_to_row(profile))
            conn.commit()
        finally:
            conn.close()

    async def load_profile(self, agent_id: str) -> IdentityProfile | None:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM identities WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            if row:
                return self._row_to_profile(row)
            return None
        finally:
            conn.close()

    async def update_profile(self, profile: IdentityProfile) -> None:
        await self.save_profile(profile)

    async def list_all(self) -> list[IdentityProfile]:
        """列出所有已保存的 Agent 身份。"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM identities ORDER BY created_at DESC").fetchall()
            return [self._row_to_profile(r) for r in rows]
        finally:
            conn.close()

    async def delete(self, agent_id: str) -> None:
        """删除一个 Agent 身份。"""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("DELETE FROM identities WHERE agent_id = ?", (agent_id,))
            conn.commit()
        finally:
            conn.close()

    async def count(self) -> int:
        """统计 Agent 数量。"""
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM identities").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    @property
    def db_path(self) -> str:
        return self._db_path