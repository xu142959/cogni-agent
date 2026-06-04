"""Tests for LLM config and gateway placeholders."""

from cogni_agent.llm.config import MODEL_PRESETS, preset


class TestLLMPresets:
    def test_default_presets(self):
        assert "fast" in MODEL_PRESETS
        assert "balanced" in MODEL_PRESETS
        assert "powerful" in MODEL_PRESETS
        assert "reasoning" in MODEL_PRESETS
        assert "local" in MODEL_PRESETS

    def test_fast_preset(self):
        cfg = preset("fast")
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 2048

    def test_balanced_preset(self):
        cfg = preset("balanced")
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.7

    def test_unknown_preset(self):
        import pytest
        with pytest.raises(KeyError):
            preset("nonexistent")
