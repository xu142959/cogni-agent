import { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Bot,
  Plus,
  History,
  Calendar,
  FolderOpen,
  Archive,
  Settings,
  User,
  Mic,
  Send,
  Bell,
  HelpCircle,
  PlusCircle,
  Globe,
  Terminal,
  Activity,
  Edit2,
  ChevronDown,
  ChevronUp,
  Brain,
  Trash2,
  Check,
  Search,
  BookOpen
} from 'lucide-react';
import { Message, ChatSession, AgentConfig, ToolItem } from '../types';

interface ChatWorkspaceProps {
  agentConfig: AgentConfig;
  tools: ToolItem[];
  onToggleTool: (toolId: string) => void;
  sessionMemories: string[];
  onAddMemory: (memory: string) => void;
  onRemoveMemory: (index: number) => void;
  onOpenSettings: () => void;
  onOpenVoice: () => void;
  voiceTextToSubmit?: string;
  clearVoiceText: () => void;
}

// Initial mockup chat history streams matching templates
const INITIAL_SESSIONS: ChatSession[] = [
  {
    id: 'ai-news',
    title: 'AI 新闻检索',
    category: 'Today',
    iconName: 'history',
    activeTools: ['search', 'vision'],
    messages: [
      {
        id: 'm1',
        role: 'user',
        content: '帮我搜索最新的 AI 新闻',
        timestamp: 'Today 10:42 AM'
      },
      {
        id: 'm2',
        role: 'agent',
        content: '好的，我来搜索最新的 AI 领域新闻...',
        timestamp: 'Today 10:42 AM',
        status: 'done',
        thoughtSteps: [
          { title: '步骤 1: 解析用户意图', text: '语言: 中文\n主题: 最新的 AI 人工智能行业新闻' },
          { title: '调用工具: web_search', text: '{ "query": "latest AI news today OR 最新人工智能新闻", "num_results": 5 }' }
        ],
        searchResults: [
          {
            title: 'OpenAI 宣布全新的模型对齐强化安全技术',
            description: '最新研究论文详述了全新的模型转向控制方案与安全防御策略...',
            url: 'techcrunch.com'
          },
          {
            title: 'NVIDIA 推出下一代超级 AI 计算加速器',
            description: '全新芯片架构宣称可将大说话模型的现场推理速度提升多达 4 倍...',
            url: 'wired.com'
          }
        ]
      }
    ]
  },
  {
    id: 'code-review',
    title: '代码审查: React 应用',
    category: 'Today',
    iconName: 'history',
    activeTools: ['interpreter'],
    messages: [
      {
        id: 'm3',
        role: 'user',
        content: '检查此 React hook 布局是否存在无限重复渲染模式。',
        timestamp: 'Today 9:15 AM'
      },
      {
        id: 'm4',
        role: 'agent',
        content: '我分析了您的 React 状态更新。之所以触发无限循环，是因为您在 useEffect 钩子的依赖项数组中直接传递了未缓存的全新对象字面量。下面是推荐的修复方案：',
        timestamp: 'Today 9:16 AM',
        status: 'done',
        thoughtSteps: [
          { title: '分析 AST 语法树', text: '发现不稳定的依赖项: [filterObject]' },
          { title: '验证修复状态', text: '针对过滤逻辑的属性应用 useMemo 缓存。' }
        ]
      }
    ]
  },
  {
    id: 'db-schema',
    title: '数据库模式设计',
    category: 'Yesterday',
    iconName: 'calendar',
    activeTools: ['interpreter', 'search'],
    messages: [
      {
        id: 'm5',
        role: 'user',
        content: '为用户、消息和向量日志标准表设计 Drizzle ORM 模式配置。',
        timestamp: 'Yesterday 3:40 PM'
      },
      {
        id: 'm6',
        role: 'agent',
        content: '这是采用最新 Drizzle relations 关系的干净 TypeScript 数据库模式，成功将用户映射到了多维度的向量存储表中。',
        timestamp: 'Yesterday 3:41 PM',
        status: 'done'
      }
    ]
  },
  {
    id: 'q4-notes',
    title: '第 4 季度规划笔记',
    category: 'Earlier',
    iconName: 'folder',
    activeTools: [],
    messages: [
      {
        id: 'm7',
        role: 'user',
        content: '从原始会议记录中总结第 4 季度的业务目标。',
        timestamp: 'May 28, 2026'
      },
      {
        id: 'm8',
        role: 'agent',
        content: '完成。关键项：1. 启动 Agent SDK 集成。2. 支持多通道语音控制。3. 将推理内核延迟降至 50 毫秒以下。',
        timestamp: 'May 28, 2026',
        status: 'done'
      }
    ]
  },
  {
    id: 'alpha-archived',
    title: '已归档项目: Alpha 计划',
    category: 'Earlier',
    iconName: 'archive',
    activeTools: [],
    messages: [
      {
        id: 'm9',
        role: 'user',
        content: '加载 Alpha 版本的配置参数。',
        timestamp: 'May 10, 2026'
      },
      {
        id: 'm10',
        role: 'agent',
        content: 'Alpha 版本的技术说明书已成功加载并持久化至系统数据库日志中。',
        timestamp: 'May 10, 2026',
        status: 'done'
      }
    ]
  }
];

export default function ChatWorkspace({
  agentConfig,
  tools,
  onToggleTool,
  sessionMemories,
  onAddMemory,
  onRemoveMemory,
  onOpenSettings,
  onOpenVoice,
  voiceTextToSubmit,
  clearVoiceText
}: ChatWorkspaceProps) {
  const [sessions, setSessions] = useState<ChatSession[]>(INITIAL_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState('ai-news');
  const [inputVal, setInputVal] = useState('');
  const [expandedThoughtId, setExpandedThoughtId] = useState<string | null>('m2');
  const [isAiResponding, setIsAiResponding] = useState(false);
  const [showActiveToolsConfig, setShowActiveToolsConfig] = useState(false);
  
  // Ref for auto scrolling chat viewport
  const chatEndRef = useRef<HTMLDivElement>(null);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0];

  // Auto-scroll chat window when message stacks modify
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession.messages, isAiResponding]);

  // Handle voice text submission callback from Voice overlay
  useEffect(() => {
    if (voiceTextToSubmit) {
      handleSendMessage(voiceTextToSubmit);
      clearVoiceText();
    }
  }, [voiceTextToSubmit]);

  const handleSendMessage = (textToSend?: string) => {
    const rawVal = textToSend || inputVal;
    if (!rawVal.trim() || isAiResponding) return;

    if (!textToSend) setInputVal('');

    // 1. Append User prompt message to active session
    const userMsg: Message = {
      id: Math.random().toString(),
      role: 'user',
      content: rawVal,
      timestamp: 'Today ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const updatedMessages = [...activeSession.messages, userMsg];
    setSessions(prev => prev.map(s => {
      if (s.id === s.id && s.id === activeSessionId) {
        return { ...s, messages: updatedMessages };
      }
      return s;
    }));

    // 2. Trigger AI responsive steps simulating streaming process and search cards
    setIsAiResponding(true);

    setTimeout(() => {
      // Step A: Thinking message with dynamic thinking process and searches
      const searchActive = tools.find(t => t.id === 'search')?.active;
      const interpreterActive = tools.find(t => t.id === 'interpreter')?.active;

      const thoughtSteps = [
        { title: '步骤 1: 解析核心标记符', text: `分析输入项: "${rawVal}"，当前使用模型：${agentConfig.primaryModel}` },
        { title: '步骤 2: 加载智能体角色标签', text: `建立对应的行为映射映射集: ${agentConfig.tags.join(', ')}` }
      ];

      if (searchActive) {
        thoughtSteps.push({
          title: '调用工具: web_search',
          text: `{ "query": "${rawVal}", "num_results": 3 }`
        });
      }

      let aiResponseContent = `好的，我收到您的指令了。关于“${rawVal}”，我使用当前的主模型（${agentConfig.primaryModel}）为您提供以下处理结果：`;
      let searchResults: Message['searchResults'] = undefined;

      if (searchActive && (rawVal.includes('搜索') || rawVal.includes('新闻') || rawVal.includes('search') || rawVal.includes('news'))) {
        aiResponseContent = `好的，根据您查询的“${rawVal}”内容，我在网络上为您实时提取了以下最新成果：`;
        searchResults = [
          {
            title: 'Gemini 生成式智能体的研究进展极其令人瞩目',
            description: '研究人员深度探索了在部署大规模高阶扩展范式时由服务器端执行的智能体自主动作...',
            url: 'googleapi.com'
          },
          {
            title: 'CogniAgent 核心引擎发布 v2.4 正式版说明书',
            description: '当前全新支持本地图形化索引沙箱微小组件集合，以及自定义的微型工具代理对接协议...',
            url: 'github.com/cogniagent'
          }
        ];
      } else if (interpreterActive && (rawVal.includes('Python') || rawVal.includes('代码') || rawVal.includes('code') || rawVal.includes('算法'))) {
        aiResponseContent = `我已为您启用 Python 解释器安全隔离沙箱。已经成功在计算内核层执行完毕并回传了如下结果：\n\n\`\`\`python\n# 自动计算与推理函数\nimport math\ndef solve_cogni(tokens):\n    print("Executing sandbox with GPT-backed logic...")\n    return [math.sqrt(x) for x in tokens]\n\nrun = solve_cogni([100, 224, 512])\n\`\`\``;
      } else {
        // Simple conversational replies blending dynamic tags
        aiResponseContent = `我是您的个人高级助手 **${agentConfig.name}**（定位：**${agentConfig.role}**）。我具有 ${agentConfig.tags.join('、')} 等特质，很乐意配合您当前的工作重点（${sessionMemories[1] || "AI 软件开发"}）。\n\n我已经将这些意图保存到我的内存条中，您可以随时在右上方的“Session Memory”管理器中查看。`;
      }

      const agentMsg: Message = {
        id: Math.random().toString(),
        role: 'agent',
        content: aiResponseContent,
        timestamp: 'Today ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        status: 'done',
        thoughtSteps,
        searchResults
      };

      setSessions(prev => prev.map(s => {
        if (s.id === s.id && s.id === activeSessionId) {
          return { ...s, messages: [...updatedMessages, agentMsg] };
        }
        return s;
      }));
      setExpandedThoughtId(agentMsg.id);
      setIsAiResponding(false);

    }, 1500);
  };

  const createNewSession = () => {
    const newId = 'session-' + Math.random().toString();
    const newSess: ChatSession = {
      id: newId,
      title: '新建工作区会话',
      category: 'Today',
      iconName: 'history',
      activeTools: ['search'],
      messages: [
        {
          id: Math.random().toString(),
          role: 'agent',
          content: `你好！我是 **${agentConfig.name}** (${agentConfig.role})。我已经准备就绪，当前可用的激活工具有 Web Search、Code Interpreter 等。请随时提问！`,
          timestamp: 'Just now'
        }
      ]
    };
    setSessions([newSess, ...sessions]);
    setActiveSessionId(newId);
  };

  const handleToggleActiveSessionTool = (toolId: string) => {
    onToggleTool(toolId);
  };

  return (
    <div className="flex-1 ml-[280px] flex flex-col h-screen relative bg-background overflow-hidden select-none text-gray-900">
      
      {/* 1. LEFT SIDEBAR STAGE (Rendered absolute/fixed but properly offsets) */}
      <aside className="w-[280px] h-screen fixed left-0 top-0 bg-white border-r border-gray-200 flex flex-col p-6 z-30 justify-between select-none">
        <div className="space-y-6">
          
          {/* Brand header replication */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-black rounded-md flex items-center justify-center text-white">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="font-headline text-md font-bold text-gray-900 tracking-tight">CogniAgent</h1>
              <p className="font-sans text-[9px] text-gray-400 font-bold tracking-wider uppercase">
                {agentConfig.name} AI
              </p>
            </div>
          </div>

          {/* CTA "New Chat" button */}
          <button 
            onClick={createNewSession}
            className="w-full flex items-center justify-center gap-2 bg-black hover:bg-black/90 text-white transition-colors rounded-lg py-2.5 font-sans font-semibold text-xs tracking-wider uppercase cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            新建对话
          </button>

          {/* Sidebar Navigation Items list */}
          <nav className="flex-1 overflow-y-auto space-y-4 pr-1 custom-scrollbar max-h-[460px]">
            
            {/* Today Item group */}
            <div>
              <h2 className="font-sans text-[10px] text-gray-400 font-bold tracking-wider uppercase mb-2 px-2">今天</h2>
              <div className="space-y-1">
                {sessions.filter(s => s.category === 'Today').map(sess => (
                  <button
                    key={sess.id}
                    onClick={() => setActiveSessionId(sess.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left text-xs transition-colors cursor-pointer ${
                      activeSessionId === sess.id
                        ? 'text-black font-semibold bg-gray-100'
                        : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    <History className="w-4 h-4 text-gray-400" />
                    <span className="truncate flex-1 font-sans">{sess.title}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Yesterday group */}
            {sessions.some(s => s.category === 'Yesterday') && (
              <div>
                <h2 className="font-sans text-[10px] text-gray-400 font-bold tracking-wider uppercase mb-2 px-2">昨天</h2>
                <div className="space-y-1">
                  {sessions.filter(s => s.category === 'Yesterday').map(sess => (
                    <button
                      key={sess.id}
                      onClick={() => setActiveSessionId(sess.id)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left text-xs transition-colors cursor-pointer ${
                        activeSessionId === sess.id
                          ? 'text-black font-semibold bg-gray-100'
                          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                      }`}
                    >
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span className="truncate flex-1 font-sans">{sess.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Earlier Group */}
            {sessions.some(s => s.category === 'Earlier') && (
              <div>
                <h2 className="font-sans text-[10px] text-gray-400 font-bold tracking-wider uppercase mb-2 px-2">更早之前</h2>
                <div className="space-y-1">
                  {sessions.filter(s => s.category === 'Earlier').map(sess => {
                    const IconComp = sess.iconName === 'archive' ? Archive : FolderOpen;
                    return (
                      <button
                        key={sess.id}
                        onClick={() => setActiveSessionId(sess.id)}
                        className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left text-xs transition-colors cursor-pointer ${
                          activeSessionId === sess.id
                            ? 'text-black font-semibold bg-gray-100'
                            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                        }`}
                      >
                        <IconComp className="w-4 h-4 text-gray-400" />
                        <span className="truncate flex-1 font-sans">{sess.title}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

          </nav>
        </div>

        {/* Dynamic Sidebar footer buttons for settings/accounts */}
        <div className="pt-4 border-t border-gray-100 space-y-1">
          <button 
            onClick={onOpenSettings}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-500 hover:bg-gray-50 text-xs font-sans hover:text-gray-900 transition-colors text-left cursor-pointer"
          >
            <Settings className="w-4 h-4" />
            <span>系统设置</span>
          </button>
          <div className="w-full flex items-center justify-between px-3 py-2 text-gray-500 text-xs font-sans">
            <span className="flex items-center gap-2">
              <User className="w-4 h-4 text-gray-400" />
              <span>用户账户</span>
            </span>
            <span className="text-[10px] bg-black text-white px-1.5 py-0.5 rounded uppercase font-sans font-bold">高级版</span>
          </div>
        </div>
      </aside>

      {/* 2. TOP APPMENU BAR NAVIGATION */}
      <header className="fixed top-0 right-0 w-[calc(100%-280px)] z-20 bg-white/80 backdrop-blur-xl border-b border-gray-200 flex justify-between items-center h-16 px-6 select-none">
        
        {/* Nav Links column tab */}
        <nav className="flex gap-8">
          <button className="font-sans text-xs uppercase tracking-wider text-black border-b-2 border-black pb-1 font-bold">
            模型选项
          </button>
          <button onClick={onOpenSettings} className="font-sans text-xs uppercase tracking-wider text-gray-400 hover:text-black transition-all font-semibold cursor-pointer">
            工具面板
          </button>
          <button 
            onClick={() => alert("耗时追踪日志加载完毕，未发现系统异常日志。")} 
            className="font-sans text-xs uppercase tracking-wider text-gray-400 hover:text-black transition-all font-semibold cursor-pointer"
          >
            追踪日志
          </button>
        </nav>

        {/* Right tools controllers */}
        <div className="flex items-center gap-4">
          
          {/* Glowing Voice Mode button */}
          <button 
            onClick={onOpenVoice}
            className="font-sans text-xs font-semibold uppercase tracking-wider text-black hover:bg-gray-100 transition-colors flex items-center gap-1.5 cursor-pointer bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-full"
          >
            <Mic className="w-3.5 h-3.5 text-black shrink-0" />
            语音通话模式
          </button>

          <div className="w-[1.5px] h-4 bg-gray-200"></div>

          <div className="flex gap-2.5">
            <button className="text-gray-400 hover:text-black transition-colors cursor-pointer">
              <Bell className="w-5 h-5 opacity-85" />
            </button>
            <button className="text-gray-400 hover:text-black transition-colors cursor-pointer">
              <HelpCircle className="w-5 h-5 opacity-85" />
            </button>
          </div>

          <img 
            alt="User profile representation"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuDpnZ1ds78WK49b353YjQmnZwU8RhlIfOnuna3fi9-FpBPCtzRoGDpxSlvBcsl3S-u3RcgqwN1-cqkQ6ItRSWqTzgaLngf4mhTXk6LRkYMxb4C3FqpXzUE85x6GeOk5j5ZtjKJ8CSUJ7OG7WJZr3lD6lmlQcYJQb-yZvZ2iisKhHXYpWWXP4Rqa5-hR2mCNDoh5oT4FsSf62yq5IGxVql8tYNtGwxugLxMO7Eql-ONU9zvhA-jIira0YM-T365rVbrGTy6bUcs2KJLF" 
            className="w-8 h-8 rounded-full border border-gray-200 cursor-pointer shadow-sm ml-1 hover:border-black duration-150"
          />
        </div>
      </header>

      {/* 3. CENTRAL MAIN CANVAS VIEW */}
      <main className="flex-1 overflow-y-auto pt-20 pb-32 px-8 flex flex-col items-center select-none custom-scrollbar bg-background">
        <div className="w-full max-w-[800px] flex flex-col gap-6">
          
          {/* Day / Time separator */}
          <div className="text-center text-xs font-sans text-gray-450 tracking-widest my-4">今天 10:42 AM</div>

          {/* Dynamic conversational list rendering */}
          {activeSession.messages.map((message) => {
            const isUser = message.role === 'user';
            
            return (
              <div 
                key={message.id}
                className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {isUser ? (
                  /* User prompt bubble */
                  <div className="bg-black text-white rounded-2xl rounded-tr-sm p-4 max-w-[80%] shadow-sm leading-relaxed text-sm font-sans">
                    <p>{message.content}</p>
                  </div>
                ) : (
                  /* Agent Message structure */
                  <div className="flex gap-3 items-start max-w-[85%]">
                    
                    {/* Bot avatar symbol */}
                    <div className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center shrink-0 mt-1 shadow-sm">
                      <Bot className="w-4 h-4 text-black" />
                    </div>

                    <div className="flex-1 space-y-3">
                      <div className="bg-white border border-gray-150 rounded-2xl rounded-tl-sm p-5 shadow-sm text-gray-900">
                        
                        {/* Core text reply */}
                        <div className="text-sm font-sans whitespace-pre-wrap leading-relaxed text-gray-800">
                          {message.content}
                        </div>

                        {/* Status searching spinner placeholder */}
                        {isAiResponding && activeSession.messages[activeSession.messages.length - 1].id === message.id && (
                          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-50 border border-gray-200 text-gray-900 mt-3 text-xs">
                            <Activity className="w-3.5 h-3.5 animate-spin text-black" />
                            <span>正在联网进行最新信息搜索...</span>
                          </div>
                        )}

                        {/* Interactive accordion component strictly mapping to image */}
                        {message.thoughtSteps && message.thoughtSteps.length > 0 && (
                          <div className="mt-4 border border-gray-200 rounded-lg bg-gray-50/50 overflow-hidden">
                            <button
                              onClick={() => setExpandedThoughtId(expandedThoughtId === message.id ? null : message.id)}
                              className="w-full flex items-center justify-between p-3 select-none hover:bg-gray-100/50 text-xs text-gray-850 font-sans"
                            >
                              <span className="flex items-center gap-2 font-bold font-sans uppercase tracking-wider text-gray-400 text-[11px]">
                                <Brain className="w-4 h-4 text-black shrink-0" />
                                智能体底层推理过程 (COT)
                              </span>
                              {expandedThoughtId === message.id ? (
                                <ChevronUp className="w-4 h-4 text-gray-400" />
                              ) : (
                                <ChevronDown className="w-4 h-4 text-gray-400" />
                              )}
                            </button>

                            {expandedThoughtId === message.id && (
                              <div className="p-3 pt-0 border-t border-gray-100">
                                <div className="border-l-2 border-dashed border-gray-300 pl-3.5 py-1.5 font-mono text-[11px] leading-relaxed text-gray-500 bg-white rounded-r-lg space-y-2">
                                  {message.thoughtSteps.map((step, sIdx) => (
                                    <div key={sIdx}>
                                      <div className="text-black font-semibold font-mono">{step.title}</div>
                                      <div className="text-gray-500 font-mono whitespace-pre-line">{step.text}</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Custom search result dynamic cards */}
                        {message.searchResults && message.searchResults.length > 0 && (
                          <div className="mt-4 space-y-2">
                            {message.searchResults.map((result, rIdx) => (
                              <div 
                                key={rIdx}
                                onClick={() => alert(`即将跳转查阅第三方参考来源：${result.url}`)}
                                className="bg-white border border-gray-150 p-3.5 rounded-lg hover:border-black/30 hover:bg-gray-50/50 transition-all text-left cursor-pointer"
                              >
                                <h4 className="text-xs font-bold font-sans text-gray-900 line-clamp-1 mb-1">{result.title}</h4>
                                <p className="text-[11px] font-sans text-gray-500 line-clamp-1 mb-2">{result.description}</p>
                                <span className="text-[9px] font-mono font-bold tracking-wider text-black uppercase">{result.url}</span>
                              </div>
                            ))}
                          </div>
                        )}

                      </div>
                    </div>

                  </div>
                )}
              </div>
            );
          })}

          {/* AI Response simulated indicator inline */}
          {isAiResponding && (
            <div className="flex gap-3 items-start max-w-[85%]">
              <div className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center shrink-0 mt-1 shadow-sm">
                <Bot className="w-4 h-4 text-black animate-pulse" />
              </div>
              <div className="bg-white border border-gray-150 rounded-2xl rounded-tl-sm p-4 shadow-sm flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-black animate-bounce shrink-0" style={{ animationDelay: '0s' }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-black animate-bounce shrink-0" style={{ animationDelay: '0.15s' }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-black animate-bounce shrink-0" style={{ animationDelay: '0.3s' }}></span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </main>

      {/* 4. FLOATING CHAT INPUT AREA */}
      <div className="absolute bottom-10 left-0 w-full px-8 z-10 flex justify-center">
        <div className="w-full max-w-[800px] flex flex-col gap-1.5">
          <div className="bg-white border border-gray-200 rounded-xl p-2 flex items-end gap-2.5 shadow-md hover:border-gray-350 focus-within:border-black transition-all">
            
            <button 
              onClick={() => alert("请选择要作为上下文解析上传的本地文件、媒体库或代码资源...")}
              className="p-2 text-gray-400 hover:text-black transition-colors hover:bg-gray-50 rounded-lg shrink-0 cursor-pointer"
              title="添加并上传附件"
            >
              <PlusCircle className="w-5.5 h-5.5" />
            </button>

            <textarea 
              rows={1}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={`向 ${agentConfig.name} 输入消息并提问...`}
              className="flex-1 bg-transparent border-none outline-none focus:ring-0 text-gray-900 font-sans text-sm resize-none py-2 placeholder:text-gray-400 max-h-[160px] custom-scrollbar min-h-[38px]"
            />

            <button 
              onClick={onOpenVoice}
              className="p-2 text-gray-400 hover:text-black transition-colors hover:bg-gray-50 rounded-lg shrink-0 cursor-pointer"
              title="语音跟智能体通话"
            >
              <Mic className="w-5.5 h-5.5" />
            </button>

            <button 
              onClick={() => handleSendMessage()}
              disabled={isAiResponding || !inputVal.trim()}
              className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-all ${
                inputVal.trim() && !isAiResponding
                  ? 'bg-black text-white hover:bg-black/90 cursor-pointer'
                  : 'bg-gray-100 text-gray-405 cursor-not-allowed'
              }`}
            >
              <Send className="w-4.5 h-4.5" />
            </button>

          </div>
          <div className="text-center font-sans text-[10px] text-gray-400 opacity-60">
            {agentConfig.name} 可能会生成不符合预期的答复。请注意核对关键性信息。
          </div>
        </div>
      </div>

      {/* 6. GLOBAL FOOTER NAVIGATION SATURATION BAR */}
      <footer className="fixed bottom-0 left-[280px] w-[calc(100%-280px)] h-8 bg-white border-t border-gray-150 flex items-center justify-between px-6 z-20 select-none shadow-xs text-gray-500">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.7)] animate-pulse"></div>
            <span className="font-mono text-[10px] text-gray-500">正常连接</span>
          </div>
          <div className="w-[1px] h-3 bg-gray-200"></div>
          <span className="font-mono text-[10px] text-gray-500">基座模型: {agentConfig.primaryModel}</span>
          <div className="w-[1px] h-3 bg-gray-200"></div>
          <span className="font-mono text-[10px] text-gray-500">上下文消耗: {messageTokensCount(activeSession.messages)} token</span>
        </div>
        <div className="font-mono text-[10px] text-gray-400">
          内核时延: {isAiResponding ? "正在计算..." : "42 毫秒"}
        </div>
      </footer>

    </div>
  );
}

// Simple token estimation helper
function messageTokensCount(messages: Message[]) {
  const characters = messages.reduce((acc, m) => acc + m.content.length, 0);
  return Math.round(characters * 0.35 + 850);
}
