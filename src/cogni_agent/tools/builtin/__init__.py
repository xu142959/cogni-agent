"""Built-in tools for CogniAgent — web search, file I/O, computation, code execution."""

from __future__ import annotations

import os
from pathlib import Path

from cogni_agent.tools.base import BaseTool, ToolSchema


# ─── Web Search (DuckDuckGo) ────────────────────────────────

class WebSearch(BaseTool):
    """Search the web via DuckDuckGo. No API key required."""

    name = "web_search"
    description = (
        "Search the web for current information. "
        "Returns up to 5 results with titles, snippets, and URLs. "
        "Best for: recent news, factual queries, general knowledge."
    )
    schema = ToolSchema(
        properties={
            "query": {
                "type": "string",
                "description": "The search query (same as you'd type into Google)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (1-10, default 5)",
            },
        },
        required=["query"],
    )

    async def run(self, query: str, max_results: int = 5) -> str:
        """Search the web.

        Args:
            query: The search query string
            max_results: Maximum number of results (1-10)
        """
        try:
            from duckduckgo_search import DDGS

            max_results = max(1, min(10, int(max_results)))
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return f"No results found for '{query}'."

            lines = [f"Web search results for: {query}", ""]
            for i, r in enumerate(results, 1):
                title = r.get("title", "Untitled")
                snippet = r.get("body", "")
                url = r.get("href", "")
                lines.append(f"{i}. {title}")
                lines.append(f"   {snippet[:200]}")
                if url:
                    lines.append(f"   URL: {url}")
                lines.append("")

            return "\n".join(lines)

        except ImportError:
            return (
                f"[Web search requires duckduckgo_search]\n"
                f"pip install duckduckgo_search"
            )
        except Exception as exc:
            return f"[Web search error: {exc}]"


class WebFetch(BaseTool):
    """Fetch and read the content of a web page."""

    name = "web_fetch"
    description = (
        "Fetch a web page and return its text content. "
        "Useful for reading articles, documentation, or specific pages."
    )
    schema = ToolSchema(
        properties={
            "url": {
                "type": "string",
                "description": "The full URL of the page to fetch (including https://)",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (default 4000, max 20000)",
            },
        },
        required=["url"],
    )

    async def run(self, url: str, max_chars: int = 4000) -> str:
        """Fetch a web page.

        Args:
            url: The URL to fetch
            max_chars: Maximum characters to return
        """
        import httpx
        from html import unescape
        import re

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={"User-Agent": "CogniAgent/1.0"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            # Strip tags, get readable text
            text = re.sub(r"<[^>]+>", " ", html)
            text = unescape(text)
            text = re.sub(r"\s+", " ", text).strip()
            text = text[:min(int(max_chars), 20000)]

            return f"Content from {url}:\n\n{text}"

        except httpx.HTTPStatusError as exc:
            return f"[HTTP {exc.response.status_code} when fetching {url}]"
        except Exception as exc:
            return f"[Error fetching {url}: {exc}]"


# ─── File I/O ───────────────────────────────────────────────

class FileRead(BaseTool):
    """Read the contents of a file from the local filesystem."""

    name = "file_read"
    description = (
        "Read the contents of a file. "
        "Returns the file content as text. Supports any text-based file format."
    )
    schema = ToolSchema(
        properties={
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file",
            },
            "encoding": {
                "type": "string",
                "description": "File encoding (default: utf-8)",
            },
        },
        required=["path"],
    )

    async def run(self, path: str, encoding: str = "utf-8") -> str:
        """Read a file.

        Args:
            path: Path to the file
            encoding: File encoding
        """
        try:
            resolved = Path(path).expanduser().resolve()
            if not resolved.exists():
                return f"[File not found: {resolved}]"
            if not resolved.is_file():
                return f"[Not a file: {resolved}]"

            # Security: limit file size to 1MB
            size = resolved.stat().st_size
            if size > 1_000_000:
                return f"[File too large: {size:,} bytes (max 1MB)]"

            # Read with aiofiles if available, fallback to built-in open
            try:
                import aiofiles
                async with aiofiles.open(resolved, encoding=encoding) as f:
                    content = await f.read()
            except ImportError:
                with open(resolved, encoding=encoding) as f:
                    content = f.read()

            return f"File: {resolved}\n---\n{content}"

        except Exception as exc:
            return f"[Error reading file: {exc}]"


class FileWrite(BaseTool):
    """Write content to a file on the local filesystem."""

    name = "file_write"
    description = (
        "Write content to a file. Creates parent directories if needed. "
        "WARNING: This will overwrite existing files."
    )
    schema = ToolSchema(
        properties={
            "path": {
                "type": "string",
                "description": "Absolute or relative path where to write the file",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
        },
        required=["path", "content"],
    )

    async def run(self, path: str, content: str) -> str:
        """Write a file.

        Args:
            path: Path where to write
            content: Content to write
        """
        try:
            resolved = Path(path).expanduser().resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)

            try:
                import aiofiles
                async with aiofiles.open(resolved, "w", encoding="utf-8") as f:
                    await f.write(content)
            except ImportError:
                with open(resolved, "w", encoding="utf-8") as f:
                    f.write(content)

            return f"Successfully wrote {len(content)} bytes to {resolved}"

        except Exception as exc:
            return f"[Error writing file: {exc}]"


class FileList(BaseTool):
    """List files and directories in a given path."""

    name = "file_list"
    description = (
        "List files and directories at a given path. "
        "Shows name, size, and last modified time."
    )
    schema = ToolSchema(
        properties={
            "path": {
                "type": "string",
                "description": "Directory path to list (default: current directory)",
            },
            "pattern": {
                "type": "string",
                "description": "Optional glob pattern to filter (e.g., '*.py', '*.md')",
            },
        },
    )

    async def run(self, path: str = ".", pattern: str = "*") -> str:
        """List directory contents.

        Args:
            path: Directory path
            pattern: Glob filter pattern
        """
        try:
            resolved = Path(path).expanduser().resolve()
            if not resolved.exists():
                return f"[Path not found: {resolved}]"
            if not resolved.is_dir():
                return f"[Not a directory: {resolved}]"

            entries = list(resolved.glob(pattern))
            if not entries:
                return f"[No files matching '{pattern}' in {resolved}]"

            lines = [f"Contents of {resolved}/ ({len(entries)} entries)", ""]
            for entry in sorted(entries):
                if entry.is_dir():
                    lines.append(f"  📁 {entry.name}/")
                else:
                    size = entry.stat().st_size
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024**2:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/1024**2:.1f}MB"
                    lines.append(f"  📄 {entry.name}  ({size_str})")

            return "\n".join(lines)

        except Exception as exc:
            return f"[Error listing directory: {exc}]"


# ─── Computation ────────────────────────────────────────────

class Calculator(BaseTool):
    """Evaluate mathematical expressions with full math library support."""

    name = "calculator"
    description = (
        "Evaluate a mathematical expression and return the numeric result. "
        "Supports: +, -, *, /, **, %, //, and functions from Python's math module "
        "(sqrt, sin, cos, log, pi, e, floor, ceil, abs, round, etc.)."
    )
    schema = ToolSchema(
        properties={
            "expression": {
                "type": "string",
                "description": (
                    "The mathematical expression to evaluate. "
                    'Examples: "2 + 2", "(15 + 3) * 2", "sqrt(144)", '
                    '"sin(pi/4)", "log(100, 10)", "2 ** 10"'
                ),
            },
        },
        required=["expression"],
    )

    async def run(self, expression: str) -> str:
        """Evaluate a mathematical expression.

        Args:
            expression: A mathematical expression string
        """
        import math
        import numbers

        allowed = {
            k: v for k, v in math.__dict__.items()
            if not k.startswith("__")
        }
        allowed.update({
            "abs": abs, "round": round, "int": int, "float": float,
            "min": min, "max": max, "sum": sum,
        })

        try:
            result = eval(expression.strip(), {"__builtins__": {}}, allowed)
            if isinstance(result, numbers.Number):
                return str(result)
            return f"Error: result is not a number ({type(result).__name__})"
        except Exception as exc:
            return f"Error evaluating '{expression}': {exc}"


# ─── Python Code Execution (Sandboxed) ──────────────────────

class PythonREPL(BaseTool):
    """Execute Python code in a restricted environment. Use for data analysis, scripting."""

    name = "python_repl"
    description = (
        "Execute Python code and return stdout + printed output. "
        "Useful for data analysis, text processing, or any computation "
        "that can't be done with the calculator tool alone. "
        "IMPORTANT: This runs in a restricted environment — no network access, "
        "no file writes (except /tmp)."
    )
    schema = ToolSchema(
        properties={
            "code": {
                "type": "string",
                "description": (
                    "The Python code to execute. "
                    "Use print() to see output. "
                    "Variables persist between calls in the same session. "
                    "Available modules: math, json, re, collections, datetime, typing, random."
                ),
            },
        },
        required=["code"],
    )

    # Session-level namespace
    _namespace: dict = {}

    async def run(self, code: str) -> str:
        """Execute Python code.

        Args:
            code: Python code to execute
        """
        import io
        import sys
        import traceback

        # Pre-approved modules for import
        _allowed_modules = {
            "math", "json", "re", "collections", "datetime",
            "typing", "random", "statistics", "itertools",
        }

        def _safe_import(name, *args, **kwargs):
            base = name.split(".")[0]
            if base in _allowed_modules:
                return __import__(name, *args, **kwargs)
            raise ImportError(f"module '{name}' is not allowed")

        safe_builtins = {
            "abs": abs, "all": all, "any": any, "bool": bool,
            "callable": callable, "chr": chr, "dict": dict, "dir": dir,
            "enumerate": enumerate, "Exception": Exception,
            "filter": filter, "float": float, "format": format,
            "frozenset": frozenset, "getattr": getattr, "hasattr": hasattr,
            "int": int, "isinstance": isinstance, "issubclass": issubclass,
            "iter": iter, "len": len, "list": list, "map": map,
            "max": max, "min": min, "next": next, "object": object,
            "ord": ord, "pow": pow, "print": print, "range": range,
            "repr": repr, "reversed": reversed, "round": round,
            "set": set, "setattr": setattr, "slice": slice, "sorted": sorted,
            "str": str, "sum": sum, "tuple": tuple, "type": type,
            "zip": zip, "True": True, "False": False, "None": None,
            "__import__": _safe_import,
        }

        # Pre-approved modules
        import math, json, re, collections, datetime, typing, random, statistics, itertools

        safe_modules = {
            "math": math, "json": json, "re": re,
            "collections": collections, "datetime": datetime,
            "typing": typing, "random": random,
            "statistics": statistics, "itertools": itertools,
        }

        try:
            old_stdout = sys.stdout
            redirected = io.StringIO()
            sys.stdout = redirected

            exec(code, {"__builtins__": safe_builtins, **safe_modules}, self._namespace)

            sys.stdout = old_stdout
            output = redirected.getvalue()

            if not output:
                return "[Code executed successfully — no output]"
            return output.strip()

        except Exception:
            return f"[Error]\n{traceback.format_exc()}"
        finally:
            sys.stdout = old_stdout


class Echo(BaseTool):
    """Echo input back (for testing)."""

    name = "echo"
    description = "Echo the input back to the user."

    schema = ToolSchema(
        properties={
            "message": {
                "type": "string",
                "description": "The message to echo back",
            },
        },
        required=["message"],
    )

    async def run(self, message: str) -> str:
        """Echo a message.

        Args:
            message: The message to echo back
        """
        return f"Echo: {message}"