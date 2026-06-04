"""LLM configuration utilities."""

from cogni_agent.core.types import LLMConfig

# Common model presets
MODEL_PRESETS = {
    "fast": LLMConfig(model="gpt-4o-mini", temperature=0.3, max_tokens=2048),
    "balanced": LLMConfig(model="gpt-4o", temperature=0.7, max_tokens=4096),
    "powerful": LLMConfig(model="claude-sonnet-4-6", temperature=0.7, max_tokens=8192),
    "reasoning": LLMConfig(model="claude-opus-4-8", temperature=0.5, max_tokens=16384),
    "local": LLMConfig(model="ollama/llama3.1", temperature=0.7, max_tokens=4096),
}


def preset(name: str) -> LLMConfig:
    """Get a named model preset."""
    if name not in MODEL_PRESETS:
        msg = f"Unknown preset: {name}. Available: {list(MODEL_PRESETS)}"
        raise KeyError(msg)
    return MODEL_PRESETS[name]