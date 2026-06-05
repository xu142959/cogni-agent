"""Vision module —让 Agent 拥有"眼睛"，能看见并理解屏幕。

像豆包一样：
  - 看到屏幕上有什么
  - 认出图标、按钮、文字
  - 理解当前界面状态
  - 找到特定 UI 元素的位置

Architecture:
┌──────────────────────────────────────────────────┐
│                  VisionSystem                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │ Screenshot │  │ OCR (文字) │  │ Understand │ │
│  │ (截图)     │  │ 识别屏幕文字│  │ 理解屏幕内容│ │
│  └────────────┘  └────────────┘  └────────────┘ │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │ Locate     │  │ Describe   │  │ Changes   │ │
│  │ 找UI元素   │  │ 描述界面   │  │ 检测变化   │ │
│  └────────────┘  └────────────┘  └────────────┘ │
└──────────────────────────────────────────────────┘
"""

from __future__ import annotations

import io
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Literal

from cogni_agent.core.types import Message
from cogni_agent.core.interfaces import LLMGateway
from cogni_agent.llm import LiteLLMGateway


# ═══════════════════════════════════════════════════════════
# OCR — 屏幕文字识别 (完全本地离线)
# ═══════════════════════════════════════════════════════════

class OCREngine:
    """OCR 文字识别引擎。从图片中提取文字。

    后端:
        - rapidocr: 本地离线, 速度快, 中文英文都好
        - easyocr: 本地离线, 支持更多语言
        - paddleocr: 百度 PaddleOCR, 精确度高
        - tesseract: 传统 OCR, 需要系统安装 tesseract
    """

    def __init__(
        self,
        backend: Literal["rapidocr", "easyocr", "paddleocr", "tesseract"] = "rapidocr",
        lang: str = "ch",
    ):
        self._backend = backend
        self._lang = lang
        self._model = None

    def _get_ocr(self):
        """延迟加载 OCR 模型。"""
        if self._model is not None:
            return self._model

        if self._backend == "rapidocr":
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._model = RapidOCR()
            except ImportError:
                raise ImportError("pip install rapidocr-onnxruntime")
        elif self._backend == "easyocr":
            try:
                import easyocr
                lang_map = {"ch": "ch_sim", "en": "en"}
                self._model = easyocr.Reader([lang_map.get(self._lang, "en")])
            except ImportError:
                raise ImportError("pip install easyocr")
        elif self._backend == "paddleocr":
            try:
                from paddleocr import PaddleOCR
                self._model = PaddleOCR(use_angle_cls=True, lang=self._lang)
            except ImportError:
                raise ImportError("pip install paddleocr")
        else:
            import pytesseract
            self._model = pytesseract

        return self._model

    async def extract_text(self, image_path: str) -> str:
        """从图片中提取文字。

        Args:
            image_path: 图片路径

        Returns:
            识别出的文字内容
        """
        engine = self._get_ocr()

        if self._backend == "rapidocr":
            result, elapse = engine(image_path)
            if result:
                texts = [item[1] for item in result]
                return "\n".join(texts)
            return "[未检测到文字]"

        elif self._backend == "easyocr":
            result = engine.readtext(image_path)
            texts = [item[1] for item in result]
            return "\n".join(texts)

        elif self._backend == "paddleocr":
            result = engine.ocr(image_path, cls=True)
            texts = []
            for line in result:
                for item in line:
                    texts.append(item[1][0])
            return "\n".join(texts)

        else:  # tesseract
            text = engine.image_to_string(image_path, lang=self._lang)
            return text.strip() or "[未检测到文字]"

    async def extract_text_with_positions(self, image_path: str) -> list[dict]:
        """提取文字及其位置信息。

        Returns:
            [{"text": "...", "bbox": [x1,y1,x2,y2], "confidence": 0.95}, ...]
        """
        engine = self._get_ocr()

        results = []

        if self._backend == "rapidocr":
            result, elapse = engine(image_path)
            if result:
                for item in result:
                    bbox, text, confidence = item
                    results.append({
                        "text": text,
                        "bbox": bbox,
                        "confidence": confidence,
                    })

        elif self._backend == "easyocr":
            result = engine.readtext(image_path)
            for item in result:
                bbox, text, confidence = item
                results.append({
                    "text": text,
                    "bbox": bbox,
                    "confidence": confidence,
                })

        return results


# ═══════════════════════════════════════════════════════════
# 屏幕理解 (Screen Understanding)
# ═══════════════════════════════════════════════════════════

class ScreenUnderstanding:
    """屏幕理解 — 让 Agent 真正"看懂"屏幕。

    功能:
        1. 截图 → OCR 提取文字 → 理解界面内容
        2. 找 UI 元素 (文本匹配)
        3. 屏幕变化检测 (前后对比)
        4. 界面描述 (截图 + OCR 结果 → LLM 理解)
    """

    def __init__(
        self,
        llm: LLMGateway | None = None,
        ocr_engine: OCREngine | None = None,
    ):
        self._llm = llm or LiteLLMGateway()
        self._ocr = ocr_engine or OCREngine()
        self._last_screenshot: str | None = None

    async def understand_screen(self, image_path: str) -> str:
        """理解屏幕内容 — 用 OCR + 视觉描述。

        返回对人类友好的屏幕描述。
        """
        # 1. 提取文字
        ocr_text = await self._ocr.extract_text(image_path)
        ocr_info = ocr_text if ocr_text and ocr_text != "[未检测到文字]" else "屏幕上未检测到文字"

        # 2. 用 LLM 理解屏幕内容
        prompt = (
            f"以下是从一张屏幕截图中 OCR 识别出的文字内容。\n"
            f"请根据这些文字推测：\n"
            f"1. 这是什么软件/界面？\n"
            f"2. 用户当前在做什么？\n"
            f"3. 屏幕上主要有哪些元素？\n"
            f"4. 用户可以执行什么操作？\n\n"
            f"OCR 识别文字:\n{ocr_info}\n\n"
            f"请给出简洁清晰的分析。"
        )

        response = await self._llm.chat([Message(role="user", content=prompt)])
        return response.content

    async def find_ui_element(self, image_path: str, target_text: str) -> dict | None:
        """在屏幕截图中找到包含目标文字的 UI 元素位置。

        Args:
            image_path: 截图路径
            target_text: 要找的文字（如"发送"、"确定"）

        Returns:
            {"text": "...", "bbox": [x1,y1,x2,y2], "center": (cx,cy)} 或 None
        """
        items = await self._ocr.extract_text_with_positions(image_path)

        for item in items:
            if target_text.lower() in item["text"].lower():
                bbox = item["bbox"]
                # 计算中心点 (用于鼠标点击)
                if len(bbox) >= 4:
                    cx = (bbox[0][0] + bbox[2][0]) // 2
                    cy = (bbox[0][1] + bbox[2][1]) // 2
                else:
                    cx, cy = 0, 0
                return {
                    "text": item["text"],
                    "bbox": bbox,
                    "center": (cx, cy),
                    "confidence": item.get("confidence", 0),
                }

        return None

    async def list_all_ui_elements(self, image_path: str) -> list[dict]:
        """列出屏幕上的所有可交互元素（带文字和位置）。"""
        return await self._ocr.extract_text_with_positions(image_path)

    async def detect_changes(
        self,
        new_screenshot: str,
        old_screenshot: str | None = None,
    ) -> str:
        """检测屏幕变化（如果有前一张截图的话）。"""
        old = old_screenshot or self._last_screenshot
        if old is None:
            old_text = ""
        else:
            old_text = await self._ocr.extract_text(old)

        new_text = await self._ocr.extract_text(new_screenshot)
        self._last_screenshot = new_screenshot

        if not old_text:
            return f"屏幕内容:\n{new_text}"

        prompt = (
            f"对比以下两张屏幕截图的 OCR 结果:\n\n"
            f"之前:\n{old_text}\n\n"
            f"现在:\n{new_text}\n\n"
            f"发生了什么变化？请总结。"
        )
        response = await self._llm.chat([Message(role="user", content=prompt)])
        return response.content


# ═══════════════════════════════════════════════════════════
# 统一视觉接口 (一站式视觉能力)
# ═══════════════════════════════════════════════════════════

class VisionSystem:
    """统一视觉系统 — 一站式屏幕理解和识别。

    像豆包一样：
        screen = VisionSystem()
        desc = await screen.look()       # "看一下屏幕"
        btn = await screen.find("发送")  # "找到发送按钮"
        text = await screen.read()       # "读取屏幕文字"
        await screen.click("确定")       # "点击确定按钮"
    """

    def __init__(
        self,
        llm: LLMGateway | None = None,
        ocr_backend: str = "rapidocr",
    ):
        self.ocr = OCREngine(backend=ocr_backend)
        self.understanding = ScreenUnderstanding(llm=llm, ocr_engine=self.ocr)
        self._llm = llm

    async def look(self, image_path: str | None = None) -> str:
        """"看一眼"屏幕，返回对当前界面的理解。

        如果未提供 image_path，会自动截图（需要屏幕权限）。
        """
        if image_path is None:
            image_path = await self._screenshot()
        return await self.understanding.understand_screen(image_path)

    async def read(self, image_path: str | None = None) -> str:
        """读取屏幕上的所有文字（OCR）。"""
        if image_path is None:
            image_path = await self._screenshot()
        return await self.ocr.extract_text(image_path)

    async def find(
        self,
        target_text: str,
        image_path: str | None = None,
    ) -> dict | None:
        """在屏幕上找到包含目标文字的元素位置。"""
        if image_path is None:
            image_path = await self._screenshot()
        return await self.understanding.find_ui_element(image_path, target_text)

    async def find_all(self, image_path: str | None = None) -> list[dict]:
        """列出屏幕上所有可识别的 UI 元素。"""
        if image_path is None:
            image_path = await self._screenshot()
        return await self.understanding.list_all_ui_elements(image_path)

    async def click(self, target_text: str) -> str:
        """找到目标文字并返回点击坐标（供电脑控制工具使用）。

        Returns: "点击位置: (x, y)"
        """
        result = await self.find(target_text)
        if result and result.get("center"):
            cx, cy = result["center"]
            return f"点击位置: ({cx}, {cy})"
        return f"未找到元素: {target_text}"

    async def _screenshot(self) -> str:
        """自动截图，返回临时文件路径。"""
        try:
            from cogni_agent.tools.computer import _BACKEND
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                path = f.name
            _BACKEND.screenshot(path)
            return path
        except Exception as exc:
            raise RuntimeError(f"截图失败: {exc}")


# ═══════════════════════════════════════════════════════════
# 视觉工具 (可作为 CogniAgent 的工具)
# ═══════════════════════════════════════════════════════════

from cogni_agent.tools.base import BaseTool, ToolSchema


class ScreenLookTool(BaseTool):
    """视觉理解工具 — Agent 的"眼睛"。看一眼屏幕并理解内容。"""

    name = "screen_look"
    description = (
        "查看屏幕并理解当前显示的内容。"
        "返回对人类友好的界面描述：当前是什么软件、有什么元素、用户可以做什么。"
        "就像你看一眼屏幕就知道自己在什么界面上一样。"
    )

    _vision: VisionSystem = None

    async def run(self) -> str:
        if self._vision is None:
            self._vision = VisionSystem()
        return await self._vision.look()


class ScreenReadTool(BaseTool):
    """屏幕文字识别工具 — 读取屏幕上显示的所有文字。"""

    name = "screen_read"
    description = "读取屏幕上显示的所有文字信息，包括菜单、按钮文本、内容文字等。"

    _vision: VisionSystem = None

    async def run(self) -> str:
        if self._vision is None:
            self._vision = VisionSystem()
        return await self._vision.read()


class ScreenFindTool(BaseTool):
    """UI 元素定位工具 — 在屏幕上找到指定文字的位置。"""

    name = "screen_find"
    description = "在屏幕上找到包含指定文字的 UI 元素位置。返回坐标供鼠标点击使用。"

    schema = ToolSchema(
        properties={
            "text": {
                "type": "string",
                "description": "要查找的文字内容，如'发送'、'确定'、'搜索'",
            },
        },
        required=["text"],
    )

    _vision: VisionSystem = None

    async def run(self, text: str) -> str:
        if self._vision is None:
            self._vision = VisionSystem()
        result = await self._vision.find(text)
        if result:
            cx, cy = result["center"]
            return f"✅ 找到 '{text}'，位置 ({cx}, {cy})，置信度 {result.get('confidence', 0):.0%}"
        return f"❌ 未找到 '{text}'"


class ScreenListElementsTool(BaseTool):
    """UI 元素列表工具 — 列出屏幕上所有可识别的元素。"""

    name = "screen_list_elements"
    description = "列出屏幕上所有可识别的 UI 元素及其位置。在操作电脑前使用，了解当前界面布局。"

    _vision: VisionSystem = None

    async def run(self) -> str:
        if self._vision is None:
            self._vision = VisionSystem()
        elements = await self._vision.find_all()
        if not elements:
            return "屏幕上未检测到可识别的 UI 元素"

        lines = [f"屏幕上找到 {len(elements)} 个元素:", ""]
        for i, el in enumerate(elements, 1):
            bbox = el.get("bbox", [])
            if bbox and len(bbox) >= 4:
                pos = f"({bbox[0][0]},{bbox[0][1]})-({bbox[2][0]},{bbox[2][1]})"
            else:
                pos = "未知位置"
            lines.append(f"  {i}. [{pos}] {el['text'][:30]}")
            if el.get("confidence", 0) < 0.5:
                lines[-1] += " (低置信度)"

        return "\n".join(lines)