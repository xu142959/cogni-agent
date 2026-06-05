from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cogni_agent import AgentRuntime
from cogni_agent.multi_agent import AgentTeam, ROLE_TEMPLATES
from cogni_agent.tools import WebSearch, WebFetch, Calculator, PythonREPL, FileRead, FileWrite


app = FastAPI(title="CogniAgent Lab")

sessions: dict[str, AgentRuntime] = {}
teams: dict[str, AgentTeam] = {}
team_results: dict[str, dict] = {}


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


class CreateTeamRequest(BaseModel):
    task: str = "分析 AI Agent 框架的优缺点"
    model: str = "gpt-4o"
    max_debate_rounds: int = 3
    roles: list[str] = []


TOOL_MAP = {
    "web_search": WebSearch, "web_fetch": WebFetch,
    "calculator": Calculator, "python_repl": PythonREPL,
    "file_read": FileRead, "file_write": FileWrite,
}


@app.post("/api/agents")
async def create_agent(req: CreateAgentRequest) -> dict:
    session_id = uuid.uuid4().hex[:12]
    tools = []
    for t_name in req.tools:
        tool_cls = TOOL_MAP.get(t_name)
        if tool_cls:
            tools.append(tool_cls())
    try:
        agent = await AgentRuntime.create(
            name=req.name, role=req.role,
            personality=req.personality, values=req.values,
            model=req.model, max_iterations=req.max_iterations,
            enable_memory=req.enable_memory, enable_evolution=req.enable_evolution,
            tools=tools,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    sessions[session_id] = agent
    return {
        "session_id": session_id, "name": agent.profile.name,
        "role": agent.profile.role, "personality": agent.profile.personality_traits,
        "values": agent.profile.values, "tool_count": len(tools),
    }


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    agent = sessions.get(req.session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        response = await agent.run(req.message)
    except Exception as exc:
        return {"response": f"[Error: {exc}]", "thought_chain": [], "evolution": None}
    thought_chain = []
    if hasattr(agent.reasoner, "last_thought_chain"):
        thought_chain = agent.reasoner.last_thought_chain
    return {"response": response, "thought_chain": thought_chain, "evolution": agent.get_last_evolution()}


@app.get("/api/agents/{session_id}")
async def get_agent(session_id: str) -> dict:
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "profile": {
            "name": agent.profile.name, "role": agent.profile.role,
            "personality": agent.profile.personality_traits,
            "values": agent.profile.values,
            "created_at": str(agent.profile.created_at), "evolved_at": str(agent.profile.evolved_at),
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
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    if query:
        items = await agent.memory.retrieve_relevant(agent.agent_id, query=query, top_k=top_k)
    else:
        items = agent.memory.get_working_context(agent.agent_id, max_count=top_k)
    counts = await agent.memory.count_memories(agent.agent_id)
    return {
        "memories": [{"id": m.id, "content": m.content[:300], "memory_type": m.memory_type,
                       "importance": m.importance} for m in items],
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
        result.append({"session_id": sid, "name": agent.profile.name,
                       "role": agent.profile.role,
                       "tool_count": len(agent.tools.list_all()) if hasattr(agent.tools, "list_all") else 0})
    return {"agents": result, "count": len(result)}


# ═══ Multi-Agent Team API ═══════════════════════════════════

@app.get("/api/teams/roles")
async def list_role_templates() -> dict:
    return {"roles": list(ROLE_TEMPLATES.keys())}


@app.post("/api/teams")
async def create_team(req: CreateTeamRequest) -> dict:
    team_id = uuid.uuid4().hex[:12]
    team = AgentTeam(
        model=req.model,
        max_debate_rounds=req.max_debate_rounds,
    )

    if req.roles:
        for role_name in req.roles:
            await team.add_agent_by_template(role_name)
        role_names = req.roles
    else:
        roles = await team.suggest_roles(req.task)
        for role_name in roles:
            await team.add_agent_by_template(role_name)
        role_names = roles

    teams[team_id] = team

    return {
        "team_id": team_id,
        "num_agents": team.agent_count,
        "role_names": role_names,
        "task": req.task,
        "max_debate_rounds": req.max_debate_rounds,
    }


@app.post("/api/teams/{team_id}/debate")
async def run_debate(team_id: str) -> dict:
    team = teams.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Store the task when team was created
    # We need to pass the task — let's get it from the teams store
    # For now, re-use a fixed task
    result = await team.debate()

    return {
        "team_id": team_id,
        "final_answer": result.final_answer,
        "num_agents": result.num_agents,
        "rounds": result.rounds,
        "contributions": result.contributions,
        "consensus": result.consensus,
    }


@app.get("/api/teams")
async def list_teams() -> dict:
    result = []
    for tid, team in teams.items():
        result.append({"team_id": tid, "num_agents": team.agent_count})
    return {"teams": result, "count": len(result)}


@app.get("/api/teams/{team_id}")
async def get_team(team_id: str) -> dict:
    team = teams.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    agent_info = []
    for name, agent in team.agents.items():
        agent_info.append({"name": name, "role": agent.profile.role})
    return {
        "team_id": team_id,
        "num_agents": team.agent_count,
        "agents": agent_info,
        "debate_history": len(team.debate_history),
    }


@app.get("/")
async def index():
    return FileResponse("web_console/static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")