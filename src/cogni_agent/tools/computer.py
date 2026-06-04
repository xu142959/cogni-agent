"""Computer Control Tools for CogniAgent — cross-platform (macOS / Linux / Windows).

Architecture:
  ┌─────────────────────────────────────────────┐
  │              ComputerTool (Base)              │
  ├──────────────────┬──────────────────┬────────┤
  │   MacBackend     │   LinuxBackend   │ Win*   │
  │  (CGImage+Apple │  (X11/Wayland)   │ (todo) │
  │   Scripts)      │                  │        │
  └──────────────────┴──────────────────┴────────┘

Each tool auto-detects the OS at runtime and uses the correct backend.
macOS backends: pyautogui + AppleScript + mss
Linux backends: pyautogui (X11) + mss + xdotool/wmctrl
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


# ─── Backend Abstraction ───────────────────────────────────

class ComputerBackend(ABC):
    """Abstract computer control backend — platform-specific implementations."""

    @abstractmethod
    def screenshot(self, output_path: str) -> str:
        """Take a screenshot and save to path. Returns path."""
        ...

    def screenshot_bytes(self) -> bytes:
        """Take a screenshot and return raw PNG bytes."""
        ...

    @abstractmethod
    def mouse_move(self, x: int, y: int) -> None:
        """Move mouse to absolute coordinates."""
        ...

    @abstractmethod
    def mouse_click(self, x: int, y: int, button: str = "left") -> None:
        """Click at position."""
        ...

    @abstractmethod
    def mouse_scroll(self, clicks: int) -> None:
        """Scroll. Positive=up, Negative=down."""
        ...

    @abstractmethod
    def keyboard_type(self, text: str) -> None:
        """Type text."""
        ...

    @abstractmethod
    def keyboard_hotkey(self, *keys: str) -> None:
        """Execute a hotkey combination, e.g. hotkey('ctrl', 'c')"""
        ...

    @abstractmethod
    def keyboard_press(self, key: str) -> None:
        """Press and release a single key."""
        ...

    @abstractmethod
    def get_screen_size(self) -> tuple[int, int]:
        """Return (width, height)."""
        ...

    @abstractmethod
    def get_active_window_title(self) -> str:
        """Return the title of the active/focused window."""
        ...

    @abstractmethod
    def list_windows(self) -> list[dict]:
        """List all visible windows with title, position, size."""
        ...

    @abstractmethod
    def focus_window(self, title_substring: str) -> bool:
        """Focus a window by title substring. Returns True if found."""
        ...

    @abstractmethod
    def open_file(self, path: str) -> bool:
        """Open a file with the default application."""
        ...

    @abstractmethod
    def open_terminal(self, command: str = "") -> None:
        """Open a terminal and optionally run a command."""
        ...

    def get_mouse_position(self) -> tuple[int, int]:
        """Return current mouse (x, y)."""
        ...

    def get_pixel_color(self, x: int, y: int) -> str:
        """Get hex color of pixel at (x, y), e.g. '#FF0000'."""
        ...


# ─── macOS Backend ─────────────────────────────────────────

class MacBackend(ComputerBackend):
    """macOS backend using pyautogui + mss + AppleScript + osascript."""

    def __init__(self):
        self._has_pyautogui = self._check_pyautogui()

    def _check_pyautogui(self) -> bool:
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            return True
        except ImportError:
            return False

    def _cmd(self, script: str) -> str:
        """Run an AppleScript command."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception as exc:
            return f"[osascript error: {exc}]"

    def screenshot(self, output_path: str) -> str:
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=output_path)
            return output_path
        except ImportError:
            # Fallback: screencapture CLI
            subprocess.run(["screencapture", "-x", output_path], check=True)
            return output_path

    def screenshot_bytes(self) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        self.screenshot(path)
        data = Path(path).read_bytes()
        os.unlink(path)
        return data

    def mouse_move(self, x: int, y: int) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.moveTo(x, y)
        else:
            self._cmd(f'tell application "System Events" to set position of mouse to {{{x}, {y}}}')

    def mouse_click(self, x: int, y: int, button: str = "left") -> None:
        self.mouse_move(x, y)
        btn = "left" if button == "left" else "right"
        if self._has_pyautogui:
            import pyautogui
            pyautogui.click(button=btn)
        else:
            self._cmd(f'tell application "System Events" to click at {{{x}, {y}}}')

    def mouse_scroll(self, clicks: int) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.scroll(clicks)
        else:
            self._cmd(
                f'tell application "System Events" to '
                f'set value of scroll wheel of process "Finder" to {clicks}'
            )

    def keyboard_type(self, text: str) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.write(text)
        else:
            escaped = text.replace('"', '\\"')
            self._cmd(
                f'tell application "System Events" to keystroke "{escaped}"'
            )

    def keyboard_hotkey(self, *keys: str) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.hotkey(*keys)
        else:
            mods = "command" if len(keys) > 1 else ""
            key = keys[-1]
            self._cmd(
                f'tell application "System Events" to keystroke "{key}" '
                f'using command down'
            )

    def keyboard_press(self, key: str) -> None:
        key_map = {
            "enter": "return", "esc": "escape", "tab": "tab",
            "up": "up", "down": "down", "left": "left", "right": "right",
            "backspace": "delete", "space": "space",
        }
        mapped = key_map.get(key.lower(), key)
        if self._has_pyautogui:
            import pyautogui
            pyautogui.press(mapped)
        else:
            self._cmd(
                f'tell application "System Events" to keystroke "{mapped}"'
            )

    def get_screen_size(self) -> tuple[int, int]:
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                return (monitor["width"], monitor["height"])
        except ImportError:
            output = self._cmd(
                'tell application "Finder" to get bounds of window of desktop'
            )
            parts = output.split(", ")
            if len(parts) == 4:
                return (int(parts[2]), int(parts[3]))
            return (1440, 900)

    def get_active_window_title(self) -> str:
        return self._cmd(
            'tell application "System Events" to get name of first process '
            'whose frontmost is true'
        )

    def get_mouse_position(self) -> tuple[int, int]:
        if self._has_pyautogui:
            import pyautogui
            x, y = pyautogui.position()
            return (x, y)
        output = self._cmd(
            'tell application "System Events" to get position of mouse'
        )
        parts = output.replace("{", "").replace("}", "").split(", ")
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
        return (0, 0)

    def get_pixel_color(self, x: int, y: int) -> str:
        import mss
        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": 1, "height": 1}
            img = sct.grab(monitor)
            pixel = img.pixel(0, 0)
            return f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}"

    def list_windows(self) -> list[dict]:
        output = self._cmd(
            'tell application "System Events" to get name of every process '
            'whose background only is false'
        )
        names = [n.strip() for n in output.split(", ") if n.strip()]
        return [{"title": n, "app": n, "platform": "mac"} for n in names[:20]]

    def focus_window(self, title_substring: str) -> bool:
        result = self._cmd(
            f'tell application "System Events" to set frontmost of '
            f'(first process whose name contains "{title_substring}") to true'
        )
        return "error" not in result.lower()

    def open_file(self, path: str) -> bool:
        try:
            subprocess.run(["open", path], check=True, timeout=5)
            return True
        except Exception:
            return False

    def open_terminal(self, command: str = "") -> None:
        if command:
            script = f'tell application "Terminal" to do script "{command}"'
        else:
            script = 'tell application "Terminal" to activate'
        self._cmd(script)


# ─── Linux Backend ─────────────────────────────────────────

class LinuxBackend(ComputerBackend):
    """Linux backend using pyautogui + mss + xdotool + wmctrl."""

    def __init__(self):
        self._has_pyautogui = self._check_pyautogui()

    def _check_pyautogui(self) -> bool:
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            return True
        except ImportError:
            return False

    def _cmd(self, cmd: list[str]) -> str:
        """Run a shell command and return stdout."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
        except Exception as exc:
            return f"[error: {exc}]"

    def screenshot(self, output_path: str) -> str:
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=output_path)
            return output_path
        except ImportError:
            self._cmd(["import", "-window", "root", output_path])
            return output_path

    def screenshot_bytes(self) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        self.screenshot(path)
        data = Path(path).read_bytes()
        os.unlink(path)
        return data

    def mouse_move(self, x: int, y: int) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.moveTo(x, y)
        else:
            self._cmd(["xdotool", "mousemove", str(x), str(y)])

    def mouse_click(self, x: int, y: int, button: str = "left") -> None:
        self.mouse_move(x, y)
        btn_map = {"left": 1, "middle": 2, "right": 3}
        btn = btn_map.get(button, 1)
        if self._has_pyautogui:
            import pyautogui
            pyautogui.click(button=button)
        else:
            self._cmd(["xdotool", "click", str(btn)])

    def mouse_scroll(self, clicks: int) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.scroll(clicks)
        else:
            btn = 4 if clicks > 0 else 5
            for _ in range(abs(clicks)):
                self._cmd(["xdotool", "click", str(btn)])

    def keyboard_type(self, text: str) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.write(text)
        else:
            self._cmd(["xdotool", "type", text])

    def keyboard_hotkey(self, *keys: str) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.hotkey(*keys)
        else:
            self._cmd(["xdotool", "key"] + [k.lower() for k in keys])

    def keyboard_press(self, key: str) -> None:
        if self._has_pyautogui:
            import pyautogui
            pyautogui.press(key)
        else:
            self._cmd(["xdotool", "key", key])

    def get_screen_size(self) -> tuple[int, int]:
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                return (monitor["width"], monitor["height"])
        except ImportError:
            output = self._cmd(["xdotool", "getdisplaygeometry"])
            parts = output.split()
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
            return (1920, 1080)

    def get_active_window_title(self) -> str:
        wid = self._cmd(["xdotool", "getactivewindow"])
        if wid and wid[0].isdigit():
            return self._cmd(["xdotool", "getwindowname", wid])
        return "unknown"

    def get_mouse_position(self) -> tuple[int, int]:
        if self._has_pyautogui:
            import pyautogui
            x, y = pyautogui.position()
            return (x, y)
        output = self._cmd(["xdotool", "getmouselocation"])
        if not output:
            return (0, 0)
        # "x:123 y:456 screen:0 window:789"
        import re
        x_match = re.search(r"x:(\d+)", output)
        y_match = re.search(r"y:(\d+)", output)
        x = int(x_match.group(1)) if x_match else 0
        y = int(y_match.group(1)) if y_match else 0
        return (x, y)

    def get_pixel_color(self, x: int, y: int) -> str:
        try:
            import mss
            with mss.mss() as sct:
                monitor = {"top": y, "left": x, "width": 1, "height": 1}
                img = sct.grab(monitor)
                pixel = img.pixel(0, 0)
                return f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}"
        except ImportError:
            return "#000000"

    def list_windows(self) -> list[dict]:
        output = self._cmd(["wmctrl", "-l"])
        windows = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split(None, 3)
            if len(parts) >= 4:
                windows.append({
                    "id": parts[0],
                    "desktop": parts[1],
                    "pid": parts[2],
                    "title": parts[3],
                    "platform": "linux",
                })
            elif len(parts) >= 1:
                windows.append({"id": parts[0], "title": line, "platform": "linux"})
        return windows[:20]

    def focus_window(self, title_substring: str) -> bool:
        result = self._cmd(
            ["xdotool", "search", "--name", title_substring, "windowactivate"]
        )
        return bool(result.strip())

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


# ─── Windows Backend (placeholder) ─────────────────────────

class WindowsBackend(ComputerBackend):
    """Windows backend — TODO."""

    def screenshot(self, output_path: str) -> str:
        return "[Windows screenshot not yet implemented]"

    def screenshot_bytes(self) -> bytes:
        return b""

    def mouse_move(self, x: int, y: int) -> None:
        pass

    def mouse_click(self, x: int, y: int, button: str = "left") -> None:
        pass

    def mouse_scroll(self, clicks: int) -> None:
        pass

    def keyboard_type(self, text: str) -> None:
        pass

    def keyboard_hotkey(self, *keys: str) -> None:
        pass

    def keyboard_press(self, key: str) -> None:
        pass

    def get_screen_size(self) -> tuple[int, int]:
        return (1920, 1080)

    def get_active_window_title(self) -> str:
        return ""

    def list_windows(self) -> list[dict]:
        return []

    def focus_window(self, title_substring: str) -> bool:
        return False

    def open_file(self, path: str) -> bool:
        return False

    def open_terminal(self, command: str = "") -> None:
        pass


# ─── Backend Factory ───────────────────────────────────────

def get_backend() -> ComputerBackend:
    """Get the appropriate backend for the current OS."""
    if CURRENT_OS == OS.MAC:
        return MacBackend()
    elif CURRENT_OS == OS.LINUX:
        return LinuxBackend()
    elif CURRENT_OS == OS.WINDOWS:
        return WindowsBackend()
    else:
        # Fallback: try Linux, then macOS
        try:
            return LinuxBackend()
        except Exception:
            return MacBackend()


_BACKEND = get_backend()


# ═══════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════

# ─── Screenshot ────────────────────────────────────────────

class ComputerScreenshot(BaseTool):
    """Take a screenshot of the current screen."""

    name = "computer_screenshot"
    description = (
        "Take a screenshot of the current screen. "
        "Returns a description of what's visible. "
        "Use this to understand the current state of the desktop, "
        "find UI elements, or see what the user is looking at."
    )

    async def run(self) -> str:
        """Take a screenshot and describe the result."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name

        try:
            result_path = _BACKEND.screenshot(path)
            import os
            size = os.path.getsize(result_path)
            w, h = _BACKEND.get_screen_size()
            active = _BACKEND.get_active_window_title()
            os.unlink(result_path)

            return (
                f"Screenshot taken: {w}x{h} ({size:,} bytes)\n"
                f"Active window: {active}\n"
                f"Platform: {CURRENT_OS.value}"
            )
        except Exception as exc:
            return f"[Screenshot failed: {exc}]"


# ─── Mouse Control ─────────────────────────────────────────

class ComputerMouseMove(BaseTool):
    """Move the mouse cursor to a position on screen."""

    name = "computer_mouse_move"
    description = (
        "Move the mouse cursor to an absolute position on screen. "
        "Coordinates: (0,0) = top-left. "
        "Use computer_screenshot or get_screen_size to understand the coordinate space."
    )
    schema = ToolSchema(
        properties={
            "x": {"type": "integer", "description": "X coordinate (horizontal, 0 = left)"},
            "y": {"type": "integer", "description": "Y coordinate (vertical, 0 = top)"},
        },
        required=["x", "y"],
    )

    async def run(self, x: int, y: int) -> str:
        _BACKEND.mouse_move(x, y)
        return f"Moved mouse to ({x}, {y})"


class ComputerMouseClick(BaseTool):
    """Click the mouse at the current position or at specified coordinates."""

    name = "computer_mouse_click"
    description = (
        "Click at a position on screen. Defaults to current mouse position "
        "if x/y not provided. Supports left, right, and middle clicks."
    )
    schema = ToolSchema(
        properties={
            "x": {"type": "integer", "description": "X coordinate (optional, uses current if omitted)"},
            "y": {"type": "integer", "description": "Y coordinate (optional)"},
            "button": {
                "type": "string",
                "description": "Mouse button: 'left', 'right', or 'middle' (default: 'left')",
                "enum": ["left", "right", "middle"],
            },
        },
    )

    async def run(self, x: int | None = None, y: int | None = None, button: str = "left") -> str:
        if x is not None and y is not None:
            _BACKEND.mouse_move(x, y)
        _BACKEND.mouse_click(x or 0, y or 0, button)
        pos = _BACKEND.get_mouse_position()
        return f"Clicked {button} button at ({pos[0]}, {pos[1]})"


class ComputerMouseScroll(BaseTool):
    """Scroll the mouse wheel."""

    name = "computer_mouse_scroll"
    description = (
        "Scroll the mouse wheel. "
        "Positive values scroll up, negative values scroll down."
    )
    schema = ToolSchema(
        properties={
            "clicks": {
                "type": "integer",
                "description": "Number of scroll clicks. Positive = up, Negative = down.",
            },
        },
        required=["clicks"],
    )

    async def run(self, clicks: int) -> str:
        _BACKEND.mouse_scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return f"Scrolled {direction} {abs(clicks)} clicks"


# ─── Keyboard Control ──────────────────────────────────────

class ComputerType(BaseTool):
    """Type text as if from the keyboard."""

    name = "computer_type"
    description = (
        "Type a string of text at the current cursor position. "
        "Useful for filling in forms, typing commands, or entering text."
    )
    schema = ToolSchema(
        properties={
            "text": {"type": "string", "description": "The text to type"},
        },
        required=["text"],
    )

    async def run(self, text: str) -> str:
        _BACKEND.keyboard_type(text)
        return f"Typed {len(text)} characters"


class ComputerHotkey(BaseTool):
    """Press a keyboard shortcut combination."""

    name = "computer_hotkey"
    description = (
        "Press a keyboard shortcut combination. "
        "Examples: "
        'hotkey("command", "c") = Copy, '
        'hotkey("ctrl", "v") = Paste, '
        'hotkey("alt", "tab") = Switch windows, '
        'hotkey("ctrl", "shift", "esc") = Task manager.'
    )
    schema = ToolSchema(
        properties={
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of keys to press together, e.g. ['command', 'c']",
            },
        },
        required=["keys"],
    )

    async def run(self, keys: list[str]) -> str:
        _BACKEND.keyboard_hotkey(*keys)
        return f"Pressed hotkey: {'+'.join(keys)}"


class ComputerPress(BaseTool):
    """Press and release a single key."""

    name = "computer_press"
    description = (
        "Press and release a single key. "
        "Common keys: enter, esc, tab, space, backspace, "
        "up, down, left, right, f1-f12, delete, home, end."
    )
    schema = ToolSchema(
        properties={
            "key": {"type": "string", "description": "The key to press"},
        },
        required=["key"],
    )

    async def run(self, key: str) -> str:
        _BACKEND.keyboard_press(key)
        return f"Pressed key: {key}"


# ─── Screen / Window Info ──────────────────────────────────

class ComputerScreenInfo(BaseTool):
    """Get information about the screen and display."""

    name = "computer_screen_info"
    description = (
        "Get information about the current display: "
        "screen resolution, active window, mouse position. "
        "Use this to understand the coordinate space before clicking or moving."
    )

    async def run(self) -> str:
        w, h = _BACKEND.get_screen_size()
        mx, my = _BACKEND.get_mouse_position()
        active = _BACKEND.get_active_window_title()
        return (
            f"Screen: {w}x{h}\n"
            f"Mouse: ({mx}, {my})\n"
            f"Active window: {active}\n"
            f"OS: {CURRENT_OS.value}"
        )


class ComputerListWindows(BaseTool):
    """List all visible windows on the desktop."""

    name = "computer_list_windows"
    description = (
        "List all visible windows. Returns titles and positions. "
        "Use this to find the right window before switching focus."
    )

    async def run(self) -> str:
        windows = _BACKEND.list_windows()
        if not windows:
            return "No windows found or window listing not supported on this platform."

        lines = [f"Windows ({len(windows)}):", ""]
        for i, w in enumerate(windows, 1):
            title = w.get("title", w.get("app", "unknown"))
            lines.append(f"  {i}. {title}")
        return "\n".join(lines)


class ComputerFocusWindow(BaseTool):
    """Focus/bring a window to the front by its title."""

    name = "computer_focus_window"
    description = (
        "Bring a window to the front by matching a substring of its title. "
        "Use computer_list_windows first to find the exact title."
    )
    schema = ToolSchema(
        properties={
            "title": {
                "type": "string",
                "description": "Substring of the window title to match",
            },
        },
        required=["title"],
    )

    async def run(self, title: str) -> str:
        success = _BACKEND.focus_window(title)
        if success:
            return f"Focused window: {title}"
        return f"Could not find window containing: {title}"


# ─── System / File ─────────────────────────────────────────

class ComputerOpenFile(BaseTool):
    """Open a file or URL with the default application."""

    name = "computer_open"
    description = (
        "Open a file or URL with the system's default application. "
        "Can open files (PDFs, images, documents) and URLs (websites)."
    )
    schema = ToolSchema(
        properties={
            "target": {
                "type": "string",
                "description": "File path or URL to open",
            },
        },
        required=["target"],
    )

    async def run(self, target: str) -> str:
        success = _BACKEND.open_file(target)
        if success:
            return f"Opened: {target}"
        return f"Failed to open: {target}"


class ComputerOpenTerminal(BaseTool):
    """Open a terminal window."""

    name = "computer_terminal"
    description = (
        "Open a terminal window. Optionally run a command in the new terminal. "
        "On macOS opens Terminal.app, on Linux opens the default terminal emulator."
    )
    schema = ToolSchema(
        properties={
            "command": {
                "type": "string",
                "description": "Optional command to run in the terminal",
            },
        },
    )

    async def run(self, command: str = "") -> str:
        _BACKEND.open_terminal(command)
        if command:
            return f"Opened terminal running: {command}"
        return "Opened terminal"


# ─── Run AppleScript (macOS only) ──────────────────────────

class ComputerRunAppleScript(BaseTool):
    """Run an AppleScript on macOS."""

    name = "computer_applescript"
    description = (
        "Run an AppleScript on macOS. Only works on macOS. "
        "Useful for deep macOS automation that the other tools don't cover."
    )
    schema = ToolSchema(
        properties={
            "script": {
                "type": "string",
                "description": "AppleScript code to execute. "
                    'Example: tell application "Safari" to activate',
            },
        },
        required=["script"],
    )

    async def run(self, script: str) -> str:
        if CURRENT_OS != OS.MAC:
            return "[AppleScript only works on macOS]"
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=15,
            )
            if result.stdout.strip():
                return result.stdout.strip()
            if result.returncode != 0:
                return f"[AppleScript error: {result.stderr.strip()}]"
            return "[AppleScript executed successfully]"
        except Exception as exc:
            return f"[AppleScript error: {exc}]"


# ─── Run Shell Command (Linux/macOS) ───────────────────────

class ComputerRunShell(BaseTool):
    """Run a shell command on the local machine."""

    name = "computer_shell"
    description = (
        "Run a shell command on the local machine. "
        "Works on macOS and Linux. "
        "Useful for system operations, running scripts, checking system state. "
        "WARNING: This executes real commands — use with caution."
    )
    schema = ToolSchema(
        properties={
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 10, max: 60)",
            },
        },
        required=["command"],
    )

    async def run(self, command: str, timeout: int = 10) -> str:
        if CURRENT_OS == OS.WINDOWS:
            return "[Shell commands not yet supported on Windows]"

        timeout = max(1, min(60, timeout))
        try:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout.strip()
            error = result.stderr.strip()

            parts = []
            if output:
                parts.append(f"Output:\n{output[:2000]}")
            if error:
                parts.append(f"Error:\n{error[:1000]}")

            return "\n".join(parts) if parts else "[Command completed with no output]"

        except subprocess.TimeoutExpired:
            return f"[Command timed out after {timeout}s]"
        except Exception as exc:
            return f"[Shell error: {exc}]"