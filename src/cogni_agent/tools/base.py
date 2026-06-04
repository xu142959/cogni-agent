"""Tool system — base tool, schemas, and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from inspect import signature
from typing import Any


class ToolSchema:
    """Declarative tool parameter schema — mirrors OpenAI function calling format."""

    def __init__(self, properties: dict[str, dict], required: list[str] | None = None):
        self.properties = properties
        self.required = required or []

    def to_openai(self) -> dict:
        return {
            "type": "object",
            "properties": self.properties,
            "required": self.required,
        }


class BaseTool(ABC):
    """Base class for all tools. Subclass and implement run()."""

    name: str = ""
    description: str = ""
    # Optional explicit schema; if omitted, inferred from run() signature
    schema: ToolSchema | None = None

    @abstractmethod
    async def run(self, **kwargs) -> str:
        """Execute the tool with the given arguments."""
        ...

    def to_openai_tool(self) -> dict:
        """Convert this tool to OpenAI function calling format."""
        if self.schema:
            parameters = self.schema.to_openai()
        else:
            parameters = self._infer_parameters()

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }

    def _infer_parameters(self) -> dict:
        """Infer JSON schema from the run() method signature."""
        sig = signature(self.run)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "kwargs":
                continue
            json_type = self._py_type_to_json(param.annotation)
            prop: dict[str, Any] = {"type": json_type}

            # Add description from docstring if available
            hint = self._get_docstring_hint(param_name)
            if hint:
                prop["description"] = hint

            properties[param_name] = prop
            if param.default == param.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def _py_type_to_json(self, py_type: type) -> str:
        mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }
        return mapping.get(py_type, "string")

    def _get_docstring_hint(self, param_name: str) -> str:
        """Extract parameter description from the docstring."""
        if not self.run.__doc__:
            return ""
        lines = self.run.__doc__.split("\n")
        in_args = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Args:"):
                in_args = True
                continue
            if in_args:
                if stripped.startswith("Returns:") or not stripped:
                    break
                if stripped.startswith(param_name):
                    colon_pos = stripped.find(":")
                    if colon_pos > 0:
                        return stripped[colon_pos + 1:].strip()
        return ""


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if not tool.name:
            raise ValueError(f"Tool must have a name: {tool.__class__.__name__}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        """Return all tool definitions in OpenAI function calling format."""
        if not self._tools:
            return []
        return [tool.to_openai_tool() for tool in self._tools.values()]

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())