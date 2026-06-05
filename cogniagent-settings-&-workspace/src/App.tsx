import { useState, useEffect } from 'react';
import ChatWorkspace from './components/ChatWorkspace';
import SettingsModal from './components/SettingsModal';
import VoiceModeOverlay from './components/VoiceModeOverlay';
import { AgentConfig, ToolItem } from './types';

// Initial tool sets perfectly designed based on mockup specifications
const INITIAL_TOOLS: ToolItem[] = [
  {
    id: 'search',
    name: '网络搜索',
    description: '从互联网获取实时信息与最新数据。',
    lastUsed: '2分钟前',
    active: true,
  },
  {
    id: 'interpreter',
    name: '代码解释器',
    description: '在安全隔离的沙箱中执行 Python 计算代码。',
    statusType: 'running',
    statusText: '运行中',
    active: true,
  },
  {
    id: 'control',
    name: '计算机控制',
    description: '允许智能体与本地操作系统和应用程序进行交互。',
    statusType: 'required',
    statusText: '需要授权',
    active: false,
  },
  {
    id: 'vision',
    name: '视觉与分析',
    description: '处理、识别并理解用户上传的图形和视觉输入。',
    modelText: 'GPT-4o-vision (视觉版)',
    active: true,
  }
];

const INITIAL_MEMORIES = [
  "用户倾向于使用中文普通话进行日常交流与回复。",
  "当前核心工作重点：下一代 AI 自主智能体应用研究与开发。"
];

export default function App() {
  // 1. Core Config state loaded
  const [agentConfig, setAgentConfig] = useState<AgentConfig>({
    name: '小悟',
    role: '智能助手',
    tags: ['友善', '严谨', '好奇'],
    primaryModel: 'GPT-4o (Optimized)',
    apiKeyOverride: ''
  });

  // 2. Active tools state
  const [tools, setTools] = useState<ToolItem[]>(INITIAL_TOOLS);

  // 3. User Vector Memory states
  const [sessionMemories, setSessionMemories] = useState<string[]>(INITIAL_MEMORIES);

  // 4. Floating Overlay toggles
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);
  const [voiceTextToSubmit, setVoiceTextToSubmit] = useState<string | undefined>(undefined);

  // Hook global hotkeys for ultimate developer efficiency
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Ctrl+K or Cmd+K to toggle settings panel
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSettingsOpen((prev) => !prev);
      }
      // Ctrl+M or Cmd+M to toggle Voice Mode
      if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
        e.preventDefault();
        setIsVoiceOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const handleToggleTool = (toolId: string) => {
    setTools((prevTools) =>
      prevTools.map((t) => (t.id === toolId ? { ...t, active: !t.active } : t))
    );
  };

  const handleAddCustomTool = (newTool: Omit<ToolItem, 'id'>) => {
    const customId = 'custom-' + Math.random().toString();
    const created: ToolItem = {
      id: customId,
      ...newTool,
    };
    setTools((prev) => [...prev, created]);
  };

  const handleAddMemory = (newMemory: string) => {
    setSessionMemories((prev) => [...prev, newMemory]);
  };

  const handleRemoveMemory = (indexToRemove: number) => {
    setSessionMemories((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const handleClearCache = () => {
    setSessionMemories([INITIAL_MEMORIES[0]]);
    setTools(INITIAL_TOOLS);
    setAgentConfig({
      name: '小悟',
      role: '智能助手',
      tags: ['友善', '严谨', '好奇'],
      primaryModel: 'GPT-4o (Optimized)',
      apiKeyOverride: ''
    });
    alert("本地向量数据库和系统缓存已成功清空，各项智能体预设已被安全还原。");
  };

  return (
    <div className="w-screen h-screen bg-background text-on-surface font-sans overflow-hidden antialiased">
      
      {/* Prime Chat Workspace layer */}
      <ChatWorkspace
        agentConfig={agentConfig}
        tools={tools}
        onToggleTool={handleToggleTool}
        sessionMemories={sessionMemories}
        onAddMemory={handleAddMemory}
        onRemoveMemory={handleRemoveMemory}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenVoice={() => setIsVoiceOpen(true)}
        voiceTextToSubmit={voiceTextToSubmit}
        clearVoiceText={() => setVoiceTextToSubmit(undefined)}
      />

      {/* Glossy System Settings pane modal overlay */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        agentConfig={agentConfig}
        onSaveAgentConfig={(newConfig) => setAgentConfig(newConfig)}
        tools={tools}
        onToggleTool={handleToggleTool}
        onAddCustomTool={handleAddCustomTool}
        sessionMemories={sessionMemories}
        onAddMemory={handleAddMemory}
        onRemoveMemory={handleRemoveMemory}
        onClearCache={handleClearCache}
      />

      {/* Immersive Soundwave Voice Mode overlay */}
      <VoiceModeOverlay
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
        onSubmitSpokenText={(spokenText) => setVoiceTextToSubmit(spokenText)}
        agentName={agentConfig.name}
      />

    </div>
  );
}
