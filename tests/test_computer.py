"""Tests for computer control tools — 像人类一样操作电脑。"""

import platform
import pytest

from cogni_agent.tools.computer import (
    CURRENT_OS,
    OS,
    ComputerGetScreenInfo,
    ComputerListWindows,
    ComputerType,
    ComputerHotkey,
    ComputerPressKey,
    ComputerSwitchWindow,
    ComputerOpenFile,
    ComputerOpenTerminal,
    ComputerRunShell,
    ComputerOpenProgram,
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
    async def test_get_screen_info(self):
        tool = ComputerGetScreenInfo()
        result = await tool.run()
        assert "屏幕分辨率" in result
        assert "当前活动窗口" in result


class TestPressKey:
    @pytest.mark.asyncio
    async def test_press_key(self):
        tool = ComputerPressKey()
        result = await tool.run(key="enter")
        assert "enter" in result

    @pytest.mark.asyncio
    async def test_press_key_multiple_times(self):
        tool = ComputerPressKey()
        result = await tool.run(key="tab", times=3)
        assert "3 次" in result

    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerPressKey()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "press_key"
        assert "key" in ot["function"]["parameters"]["required"]


class TestType:
    @pytest.mark.asyncio
    async def test_type_text(self):
        tool = ComputerType()
        result = await tool.run(text="hello")
        assert "5 个字符" in result

    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerType()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "type_text"
        assert "text" in ot["function"]["parameters"]["required"]


class TestHotkey:
    @pytest.mark.asyncio
    async def test_hotkey(self):
        tool = ComputerHotkey()
        result = await tool.run(keys=["ctrl", "c"])
        assert "ctrl+c" in result

    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerHotkey()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "press_hotkey"
        assert "keys" in ot["function"]["parameters"]["required"]


class TestOpenProgram:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerOpenProgram()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "open_program"
        assert "name" in ot["function"]["parameters"]["required"]


class TestListWindows:
    @pytest.mark.asyncio
    async def test_list_windows(self):
        tool = ComputerListWindows()
        result = await tool.run()
        assert isinstance(result, str)
        assert len(result) > 0


class TestSwitchWindow:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerSwitchWindow()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "switch_window"
        assert "title" in ot["function"]["parameters"]["required"]


class TestOpenFile:
    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerOpenFile()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "open_file"
        assert "path" in ot["function"]["parameters"]["required"]


class TestRunShell:
    @pytest.mark.asyncio
    async def test_simple_command(self):
        tool = ComputerRunShell()
        result = await tool.run(command="echo hello", timeout=5)
        if CURRENT_OS in (OS.MAC, OS.LINUX):
            assert "hello" in result or "Output" in result

    @pytest.mark.asyncio
    async def test_schema(self):
        tool = ComputerRunShell()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "run_command"


class TestToolDefinitions:
    def test_computer_tool_names(self):
        from cogni_agent.tools import all_tools
        tools = all_tools()
        computer_names = {t.name for t in tools}
        assert "press_key" in computer_names
        assert "type_text" in computer_names
        assert "press_hotkey" in computer_names
        assert "open_program" in computer_names
        assert "run_command" in computer_names
        assert "switch_window" in computer_names
        assert "list_windows" in computer_names
        assert "get_screen_info" in computer_names
        assert "open_file" in computer_names
        assert "open_terminal" in computer_names