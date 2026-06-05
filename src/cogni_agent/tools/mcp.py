"""MCP (Model Context Protocol) integration for CogniAgent.

Connects to MCP servers and exposes their tools as CogniAgent BaseTool instances.
This gives agents access to the entire MCP ecosystem:
filesystem, database, browser, Slack, GitHub, and more.

Usage:
    from cogni_agent.tools.mcp import MCPToolset

    # Connect to an MCP server and get tools
    toolset = await MCPToolset.connect("filesystem", "/path/to/dir")
    agent = await AgentRuntime.create(
        name="助手",
        tools=toolset.tools,  # All MCP tools as BaseTool instances
    )
"""

from __future__ import annotations

import json
from typing import Any

from cogni_agent.tools.base import BaseTool, ToolSchema


class MCPToolWrapper(BaseTool):
    """Wraps an MCP tool as a CogniAgent BaseTool."""

    def __init__(self, name: str, description: str, input_schema: dict, session: Any):
        self.name = name
        self.description = description
        self._schema_dict = input_schema
        self._session = session
        self.schema = self._build_schema(input_schema)

    def _build_schema(self, schema: dict) -> ToolSchema:
        """Convert MCP JSON Schema to CogniAgent ToolSchema."""
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        return ToolSchema(properties=properties, required=required)

    async def run(self, **kwargs) -> str:
        """Execute the tool via MCP protocol."""
        try:
            result = await self._session.call_tool(self.name, arguments=kwargs)
            if hasattr(result, "content"):
                parts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    elif hasattr(item, "data"):
                        parts.append(f"[Binary data: {len(item.data)} bytes]")
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
            return str(result)
        except Exception as exc:
            return f"[MCP tool '{self.name}' error: {exc}]"


class MCPToolset:
    """A collection of tools exposed by an MCP server.

    Manages the MCP client connection and converts server tools
    into BaseTool instances usable by any CogniAgent.
    """

    def __init__(self):
        self._session = None
        self._tools: list[MCPToolWrapper] = []

    @classmethod
    async def connect(
        cls,
        server_name: str,
        *args,
        command: str | None = None,
        url: str | None = None,
        **kwargs,
    ) -> MCPToolset:
        """Connect to an MCP server and get its tools.

        Args:
            server_name: Logical name for the server (e.g. "filesystem", "database")
            command: Shell command to start a stdio-based MCP server
            url: URL of an SSE-based MCP server (mutually exclusive with command)
            *args, **kwargs: Additional arguments passed to the server

        Returns:
            MCPToolset with .tools list ready to pass to AgentRuntime.create()
        """
        import warnings
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters
        except ImportError:
            raise ImportError("MCP support requires: pip install mcp")

        self = cls()

        if url:
            # SSE-based connection — connect via HTTP
            try:
                from mcp.client.sse import sse_client
                async with sse_client(url=url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self._session = session
                        await self._discover_tools()
                        return self
            except Exception as exc:
                raise ConnectionError(f"Failed to connect to MCP server at {url}: {exc}")

        # Stdio-based connection (default)
        server_params = StdioServerParameters(
            command=command or server_name,
            args=list(args) if args else [],
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    await self._discover_tools()
        except Exception as exc:
            raise ConnectionError(
                f"Failed to start MCP server '{server_name}': {exc}\n"
                f"Make sure the server is installed. Common servers:\n"
                f"  npx @modelcontextprotocol/server-filesystem /path\n"
                f"  npx @modelcontextprotocol/server-github\n"
                f"  pip install mcp-server-sqlite"
            )

        return self

    async def _discover_tools(self) -> None:
        """Query the MCP server for its available tools and wrap them."""
        response = await self._session.list_tools()
        for tool in response.tools:
            wrapper = MCPToolWrapper(
                name=tool.name,
                description=tool.description or f"MCP tool: {tool.name}",
                input_schema=tool.inputSchema,
                session=self._session,
            )
            self._tools.append(wrapper)

    @property
    def tools(self) -> list[MCPToolWrapper]:
        """Get all MCP tools as CogniAgent BaseTool instances."""
        return list(self._tools)

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self._tools]

    async def close(self):
        """Close the MCP session."""
        if self._session:
            await self._session.close()


class MCPBuiltinServer:
    """Built-in MCP-like tools that don't require external servers.

    These implement the MCP tool interface directly for common operations.
    Can be used standalone or as templates for writing custom MCP servers.
    """

    @staticmethod
    async def create_tool(name: str, func, description: str, schema: dict) -> BaseTool:
        """Create a CogniAgent tool from a Python function.

        This provides a simple way to create tools without needing
        a full MCP server setup.
        """
        tool_schema = ToolSchema(
            properties=schema.get("properties", {}),
            required=schema.get("required", []),
        )

        class DynamicTool(BaseTool):
            name = name
            description = description
            schema = tool_schema

            async def run(self, **kwargs) -> str:
                return await func(**kwargs)

        return DynamicTool()