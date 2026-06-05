"""Tests for Multi-Agent Collaboration system."""

import os
import pytest

from cogni_agent.multi_agent import AgentRole, AgentTeam, ROLE_TEMPLATES


has_api = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
needs_api = pytest.mark.skipif(not has_api, reason="Requires API key")


class TestAgentRole:
    def test_role_creation(self):
        role = AgentRole(
            name="researcher",
            role="research specialist",
            personality=["thorough"],
            values=["accuracy"],
        )
        assert role.name == "researcher"
        assert role.role == "research specialist"

    def test_system_prompt(self):
        role = AgentRole(
            name="test_bot",
            role="tester",
            personality=["precise"],
            instructions="Test everything.",
        )
        prompt = role.to_system_prompt()
        assert "test_bot" in prompt
        assert "tester" in prompt
        assert "Test everything." in prompt

    def test_default_values(self):
        role = AgentRole(name="empty", role="helper")
        assert role.personality == []
        assert role.values == []
        assert role.tools == []


class TestRoleTemplates:
    def test_all_templates_exist(self):
        assert "researcher" in ROLE_TEMPLATES
        assert "critic" in ROLE_TEMPLATES
        assert "analyst" in ROLE_TEMPLATES
        assert "synthesizer" in ROLE_TEMPLATES
        assert "creative" in ROLE_TEMPLATES
        assert "planner" in ROLE_TEMPLATES

    def test_template_has_instructions(self):
        for name, role in ROLE_TEMPLATES.items():
            assert role.name == name
            assert role.instructions, f"Template '{name}' has no instructions"
            assert len(role.personality) >= 2


class TestAgentTeam:
    def test_create_team(self):
        team = AgentTeam()
        assert team.agent_count == 0
        assert team.list_roles() == list(ROLE_TEMPLATES.keys())

    @pytest.mark.asyncio
    async def test_add_agent(self):
        team = AgentTeam()
        role = AgentRole(name="custom", role="helper", personality=["nice"])
        agent = await team.add_agent(role)
        assert agent.profile.name == "custom"
        assert agent.profile.role == "helper"
        assert team.agent_count == 1

    @pytest.mark.asyncio
    async def test_add_agent_by_template(self):
        team = AgentTeam()
        agent = await team.add_agent_by_template("researcher")
        assert agent.profile.name == "researcher"
        assert "research specialist" in agent.profile.role
        assert team.agent_count == 1

    @pytest.mark.asyncio
    async def test_add_multiple_agents(self):
        team = AgentTeam()
        await team.add_agent_by_template("researcher")
        await team.add_agent_by_template("critic")
        await team.add_agent_by_template("synthesizer")
        assert team.agent_count == 3

    @pytest.mark.asyncio
    async def test_suggest_roles(self):
        team = AgentTeam()
        roles = await team.suggest_roles("Analyze market trends for AI industry")
        assert len(roles) >= 1
        for r in roles:
            assert r in ROLE_TEMPLATES

    @pytest.mark.asyncio
    async def test_suggest_roles_simple_task(self):
        team = AgentTeam()
        roles = await team.suggest_roles("Write a hello world program")
        assert len(roles) >= 1

    def test_unknown_template_raises(self):
        team = AgentTeam()
        with pytest.raises(ValueError):
            import asyncio
            asyncio.run(team.add_agent_by_template("nonexistent"))

    @needs_api
    @pytest.mark.asyncio
    async def test_vote(self):
        team = AgentTeam(model="gpt-4o-mini")
        await team.add_agent_by_template("researcher")
        await team.add_agent_by_template("analyst")

        results = await team.vote(
            "Which programming language is best for data science?",
            options=["Python", "R", "Julia"],
        )
        assert sum(results.values()) == 2  # 2 agents voted

    @needs_api
    @needs_api
    @pytest.mark.asyncio
    async def test_debate_two_agents(self):
        team = AgentTeam(model="gpt-4o-mini", max_debate_rounds=2)
        await team.add_agent_by_template("researcher")
        await team.add_agent_by_template("synthesizer")

        result = await team.debate(
            "What are the top 3 trends in AI for 2026?",
            rounds=2,
        )

        assert result.num_agents == 2
        assert result.rounds == 2
        assert len(result.final_answer) > 0
        assert len(result.contributions) == 2
        assert len(result.debate_history) == 2

    @needs_api
    @pytest.mark.asyncio
    async def test_debate_three_agents(self):
        team = AgentTeam(model="gpt-4o-mini", max_debate_rounds=2)
        await team.add_agent_by_template("researcher")
        await team.add_agent_by_template("critic")
        await team.add_agent_by_template("synthesizer")

        result = await team.debate(
            "Should companies invest in on-premise or cloud AI infrastructure?",
            rounds=2,
        )

        assert result.num_agents == 3
        assert result.consensus is True
        assert len(result.final_answer) > 50

    def test_debate_history_reset(self):
        team = AgentTeam()
        assert team.debate_history == []

    @needs_api
    @pytest.mark.asyncio
    async def test_auto_role_suggestion(self):
        """Team should auto-create agents from suggested roles."""
        team = AgentTeam(model="gpt-4o-mini", max_debate_rounds=2)

        result = await team.debate(
            "Explain quantum computing in simple terms.",
        )

        assert result.num_agents >= 2
        assert len(result.final_answer) > 0