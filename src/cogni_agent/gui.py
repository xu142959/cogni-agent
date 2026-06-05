#!/usr/bin/env python3
"""CogniAgent 桌面客户端 — 像豆包一样的桌面 AI Agent。

跨平台: Windows / macOS / Linux
启动: cogni-agent gui
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from pathlib import Path

# ─── 异步支持 ─────────────────────────────────────────────

class AsyncRunner:
    """在独立线程中运行 async 代码，通过回调回到主线程。"""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro, callback=None):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if callback:
            future.add_done_callback(lambda f: callback(f.result() if not f.exception() else str(f.exception())))
        return future


# ─── 桌面应用 ─────────────────────────────────────────────

class DesktopApp:
    """CogniAgent 桌面客户端主窗口。"""

    def __init__(self):
        self._async = AsyncRunner()
        self._agent = None
        self._voice = None
        self._app = None

    def run(self):
        try:
            from PyQt6.QtWidgets import (
                QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget,
                QSplitter, QTabWidget, QStatusBar, QMenuBar,
            )
            from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
            from PyQt6.QtGui import QAction
        except ImportError:
            print("需要 PyQt6: pip install PyQt6")
            sys.exit(1)

        # ─── 信号桥：跨线程安全更新 UI ───
        class SignalBridge(QObject):
            append_chat_signal = pyqtSignal(str, str)
            update_status_signal = pyqtSignal(str)
            update_agent_info_signal = pyqtSignal(str, str, str)
            set_input_text_signal = pyqtSignal(str)

        self._signals = SignalBridge()

        self._app = QApplication(sys.argv)
        self._app.setApplicationName("CogniAgent")
        self._app.setStyle("Fusion")

        # 深色主题
        self._app.setStyleSheet("""
            QMainWindow, QWidget { background-color: #1a1d27; color: #e1e4ed; }
            QTextEdit, QLineEdit {
                background-color: #0f1117; color: #e1e4ed;
                border: 1px solid #2a2d3a; border-radius: 6px; padding: 8px; font-size: 14px;
            }
            QPushButton {
                background-color: #6c5ce7; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7c6cf7; }
            QPushButton:disabled { background-color: #2a2d3a; color: #8b8fa3; }
            QListWidget {
                background-color: #0f1117; border: 1px solid #2a2d3a;
                border-radius: 6px; color: #e1e4ed; font-size: 13px;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2a2d3a; }
            QListWidget::item:selected { background-color: #6c5ce7; }
            QTabWidget::pane { background-color: #1a1d27; border: 1px solid #2a2d3a; }
            QTabBar::tab { background-color: #0f1117; color: #8b8fa3; padding: 8px 16px; margin: 2px; }
            QTabBar::tab:selected { background-color: #6c5ce7; color: white; }
            QStatusBar { background-color: #0f1117; color: #8b8fa3; font-size: 12px; }
            QMenuBar { background-color: #0f1117; color: #e1e4ed; }
            QMenuBar::item:selected { background-color: #6c5ce7; }
            QMenu { background-color: #1a1d27; color: #e1e4ed; border: 1px solid #2a2d3a; }
            QMenu::item:selected { background-color: #6c5ce7; }
        """)

        window = QMainWindow()
        window.setWindowTitle("CogniAgent")
        window.setMinimumSize(900, 600)
        window.resize(1100, 700)

        # 菜单
        menubar = window.menuBar()
        file_menu = menubar.addMenu("文件")
        new_action = QAction("新建 Agent", window)
        new_action.triggered.connect(lambda: self._async.run(self._create_agent()))
        file_menu.addAction(new_action)

        tools_menu = menubar.addMenu("工具")
        voice_action = QAction("语音输入", window)
        voice_action.triggered.connect(lambda: self._async.run(self._voice_input()))
        tools_menu.addAction(voice_action)

        # 主布局
        central = QWidget()
        window.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter()

        # 左侧聊天区
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("💬 CogniAgent 对话")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        chat_layout.addWidget(title)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setMinimumWidth(500)
        chat_layout.addWidget(self._chat_display)

        # 输入区
        input_layout = QHBoxLayout()
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("输入消息...")
        self._input_field.returnPressed.connect(lambda: self._async.run(self._send_message()))
        input_layout.addWidget(self._input_field)

        send_btn = QPushButton("发送")
        send_btn.clicked.connect(lambda: self._async.run(self._send_message()))
        input_layout.addWidget(send_btn)

        voice_btn = QPushButton("🎤 语音")
        voice_btn.clicked.connect(lambda: self._async.run(self._voice_input()))
        input_layout.addWidget(voice_btn)

        chat_layout.addLayout(input_layout)
        splitter.addWidget(chat_widget)

        # 右侧面板
        right_panel = QTabWidget()
        right_panel.setMinimumWidth(300)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        self._agent_name_label = QLabel("Agent: 未创建")
        self._agent_name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(self._agent_name_label)

        self._agent_info = QTextEdit()
        self._agent_info.setReadOnly(True)
        self._agent_info.setMaximumHeight(200)
        info_layout.addWidget(self._agent_info)

        create_btn = QPushButton("🚀 创建 Agent")
        create_btn.clicked.connect(lambda: self._async.run(self._create_agent()))
        info_layout.addWidget(create_btn)
        right_panel.addTab(info_widget, "Agent")

        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)
        self._tools_list = QListWidget()
        from cogni_agent.tools import all_tools
        for tool in all_tools():
            self._tools_list.addItem(f"🔧 {tool.name}: {tool.description[:40]}...")
        tools_layout.addWidget(self._tools_list)
        right_panel.addTab(tools_widget, "工具")

        splitter.addWidget(right_panel)
        splitter.setSizes([600, 300])
        main_layout.addWidget(splitter)

        # 状态栏
        status = QStatusBar()
        self._status_label = QLabel("就绪")
        status.addWidget(self._status_label)
        window.setStatusBar(status)

        # ─── 信号绑定（主线程安全） ───
        def on_append_chat(role, content):
            if role == "user":
                html = f'<div style="color: #6c5ce7; font-weight: bold; margin-top: 8px;">🧑 你:</div><div style="color: #e1e4ed; margin-left: 16px; margin-bottom: 8px;">{content}</div>'
            elif role == "agent":
                name = self._agent.profile.name if self._agent else "Agent"
                html = f'<div style="color: #00b894; font-weight: bold; margin-top: 8px;">🤖 {name}:</div><div style="color: #e1e4ed; margin-left: 16px; margin-bottom: 8px;">{content}</div>'
            else:
                html = f'<div style="color: #8b8fa3; font-style: italic; margin: 4px;">{content}</div>'
            self._chat_display.append(html)
            self._chat_display.verticalScrollBar().setValue(self._chat_display.verticalScrollBar().maximum())

        def on_update_status(text):
            self._status_label.setText(text)

        def on_update_agent_info(name, role, info):
            self._agent_name_label.setText(f"🧠 {name} ({role})")
            self._agent_info.setText(info)

        def on_set_input_text(text):
            self._input_field.setText(text)

        self._signals.append_chat_signal.connect(on_append_chat)
        self._signals.update_status_signal.connect(on_update_status)
        self._signals.update_agent_info_signal.connect(on_update_agent_info)
        self._signals.set_input_text_signal.connect(on_set_input_text)

        QTimer.singleShot(100, lambda: self._async.run(self._create_agent()))

        window.show()
        sys.exit(self._app.exec())

    def _append_chat(self, role, content):
        self._signals.append_chat_signal.emit(role, content)

    def _update_status(self, text):
        self._signals.update_status_signal.emit(text)

    async def _create_agent(self):
        try:
            from cogni_agent import AgentRuntime
            from cogni_agent.tools import all_tools

            self._update_status("⏳ 创建 Agent...")

            self._agent = await AgentRuntime.create(
                name="小悟", role="智能助手",
                personality=["友善", "严谨"],
                tools=all_tools(),
                enable_memory=True, enable_evolution=True,
            )

            info = f"性格: {', '.join(self._agent.profile.personality_traits)}\n工具: {len(self._agent.tools.list_all())} 个"
            self._signals.update_agent_info_signal.emit(
                self._agent.profile.name, self._agent.profile.role, info
            )

            self._append_chat("system", f"✅ Agent '{self._agent.profile.name}' 已创建，请开始对话！")
            self._update_status(f"✅ {self._agent.profile.name} 就绪")

        except Exception as exc:
            self._append_chat("system", f"❌ 创建失败: {exc}")
            self._update_status("❌ 创建失败")

    async def _send_message(self):
        text = self._input_field.text().strip()
        if not text or not self._agent:
            return

        self._input_field.clear()
        self._append_chat("user", text)
        self._update_status("⏳ 思考中...")

        try:
            response = await self._agent.run(text)
            self._append_chat("agent", response)
            self._update_status("✅ 就绪")
        except Exception as exc:
            self._append_chat("system", f"❌ 错误: {exc}")
            self._update_status("❌ 错误")

    async def _voice_input(self):
        try:
            from cogni_agent.voice import VoiceIO
            self._update_status("🎤 正在听...")
            self._append_chat("system", "🎤 请说话...")

            if self._voice is None:
                self._voice = VoiceIO()

            text = await self._voice.listen(duration=5)
            if text:
                self._signals.set_input_text_signal.emit(text)
                self._update_status(f"✅ 识别: {text[:30]}...")
            else:
                self._update_status("❌ 未识别到语音")
        except Exception as exc:
            self._update_status(f"❌ 语音错误: {exc}")


def main():
    DesktopApp().run()


if __name__ == "__main__":
    main()