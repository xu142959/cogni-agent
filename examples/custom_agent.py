"""Example using the fluent AgentBuilder API."""

import asyncio

from cogni_agent.builder import AgentBuilder


async def main():
    # Using the fluent builder
    agent = await (
        AgentBuilder()
        .with_name("Alex")
        .with_role("research assistant")
        .with_personality("thorough", "curious", "methodical")
        .with_values("accuracy", "clarity", "open science")
        .with_model("gpt-4o")
        .with_max_iterations(15)
        .verbose()
        .build()
    )

    print(f"Created: {agent}")

    response = await agent.run(
        "Explain the difference between ReAct and Plan-and-Execute "
        "reasoning patterns in AI agents."
    )
    print(f"\nAgent:\n{response}")


if __name__ == "__main__":
    asyncio.run(main())
