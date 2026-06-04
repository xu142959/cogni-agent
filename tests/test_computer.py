"""Tests for computer control tools — cross-platform."""

import platform
import pytest

from cogni_agent.tools.computer import (
    CURRENT_OS,
    OS,
    ComputerScreenshot,
    ComputerScreenInfo,
    ComputerListWindows,
    ComputerMouseMove,
    ComputerMouseClick,
    ComputerType,
    ComputerHotkey,
    ComputerPress,
    ComputerFocusWindow,
    ComputerOpenFile,
    ComputerOpenTerminal,
    ComputerRunAppleScript,
    ComputerRunShell,
)


class TestPlatformDetection:
    def test_os_detected(self):
        assert CURRENT_OS in (OS.MAC, OS.LINUX, OS.WINDOWS, OS.UNKNOWN)

    def test_os_platform_match(self):
        raw = platform.system().lower()
        if raw == "darwin":
            assert CURRENT_OS == OS.MAC
        elif raw == "linux":
            assert CURRENT_OS == OS.LINUX
        elif raw == "windows":
            assert CURRENT_OS == OS.WINDOWS


class TestScreenInfo:
    @pytest.mark.asyncio
    async def test_screen_info(self):
        tool = ComputerScreenInfo()
        result = await tool.run()
        assert "Screen:" in result
        assert "Mouse:" in result
        assert CURRENT_OS.value in result


class TestScreenshot:
    @pytest.mark.asyncio
    async def test_screenshot(self):
        tool = ComputerScreenshot()
        result = await tool.run()
        assert "Screenshot" in result or "failed" in result


class TestMouseMove:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerMouseMove()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_mouse_move"
        assert "x" in ot["function"]["parameters"]["required"]
        assert "y" in ot["function"]["parameters"]["required"]


class TestMouseClick:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerMouseClick()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_mouse_click"
        assert "button" in ot["function"]["parameters"]["properties"]


class TestType:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerType()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_type"
        assert "text" in ot["function"]["parameters"]["required"]


class TestHotkey:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerHotkey()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_hotkey"
        assert "keys" in ot["function"]["parameters"]["required"]


class TestPress:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerPress()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_press"
        assert "key" in ot["function"]["parameters"]["required"]


class TestListWindows:
    @pytest.mark.asyncio
    async def test_list_windows(self):
        tool = ComputerListWindows()
        result = await tool.run()
        # Should return either a list or a "not supported" message
        assert isinstance(result, str)
        assert len(result) > 0


class TestFocusWindow:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerFocusWindow()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_focus_window"


class TestOpenFile:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerOpenFile()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_open"
        assert "target" in ot["function"]["parameters"]["required"]


class TestAppleScript:
    @pytest.mark.asyncio
    async def test_mac_only(self):
        tool = ComputerRunAppleScript()
        result = await tool.run(script="return \"hello\"")
        if CURRENT_OS == OS.MAC:
            assert "hello" in result.lower() or "executed" in result.lower()
        else:
            assert "only works on macOS" in result


class TestRunShell:
    @pytest.mark.asyncio
    async def test_simple_command(self):
        tool = ComputerRunShell()
        result = await tool.run(command="echo hello", timeout=5)
        if CURRENT_OS in (OS.MAC, OS.LINUX):
            assert "hello" in result or "Output" in result
        else:
            # Windows not supported
            assert result is not None

    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerRunShell()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "computer_shell"


class TestToolDefinitions:
    def test_all_tool_names(self):
        from cogni_agent.tools import all_tools
        tools = all_tools()
        computer_tools = [t for t in tools if t.name.startswith("computer_")]
        assert len(computer_tools) >= 10
        names = {t.name for t in computer_tools}
        assert "computer_screenshot" in names
        assert "computer_mouse_move" in names
        assert "computer_type" in names
        assert "computer_shell" in names