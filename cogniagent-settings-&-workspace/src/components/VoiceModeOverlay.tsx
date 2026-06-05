import { useState, useEffect } from 'react';
import {
  X,
  Mic,
  Pause,
  Play,
  Square,
  Sparkles,
  HelpCircle,
  Bell,
  Volume2
} from 'lucide-react';

interface VoiceModeOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitSpokenText: (text: string) => void;
  agentName: string;
}

const PRESET_PHRASES = [
  "帮我搜索最新的 AI 新闻",
  "总结一下 Drizzle Orm 的主要配置步骤",
  "用 Python 实现一个快速排序算法并测试",
  "分析当前项目中的 typescript 类型声明"
];

export default function VoiceModeOverlay({
  isOpen,
  onClose,
  onSubmitSpokenText,
  agentName
}: VoiceModeOverlayProps) {
  const [isPaused, setIsPaused] = useState(false);
  const [transcript, setTranscript] = useState("帮我搜索最新的 AI 新闻");
  const [typedTranscript, setTypedTranscript] = useState("");
  const [soundwaveActive, setSoundwaveActive] = useState(true);

  // Sync initial type effect on opening
  useEffect(() => {
    if (isOpen) {
      setTypedTranscript("");
      let index = 0;
      const interval = setInterval(() => {
        if (index <= transcript.length) {
          setTypedTranscript(transcript.slice(0, index));
          index++;
        } else {
          clearInterval(interval);
        }
      }, 70);
      return () => clearInterval(interval);
    }
  }, [isOpen, transcript]);

  if (!isOpen) return null;

  const handlePresetSelect = (text: string) => {
    setTranscript(text);
  };

  const handleStopAndSubmit = () => {
    onSubmitSpokenText(transcript);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-40 bg-[#111319] text-on-surface flex flex-col items-center justify-center glow-bg overflow-hidden">
      
      {/* Top Navbar strictly replicated from images */}
      <nav className="fixed top-0 left-0 w-full z-50 bg-[#111319]/80 backdrop-blur-xl border-b border-outline-variant flex justify-between items-center h-16 px-6 select-none shadow-sm">
        <div className="flex items-center gap-4">
          <span className="font-headline text-lg font-bold text-primary">CogniAgent</span>
          <div className="hidden md:flex gap-6">
            <span className="font-sans text-xs uppercase tracking-wider text-on-surface-variant font-medium opacity-60">语言模型</span>
            <span className="font-sans text-xs uppercase tracking-wider text-on-surface-variant font-medium opacity-60">所有工具</span>
            <span className="font-sans text-xs uppercase tracking-wider text-on-surface-variant font-medium opacity-60">执行日志</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="font-sans text-xs font-semibold uppercase tracking-wider text-primary border-b-2 border-primary pb-1">
            语音模式
          </button>
          <div className="flex gap-3 text-on-surface-variant">
            <button className="hover:text-primary transition-colors cursor-pointer"><Bell className="w-5 h-5 opacity-85" /></button>
            <button className="hover:text-primary transition-colors cursor-pointer"><HelpCircle className="w-5 h-5 opacity-85" /></button>
          </div>
        </div>
      </nav>

      {/* Main interaction canvas */}
      <main className="fixed inset-0 z-30 pt-16 flex flex-col items-center justify-center select-none">
        
        {/* Floating Close button top-left */}
        <button 
          onClick={onClose}
          className="absolute top-24 left-6 z-50 w-10 h-10 rounded-full glass-panel flex items-center justify-center text-on-surface-variant hover:text-primary hover:border-primary transition-all shadow-md cursor-pointer"
          title="退出语音模式"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Center interaction node */}
        <div className="relative flex flex-col items-center justify-center flex-1 w-full max-w-2xl mx-auto px-4">
          
          {/* Sounds Wave ripples exactly matching animations */}
          <div className="relative w-52 h-52 flex items-center justify-center mb-8">
            {soundwaveActive && !isPaused && (
              <>
                <div className="absolute inset-0 rounded-full bg-primary-container/30 ripple"></div>
                <div className="absolute inset-0 rounded-full bg-primary-container/20 ripple-2"></div>
                <div className="absolute inset-0 rounded-full bg-primary-container/10 ripple-3"></div>
              </>
            )}
            
            {/* Main pulsing microphone container */}
            <button 
              onClick={() => {
                setIsPaused(!isPaused);
                setSoundwaveActive(isPaused);
              }}
              className={`relative z-10 w-24 h-24 rounded-full flex items-center justify-center shadow-lg transition-all duration-300 ${
                isPaused 
                  ? 'bg-surface-container-high border-2 border-outline/50 text-outline' 
                  : 'bg-primary-container text-on-primary-container mic-pulse shadow-primary-container/50'
              }`}
            >
              <Mic className="w-10 h-10" />
            </button>
          </div>

          {/* Listening status dynamic labels */}
          <div className="text-center mb-8">
            {isPaused ? (
              <h2 className="font-headline text-2xl text-outline font-medium">语音已暂停</h2>
            ) : (
              <h2 className="font-headline text-2xl text-primary font-bold animate-pulse tracking-wide">
                正在聆听...
              </h2>
            )}
          </div>

          {/* SCRIPTED TRANSCRIPT CONTAINER WITH GLASSMORPHISM */}
          <div className="glass-panel rounded-xl p-5 max-w-lg w-full mb-8 transform hover:scale-[1.01] transition-all bg-[#1e1f26]/40 flex flex-col gap-3">
            <div className="font-sans text-body-lg text-on-surface text-center flex items-center justify-center gap-2 font-medium">
              <Mic className="w-5 h-5 text-primary shrink-0 animate-bounce" />
              <span>"{typedTranscript || "..."}"</span>
            </div>
            
            <span className="w-full h-[1px] bg-outline-variant/30 my-1"></span>
            
            {/* Audio Presets helper to test voice inputs easily */}
            <div className="space-y-1.5">
              <p className="text-[10px] text-outline uppercase tracking-wider text-center font-semibold text-primary/70">
                点击选择并模拟发送语音指令：
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                {PRESET_PHRASES.map((phrase) => (
                  <button
                    key={phrase}
                    onClick={() => handlePresetSelect(phrase)}
                    className={`p-1.5 text-left text-xs rounded-lg transition-all border ${
                      transcript === phrase 
                        ? 'bg-primary/10 border-primary/40 text-primary' 
                        : 'bg-white/5 border-transparent text-on-surface-variant hover:bg-white/10 hover:text-on-surface font-sans font-medium'
                    }`}
                  >
                    {phrase}
                  </button>
                ))}
              </div>
            </div>
          </div>

        </div>

        {/* Bottom Navigation controls */}
        <div className="w-full pb-10 flex flex-col items-center justify-end">
          
          {/* Dynamic talking dots strictly designed */}
          {!isPaused && (
            <div className="mb-4 opacity-75 flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-bounce" style={{ animationDelay: '0s' }}></span>
              <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-bounce" style={{ animationDelay: '0.15s' }}></span>
              <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-bounce" style={{ animationDelay: '0.3s' }}></span>
            </div>
          )}

          <div className="flex gap-6 bg-surface-container-high/65 p-2 rounded-full border border-outline-variant/50 shadow-xl">
            <button
              onClick={() => {
                setIsPaused(!isPaused);
                setSoundwaveActive(isPaused);
              }}
              className="w-14 h-14 rounded-full bg-surface-variant hover:bg-surface-container-highest border border-outline-variant hover:border-primary transition-colors flex items-center justify-center text-on-surface hover:text-primary cursor-pointer" 
              title={isPaused ? "开启语音" : "麦克风静音"}
            >
              {isPaused ? <Play className="w-6 h-6 fill-current" /> : <Pause className="w-6 h-6 fill-current" />}
            </button>
            <button
              onClick={handleStopAndSubmit}
              className="w-14 h-14 rounded-full bg-error-container hover:bg-error hover:text-on-error border border-error-container transition-colors flex items-center justify-center text-on-error-container hover:shadow-lg hover:shadow-error/20 cursor-pointer" 
              title="停止并发送指令"
            >
              <Square className="w-5 h-5 fill-current" />
            </button>
          </div>
        </div>

      </main>
    </div>
  );
}
