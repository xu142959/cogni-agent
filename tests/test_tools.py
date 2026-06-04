"""Tool system tests — WebSearch, File I/O, Calculator, PythonREPL, etc."""

import pytest

from cogni_agent.tools import (
    BaseTool,
    Calculator,
    Echo,
    FileList,
    FileRead,
    FileWrite,
    PythonREPL,
    ToolRegistry,
    ToolSchema,
    WebFetch,
    WebSearch,
)


# ─── Calculator ─────────────────────────────────────────────

class TestCalculator:
    @pytest.mark.asyncio
    async def test_simple_arithmetic(self):
        calc = Calculator()
        result = await calc.run(expression="2 + 2")
        assert result.strip() == "4"

    @pytest.mark.asyncio
    async def test_complex_expression(self):
        calc = Calculator()
        result = await calc.run(expression="(15 + 3) * 2")
        assert result.strip() == "36"

    @pytest.mark.asyncio
    async def test_sqrt(self):
        calc = Calculator()
        result = await calc.run(expression="sqrt(144)")
        assert result.strip() == "12.0"

    @pytest.mark.asyncio
    async def test_trig(self):
        calc = Calculator()
        import math
        result = await calc.run(expression="sin(pi/2)")
        assert abs(float(result) - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_invalid_expression(self):
        calc = Calculator()
        result = await calc.run(expression="invalid @@ syntax")
        assert "Error" in result

    def test_schema(self):
        calc = Calculator()
        ot = calc.to_openai_tool()
        assert ot["function"]["name"] == "calculator"
        assert "expression" in ot["function"]["parameters"]["properties"]
        assert "expression" in ot["function"]["parameters"]["required"]


# ─── Web Search ─────────────────────────────────────────────

class TestWebSearch:
    @pytest.mark.asyncio
    async def test_web_search(self):
        tool = WebSearch()
        result = await tool.run(query="Python programming language")
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_web_search_max_results(self):
        tool = WebSearch()
        result = await tool.run(query="test", max_results=3)
        assert result is not None

    def test_schema(self):
        tool = WebSearch()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "web_search"
        assert "query" in ot["function"]["parameters"]["required"]


# ─── Web Fetch ──────────────────────────────────────────────

class TestWebFetch:
    @pytest.mark.asyncio
    async def test_fetch(self):
        tool = WebFetch()
        result = await tool.run(url="https://example.com", max_chars=500)
        assert "Example Domain" in result or "example" in result.lower()

    @pytest.mark.asyncio
    async def test_fetch_invalid_url(self):
        tool = WebFetch()
        result = await tool.run(url="https://this-does-not-exist-12345.com")
        assert "[Error" in result or "[HTTP" in result or "Error" in result

    def test_schema(self):
        tool = WebFetch()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "web_fetch"
        assert "url" in ot["function"]["parameters"]["required"]


# ─── File I/O ───────────────────────────────────────────────

class TestFileRead:
    @pytest.mark.asyncio
    async def test_read_existing_file(self):
        tool = FileRead()
        result = await tool.run(path="README.md")
        assert "CogniAgent" in result or "Error" not in result

    @pytest.mark.asyncio
    async def test_read_nonexistent(self):
        tool = FileRead()
        result = await tool.run(path="/nonexistent_file_xyz.txt")
        assert "[File not found" in result

    def test_schema(self):
        tool = FileRead()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "file_read"


class TestFileWrite:
    @pytest.mark.asyncio
    async def test_write_and_readback(self):
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".txt")

        write_tool = FileWrite()
        write_result = await write_tool.run(path=tmp, content="hello world")
        assert "Successfully" in write_result

        read_tool = FileRead()
        read_result = await read_tool.run(path=tmp)
        assert "hello world" in read_result

        os.unlink(tmp)


class TestFileList:
    @pytest.mark.asyncio
    async def test_list_directory(self):
        tool = FileList()
        result = await tool.run(path=".")
        # Should find README.md and other project files
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_list_with_pattern(self):
        tool = FileList()
        result = await tool.run(path=".", pattern="*.md")
        assert "README.md" in result or "[No files" in result


# ─── Python REPL ────────────────────────────────────────────

class TestPythonREPL:
    @pytest.mark.asyncio
    async def test_simple_code(self):
        repl = PythonREPL()
        result = await repl.run(code="print('hello world')")
        assert result.strip() == "hello world"

    @pytest.mark.asyncio
    async def test_math_operations(self):
        repl = PythonREPL()
        result = await repl.run(code="print(sum(range(100)))")
        assert result.strip() == "4950"

    @pytest.mark.asyncio
    async def test_variable_persistence(self):
        repl = PythonREPL()
        await repl.run(code="x = 42")
        result = await repl.run(code="print(x)")
        assert result.strip() == "42"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        repl = PythonREPL()
        result = await repl.run(code="print(1/0)")
        assert "Error" in result or "ZeroDivisionError" in result

    @pytest.mark.asyncio
    async def test_restricted_imports(self):
        # File I/O modules should not be available
        repl = PythonREPL()
        result = await repl.run(code="""
try:
    import os
    print("os imported")
except Exception as e:
    print(f"blocked: {e}")
""")
        assert "blocked" in result

    def test_schema(self):
        repl = PythonREPL()
        ot = repl.to_openai_tool()
        assert ot["function"]["name"] == "python_repl"


# ─── Tool Schema ────────────────────────────────────────────

class TestToolSchema:
    def test_schema_creation(self):
        schema = ToolSchema(
            properties={
                "query": {"type": "string", "description": "The query"},
            },
            required=["query"],
        )
        openai = schema.to_openai()
        assert openai["type"] == "object"
        assert "query" in openai["properties"]
        assert "query" in openai["required"]

    def test_schema_without_required(self):
        schema = ToolSchema(properties={"opt": {"type": "string"}})
        openai = schema.to_openai()
        assert openai["required"] == []


# ─── Echo (convenience) ────────────────────────────────────

class TestEcho:
    @pytest.mark.asyncio
    async def test_echo(self):
        echo = Echo()
        result = await echo.run(message="hello")
        assert result == "Echo: hello"