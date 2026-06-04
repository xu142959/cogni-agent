# CogniAgent — 项目文档

## 项目概况

认知 AI Agent 框架。Agent 不是流程编排工具，而是拥有自我认知和进化能力的 AI 生命体。

## 核心架构

```
src/cogni_agent/
├── core/          # 类型系统 / 抽象接口 / 异常
├── llm/           # LLM 网关 (litellm, 100+模型)
├── reasoning/     # 推理引擎 (ReAct, Plan-and-Execute)
├── identity/      # 自我认知 (Identity Profile, Capability Map)
├── memory/        # 记忆系统 (ChromaDB, 四层架构)
├── evolution/     # 进化引擎 (反思→学习→适应→巩固)
├── tools/         # 21个内置工具
├── runtime.py     # AgentRuntime 主入口
├── builder.py     # 流式 Builder API
└── __main__.py    # CLI 入口
```

## 三句话定位

1. **装大脑** — 推理引擎 + 决策引擎 + 元认知监控
2. **有自我** — Identity Profile + Capability Map + 关系模型
3. **能进化** — 反思→学习→适应→巩固 进化飞轮

## 关键文件

| 文件 | 说明 |
|---|---|
| `runtime.py` | 核心入口，所有模块的编排器 |
| `reasoning/react.py` | ReAct 推理循环 + ThoughtStep 思维链捕获 |
| `identity/manager.py` | 自我认知：身份/能力/关系/进化 |
| `memory/manager.py` | 四层记忆：工作/语义/情景/程序 |
| `memory/stores.py` | InMemoryStore + ChromaDBStore |
| `evolution/engine.py` | 进化飞轮：Reflect→Learn→Adapt→Consolidate |
| `tools/builtin/__init__.py` | Web/文件/计算/Python 工具 |
| `tools/computer.py` | 跨平台电脑控制 (macOS/Linux/Windows占位) |

## 常用命令

```bash
# 安装
pip install -e ".[dev,web]"

# 测试（无 API Key）
pytest tests/ -v -k "not needs_api"

# 测试（全部）
OPENAI_API_KEY=sk-... pytest tests/ tests/integration

# 启动 Web Console
python web_console/app.py
# → http://localhost:8080

# 打包
python -m build --wheel

# 发布
twine upload dist/*
```

## 设计原则

- **零 API Key 可用** — DuckDuckGo 搜索 + hash fallback 嵌入
- **跨平台** — macOS + Linux 完整支持，Windows 占位
- **异步优先** — 所有 LLM/工具调用都是 async
- **Pydantic v2** — 所有数据模型类型安全
- **可插拔** — 推理策略/记忆后端/工具均可替换

## 竞品差异

| 维度 | 竞品 | CogniAgent |
|---|---|---|
| 自我认知 | ❌ | ✅ |
| 自动进化 | ❌ | ✅ |
| 结构化记忆 | 单层 | 四层 |
| 电脑控制 | ❌ | 跨平台 14工具 |
| 零 API Key 可用 | ❌ | ✅ |

## 关键词

AI Agent, 认知引擎, 自我认知, 自动进化, ReAct, 工具调用, 电脑控制, 记忆系统, LLM