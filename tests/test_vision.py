"""Tests for Vision module — OCR, screen understanding, and vision tools."""

import pytest

from cogni_agent.vision import (
    OCREngine,
    ScreenUnderstanding,
    VisionSystem,
    ScreenLookTool,
    ScreenReadTool,
    ScreenFindTool,
    ScreenListElementsTool,
)


class TestOCREngine:
    def test_init_rapidocr(self):
        ocr = OCREngine(backend="rapidocr")
        assert ocr._backend == "rapidocr"

    def test_init_easyocr(self):
        ocr = OCREngine(backend="easyocr")
        assert ocr._backend == "easyocr"


class TestScreenUnderstanding:
    def test_init(self):
        su = ScreenUnderstanding()
        assert su._ocr is not None
        assert su._llm is not None


class TestVisionSystem:
    def test_init(self):
        vs = VisionSystem()
        assert vs.ocr is not None
        assert vs.understanding is not None


class TestVisionTools:
    def test_screen_look_tool_schema(self):
        tool = ScreenLookTool()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "screen_look"

    def test_screen_read_tool_schema(self):
        tool = ScreenReadTool()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "screen_read"

    def test_screen_find_tool_schema(self):
        tool = ScreenFindTool()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "screen_find"
        assert "text" in ot["function"]["parameters"]["required"]

    def test_screen_list_elements_tool_schema(self):
        tool = ScreenListElementsTool()
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "screen_list_elements"


class TestAllTools:
    def test_vision_tools_in_all_tools(self):
        from cogni_agent.tools import all_tools
        tools = all_tools()
        names = {t.name for t in tools}
        assert "screen_look" in names
        assert "screen_read" in names
        assert "screen_find" in names
        assert "screen_list_elements" in names

    def test_total_tool_count(self):
        from cogni_agent.tools import all_tools
        tools = all_tools()
        assert len(tools) == 23  # 10 computer + 2 web + 3 file + 2 calc + 2 voice + 4 vision