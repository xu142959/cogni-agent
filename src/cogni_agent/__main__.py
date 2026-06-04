"""CLI entry point for cogni-agent."""

import asyncio
import sys


def main():
    """Main CLI entry point."""
    print("╔══════════════════════════════════════════╗")
    print("║         CogniAgent v0.1.0               ║")
    print("║   Agents with self-awareness & evolution ║")
    print("╚══════════════════════════════════════════╝")
    print()
    print("Commands:")
    print("  cogni-agent                  Start interactive REPL")
    print("  cogni-agent web              Start web console")
    print("  cogni-agent --version        Show version")
    print()

    if "--version" in sys.argv:
        from cogni_agent import __version__
        print(__version__)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "web":
        _run_web()
        return

    # Interactive REPL
    _run_repl()


def _run_web():
    """Start the web console."""
    try:
        import uvicorn
        print("Starting CogniAgent Web Console at http://localhost:8080")
        from web_console.app import app
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
    except ImportError:
        print("Web console requires: pip install 'cogni-agent[web]'")
        sys.exit(1)


def _run_repl():
    """Start an interactive Python REPL with cogni_agent pre-loaded."""
    try:
        import IPython
    except ImportError:
        print("REPL requires: pip install 'cogni-agent[dev]'")
        sys.exit(1)

    from traitlets.config import Config

    c = Config()
    c.InteractiveShellApp.exec_lines = [
        "from cogni_agent import AgentRuntime, AgentBuilder",
        "from cogni_agent.tools import *",
        "print('CogniAgent loaded! Use AgentRuntime.create(name=...) to create an agent.')",
    ]

    IPython.start_ipython(config=c, argv=[])


if __name__ == "__main__":
    main()