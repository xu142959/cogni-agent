import { useState, useEffect, FormEvent } from 'react';
import {
  X,
  Minus,
  Settings,
  Brain,
  Terminal,
  Monitor,
  Eye,
  Badge,
  Wrench,
  Database,
  Palette,
  Keyboard,
  Info,
  Plus,
  ShieldAlert,
  Search,
  Check,
  Edit2,
  Trash2,
  Lock,
  Compass,
  FileDown
} from 'lucide-react';
import { AgentConfig, ToolItem } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentConfig: AgentConfig;
  onSaveAgentConfig: (config: AgentConfig) => void;
  tools: ToolItem[];
  onToggleTool: (toolId: string) => void;
  onAddCustomTool: (tool: Omit<ToolItem, 'id'>) => void;
  sessionMemories: string[];
  onAddMemory: (memory: string) => void;
  onRemoveMemory: (index: number) => void;
  onClearCache: () => void;
}

export default function SettingsModal({
  isOpen,
  onClose,
  agentConfig,
  onSaveAgentConfig,
  tools,
  onToggleTool,
  onAddCustomTool,
  sessionMemories,
  onAddMemory,
  onRemoveMemory,
  onClearCache
}: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'agent' | 'tools' | 'data' | 'appearance' | 'hotkeys'>('agent');
  
  // Local state for Agent Config inputs (to allow discard)
  const [localName, setLocalName] = useState(agentConfig.name);
  const [localRole, setLocalRole] = useState(agentConfig.role);
  const [localTags, setLocalTags] = useState<string[]>([...agentConfig.tags]);
  const [localModel, setLocalModel] = useState(agentConfig.primaryModel);
  const [localApiKey, setLocalApiKey] = useState(agentConfig.apiKeyOverride);
  const [isEditingKey, setIsEditingKey] = useState(false);
  const [newTagInput, setNewTagInput] = useState('');
  const [isAddingTag, setIsAddingTag] = useState(false);

  // New custom tool form state
  const [isAddingTool, setIsAddingTool] = useState(false);
  const [toolFormName, setToolFormName] = useState('');
  const [toolFormDesc, setToolFormDesc] = useState('');
  const [toolFormModel, setToolFormModel] = useState('');

  // Memory management state
  const [newMemoryInput, setNewMemoryInput] = useState('');
  const [isClearing, setIsClearing] = useState(false);

  // Sync state with parent's config on open
  useEffect(() => {
    if (isOpen) {
      setLocalName(agentConfig.name);
      setLocalRole(agentConfig.role);
      setLocalTags([...agentConfig.tags]);
      setLocalModel(agentConfig.primaryModel);
      setLocalApiKey(agentConfig.apiKeyOverride);
    }
  }, [isOpen, agentConfig]);

  if (!isOpen) return null;

  const handleAddTag = () => {
    if (newTagInput.trim() && !localTags.includes(newTagInput.trim())) {
      setLocalTags([...localTags, newTagInput.trim()]);
      setNewTagInput('');
      setIsAddingTag(false);
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setLocalTags(localTags.filter(tag => tag !== tagToRemove));
  };

  const handleSave = () => {
    onSaveAgentConfig({
      name: localName,
      role: localRole,
      tags: localTags,
      primaryModel: localModel,
      apiKeyOverride: localApiKey
    });
    onClose();
  };

  const handleDiscard = () => {
    setLocalName(agentConfig.name);
    setLocalRole(agentConfig.role);
    setLocalTags([...agentConfig.tags]);
    setLocalModel(agentConfig.primaryModel);
    setLocalApiKey(agentConfig.apiKeyOverride);
    setIsEditingKey(false);
    onClose();
  };

  const handleCreateTool = (e: FormEvent) => {
    e.preventDefault();
    if (toolFormName.trim() && toolFormDesc.trim()) {
      onAddCustomTool({
        name: toolFormName,
        description: toolFormDesc,
        active: true,
        statusType: 'idle',
        statusText: 'Ready',
        lastUsed: 'Just now',
        modelText: toolFormModel || undefined
      });
      setToolFormName('');
      setToolFormDesc('');
      setToolFormModel('');
      setIsAddingTool(false);
    }
  };

  const executeClearCache = () => {
    setIsClearing(true);
    setTimeout(() => {
      onClearCache();
      setIsClearing(false);
    }, 1000);
  };

  const handleCreateMemory = () => {
    if (newMemoryInput.trim()) {
      onAddMemory(newMemoryInput.trim());
      setNewMemoryInput('');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
      {/* Desktop Window Container */}
      <div className="bg-white border border-gray-200 w-full max-w-5xl h-[780px] min-h-[580px] flex flex-col rounded-xl overflow-hidden shadow-xl relative select-none text-gray-900">
        
        {/* Window Title Bar */}
        <div className="h-12 bg-gray-50 border-b border-gray-200 flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <span className="text-xl">🧠</span>
            <span className="font-headline font-semibold text-sm text-gray-900">CogniAgent 系统设置</span>
          </div>
          <div className="flex items-center gap-2">
            <button 
              aria-label="Minimize" 
              onClick={handleDiscard}
              className="w-4 h-4 rounded-full bg-gray-200 hover:bg-gray-300 transition-colors flex items-center justify-center group"
            >
              <Minus className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 text-gray-600 duration-100" />
            </button>
            <button 
              aria-label="Close" 
              onClick={handleDiscard}
              className="w-4 h-4 rounded-full bg-red-100 hover:bg-red-500 transition-colors flex items-center justify-center group"
            >
              <X className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 text-white font-extrabold duration-100" />
            </button>
          </div>
        </div>

        {/* Main Layout Area */}
        <div className="flex flex-1 overflow-hidden">
          
          {/* Left Sidebar Navigation */}
          <aside className="w-[240px] bg-gray-50/50 border-r border-gray-200 flex flex-col p-4 justify-between">
            <nav className="flex flex-col gap-1.5">
              <button
                onClick={() => { setActiveTab('agent'); setIsAddingTool(false); }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-sans text-sm text-left transition-all cursor-pointer ${
                  activeTab === 'agent'
                    ? 'bg-gray-100 text-black font-semibold'
                    : 'text-gray-500 hover:bg-gray-100/50 hover:text-gray-900'
                }`}
              >
                <Brain className={`w-5 h-5 ${activeTab === 'agent' ? 'text-black' : 'text-gray-400'}`} />
                Agent 设置
              </button>

              <button
                onClick={() => { setActiveTab('tools'); setIsAddingTool(false); }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-sans text-sm text-left transition-all cursor-pointer ${
                  activeTab === 'tools'
                    ? 'bg-gray-100 text-black font-semibold'
                    : 'text-gray-500 hover:bg-gray-100/50 hover:text-gray-900'
                }`}
              >
                <Wrench className={`w-5 h-5 ${activeTab === 'tools' ? 'text-black' : 'text-gray-400'}`} />
                工具管理
              </button>

              <button
                onClick={() => { setActiveTab('data'); setIsAddingTool(false); }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-sans text-sm text-left transition-all cursor-pointer ${
                  activeTab === 'data'
                    ? 'bg-gray-100 text-black font-semibold'
                    : 'text-gray-500 hover:bg-gray-100/50 hover:text-gray-900'
                }`}
              >
                <Database className={`w-5 h-5 ${activeTab === 'data' ? 'text-black' : 'text-gray-400'}`} />
                数据
              </button>

              <button
                onClick={() => { setActiveTab('appearance'); setIsAddingTool(false); }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-sans text-sm text-left transition-all cursor-pointer ${
                  activeTab === 'appearance'
                    ? 'bg-gray-100 text-black font-semibold'
                    : 'text-gray-500 hover:bg-gray-100/50 hover:text-gray-900'
                }`}
              >
                <Palette className={`w-5 h-5 ${activeTab === 'appearance' ? 'text-black' : 'text-gray-400'}`} />
                外观
              </button>

              <button
                onClick={() => { setActiveTab('hotkeys'); setIsAddingTool(false); }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-sans text-sm text-left transition-all cursor-pointer ${
                  activeTab === 'hotkeys'
                    ? 'bg-gray-100 text-black font-semibold'
                    : 'text-gray-500 hover:bg-gray-100/50 hover:text-gray-900'
                }`}
              >
                <Keyboard className={`w-5 h-5 ${activeTab === 'hotkeys' ? 'text-black' : 'text-gray-400'}`} />
                快捷键
              </button>
            </nav>

            {/* Stable Version string in sidebar footer */}
            <div className="pt-3 border-t border-gray-100">
              <div className="flex items-center gap-2 px-3 py-1.5 text-gray-400 font-sans text-xs">
                <Info className="w-4 h-4 shrink-0 text-gray-450" />
                <span>v2.4.1 (Stable)</span>
              </div>
            </div>
          </aside>

          {/* Right Main Panel */}
          <main className="flex-1 bg-white p-8 overflow-y-auto relative custom-scrollbar text-gray-900">
            
            {activeTab === 'agent' && (
              <div className="max-w-2xl mx-auto space-y-6">
                <header>
                  <h1 className="font-headline text-3xl font-bold text-gray-900 mb-1">Agent 设置</h1>
                  <p className="font-sans text-sm text-gray-500">配置您专属智能体（CogniAgent）的核心身份特征与基础行为参数。</p>
                </header>

                {/* Identity Sub-section */}
                <section className="space-y-5">
                  <h2 className="font-sans text-xs font-semibold uppercase tracking-wider text-black border-b border-gray-200 pb-1.5">
                    智能体身份
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    
                    {/* Name Input */}
                    <div className="space-y-2">
                      <label htmlFor="agent-name" className="block font-sans text-sm text-gray-600">
                        名称
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                          <Brain className="w-4.5 h-4.5 text-gray-400" />
                        </div>
                        <input
                          id="agent-name"
                          type="text"
                          value={localName}
                          onChange={(e) => setLocalName(e.target.value)}
                          className="w-full bg-white border border-gray-200 rounded-lg py-2 pl-10 pr-3 text-gray-900 font-sans text-sm focus:border-black focus:ring-1 focus:ring-black focus:outline-none transition-all placeholder:text-gray-400 shadow-xs"
                          placeholder="例如: 小悟"
                        />
                      </div>
                    </div>

                    {/* Role Input */}
                    <div className="space-y-2">
                      <label htmlFor="agent-role" className="block font-sans text-sm text-gray-600">
                        主要角色
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                          <Compass className="w-4.5 h-4.5 text-gray-400" />
                        </div>
                        <input
                          id="agent-role"
                          type="text"
                          value={localRole}
                          onChange={(e) => setLocalRole(e.target.value)}
                          className="w-full bg-white border border-gray-200 rounded-lg py-2 pl-10 pr-3 text-gray-900 font-sans text-sm focus:border-black focus:ring-1 focus:ring-black focus:outline-none transition-all placeholder:text-gray-400 shadow-xs"
                          placeholder="智能体角色定位，例如：智能助手"
                        />
                      </div>
                    </div>

                  </div>

                  {/* Personality Tags */}
                  <div className="space-y-2">
                    <label className="block font-sans text-sm text-gray-600">
                      性格特征标签
                    </label>
                    <div className="flex flex-wrap gap-2.5 items-center">
                      {localTags.map((tag) => (
                        <span 
                          key={tag}
                          className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-50 border border-gray-200 text-gray-700 font-sans text-xs rounded-full"
                        >
                          {tag}
                          <button 
                            aria-label="Remove tag" 
                            onClick={() => handleRemoveTag(tag)}
                            className="text-gray-400 hover:text-black transition-colors"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </span>
                      ))}
                      {isAddingTag ? (
                        <div className="inline-flex items-center gap-1 bg-white px-2 py-0.5 border border-gray-250 rounded-full">
                          <input
                            type="text"
                            autoFocus
                            value={newTagInput}
                            onChange={(e) => setNewTagInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleAddTag();
                              if (e.key === 'Escape') setIsAddingTag(false);
                            }}
                            className="bg-transparent border-none outline-none text-xs text-gray-900 max-w-[80px] p-0.5 focus:ring-0"
                            placeholder="新标签..."
                          />
                          <button onClick={handleAddTag} className="text-gray-600 hover:text-black">
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => setIsAddingTag(false)} className="text-gray-400 hover:text-black">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setIsAddingTag(true)}
                          className="inline-flex items-center justify-center px-3 py-1 rounded-full bg-white hover:bg-gray-50 border border-dashed border-gray-300 text-gray-500 font-sans text-xs transition-colors cursor-pointer"
                        >
                          <Plus className="w-3.5 h-3.5 mr-1" /> 添加标签
                        </button>
                      )}
                    </div>
                  </div>
                </section>

                {/* Engine Configuration Sub-section */}
                <section className="space-y-5 pt-6 border-t border-gray-150">
                  <h2 className="font-sans text-xs font-semibold uppercase tracking-wider text-black border-b border-gray-200 pb-1.5">
                    智能推理引擎配置
                  </h2>

                  {/* Primary Model dropdown */}
                  <div className="space-y-2 max-w-sm">
                    <label htmlFor="model-select" className="block font-sans text-sm text-gray-600">
                      首选基础大模型
                    </label>
                    <div className="relative">
                      <select
                        id="model-select"
                        value={localModel}
                        onChange={(e) => setLocalModel(e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg py-2 pl-3 pr-10 text-gray-900 font-sans text-sm focus:border-black focus:ring-1 focus:ring-black focus:outline-none transition-all shadow-xs cursor-pointer"
                      >
                        <option value="GPT-4o (Optimized)">GPT-4o (优化推荐)</option>
                        <option value="Claude 3 Opus">Claude 3 Opus</option>
                        <option value="Gemini 1.5 Pro">Gemini 1.5 Pro</option>
                        <option value="Local Llama-3-70b">Local Llama-3-70b</option>
                      </select>
                    </div>
                  </div>

                  {/* API Key Override block */}
                  <div className="space-y-2">
                    <label htmlFor="api-key" className="block font-sans text-sm text-gray-600">
                      自定义 API Key (覆盖默认)
                    </label>
                    <div className="flex gap-3">
                      <div className="relative flex-1">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                          <Lock className="w-4 h-4 text-gray-400" />
                        </div>
                        {isEditingKey ? (
                          <input
                            id="api-key-input"
                            type="text"
                            value={localApiKey}
                            onChange={(e) => setLocalApiKey(e.target.value)}
                            className="w-full bg-white border border-gray-200 rounded-lg py-2 pl-10 pr-3 text-gray-900 font-mono text-sm focus:border-black focus:ring-1 focus:ring-black focus:outline-none transition-all shadow-xs"
                            placeholder="输入自定义密钥 (sk-proj-...)"
                          />
                        ) : (
                          <input
                            id="api-key"
                            type="password"
                            disabled
                            value={localApiKey || "sk-proj-xxxxxxxxxxxxxxxxxxxx"}
                            className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2 pl-10 pr-3 text-gray-950 font-mono text-sm opacity-65 cursor-not-allowed select-none"
                          />
                        )}
                      </div>
                      
                      {isEditingKey ? (
                        <button
                          onClick={() => {
                            if (localApiKey.trim()) setIsEditingKey(false);
                          }}
                          className="px-4 py-2 rounded-lg bg-black text-white font-sans text-sm hover:bg-black/90 transition-all flex items-center gap-1.5 cursor-pointer"
                        >
                          <Check className="w-4 h-4" /> 保存密钥
                        </button>
                      ) : (
                        <button
                          onClick={() => setIsEditingKey(true)}
                          className="px-4 py-2 rounded-lg bg-white border border-gray-250 hover:border-black hover:bg-gray-50 text-gray-900 font-sans text-sm transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
                        >
                          <Edit2 className="w-4 h-4" /> 重新修改
                        </button>
                      )}
                    </div>
                    <p className="font-sans text-xs text-gray-400 mt-1">留空将直接使用系统的默认预设密钥。</p>
                  </div>
                </section>

                {/* Save Actions (Sticky Bottom) */}
                <div className="pt-6 pb-2 mt-8 flex justify-end gap-3 border-t border-gray-150">
                  <button
                    onClick={handleDiscard}
                    className="px-4 py-2 rounded-lg text-gray-500 font-sans text-sm hover:bg-gray-100 transition-all cursor-pointer"
                  >
                    放弃修改
                  </button>
                  <button
                    onClick={handleSave}
                    className="px-5 py-2.5 rounded-lg bg-black text-white font-sans text-sm hover:bg-black/90 transition-all shadow-sm flex items-center gap-1.5 font-medium cursor-pointer"
                  >
                    <Check className="w-4.5 h-4.5" /> 保存智能体配置
                  </button>
                </div>
              </div>
            )}              {/* 2. TOOLS MANAGEMENT TAB */}
            {activeTab === 'tools' && (
              <div className="max-w-2xl mx-auto space-y-6">
                <header className="flex justify-between items-start flex-wrap gap-4">
                  <div className="space-y-1">
                    <h1 className="font-headline text-3xl font-bold text-gray-900">工具管理</h1>
                    <p className="font-sans text-sm text-gray-500">配置并监控 CogniAgent 可用的外部工具与插件。</p>
                  </div>
                  <button
                    onClick={() => setIsAddingTool(true)}
                    className="px-4 py-2.5 rounded-lg bg-black text-white font-sans text-sm flex items-center gap-1.5 hover:bg-black/90 transition-colors cursor-pointer"
                  >
                    <Plus className="w-4.5 h-4.5" /> 添加自定义工具
                  </button>
                </header>

                {/* Inline form to create custom tools */}
                {isAddingTool && (
                  <form onSubmit={handleCreateTool} className="p-5 rounded-xl border border-gray-250 bg-gray-50/50 space-y-4">
                    <h3 className="font-bold font-headline text-gray-900 text-base flex items-center justify-between">
                      连接并新建自定义工具
                      <button type="button" onClick={() => setIsAddingTool(false)} className="hover:text-red-500 text-gray-400 cursor-pointer">
                        <X className="w-5 h-5" />
                      </button>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-xs text-gray-600">工具名称 *</label>
                        <input
                          type="text"
                          required
                          value={toolFormName}
                          onChange={(e) => setToolFormName(e.target.value)}
                          placeholder="例如：内部数据库查询器"
                          className="w-full bg-white border border-gray-200 rounded-lg p-2 text-sm text-gray-900"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs text-gray-600">代理模型 (可选)</label>
                        <input
                          type="text"
                          value={toolFormModel}
                          onChange={(e) => setToolFormModel(e.target.value)}
                          placeholder="例如：gpt-4o-db"
                          className="w-full bg-white border border-gray-200 rounded-lg p-2 text-sm text-gray-900"
                        />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs text-gray-600">描述 *</label>
                      <textarea
                        required
                        value={toolFormDesc}
                        onChange={(e) => setToolFormDesc(e.target.value)}
                        placeholder="例如：连接内部系统以查询或验证用户当前余额与订单明细..."
                        rows={2}
                        className="w-full bg-white border border-gray-200 rounded-lg p-2 text-sm text-gray-900"
                      />
                    </div>
                    <div className="flex justify-end gap-2.5 pt-2">
                      <button
                        type="button"
                        onClick={() => setIsAddingTool(false)}
                        className="px-3 py-1.5 rounded-lg text-sm hover:bg-gray-100 text-gray-500 cursor-pointer"
                      >
                        取消
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-1.5 rounded-lg bg-black text-white text-sm font-semibold hover:bg-black/90 cursor-pointer"
                      >
                        保存工具
                      </button>
                    </div>
                  </form>
                )}

                {/* Tool lists mapping perfectly to images */}
                <div className="grid grid-cols-1 gap-4">
                  {tools.map((tool) => {
                    // Check ID and render relevant layout
                    const isSearch = tool.id === 'search';
                    const isInterpreter = tool.id === 'interpreter';
                    const isControl = tool.id === 'control';
                    const isVision = tool.id === 'vision';

                    let ToolIcon = Wrench;
                    if (isSearch) ToolIcon = Search;
                    else if (isInterpreter) ToolIcon = Terminal;
                    else if (isControl) ToolIcon = Monitor;
                    else if (isVision) ToolIcon = Eye;

                    return (
                      <div 
                        key={tool.id}
                        className="p-5 rounded-xl bg-white border border-gray-200 flex items-center gap-4 hover:border-black transition-colors"
                      >
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center shrink-0 ${
                          tool.active && !isControl ? 'bg-black text-white' : 'bg-gray-150 text-gray-400'
                        }`}>
                          <ToolIcon className="w-6 h-6" />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
                            <div className="flex items-center gap-2">
                              <h3 className="font-bold text-gray-900 text-base">{tool.name}</h3>
                              {isControl && (
                                <span className="px-2 py-0.5 rounded-full bg-red-50 border border-red-200 text-red-600 text-[10px] font-bold">
                                  需要系统授权
                                </span>
                              )}
                            </div>
                            
                            {/* Toggle Switches */}
                            <button
                              onClick={() => {
                                if (isControl) {
                                  alert("计算机控制工具需要操作系统管理员（OS Agent）授权。请在主控台确认您的配置。");
                                  return;
                                }
                                onToggleTool(tool.id);
                              }}
                              className={`w-10 h-5 rounded-full relative transition-colors cursor-pointer ${
                                tool.active && !isControl ? 'bg-black' : 'bg-gray-100 border border-gray-200'
                              }`}
                              title={isControl ? "安全级别过高" : "启用或禁用该工具"}
                            >
                              <div className={`absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all bg-white shadow-xs ${
                                tool.active && !isControl ? 'right-0.5' : 'left-0.5'
                              }`} />
                            </button>
                          </div>

                          <p className="text-sm text-gray-500 mb-1">{tool.description}</p>
                          
                          {/* Footer parameters per tool */}
                          {isSearch && (
                            <div className="text-xs text-gray-400 font-sans">
                              上一次调用: {tool.lastUsed || "2分钟前"}
                            </div>
                          )}

                          {isInterpreter && (
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <span className="text-xs text-black flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0"></span> 
                                运行中
                              </span>
                              <button 
                                onClick={() => alert("开始配置沙箱中的 Python 可执行文件路径...")}
                                className="text-xs font-semibold text-black hover:underline cursor-pointer"
                              >
                                配置参数
                              </button>
                            </div>
                          )}

                          {/* Render custom tools footer dynamically */}
                          {!isSearch && !isInterpreter && !isControl && !isVision && (
                            <div className="text-xs text-gray-400 font-sans">
                              {tool.modelText ? `代理模型: ${tool.modelText}` : `当前状态: 保持常驻且空闲`}
                            </div>
                          )}

                          {isVision && (
                            <div className="text-xs text-gray-400 font-sans">
                              后台模型: {tool.modelText || "GPT-4o-vision"}
                            </div>
                          )}

                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 3. MOCK DATA TAB */}
            {activeTab === 'data' && (
              <div className="max-w-2xl mx-auto space-y-6">
                <header>
                  <h1 className="font-headline text-3xl font-bold text-gray-900 mb-1">会话数据与核心记忆</h1>
                  <p className="font-sans text-sm text-gray-500">持续监控本系统加载并保留的记忆状态与持久化变量数据库。</p>
                </header>

                {/* Session memories management */}
                <section className="space-y-4 p-5 rounded-xl bg-white border border-gray-200">
                  <h3 className="text-sm font-semibold uppercase text-black tracking-wider border-b border-gray-150 pb-1.5">
                    常驻上下文智能记忆缓存 (Live Memories)
                  </h3>
                  <div className="space-y-3">
                    {sessionMemories.map((memo, idx) => (
                      <div key={idx} className="flex justify-between items-center gap-4 bg-white border border-gray-200 p-3 rounded-lg relative overflow-hidden pl-5 text-gray-950">
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-black"></div>
                        <p className="text-sm text-gray-855 font-sans">{memo}</p>
                        <button
                          onClick={() => onRemoveMemory(idx)}
                          className="hover:text-red-500 text-gray-400 transition-colors cursor-pointer"
                          title="忘却本条记忆"
                        >
                          <Trash2 className="w-4 h-4 shrink-0" />
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Add memory block inline */}
                  <div className="flex gap-2.5 pt-3">
                    <input
                      type="text"
                      value={newMemoryInput}
                      onChange={(e) => setNewMemoryInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleCreateMemory()}
                      placeholder="例如，添加您个性化的开发偏好参数: 用户喜欢优雅的中文显示风格..."
                      className="flex-1 bg-white border border-gray-200 rounded-lg p-2 text-sm text-gray-900 focus:border-black focus:outline-none"
                    />
                    <button
                      onClick={handleCreateMemory}
                      className="px-4 py-2 bg-black hover:bg-black/90 text-white rounded-lg font-sans text-sm font-semibold transition-all flex items-center gap-1.5 cursor-pointer"
                    >
                      <Plus className="w-4 h-4" /> 深度注入
                    </button>
                  </div>
                </section>

                {/* Utilities Section */}
                <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 rounded-xl bg-white border border-gray-200 space-y-3">
                    <h4 className="font-headline font-semibold text-gray-900">导出系统配置与日志</h4>
                    <p className="text-xs text-gray-500">将当前的会话上下文结构、智能体性格配置以及激活状态的工具链导出为标准的本地 JSON 文件。</p>
                    <button 
                      onClick={() => {
                        const fileData = JSON.stringify({ agentConfig, tools, sessionMemories }, null, 2);
                        const blob = new Blob([fileData], { type: "application/json" });
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = `cogniagent-config-${localName.toLowerCase().replace(/\s/g, "-")}.json`;
                        link.click();
                      }}
                      className="px-3 py-2 bg-white border border-gray-200 text-gray-900 hover:border-black text-xs rounded-lg flex items-center gap-1.5 hover:bg-gray-50 cursor-pointer"
                    >
                      <FileDown className="w-4 h-4" /> 导出配置文件 (JSON)
                    </button>
                  </div>

                  <div className="p-5 rounded-xl bg-white border border-gray-200 space-y-3">
                    <h4 className="font-headline font-semibold text-gray-900">清空系统动态缓存</h4>
                    <p className="text-xs text-red-500">注意：清除所有会话历史和临时的个性记忆数据，智能体在重启后还原至初始设置值。</p>
                    <button
                      onClick={executeClearCache}
                      disabled={isClearing}
                      className={`px-3 py-2 border text-xs rounded-lg flex items-center gap-1.5 transition-all text-red-600 border-red-200 hover:bg-red-50 cursor-pointer ${
                        isClearing && "opacity-50 cursor-not-allowed"
                      }`}
                    >
                      {isClearing ? "正在还原中..." : "立刻重置系统缓存"}
                    </button>
                  </div>
                </section>
              </div>
            )}

            {/* 4. APPEARANCE TAB */}
            {activeTab === 'appearance' && (
              <div className="max-w-2xl mx-auto space-y-6">
                <header>
                  <h1 className="font-headline text-3xl font-bold text-gray-900 mb-1">外观与视觉主题</h1>
                  <p className="font-sans text-sm text-gray-500">自定义界面的视觉氛围强调色以及悬浮面板的背景对比度规则。</p>
                </header>

                {/* Accent selection */}
                <section className="p-5 rounded-xl bg-white border border-gray-200 space-y-4">
                  <h3 className="font-headline font-bold text-gray-900">界面高亮强调色</h3>
                  <p className="text-xs text-gray-500">配置您全局所有的激活切换器、流式标志和按钮使用的霓虹装饰强调色：</p>
                  <div className="flex gap-4">
                    {[
                      { name: '经典魅力紫', color: 'bg-indigo-650 border-indigo-400', hex: '#6c5ce7' },
                      { name: '护眼极客绿', color: 'bg-emerald-500 border-emerald-300', hex: '#10b981' },
                      { name: '数字青空蓝', color: 'bg-cyan-500 border-cyan-300', hex: '#06b6d4' },
                      { name: '落日明澈黄', color: 'bg-amber-500 border-amber-300', hex: '#f59e0b' },
                    ].map((accent) => (
                      <button
                        key={accent.name}
                        onClick={() => {
                          document.documentElement.style.setProperty('--color-primary', accent.hex);
                          document.documentElement.style.setProperty('--color-primary-container', accent.hex);
                        }}
                        className="flex flex-col items-center gap-1.5"
                      >
                        <span className={`w-8 h-8 rounded-full ${accent.color} border-2 hover:scale-110 transition-transform cursor-pointer shadow-md`}></span>
                        <span className="text-[10px] text-gray-500 font-sans">{accent.name}</span>
                      </button>
                    ))}
                  </div>
                </section>

                {/* Display variations */}
                <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 rounded-xl bg-white border border-gray-200 space-y-2">
                    <h4 className="font-headline font-semibold text-gray-900 text-sm">毛玻璃背景高斯模糊</h4>
                    <p className="text-xs text-gray-500">设置后台及浮空通知栏的整体毛玻璃不透明度和模糊深度值：</p>
                    <select className="w-full bg-white border border-gray-200 rounded-lg p-2 text-sm text-gray-900">
                      <option selected>高模糊 (20px 模糊 / 45% 黑色渐变)</option>
                      <option>中等模糊 (12px 模糊 / 30% 黑色渐变)</option>
                      <option>无模糊 (实色纯底容器)</option>
                    </select>
                  </div>

                  <div className="p-5 rounded-xl bg-white border border-gray-200 space-y-2">
                    <h4 className="font-headline font-semibold text-gray-900 text-sm">背景粒子声波动画</h4>
                    <p className="text-xs text-gray-500">在智能助手进行思考、推理或联网检索时，是否播放环形粒子声波视觉涟漪：</p>
                    <select className="w-full bg-white border border-gray-200 rounded-lg p-2 text-sm text-gray-900">
                      <option selected>始终播放炫酷流体动画 (推荐)</option>
                      <option>开启低能耗静态预设</option>
                      <option>完全关闭声波粒子动效</option>
                    </select>
                  </div>
                </section>
              </div>
            )}

            {/* 5. HOTKEYS TAB */}
            {activeTab === 'hotkeys' && (
              <div className="max-w-2xl mx-auto space-y-6">
                <header>
                  <h1 className="font-headline text-3xl font-bold text-gray-900 mb-1">系统快捷键映射</h1>
                  <p className="font-sans text-sm text-gray-500">无需点击鼠标，在键盘上直接触发的高效组合指令。</p>
                </header>

                <section className="p-5 rounded-xl bg-white border border-gray-200 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pb-2">
                    
                    <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200">
                      <span className="text-sm text-gray-600">打开/关闭 语音模式</span>
                      <kbd className="px-2.5 py-1 bg-gray-100 border border-gray-200 font-mono text-xs text-black rounded-md shadow-xs">
                        Ctrl+M
                      </kbd>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200">
                      <span className="text-sm text-gray-600">打开/关闭 系统设置面板</span>
                      <kbd className="px-2.5 py-1 bg-gray-100 border border-gray-200 font-mono text-xs text-black rounded-md shadow-xs">
                        Ctrl+K
                      </kbd>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200">
                      <span className="text-sm text-gray-600">添加新的个性特征标签</span>
                      <kbd className="px-2.5 py-1 bg-gray-100 border border-gray-200 font-mono text-xs text-black rounded-md shadow-xs">
                        Ctrl+T
                      </kbd>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200">
                      <span className="text-sm text-gray-600">启动全新的工作会话</span>
                      <kbd className="px-2.5 py-1 bg-gray-100 border border-gray-200 font-mono text-xs text-black rounded-md shadow-xs">
                        Ctrl+I
                      </kbd>
                    </div>

                  </div>
                  <p className="text-xs text-gray-400 text-center">* 说明：以上组合按键随时在当前的网页客户端内均可全局触发，尽享极致效率！</p>
                </section>
              </div>
            )}

          </main>
        </div>

      </div>
    </div>
  );
}
