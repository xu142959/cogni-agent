"""Integration test runner — run all tests with optional API keys.

Usage:
  # Unit tests only (no API keys needed)
  pytest tests/ -v

  # Integration tests with API keys
  OPENAI_API_KEY=sk-... pytest tests/integration/ -v

  # All tests including integration
  OPENAI_API_KEY=sk-... OPENAI_MODEL=gpt-4o-mini pytest tests/ tests/integration/ -v

  # With coverage
  OPENAI_API_KEY=sk-... pytest tests/ tests/integration/ -v --cov=cogni_agent
"""

import pytest

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
