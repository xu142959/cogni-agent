"""LLM Gateway — unified model access via litellm."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import litellm

from cogni_agent.core.errors import LLMError
from cogni_agent.core.interfaces import LLMGateway as BaseLLMGateway
from cogni_agent.core.types import LLMConfig, LLMResponse, LLMToolCall, Message


class LiteLLMGateway(BaseLLMGateway):
    """LLM gateway implementation using litellm for multi-model support."""

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
        api_key = cfg.api_key or os.getenv(self._env_key_for_model(cfg.model))

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
        if cfg.api_base:
            kwargs["api_base"] = cfg.api_base
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

        # Parse tool calls from the response
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
        }
        return mapping.get(prefix, "OPENAI_API_KEY")


# Convenience alias
LLMGateway = LiteLLMGateway