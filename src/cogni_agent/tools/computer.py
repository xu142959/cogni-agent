"""Computer Control Tools for CogniAgent — 像人类一样操作电脑。

核心理念：不靠截图定位，而是用快捷键、命令行、系统 API 直接控制。

人类怎么操作电脑？
  1. 按 Win/Command 打开开始菜单
  2. 打字搜索程序 → Enter 打开
  3. Alt+Tab 切换窗口
  4. Ctrl+C / Ctrl+V 复制粘贴
  5. 在终端里敲命令
  6. 直接打开文件/文件夹

CogniAgent 的电脑控制也一样：
  → computer_open_program("chrome")      # 打开浏览器
  → computer_press("tab", 3)              # 按3次Tab
  → computer_type("youtube.com")          # 打字
  → computer_press("enter")               # 按回车
  → computer_hotkey("ctrl", "c")          # 复制
  → computer_focus_window("Chrome")       # 切换到Chrome

跨平台支持：macOS / Linux / Windows 统一接口
"""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Literal

from cogni_agent.tools.base import BaseTool, ToolSchema


# ─── Platform Detection ────────────────────────────────────

class OS(Enum):
    MAC = "darwin"
    LINUX = "linux"
    WINDOWS = "windows"
    UNKNOWN = "unknown"

    @classmethod
    def detect(cls) -> OS:
        raw = platform.system().lower()
        for os_type in cls:
            if raw == os_type.value:
                return os_type
        return cls.UNKNOWN


CURRENT_OS = OS.detect()


# ─── 键盘映射 ─────────────────────────────────────────────

KEY_MAP = {
    # 通用键
    "enter": "return", "return": "return",
    "esc": "escape", "escape": "escape",
    "tab": "tab",
    "space": "space", " ": "space",
    "backspace": "backspace", "delete": "backspace",
    # 方向键
    "up": "up", "down": "down", "left": "left", "right": "right",
    # 功能键
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
    "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
    "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
    # 修饰键
    "ctrl": "ctrl", "control": "ctrl",
    "alt": "alt", "option": "alt",
    "shift": "shift",
    "cmd": "cmd", "command": "cmd", "win": "cmd", "windows": "cmd",
    "home": "home", "end": "end",
    "pageup": "pageup", "pagedown": "pagedown",
}

# 快捷键中的修饰键映射
MODIFIER_MAP = {"ctrl", "alt", "shift", "cmd"}


# ─── 后端抽象 ─────────────────────────────────────────────

class ComputerBackend(ABC):
    """系统操作后端 — 直接控制系统，不依赖截图。"""

    @abstractmethod
    def get_active_window(self) -> str:
        """获取当前活动窗口标题。"""
        ...

    @abstractmethod
    def list_windows(self) -> list[str]:
        """列出所有打开的窗口标题。"""
        ...

    @abstractmethod
    def focus_window(self, title: str) -> bool:
        """切换到指定窗口。"""
        ...

    @abstractmethod
    def press_key(self, key: str) -> None:
        """按一个键。"""
        ...

    @abstractmethod
    def type_text(self, text: str) -> None:
        """输入文本。"""
        ...

    @abstractmethod
    def hotkey(self, *keys: str) -> None:
        """按快捷键组合。"""
        ...

    @abstractmethod
    def open_program(self, program_name: str) -> bool:
        """打开程序/应用。"""
        ...

    @abstractmethod
    def run_command(self, command: str) -> str:
        """执行命令并返回输出。"""
        ...

    @abstractmethod
    def open_file(self, path: str) -> bool:
        """用默认程序打开文件。"""
        ...

    @abstractmethod
    def open_terminal(self, command: str = "") -> None:
        """打开终端。"""
        ...

    @abstractmethod
    def get_screen_size(self) -> tuple[int, int]:
        """获取屏幕分辨率。"""
        ...


# ─── macOS 后端 ───────────────────────────────────────────

class MacBackend(ComputerBackend):
    """macOS 后端 — 用 AppleScript + shell 命令直接控制系统。"""

    def _osascript(self, script: str) -> str:
        """执行 AppleScript。"""
        try:
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10,
            )
            return r.stdout.strip()
        except Exception as exc:
            return f""

    def get_active_window(self) -> str:
        return self._osascript(
            'tell application "System Events" to get name of first process whose frontmost is true'
        )

    def list_windows(self) -> list[str]:
        output = self._osascript(
            'tell application "System Events" to get name of every process whose background only is false'
        )
        return [n.strip() for n in output.split(", ") if n.strip()]

    def focus_window(self, title: str) -> bool:
        self._osascript(
            f'tell application "System Events" to set frontmost of '
            f'(first process whose name contains "{title}") to true'
        )
        return True

    def press_key(self, key: str) -> None:
        k = KEY_MAP.get(key.lower(), key)
        self._osascript(f'tell application "System Events" to keystroke "{k}"')

    def type_text(self, text: str) -> None:
        escaped = text.replace('"', '\\"')
        self._osascript(
            f'tell application "System Events" to keystroke "{escaped}"'
        )

    def hotkey(self, *keys: str) -> None:
        lower_keys = [k.lower() for k in keys]
        # 识别修饰键
        mods = []
        main_key = None
        for k in lower_keys:
            if k in ("ctrl", "control"):
                mods.append("control down")
            elif k in ("alt", "option"):
                mods.append("option down")
            elif k in ("shift",):
                mods.append("shift down")
            elif k in ("cmd", "command"):
                mods.append("command down")
            else:
                main_key = k

        if main_key:
            using = " using {" + ", ".join(mods) + "}" if mods else ""
            mapped = KEY_MAP.get(main_key, main_key)
            self._osascript(
                f'tell application "System Events" to keystroke "{mapped}"{using}'
            )

    def open_program(self, program_name: str) -> bool:
        try:
            subprocess.run(["open", "-a", program_name], check=True, timeout=10)
            return True
        except Exception:
            try:
                subprocess.run(["open", program_name], check=True, timeout=5)
                return True
            except Exception:
                return False

    def run_command(self, command: str) -> str:
        try:
            r = subprocess.run(
                ["bash", "-c", command],
                capture_output=True, text=True, timeout=30,
            )
            output = r.stdout.strip()
            error = r.stderr.strip()
            parts = []
            if output:
                parts.append(f"Output:\n{output[:2000]}")
            if error:
                parts.append(f"Error:\n{error[:500]}")
            return "\n".join(parts) if parts else "[命令执行完毕，无输出]"
        except subprocess.TimeoutExpired:
            return "[命令执行超时]"
        except Exception as exc:
            return f"[命令执行失败: {exc}]"

    def open_file(self, path: str) -> bool:
        try:
            subprocess.run(["open", path], check=True, timeout=5)
            return True
        except Exception:
            return False

    def open_terminal(self, command: str = "") -> None:
        if command:
            self._osascript(
                f'tell application "Terminal" to do script "{command}"'
            )
        else:
            self._osascript('tell application "Terminal" to activate')

    def get_screen_size(self) -> tuple[int, int]:
        output = self._osascript(
            'tell application "Finder" to get bounds of window of desktop'
        )
        parts = output.split(", ")
        if len(parts) == 4:
            return (int(parts[2]), int(parts[3]))
        return (1440, 900)


# ─── Linux 后端 ───────────────────────────────────────────

class LinuxBackend(ComputerBackend):
    """Linux 后端 — 用 xdotool + wmctrl + bash 直接控制系统。"""

    def _cmd(self, cmd: list[str]) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return ""

    def get_active_window(self) -> str:
        wid = self._cmd(["xdotool", "getactivewindow"])
        if wid and wid[0].isdigit():
            return self._cmd(["xdotool", "getwindowname", wid])
        return ""

    def list_windows(self) -> list[str]:
        output = self._cmd(["wmctrl", "-l"])
        windows = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split(None, 3)
            if len(parts) >= 4:
                windows.append(parts[3])
            elif parts:
                windows.append(line)
        return windows[:30]

    def focus_window(self, title: str) -> bool:
        result = self._cmd(["xdotool", "search", "--name", title, "windowactivate"])
        return bool(result)

    def press_key(self, key: str) -> None:
        k = KEY_MAP.get(key.lower(), key)
        self._cmd(["xdotool", "key", k])

    def type_text(self, text: str) -> None:
        self._cmd(["xdotool", "type", text])

    def hotkey(self, *keys: str) -> None:
        lower_keys = [k.lower() for k in keys]
        mapped = [KEY_MAP.get(k, k) for k in lower_keys]
        self._cmd(["xdotool", "key"] + mapped)

    def open_program(self, program_name: str) -> bool:
        try:
            # 尝试直接启动程序
            subprocess.Popen(
                [program_name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            try:
                self._cmd(["xdg-open", program_name])
                return True
            except Exception:
                return False

    def run_command(self, command: str) -> str:
        try:
            r = subprocess.run(
                ["bash", "-c", command],
                capture_output=True, text=True, timeout=30,
            )
            output = r.stdout.strip()[:2000]
            error = r.stderr.strip()[:500]
            parts = []
            if output:
                parts.append(f"Output:\n{output}")
            if error:
                parts.append(f"Error:\n{error}")
            return "\n".join(parts) if parts else "[命令执行完毕，无输出]"
        except subprocess.TimeoutExpired:
            return "[命令执行超时]"
        except Exception as exc:
            return f"[命令执行失败: {exc}]"

    def open_file(self, path: str) -> bool:
        try:
            subprocess.run(["xdg-open", path], check=True, timeout=5)
            return True
        except Exception:
            return False

    def open_terminal(self, command: str = "") -> None:
        if command:
            subprocess.Popen(
                ["x-terminal-emulator", "-e", "bash", "-c", command],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                ["x-terminal-emulator"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    def get_screen_size(self) -> tuple[int, int]:
        output = self._cmd(["xdotool", "getdisplaygeometry"])
        parts = output.split()
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
        return (1920, 1080)


# ─── Windows 后端 ─────────────────────────────────────────

class WindowsBackend(ComputerBackend):
    """Windows 后端 — 用 PowerShell + ctypes 直接控制系统。"""

    def _run_powershell(self, script: str) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True, text=True, timeout=10,
            )
            return r.stdout.strip()
        except Exception:
            return ""

    def get_active_window(self) -> str:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""

    def list_windows(self) -> list[str]:
        output = self._run_powershell(
            "(Get-Process | Where-Object {$_.MainWindowTitle -ne ''}) | "
            "Select-Object -ExpandProperty MainWindowTitle"
        )
        return [w.strip() for w in output.split("\n") if w.strip()][:30]

    def focus_window(self, title: str) -> bool:
        self._run_powershell(
            f"(Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}}) | "
            f"ForEach-Object {{$_.MainWindowHandle}} | "
            f"ForEach-Object {{[Microsoft.VisualBasic.Interaction]::AppActivate($_)}}"
        )
        return True

    def press_key(self, key: str) -> None:
        import ctypes
        vk_map = {
            "enter": 0x0D, "esc": 0x1B, "tab": 0x09,
            "space": 0x20, "backspace": 0x08,
            "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
            "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
            "home": 0x24, "end": 0x23, "delete": 0x2E,
            "pageup": 0x21, "pagedown": 0x22,
        }
        vk = vk_map.get(key.lower())
        if vk is None and len(key) == 1:
            vk = ord(key.upper())
        if vk is not None:
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

    def type_text(self, text: str) -> None:
        import ctypes
        for char in text:
            vk = ord(char.upper())
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

    def hotkey(self, *keys: str) -> None:
        vk_map = {
            "ctrl": 0x11, "control": 0x11,
            "alt": 0x12, "shift": 0x10,
            "win": 0x5B, "tab": 0x09,
        }
        import ctypes
        lower_keys = [k.lower() for k in keys]
        for k in lower_keys:
            vk = vk_map.get(k, ord(k.upper()))
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        for k in reversed(lower_keys):
            vk = vk_map.get(k, ord(k.upper()))
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

    def open_program(self, program_name: str) -> bool:
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", program_name],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def run_command(self, command: str) -> str:
        try:
            r = subprocess.run(
                ["cmd", "/c", command],
                capture_output=True, text=True, timeout=30,
            )
            output = r.stdout.strip()
            error = r.stderr.strip()
            parts = []
            if output:
                parts.append(f"Output:\n{output[:2000]}")
            if error:
                parts.append(f"Error:\n{error[:500]}")
            return "\n".join(parts) if parts else "[命令执行完毕，无输出]"
        except subprocess.TimeoutExpired:
            return "[命令执行超时]"
        except Exception as exc:
            return f"[命令执行失败: {exc}]"

    def open_file(self, path: str) -> bool:
        try:
            os.startfile(path)
            return True
        except Exception:
            return False

    def open_terminal(self, command: str = "") -> None:
        if command:
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", command],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd"],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    def get_screen_size(self) -> tuple[int, int]:
        import ctypes
        return (
            ctypes.windll.user32.GetSystemMetrics(0),
            ctypes.windll.user32.GetSystemMetrics(1),
        )


# ─── 后端工厂 ─────────────────────────────────────────────

def get_backend() -> ComputerBackend:
    if CURRENT_OS == OS.MAC:
        return MacBackend()
    elif CURRENT_OS == OS.LINUX:
        return LinuxBackend()
    elif CURRENT_OS == OS.WINDOWS:
        return WindowsBackend()
    return LinuxBackend()


_BACKEND = get_backend()


# ═══════════════════════════════════════════════════════════
# 工具定义
# ═══════════════════════════════════════════════════════════

class ComputerPressKey(BaseTool):
    """按键盘键 — 像人类一样按键操作。"""

    name = "press_key"
    description = (
        "按键盘上的一个键。支持所有标准键。\n"
        "常用键: enter, esc, tab, space, backspace, delete\n"
        "方向键: up, down, left, right\n"
        "功能键: f1-f12\n"
        "字母: a-z (直接传字母本身)"
    )
    schema = ToolSchema(
        properties={
            "key": {"type": "string", "description": "要按的键名，如 enter, tab, a, esc"},
            "times": {"type": "integer", "description": "按几次（默认1次）"},
        },
        required=["key"],
    )

    async def run(self, key: str, times: int = 1) -> str:
        for _ in range(times):
            _BACKEND.press_key(key)
        return f"按了 '{key}' {times} 次"


class ComputerType(BaseTool):
    """输入文字 — 像人类一样用键盘打字。"""

    name = "type_text"
    description = (
        "在当前光标位置输入一段文字。\n"
        "像人类打字一样，每个字符依次输入。\n"
        "支持中文、英文、数字、符号。"
    )
    schema = ToolSchema(
        properties={
            "text": {"type": "string", "description": "要输入的文字内容"},
        },
        required=["text"],
    )

    async def run(self, text: str) -> str:
        _BACKEND.type_text(text)
        return f"输入了 {len(text)} 个字符"


class ComputerHotkey(BaseTool):
    """快捷键组合 — 像人类一样按快捷键。"""

    name = "press_hotkey"
    description = (
        "按快捷键组合。\n"
        "常用快捷键:\n"
        "  Ctrl+C 复制, Ctrl+V 粘贴, Ctrl+X 剪切, Ctrl+Z 撤销\n"
        "  Alt+Tab 切换窗口, Ctrl+S 保存\n"
        "  Win+D 显示桌面 (Windows), Cmd+Space 搜索 (Mac)\n"
        "  Alt+F4 关闭窗口 (Windows), Cmd+Q 退出 (Mac)"
    )
    schema = ToolSchema(
        properties={
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "按键列表, 如 ['ctrl', 'c'], ['alt', 'tab']",
            },
        },
        required=["keys"],
    )

    async def run(self, keys: list[str]) -> str:
        _BACKEND.hotkey(*keys)
        return f"按了快捷键: {'+'.join(keys)}"


class ComputerOpenProgram(BaseTool):
    """打开程序/应用 — 像人类在开始菜单搜索一样打开程序。"""

    name = "open_program"
    description = (
        "打开一个程序或应用。\n"
        "像人类一样：按Win键→搜索程序名→回车。\n"
        "示例: 'chrome', 'notepad', 'calculator', 'terminal'"
    )
    schema = ToolSchema(
        properties={
            "name": {"type": "string", "description": "程序名称, 如 chrome, notepad, code"},
        },
        required=["name"],
    )

    async def run(self, name: str) -> str:
        success = _BACKEND.open_program(name)
        if success:
            return f"已打开程序: {name}"
        return f"无法打开: {name}"


class ComputerRunShell(BaseTool):
    """执行命令 — 像人类在终端里敲命令一样。"""

    name = "run_command"
    description = (
        "执行一条系统命令并返回输出结果。\n"
        "可以用来自动化任何操作：\n"
        "  - 文件操作: ls, cp, mv, rm\n"
        "  - 系统信息: ps, top, df, who\n"
        "  - 网络: ping, curl, ifconfig\n"
        "  - 进程管理: kill, nohup\n"
        "  - 任何你可以在终端做的事情"
    )
    schema = ToolSchema(
        properties={
            "command": {"type": "string", "description": "要执行的命令"},
            "timeout": {"type": "integer", "description": "超时秒数（默认30）"},
        },
        required=["command"],
    )

    async def run(self, command: str, timeout: int = 30) -> str:
        return _BACKEND.run_command(command)


class ComputerSwitchWindow(BaseTool):
    """切换窗口 — 像人类用 Alt+Tab 一样切换窗口。"""

    name = "switch_window"
    description = (
        "切换到指定窗口。根据窗口标题匹配。\n"
        "先使用 list_windows 查看当前打开的窗口。\n"
        "示例: switch_window('Chrome') 会切换到 Chrome 浏览器"
    )
    schema = ToolSchema(
        properties={
            "title": {"type": "string", "description": "窗口标题（支持模糊匹配）"},
        },
        required=["title"],
    )

    async def run(self, title: str) -> str:
        success = _BACKEND.focus_window(title)
        if success:
            return f"已切换到窗口: {title}"
        return f"未找到匹配的窗口: {title}"


class ComputerListWindows(BaseTool):
    """列出窗口 — 查看当前所有打开的窗口。"""

    name = "list_windows"
    description = (
        "列出当前所有打开的窗口标题。\n"
        "在执行 switch_window 之前使用，查看有哪些窗口可以切换。"
    )

    async def run(self) -> str:
        windows = _BACKEND.list_windows()
        if not windows:
            return "当前没有打开的窗口"
        lines = [f"当前打开的窗口 ({len(windows)}):", ""]
        for i, w in enumerate(windows, 1):
            lines.append(f"  {i}. {w}")
        return "\n".join(lines)


class ComputerGetScreenInfo(BaseTool):
    """获取屏幕信息 — 查看屏幕状态。"""

    name = "get_screen_info"
    description = (
        "获取当前屏幕信息：分辨率、活动窗口。\n"
        "在执行其他操作前可以用来了解当前状态。"
    )

    async def run(self) -> str:
        w, h = _BACKEND.get_screen_size()
        active = _BACKEND.get_active_window()
        return (
            f"屏幕分辨率: {w}x{h}\n"
            f"当前活动窗口: {active}\n"
            f"操作系统: {CURRENT_OS.value}"
        )


class ComputerOpenFile(BaseTool):
    """打开文件 — 用默认程序打开文件或文件夹。"""

    name = "open_file"
    description = (
        "用系统默认程序打开文件或文件夹。\n"
        "支持任何文件类型：PDF、图片、文档、文件夹等。"
    )
    schema = ToolSchema(
        properties={
            "path": {"type": "string", "description": "文件或文件夹路径"},
        },
        required=["path"],
    )

    async def run(self, path: str) -> str:
        success = _BACKEND.open_file(path)
        if success:
            return f"已打开: {path}"
        return f"无法打开: {path}"


class ComputerOpenTerminal(BaseTool):
    """打开终端 — 打开一个新的终端窗口。"""

    name = "open_terminal"
    description = (
        "打开一个新的终端/命令行窗口。\n"
        "可选传入一个命令，在新终端中执行。"
    )
    schema = ToolSchema(
        properties={
            "command": {"type": "string", "description": "可选：要在新终端中执行的命令"},
        },
    )

    async def run(self, command: str = "") -> str:
        _BACKEND.open_terminal(command)
        if command:
            return f"已打开终端并执行: {command}"
        return "已打开终端"