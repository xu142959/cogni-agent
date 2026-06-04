"""Tests for Reasoning engines — ReAct and Plan-and-Execute."""

import pytest

from cogni_agent.reasoning import ReActReasoner, PlanAndExecuteReasoner


class TestReActReasoner:
    def test_init(self):
        reasoner = ReActReasoner(max_iterations=5)
        assert reasoner.max_iterations == 5


class TestPlanAndExecute:
    def test_init(self):
        reasoner = PlanAndExecuteReasoner(max_iterations_per_step=3)
        assert reasoner._executor.max_iterations == 3