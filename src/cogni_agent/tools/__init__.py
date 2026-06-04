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
    ComputerFocusWindow,
    ComputerHotkey,
    ComputerListWindows,
    ComputerMouseClick,
    ComputerMouseMove,
    ComputerMouseScroll,
    ComputerOpenFile,
    ComputerOpenTerminal,
    ComputerPress,
    ComputerRunAppleScript,
    ComputerRunShell,
    ComputerScreenInfo,
    ComputerScreenshot,
    ComputerType,
)

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "ToolSchema",
    # Web tools
    "WebSearch",
    "WebFetch",
    # File tools
    "FileRead",
    "FileWrite",
    "FileList",
    # Computation
    "Calculator",
    "PythonREPL",
    # Computer control
    "ComputerScreenshot",
    "ComputerMouseMove",
    "ComputerMouseClick",
    "ComputerMouseScroll",
    "ComputerType",
    "ComputerHotkey",
    "ComputerPress",
    "ComputerScreenInfo",
    "ComputerListWindows",
    "ComputerFocusWindow",
    "ComputerOpenFile",
    "ComputerOpenTerminal",
    "ComputerRunAppleScript",
    "ComputerRunShell",
    # Testing
    "Echo",
]


def all_tools() -> list[BaseTool]:
    """Return one instance of each built-in tool (for convenience)."""
    return [
        WebSearch(),
        WebFetch(),
        FileRead(),
        FileWrite(),
        FileList(),
        Calculator(),
        PythonREPL(),
        ComputerScreenshot(),
        ComputerMouseMove(),
        ComputerMouseClick(),
        ComputerMouseScroll(),
        ComputerType(),
        ComputerHotkey(),
        ComputerPress(),
        ComputerScreenInfo(),
        ComputerListWindows(),
        ComputerFocusWindow(),
        ComputerOpenFile(),
        ComputerOpenTerminal(),
        ComputerRunAppleScript(),
        ComputerRunShell(),
    ]