export interface SearchResult {
  title: string;
  description: string;
  url: string;
}

export interface ThoughtStep {
  title: string;
  text: string;
}

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  status?: 'searching' | 'thinking' | 'done';
  thoughtSteps?: ThoughtStep[];
  searchResults?: SearchResult[];
}

export interface ChatSession {
  id: string;
  title: string;
  category: 'Today' | 'Yesterday' | 'Earlier';
  iconName: 'history' | 'calendar' | 'folder' | 'archive';
  messages: Message[];
  activeTools: string[]; // List of tool IDs enabled
}

export interface AgentConfig {
  name: string;
  role: string;
  tags: string[];
  primaryModel: string;
  apiKeyOverride: string;
}

export interface ToolItem {
  id: string;
  name: string;
  description: string;
  statusText?: string;
  statusType?: 'running' | 'idle' | 'required';
  lastUsed?: string;
  active: boolean;
  modelText?: string;
}
