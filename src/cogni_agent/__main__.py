#!/usr/bin/env python3
"""CogniAgent CLI — 命令行创建、运行、管理 Agent。

Usage:
    cogni-agent init                   创建新 Agent（交互式）
    cogni-agent chat <name>            与 Agent 对话
    cogni-agent run <name> <task>      让 Agent 执行任务
    cogni-agent list                   列出所有已保存的 Agent
    cogni-agent web                    启动 Web Console
    cogni-agent gui                    启动桌面客户端
    cogni-agent --version              版本信息
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def main():
    args = sys.argv[1:]

    if "--version" in args or "-v" in args:
        from cogni_agent import __version__
        print(f"CogniAgent v{__version__}")
        return

    if not args or args[0] in ("--help", "-h", "help"):
        show_help()
        return

    command = args[0]

    if command == "init":
        asyncio.run(cmd_init())
    elif command == "chat":
        name = args[1] if len(args) > 1 else "default"
        asyncio.run(cmd_chat(name))
    elif command == "run":
        if len(args) < 3:
            print("用法: cogni-agent run <Agent名称> <任务描述>")
            return
        asyncio.run(cmd_run(args[1], " ".join(args[2:])))
    elif command == "list":
        asyncio.run(cmd_list())
    elif command == "web":
        run_web()
    elif command == "gui":
        run_gui()
    else:
        print(f"未知命令: {command}")
        show_help()


def show_help():
    print("╔══════════════════════════════════════════════╗")
    print("║         CogniAgent v0.1.0                   ║")
    print("║   像豆包一样的桌面 AI Agent                  ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print("命令:")
    print("  cogni-agent init                创建新 Agent（交互式）")
    print("  cogni-agent chat <名称>         与 Agent 对话")
    print("  cogni-agent run <名称> <任务>    让 Agent 执行任务")
    print("  cogni-agent list                列出所有 Agent")
    print("  cogni-agent web                 启动 Web 控制台")
    print("  cogni-agent gui                 启动桌面客户端")
    print("  cogni-agent --version           版本信息")
    print()
    print("首次使用:")
    print("  cogni-agent init")
    print()


async def cmd_init():
    """交互式创建新 Agent。"""
    from cogni_agent import AgentRuntime
    from cogni_agent.identity.stores import SQLiteIdentityStore
    from cogni_agent.identity import IdentityManager

    print("\n🔧 创建新 Agent")
    print("=" * 40)

    name = input("  名称 (默认: 小悟): ").strip() or "小悟"
    role = input("  角色 (默认: 助手): ").strip() or "助手"
    personality = input("  性格 (逗号分隔，默认: 友善, 严谨): ").strip() or "友善, 严谨"
    values = input("  价值观 (逗号分隔，默认: helpful): ").strip() or "helpful"
    model = input(f"  模型 (默认: gpt-4o): ").strip() or "gpt-4o"

    personality_list = [p.strip() for p in personality.split(",")]
    values_list = [v.strip() for v in values.split(",")]

    # 使用持久化存储
    store = SQLiteIdentityStore()
    im = IdentityManager(store=store)
    context = await im.create_agent(
        name=name, role=role,
        personality=personality_list, values=values_list,
    )

    print(f"\n✅ Agent '{name}' 已创建!")
    print(f"   ID: {context.agent_id[:12]}...")
    print(f"   角色: {role}")
    print(f"   性格: {personality}")
    print(f"\n现在可以: cogni-agent chat {name}")


async def cmd_chat(name: str):
    """与 Agent 对话。"""
    from cogni_agent import AgentRuntime
    from cogni_agent.tools import all_tools

    print(f"\n💬 与 {name} 对话 (输入 'exit' 退出)")
    print("=" * 40)

    agent = await AgentRuntime.create(
        name=name, role="助手",
        tools=all_tools(),
        enable_memory=True, enable_evolution=True,
    )

    print(f"   Agent '{agent.profile.name}' 已就绪\n")

    while True:
        try:
            user_input = input("你: ").strip()
            if not user_input or user_input.lower() in ("exit", "quit", "退出"):
                break

            response = await agent.run(user_input)
            print(f"\n{agent.profile.name}: {response}\n")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as exc:
            print(f"\n[错误: {exc}]\n")


async def cmd_run(name: str, task: str):
    """让 Agent 执行单次任务。"""
    from cogni_agent import AgentRuntime
    from cogni_agent.tools import all_tools

    print(f"\n🎯 {name} 执行任务: {task}")
    print("=" * 40)

    agent = await AgentRuntime.create(
        name=name, role="助手",
        tools=all_tools(),
        enable_memory=True, enable_evolution=True,
    )

    response = await agent.run(task)
    print(f"\n{agent.profile.name}: {response}\n")


async def cmd_list():
    """列出所有已保存的 Agent。"""
    from cogni_agent.identity.stores import SQLiteIdentityStore

    store = SQLiteIdentityStore()
    profiles = await store.list_all()

    if not profiles:
        print("\n📭 还没有保存的 Agent。使用 cogni-agent init 创建。\n")
        return

    print(f"\n📋 已保存的 Agent ({len(profiles)}):")
    print("=" * 40)
    for p in profiles:
        traits = "、".join(p.personality_traits) if p.personality_traits else "-"
        print(f"  🧠 {p.name} ({p.role})")
        print(f"     性格: {traits}")
        print(f"     ID: {p.agent_id[:16]}...")
        print()


def run_web():
    """启动 Web 控制台。"""
    try:
        import uvicorn
        print("🌐 Starting CogniAgent Web Console at http://localhost:8080")
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from web_console.app import app
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
    except ImportError:
        print("Web console requires: pip install 'cogni-agent[web]'")
        sys.exit(1)


def run_gui():
    """启动桌面客户端。"""
    try:
        from cogni_agent.gui import DesktopApp
        app = DesktopApp()
        app.run()
    except ImportError as exc:
        print(f"GUI 启动失败: {exc}")
        print("Desktop client requires: pip install PyQt6")
        sys.exit(1)


if __name__ == "__main__":
    main()
