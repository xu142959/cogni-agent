"""CogniAgent Desktop Backend Server — FastAPI bridge for Electron desktop app.

启动: python3 backend_server.py
端口: 8099
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cogni_agent import AgentRuntime
from cogni_agent.tools import WebSearch, Calculator, PythonREPL, FileRead, FileWrite, VoiceInputTool, VoiceOutputTool
from cogni_agent.tools.computer import (
    ComputerPressKey, ComputerType, ComputerHotkey, ComputerRunShell,
    ComputerOpenProgram, ComputerSwitchWindow, ComputerListWindows,
    ComputerGetScreenInfo, ComputerOpenFile,
)
from cogni_agent.identity.stores import SQLiteIdentityStore
from cogni_agent.voice import VoiceIO
from cogni_agent.vision import VisionSystem

app = FastAPI(title="CogniAgent Desktop Server")

# CORS for Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 存储 ───────────────────────────────────────────────

sessions: dict[str, AgentRuntime] = {}
identity_store = SQLiteIdentityStore(os.path.expanduser("~/.cogniagent/identities.db"))


# ─── API 模型 ───────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    name: str = "小悟"
    role: str = "智能助手"
    personality: list[str] = ["友善", "严谨"]
    model: str = "gpt-4o"
    api_key: str = ""
    api_base: str = ""


class ChatRequest(BaseModel):
    session_id: str
    message: str


class VoiceSTTRequest(BaseModel):
    audio_path: str


class VoiceTTSRequest(BaseModel):
    text: str


class VisionScreenshotRequest(BaseModel):
    pass


# ─── API 路由 ───────────────────────────────────────────

@app.post("/api/agent/create")
async def create_agent(req: CreateAgentRequest):
    """创建 Agent 会话。

    默认不加载任何工具，按需启用。
    """
    session_id = uuid.uuid4().hex[:12]

    kwargs = dict(
        name=req.name,
        role=req.role,
        personality=req.personality,
        model=req.model if req.model and req.model != "gpt-4o" else os.getenv("OPENAI_MODEL", "gpt-4o"),
        tools=[],  # 默认不加载任何工具，需要时通过工具面板手动启用
        enable_memory=True,
        enable_evolution=True,
    )

    if req.api_key:
        kwargs["api_key"] = req.api_key
    if req.api_base:
        kwargs["api_base"] = req.api_base

    try:
        agent = await AgentRuntime.create(**kwargs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    sessions[session_id] = agent

    return {
        "session_id": session_id,
        "name": agent.profile.name,
        "role": agent.profile.role,
        "personality": agent.profile.personality_traits,
        "tool_count": 0,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """发送消息并返回 Agent 回复 + 思维链。"""
    agent = sessions.get(req.session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        response = await agent.run(req.message)
    except Exception as exc:
        return {"response": f"[错误] {exc}", "thought_chain": [], "evolution": None}

    thought_chain = []
    if hasattr(agent.reasoner, "last_thought_chain"):
        thought_chain = agent.reasoner.last_thought_chain

    return {
        "response": response,
        "thought_chain": thought_chain,
        "evolution": agent.get_last_evolution(),
    }


@app.get("/api/agent/{session_id}")
async def get_agent(session_id: str):
    """获取 Agent 状态信息。"""
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404)

    return {
        "name": agent.profile.name,
        "role": agent.profile.role,
        "personality": agent.profile.personality_traits,
        "capabilities": agent.get_capability_map(),
        "evolution_count": len(agent.get_evolution_history()),
        "tool_count": len(agent.tools.list_all()),
        "memory_enabled": agent.context.config.enable_memory,
    }


@app.post("/api/agent/{session_id}/reset")
async def reset_agent(session_id: str):
    """重置对话。"""
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404)
    await agent.reset_conversation()
    return {"status": "ok"}


@app.get("/api/tools")
async def list_tools():
    """列出所有可用工具。"""
    tools = all_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description[:100],
            }
            for t in tools
        ],
        "count": len(tools),
    }


@app.post("/api/voice/stt")
async def voice_stt(req: VoiceSTTRequest):
    """语音转文字。"""
    try:
        voice = VoiceIO()
        text = await voice.stt.transcribe(req.audio_path)
        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/voice/tts")
async def voice_tts(req: VoiceTTSRequest):
    """文字转语音并返回音频路径。"""
    import tempfile
    try:
        voice = VoiceIO()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            output_path = f.name
        await voice.tts.speak(req.text, output_path=output_path)
        return {"audio_path": output_path, "text": req.text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/settings")
async def get_settings():
    """获取当前设置。"""
    # 从环境变量读取
    return {
        "api_key": bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
        "api_base": os.getenv("OPENAI_API_BASE", ""),
        "data_dir": os.path.expanduser("~/.cogniagent"),
        "identities_db": os.path.expanduser("~/.cogniagent/identities.db"),
    }


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {
        "status": "ok",
        "version": "0.2.0",
        "sessions_active": len(sessions),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("COGNI_AGENT_PORT", "8099"))
    print(f"🧠 CogniAgent Desktop Server starting on port {port}...")
    print(f"   API: http://localhost:{port}")
    print(f"   Docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")