"""LLM Gateway — unified model access via litellm, with direct OpenAI client fallback."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import litellm

from cogni_agent.core.errors import LLMError
from cogni_agent.core.interfaces import LLMGateway as BaseLLMGateway
from cogni_agent.core.types import LLMConfig, LLMResponse, LLMToolCall, Message


class LiteLLMGateway(BaseLLMGateway):
    """LLM gateway implementation.

    Resolution order:
    1. If api_base is set, use OpenAI client directly (for custom APIs like NVIDIA, vLLM, Ollama)
    2. Otherwise, use litellm for 100+ provider support
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        litellm.drop_params = True

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        config_override: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config_override or self.config

        # Resolve API key: explicit > env var > litellm default
        api_key = cfg.api_key or os.getenv(self._env_key_for_model(cfg.model))
        api_base = cfg.api_base or os.getenv(self._env_base_for_model(cfg.model))

        # If custom API base is set, use OpenAI client directly
        # (handles NVIDIA, vLLM, Ollama, etc.)
        if api_base:
            return await self._chat_openai(cfg, messages, tools, api_key, api_base)

        # Otherwise use litellm for standard providers
        return await self._chat_litellm(cfg, messages, tools, api_key)

    async def _chat_openai(
        self,
        cfg: LLMConfig,
        messages: list[Message],
        tools: list[dict] | None,
        api_key: str | None,
        api_base: str,
    ) -> LLMResponse:
        """Use OpenAI client directly for custom API-compatible endpoints."""
        from openai import AsyncOpenAI

        # Strip openai/ prefix if present — custom APIs use the raw model name
        model = cfg.model
        if model.startswith("openai/"):
            model = model.split("openai/", 1)[1]

        client = AsyncOpenAI(api_key=api_key or "", base_url=api_base)

        # Properly serialize messages for OpenAI-compatible APIs
        openai_messages = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role, "content": m.content}
            # Preserve tool_call_id for tool role messages
            if m.role == "tool":
                msg["tool_call_id"] = m.metadata.get("tool_call_id", "")
            openai_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        start = time.monotonic()
        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise LLMError(f"LLM call failed: {exc}") from exc

        elapsed = int((time.monotonic() - start) * 1000)
        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[LLMToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    LLMToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=getattr(choice, "finish_reason", "stop"),
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            latency_ms=elapsed,
        )

    async def _chat_litellm(
        self,
        cfg: LLMConfig,
        messages: list[Message],
        tools: list[dict] | None,
        api_key: str | None,
    ) -> LLMResponse:
        """Use litellm for standard provider access."""
        litellm_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        kwargs: dict[str, Any] = {
            "model": cfg.model,
            "messages": litellm_messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if tools:
            kwargs["tools"] = tools

        start = time.monotonic()
        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            raise LLMError(f"LLM call failed: {exc}") from exc

        elapsed = int((time.monotonic() - start) * 1000)
        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[LLMToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    LLMToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=getattr(choice, "finish_reason", "stop"),
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            latency_ms=elapsed,
        )

    def _env_key_for_model(self, model: str) -> str:
        """Map model prefix to standard env variable name."""
        prefix = model.split("/")[0] if "/" in model else model.split("-")[0]
        mapping = {
            "gpt": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "azure": "AZURE_API_KEY",
            "openai": "OPENAI_API_KEY",
        }
        return mapping.get(prefix, "OPENAI_API_KEY")

    @staticmethod
    def _env_base_for_model(model: str) -> str | None:
        """Get custom API base URL from environment."""
        return os.getenv("OPENAI_API_BASE") or None


# Convenience alias
LLMGateway = LiteLLMGateway