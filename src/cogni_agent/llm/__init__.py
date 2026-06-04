"""LLM module — unified gateway for multi-model access."""

from cogni_agent.llm.config import LLMConfig, preset
from cogni_agent.llm.gateway import LLMGateway, LiteLLMGateway

__all__ = [
    "LLMConfig",
    "LLMGateway",
    "LiteLLMGateway",
    "preset",
]