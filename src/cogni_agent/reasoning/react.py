"""Reasoning engines — ReAct and Plan-and-Execute with full tool loop and thought capture."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from cogni_agent.core.types import (
    AgentContext,
    LLMToolCall,
    Message,
    SubTask,
    TaskPlan,
    TaskStatus,
    ToolCall,
    ToolResult,
)
from cogni_agent.core.errors import MaxIterationsError
from cogni_agent.core.interfaces import BaseReasoner, LLMGateway
from cogni_agent.llm import LiteLLMGateway
from cogni_agent.tools import ToolRegistry


class ThoughtStep:
    """A single step in the agent's reasoning process."""

    def __init__(
        self,
        step_number: int,
        thought: str = "",
        action: str = "",
        action_input: dict | None = None,
        observation: str = "",
        final_answer: str = "",
    ):
        self.step_number = step_number
        self.thought = thought
        self.action = action
        self.action_input = action_input or {}
        self.observation = observation
        self.final_answer = final_answer
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "step": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation[:300] if self.observation else "",
            "final_answer": self.final_answer[:300] if self.final_answer else "",
            "timestamp": self.timestamp,
        }


class ReActReasoner(BaseReasoner):
    """ReAct (Reasoning + Acting) iterative reasoning loop.

    Captures every Thought→Action→Observation cycle for visualization.
    """

    def __init__(
        self,
        llm: LLMGateway | None = None,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = 10,
    ):
        self._llm = llm or LiteLLMGateway()
        self._tools = tool_registry or ToolRegistry()
        self.max_iterations = max_iterations
        # Thought chain storage
        self._thought_chain: list[ThoughtStep] = []
        self._last_chain: list[ThoughtStep] = []

    async def plan(self, goal: str, context: AgentContext) -> TaskPlan:
        return TaskPlan(
            goal=goal,
            sub_tasks=[SubTask(id="react_loop", description=goal)],
            reasoning_mode="react",
        )

    @property
    def last_thought_chain(self) -> list[dict]:
        return [s.to_dict() for s in self._last_chain]

    async def execute(self, plan: TaskPlan, context: AgentContext) -> str:
        self._thought_chain = []
        system_prompt = self._build_system_prompt(context)
        messages = [Message(role="system", content=system_prompt)]
        messages.extend(context.messages)
        messages.append(Message(role="user", content=plan.goal))

        tool_defs = self._tools.to_openai_tools() or None

        for attempt in range(self.max_iterations):
            response = await self._llm.chat(messages, tools=tool_defs)

            step = ThoughtStep(step_number=attempt + 1)
            step.thought = response.content or ""

            # ── Case 1: LLM requested tool calls ──
            if response.tool_calls:
                step.action = response.tool_calls[0].name
                try:
                    step.action_input = json.loads(response.tool_calls[0].arguments)
                except (json.JSONDecodeError, IndexError):
                    step.action_input = {}

                messages.append(Message(
                    role="assistant",
                    content=response.content or f"[Calling {len(response.tool_calls)} tool(s)]",
                    metadata={"tool_calls": [tc.name for tc in response.tool_calls]},
                ))

                # Execute each tool call
                observations = []
                for tc in response.tool_calls:
                    tool_result = await self._execute_tool(tc, context)
                    obs_text = tool_result.content[:500]
                    observations.append(f"[{tc.name}] {obs_text}")

                    messages.append(Message(
                        role="tool",
                        content=tool_result.content,
                        metadata={"tool_call_id": tc.id, "tool_name": tc.name},
                    ))

                step.observation = "\n".join(observations)
                self._thought_chain.append(step)
                continue

            # ── Case 2: Final text answer — done ──
            if response.content:
                step.final_answer = response.content
                self._thought_chain.append(step)
                self._last_chain = self._thought_chain
                return response.content

        raise MaxIterationsError(
            f"ReAct loop did not complete after {self.max_iterations} iterations"
        )

    async def _execute_tool(
        self,
        tc: LLMToolCall,
        context: AgentContext,
    ) -> ToolResult:
        tool = self._tools.get(tc.name)
        if tool is None:
            return ToolResult(
                tool_call_id=tc.id,
                content=f"Error: unknown tool '{tc.name}'. Available: {list(self._tools._tools.keys())}",
                success=False,
            )

        try:
            args = json.loads(tc.arguments) if tc.arguments else {}
            result = await tool.run(**args)
            return ToolResult(tool_call_id=tc.id, content=str(result), success=True)
        except Exception as exc:
            return ToolResult(
                tool_call_id=tc.id,
                content=f"Tool '{tc.name}' raised: {exc}",
                success=False,
            )

    def _build_system_prompt(self, context: AgentContext) -> str:
        profile = context.identity
        traits = "、".join(profile.personality_traits) if profile.personality_traits else "adaptable"
        values = "、".join(profile.values) if profile.values else "helpful"

        avail_tools = self._tools.list_all()
        tool_hint = ""
        if avail_tools:
            tool_names = ", ".join(t.name for t in avail_tools)
            tool_hint = f"\nAvailable tools: {tool_names}"

        return (
            f"You are {profile.name}, a {profile.role}.\n"
            f"Personality: {traits}\n"
            f"Values: {values}"
            f"{tool_hint}"
            f"\n---\n"
            f"Think step-by-step. Use available tools when needed to accomplish the task. "
            f"Once the task is complete, provide a clear final answer."
        )


class PlanAndExecuteReasoner(BaseReasoner):
    """Plan-and-Execute: decompose first, then execute each sub-task."""

    def __init__(
        self,
        llm: LLMGateway | None = None,
        tool_registry: ToolRegistry | None = None,
        max_iterations_per_step: int = 5,
    ):
        self._llm = llm or LiteLLMGateway()
        self._executor = ReActReasoner(
            llm=llm,
            tool_registry=tool_registry,
            max_iterations=max_iterations_per_step,
        )

    async def plan(self, goal: str, context: AgentContext) -> TaskPlan:
        profile = context.identity
        prompt = (
            f"You are {profile.name}, a task planner. "
            f"Decompose the following goal into 2-5 concrete sub-tasks. "
            f"Return ONLY a numbered list, one sub-task per line.\n\n"
            f"Goal: {goal}"
        )
        response = await self._llm.chat([Message(role="user", content=prompt)])

        lines = [line.strip() for line in response.content.strip().split("\n") if line.strip()]
        sub_tasks = []
        for i, line in enumerate(lines):
            clean = line.split(". ", 1)[-1] if ". " in line else line
            sub_tasks.append(SubTask(id=f"step_{i}", description=clean))

        return TaskPlan(
            goal=goal,
            sub_tasks=sub_tasks or [SubTask(id="step_0", description=goal)],
            reasoning_mode="plan_and_execute",
        )

    async def execute(self, plan: TaskPlan, context: AgentContext) -> str:
        results = []
        for task in plan.sub_tasks:
            task.status = TaskStatus.RUNNING
            try:
                result = await self._executor.execute(
                    TaskPlan(goal=task.description, sub_tasks=[], reasoning_mode="react"),
                    context,
                )
                task.result = result
                task.status = TaskStatus.COMPLETED
                results.append(f"### {task.description}\n{result}")
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                results.append(f"### {task.description}\n[FAILED] {exc}")

        context.current_plan = plan
        return "\n\n".join(results)