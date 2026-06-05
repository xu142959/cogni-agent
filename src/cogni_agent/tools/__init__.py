"""Tools module."""

from cogni_agent.tools.base import BaseTool, ToolRegistry, ToolSchema
from cogni_agent.tools.builtin import (
    Calculator,
    Echo,
    FileList,
    FileRead,
    FileWrite,
    PythonREPL,
    WebFetch,
    WebSearch,
)
from cogni_agent.tools.computer import (
    ComputerGetScreenInfo,
    ComputerHotkey,
    ComputerListWindows,
    ComputerOpenFile,
    ComputerOpenProgram,
    ComputerOpenTerminal,
    ComputerPressKey,
    ComputerRunShell,
    ComputerSwitchWindow,
    ComputerType,
)
from cogni_agent.tools.mcp import MCPBuiltinServer, MCPToolset, MCPToolWrapper
from cogni_agent.voice import VoiceInputTool, VoiceOutputTool
from cogni_agent.vision import ScreenLookTool, ScreenReadTool, ScreenFindTool, ScreenListElementsTool

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "ToolSchema",
    "WebSearch", "WebFetch",
    "FileRead", "FileWrite", "FileList",
    "Calculator", "PythonREPL",
    # Computer control (新：像人类一样操作)
    "ComputerPressKey",
    "ComputerType",
    "ComputerHotkey",
    "ComputerOpenProgram",
    "ComputerRunShell",
    "ComputerSwitchWindow",
    "ComputerListWindows",
    "ComputerGetScreenInfo",
    "ComputerOpenFile",
    "ComputerOpenTerminal",
    # Voice
    "VoiceInputTool",
    "VoiceOutputTool",
    # Vision
    "ScreenLookTool", "ScreenReadTool", "ScreenFindTool", "ScreenListElementsTool",
    # MCP
    "MCPToolset", "MCPToolWrapper", "MCPBuiltinServer",
    # Testing
    "Echo",
]


def all_tools() -> list[BaseTool]:
    """Return one instance of each built-in tool."""
    return [
        WebSearch(), WebFetch(),
        FileRead(), FileWrite(), FileList(),
        Calculator(), PythonREPL(),
        # 电脑控制 — 像人类一样
        ComputerPressKey(), ComputerType(), ComputerHotkey(),
        ComputerOpenProgram(), ComputerRunShell(),
        ComputerSwitchWindow(), ComputerListWindows(),
        ComputerGetScreenInfo(), ComputerOpenFile(), ComputerOpenTerminal(),
        # 语音
        VoiceInputTool(), VoiceOutputTool(),
        # 视觉
        ScreenLookTool(), ScreenReadTool(), ScreenFindTool(), ScreenListElementsTool(),
    ]