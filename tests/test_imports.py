"""
CogniAgent Test Suite

Run with: pytest -v
Run with coverage: pytest --cov=cogni_agent tests/
"""

from cogni_agent import AgentRuntime


class TestImport:
    def test_import(self):
        assert AgentRuntime is not None
