"""Quickstart example — create and chat with a CogniAgent."""

import asyncio

from cogni_agent import AgentRuntime


async def main():
    # Create an agent with a distinct personality
    agent = await AgentRuntime.create(
        name="小悟",
        role="数据分析助手",
        personality=["严谨", "友善", "善于洞察"],
        values=["数据驱动决策", "保护用户隐私"],
        model="gpt-4o",  # or "claude-sonnet-4-6", "gpt-4o-mini"
        verbose=True,
    )

    print(f"Created agent: {agent}")
    print(f"Identity: {agent.profile.name} — {agent.profile.role}")
    print(f"Personality: {agent.profile.personality_traits}")
    print("---")

    # First interaction
    response = await agent.run("帮我想想有什么好的数据分析项目可以练习？")
    print(f"Agent: {response}")
    print("---")

    # Second interaction — tests memory
    response2 = await agent.run("我刚才问了你什么？")
    print(f"Agent: {response2}")
    print("---")

    # Reset conversation (keeps identity and memory)
    await agent.reset_conversation()
    print("会话已重置")


if __name__ == "__main__":
    asyncio.run(main())
