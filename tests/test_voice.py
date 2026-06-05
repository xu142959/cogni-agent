"""Tests for Voice module — TTS, STT, and VoiceIO."""

import pytest

from cogni_agent.voice import TTSEngine, STTEngine, VoiceIO, VoiceInputTool, VoiceOutputTool


class TestTTSEngine:
    def test_init_edge(self):
        tts = TTSEngine(backend="edge")
        assert tts._backend == "edge"
        assert tts._voice == "zh-CN-XiaoxiaoNeural"

    def test_init_edge_custom_voice(self):
        tts = TTSEngine(backend="edge", voice="en-US-JennyNeural")
        assert tts._voice == "en-US-JennyNeural"


class TestSTTEngine:
    def test_init_faster_whisper(self):
        stt = STTEngine(backend="faster-whisper", model_size="tiny")
        assert stt._backend == "faster-whisper"
        assert stt._model_size == "tiny"


class TestVoiceIO:
    def test_init_edge(self):
        voice = VoiceIO(tts_backend="edge")
        assert voice.stt._backend == "faster-whisper"
        assert voice.tts._backend == "edge"

    def test_voice_tools_schema(self):
        tool = VoiceInputTool()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "voice_input"
        assert "duration" in ot["function"]["parameters"]["properties"]

        tool2 = VoiceOutputTool()
        ot2 = tool2.to_openai_tool()
        assert ot2["function"]["name"] == "voice_output"
        assert "text" in ot2["function"]["parameters"]["required"]


class TestAllTools:
    def test_voice_tools_in_all_tools(self):
        from cogni_agent.tools import all_tools
        tools = all_tools()
        names = {t.name for t in tools}
        assert "voice_input" in names
        assert "voice_output" in names

    def test_total_tool_count(self):
        from cogni_agent.tools import all_tools
        tools = all_tools()
        assert len(tools) == 23  # 10 computer + 2 web + 3 file + 2 calc + 2 voice + 4 vision