"""Voice module — speech-to-text and text-to-speech for CogniAgent.

让 Agent 能"听"和"说"，像豆包一样语音对话。

Usage:
    from cogni_agent.voice import VoiceIO

    voice = VoiceIO()

    # 听：麦克风 → 文字
    text = await voice.listen()

    # 说：文字 → 语音播放
    await voice.speak("你好，我是你的 Agent")

    # 完整语音对话
    response = await agent.run(await voice.listen())
    await voice.speak(response)
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
import time
from pathlib import Path
from typing import Literal


# ═══════════════════════════════════════════════════════════
# 语音合成 (Text-to-Speech)
# ═══════════════════════════════════════════════════════════

class TTSEngine:
    """Text-to-Speech engine. 让 Agent 开口说话。

    支持后端:
        - edge-tts: 微软 Edge TTS, 免费, 音质最好, 需网络
        - pyttsx3: 离线, 系统语音, 不需要网络
        - gtts: Google TTS, 需网络
    """

    def __init__(
        self,
        backend: Literal["edge", "pyttsx3", "gtts"] = "edge",
        voice: str = "",
        lang: str = "zh-CN",
    ):
        self._backend = backend
        self._lang = lang

        if backend == "edge":
            # 中文: zh-CN-XiaoxiaoNeural, zh-CN-YunxiNeural, zh-CN-XiaoyiNeural
            self._voice = voice or "zh-CN-XiaoxiaoNeural"
            self._check_edge()
        elif backend == "gtts":
            self._check_gtts()
        elif backend == "pyttsx3":
            self._check_pyttsx3()

    def _check_edge(self):
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            raise ImportError("edge-tts required: pip install edge-tts")

    def _check_gtts(self):
        try:
            from gtts import gTTS  # noqa: F401
        except ImportError:
            raise ImportError("gTTS required: pip install gtts")

    def _check_pyttsx3(self):
        try:
            import pyttsx3  # noqa: F401
        except ImportError:
            raise ImportError("pyttsx3 required: pip install pyttsx3")

    async def speak(self, text: str, output_path: str | None = None) -> str | None:
        """合成语音并播放或保存到文件。

        Args:
            text: 要朗读的文字
            output_path: 保存路径（留空则直接播放）

        Returns:
            如果保存文件则返回路径，否则返回 None
        """
        if self._backend == "edge":
            return await self._speak_edge(text, output_path)
        elif self._backend == "gtts":
            return await self._speak_gtts(text, output_path)
        else:
            return await self._speak_pyttsx3(text)

    async def _speak_edge(self, text: str, output_path: str | None) -> str | None:
        import edge_tts

        if output_path:
            communicate = edge_tts.Communicate(text, self._voice)
            await communicate.save(output_path)
            # 播放
            self._play_audio(output_path)
            return output_path
        else:
            # 暂存到临时文件播放
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            communicate = edge_tts.Communicate(text, self._voice)
            await communicate.save(tmp_path)
            self._play_audio(tmp_path)
            os.unlink(tmp_path)
            return None

    async def _speak_gtts(self, text: str, output_path: str | None) -> str | None:
        from gtts import gTTS

        tts = gTTS(text=text, lang=self._lang[:2])

        if output_path:
            tts.save(output_path)
            self._play_audio(output_path)
            return output_path
        else:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            tts.save(tmp_path)
            self._play_audio(tmp_path)
            os.unlink(tmp_path)
            return None

    async def _speak_pyttsx3(self, text: str, output_path: str | None = None) -> str | None:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return output_path

    @staticmethod
    def _play_audio(file_path: str):
        """播放音频文件（跨平台）。"""
        import platform
        import subprocess

        system = platform.system().lower()
        try:
            if system == "darwin":  # macOS
                subprocess.Popen(["afplay", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "linux":
                subprocess.Popen(["aplay", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "windows":
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME)
        except Exception:
            pass  # 静默失败，至少文件已生成


# ═══════════════════════════════════════════════════════════
# 语音识别 (Speech-to-Text)
# ═══════════════════════════════════════════════════════════

class STTEngine:
    """Speech-to-Text engine. 让 Agent 听懂你说话。

    支持后端:
        - faster-whisper: 本地离线, 最推荐, 速度快, 准确率高
        - whisper: OpenAI Whisper (需要 openai 包)
        - sherpa-onnx: 纯离线, 轻量
    """

    def __init__(
        self,
        backend: Literal["faster-whisper", "whisper", "sherpa"] = "faster-whisper",
        model_size: str = "base",
        device: str = "auto",
        language: str = "zh",
    ):
        self._backend = backend
        self._model_size = model_size
        self._language = language
        self._model = None

        # 自动选择设备
        if device == "auto":
            self._device = "cpu"  # default to CPU, CUDA detection is optional
        else:
            self._device = device

    def _load_model(self):
        """延迟加载模型（首次调用时才加载）。"""
        if self._model is not None:
            return

        print(f"🎤 Loading STT model ({self._model_size}, {self._device})...")
        start = time.time()

        if self._backend == "faster-whisper":
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                model_size_or_path=self._model_size,
                device=self._device,
                compute_type="float16" if self._device == "cuda" else "int8",
            )

        elif self._backend == "whisper":
            import whisper
            self._model = whisper.load_model(self._model_size, device=self._device)

        elapsed = time.time() - start
        print(f"✅ STT model loaded in {elapsed:.1f}s")

    async def transcribe(self, audio_path: str) -> str:
        """将音频文件转为文字。

        Args:
            audio_path: 音频文件路径 (wav, mp3, m4a 等)

        Returns:
            识别出的文字
        """
        self._load_model()

        if self._backend == "faster-whisper":
            return await self._transcribe_faster(audio_path)
        elif self._backend == "whisper":
            return await self._transcribe_whisper(audio_path)
        else:
            return await self._transcribe_sherpa(audio_path)

    async def _transcribe_faster(self, audio_path: str) -> str:
        segments, info = self._model.transcribe(
            audio_path,
            language=self._language,
            beam_size=5,
            vad_filter=True,
        )
        texts = []
        for seg in segments:
            texts.append(seg.text)
        return " ".join(texts)

    async def _transcribe_whisper(self, audio_path: str) -> str:
        import whisper
        result = self._model.transcribe(audio_path, language=self._language)
        return result.get("text", "").strip()

    async def _transcribe_sherpa(self, audio_path: str) -> str:
        try:
            import sherpa_onnx
            # sherpa-onnx 的调用方式
            return "[sherpa-onnx 待实现]"
        except ImportError:
            return "[sherpa-onnx not installed]"


# ═══════════════════════════════════════════════════════════
# 音频录制 (Microphone)
# ═══════════════════════════════════════════════════════════

class Microphone:
    """麦克风录音工具。

    录制用户语音 → 保存为 WAV 文件 → 交给 STT 识别。
    """

    def __init__(self, sample_rate: int = 16000):
        self._sample_rate = sample_rate
        self._pyaudio = None  # lazy load

    def _ensure_pyaudio(self):
        if self._pyaudio is not None:
            return
        try:
            import pyaudio
            self._pyaudio = pyaudio
        except ImportError:
            self._pyaudio = None  # mark as checked

    async def record(self, duration: float = 5.0, output_path: str | None = None) -> str:
        """录制麦克风音频。

        Args:
            duration: 录制时长（秒）
            output_path: 保存路径（留空则使用临时文件）

        Returns:
            音频文件路径
        """
        self._ensure_pyaudio()
        if self._pyaudio is None:
            return "[麦克风不可用，请安装: pip install pyaudio]"

        import wave

        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name

        p = self._pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._sample_rate,
            input=True,
            frames_per_buffer=1024,
        )

        print(f"🎙️  Listening... ({duration}s)")
        frames = []
        for _ in range(0, int(self._sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(output_path, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self._sample_rate)
        wf.writeframes(b"".join(frames))
        wf.close()

        print(f"✅ Recording saved: {output_path}")
        return output_path


# ═══════════════════════════════════════════════════════════
# 统一 VoiceIO 接口 (一站式语音输入输出)
# ═══════════════════════════════════════════════════════════

class VoiceIO:
    """一站式语音输入输出接口。

    像豆包一样：你说话 → Agent 听懂 → Agent 回答 → 语音播放

    Usage:
        voice = VoiceIO()

        # 简单一句话
        text = await voice.listen()      # 你说话 → 文字
        await voice.speak("你好")        # 文字 → 语音

        # 与 Agent 结合
        agent = await AgentRuntime.create(...)
        while True:
            question = await voice.listen()
            answer = await agent.run(question)
            await voice.speak(answer)
    """

    def __init__(
        self,
        stt_backend: str = "faster-whisper",
        tts_backend: str = "edge",
        model_size: str = "base",
        language: str = "zh",
        tts_voice: str = "",
        sample_rate: int = 16000,
    ):
        self.stt = STTEngine(
            backend=stt_backend,
            model_size=model_size,
            language=language,
        )
        self.tts = TTSEngine(
            backend=tts_backend,
            voice=tts_voice,
            lang=language,
        )
        self.mic = Microphone(sample_rate=sample_rate)
        self._sample_rate = sample_rate

    async def listen(
        self,
        duration: float = 5.0,
        use_mic: bool = True,
        audio_path: str | None = None,
    ) -> str:
        """听用户说话 → 返回文字。

        Args:
            duration: 录制时长（秒）
            use_mic: 是否使用麦克风（False 则从 audio_path 读取）
            audio_path: 音频文件路径（use_mic=False 时使用）

        Returns:
            识别出的文字
        """
        if use_mic:
            audio_path = await self.mic.record(duration=duration)

        if not audio_path or not os.path.exists(audio_path):
            return ""

        text = await self.stt.transcribe(audio_path)
        return text.strip()

    async def speak(self, text: str, output_path: str | None = None) -> str | None:
        """说话：文字 → 语音播放。

        Args:
            text: 要朗读的文字
            output_path: 保存路径（留空则直接播放）
        """
        return await self.tts.speak(text, output_path)

    async def listen_and_speak(self, duration: float = 5.0) -> tuple[str, None]:
        """听一段 → 返回文字（等待外部处理后再 speak）。"""
        text = await self.listen(duration=duration)
        return text, None

    def listen_sync(self, duration: float = 5.0) -> str:
        """同步版 listen()，用于非 async 环境。"""
        import asyncio
        return asyncio.run(self.listen(duration=duration))

    def speak_sync(self, text: str):
        """同步版 speak()，用于非 async 环境。"""
        import asyncio
        asyncio.run(self.speak(text))


# ═══════════════════════════════════════════════════════════
# 语音快捷工具 (可作为 CogniAgent 工具)
# ═══════════════════════════════════════════════════════════

from cogni_agent.tools.base import BaseTool, ToolSchema


class VoiceInputTool(BaseTool):
    """语音输入工具 — 让 Agent 能听用户说话。"""

    name = "voice_input"
    description = "使用麦克风录制用户语音并转为文字。让用户可以用语音与 Agent 交流。"

    schema = ToolSchema(
        properties={
            "duration": {
                "type": "number",
                "description": "录音时长（秒），默认 5 秒",
            },
        },
    )

    _voice: VoiceIO = None

    async def run(self, duration: float = 5.0) -> str:
        if self._voice is None:
            self._voice = VoiceIO()
        return await self._voice.listen(duration=duration)


class VoiceOutputTool(BaseTool):
    """语音输出工具 — 让 Agent 能说话。"""

    name = "voice_output"
    description = "将文字转为语音并播放。让 Agent 可以用语音回答用户。"

    schema = ToolSchema(
        properties={
            "text": {
                "type": "string",
                "description": "要朗读的文字内容",
            },
        },
        required=["text"],
    )

    _voice: VoiceIO = None

    async def run(self, text: str) -> str:
        if self._voice is None:
            self._voice = VoiceIO()
        await self._voice.speak(text)
        return f"✅ 已朗读: {text[:50]}..."
