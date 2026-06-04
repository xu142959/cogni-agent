"""CogniAgent Agent Lab — interactive agent laboratory.

Features:
- Chat with thought chain visualization
- Self-awareness panel (Identity, Capabilities, Relationships)
- Evolution timeline
- Memory browser
- Tool call inspector
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cogni_agent import AgentRuntime
from cogni_agent.tools import WebSearch, WebFetch, Calculator, PythonREPL, FileRead, FileWrite
from cogni_agent.tools.computer import (
    ComputerScreenshot,
    ComputerMouseMove,
    ComputerMouseClick,
    ComputerScreenInfo,
    ComputerListWindows,
    ComputerType,
    ComputerHotkey,
    ComputerRunShell,
)


app = FastAPI(title="CogniAgent Lab")

# ─── In-memory session store ────────────────────────────────
sessions: dict[str, AgentRuntime] = {}


# ─── API Models ─────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    name: str = "小悟"
    role: str = "assistant"
    personality: list[str] = ["友善", "严谨"]
    values: list[str] = ["helpful"]
    model: str = "gpt-4o"
    max_iterations: int = 10
    enable_memory: bool = True
    enable_evolution: bool = True
    tools: list[str] = ["web_search", "calculator", "python_repl", "screenshot"]


class ChatRequest(BaseModel):
    session_id: str
    message: str


# ─── Tool Map ──────────────────────────────────────────────

TOOL_MAP = {
    "web_search": WebSearch,
    "web_fetch": WebFetch,
    "calculator": Calculator,
    "python_repl": PythonREPL,
    "file_read": FileRead,
    "file_write": FileWrite,
    "screenshot": ComputerScreenshot,
    "mouse_move": ComputerMouseMove,
    "mouse_click": ComputerMouseClick,
    "screen_info": ComputerScreenInfo,
    "list_windows": ComputerListWindows,
    "type_text": ComputerType,
    "hotkey": ComputerHotkey,
    "shell": ComputerRunShell,
}


# ─── API Routes ─────────────────────────────────────────────

@app.post("/api/agents")
async def create_agent(req: CreateAgentRequest) -> dict:
    """Create a new agent session."""
    session_id = uuid.uuid4().hex[:12]

    tools = []
    for t_name in req.tools:
        tool_cls = TOOL_MAP.get(t_name)
        if tool_cls:
            tools.append(tool_cls())

    try:
        agent = await AgentRuntime.create(
            name=req.name,
            role=req.role,
            personality=req.personality,
            values=req.values,
            model=req.model,
            max_iterations=req.max_iterations,
            enable_memory=req.enable_memory,
            enable_evolution=req.enable_evolution,
            tools=tools,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    sessions[session_id] = agent

    return {
        "session_id": session_id,
        "name": agent.profile.name,
        "role": agent.profile.role,
        "personality": agent.profile.personality_traits,
        "values": agent.profile.values,
        "tool_count": len(tools),
    }


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    """Send a message and return the response with thought chain."""
    agent = sessions.get(req.session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        response = await agent.run(req.message)
    except Exception as exc:
        return {
            "response": f"[Error: {exc}]",
            "thought_chain": [],
            "evolution": None,
        }

    # Get thought chain from the reasoner
    thought_chain = []
    if hasattr(agent.reasoner, "last_thought_chain"):
        thought_chain = agent.reasoner.last_thought_chain

    # Get evolution result
    evolution = agent.get_last_evolution()

    return {
        "response": response,
        "thought_chain": thought_chain,
        "evolution": evolution,
    }


@app.get("/api/agents/{session_id}")
async def get_agent(session_id: str) -> dict:
    """Get full agent state for the dashboard."""
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "profile": {
            "name": agent.profile.name,
            "role": agent.profile.role,
            "personality": agent.profile.personality_traits,
            "values": agent.profile.values,
            "created_at": agent.profile.created_at.isoformat() if agent.profile.created_at else "",
            "evolved_at": agent.profile.evolved_at.isoformat() if agent.profile.evolved_at else "",
        },
        "capabilities": agent.get_capability_map(),
        "evolution_history": agent.get_evolution_history(),
        "tool_names": agent.tools.tool_names if hasattr(agent.tools, "tool_names") else [],
    }


@app.get("/api/agents/{session_id}/self-summary")
async def get_self_summary(session_id: str) -> dict:
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "summary": agent.get_self_summary(),
        "capabilities": agent.get_capability_map(),
        "evolution": agent.get_evolution_history(),
    }


@app.get("/api/agents/{session_id}/memory")
async def get_memory(session_id: str, query: str = "", top_k: int = 10) -> dict:
    """Search agent's semantic memory."""
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")

    if query:
        items = await agent.memory.retrieve_relevant(
            agent.agent_id, query=query, top_k=top_k,
        )
    else:
        items = agent.memory.get_working_context(agent.agent_id, max_count=top_k)

    counts = await agent.memory.count_memories(agent.agent_id)

    return {
        "memories": [
            {
                "id": item.id,
                "content": item.content[:300],
                "memory_type": item.memory_type,
                "importance": item.importance,
                "timestamp": item.timestamp.isoformat() if hasattr(item.timestamp, "isoformat") else str(item.timestamp),
            }
            for item in items
        ],
        "counts": counts,
    }


@app.post("/api/agents/{session_id}/reset")
async def reset_agent(session_id: str) -> dict:
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    await agent.reset_conversation()
    return {"status": "ok"}


@app.get("/api/agents")
async def list_agents() -> dict:
    result = []
    for sid, agent in sessions.items():
        result.append({
            "session_id": sid,
            "name": agent.profile.name,
            "role": agent.profile.role,
            "tool_count": len(agent.tools.list_all()) if hasattr(agent.tools, "list_all") else 0,
        })
    return {"agents": result, "count": len(result)}


# ─── Frontend ───────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse("web_console/static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")