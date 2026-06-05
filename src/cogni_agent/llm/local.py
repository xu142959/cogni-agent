"""Local LLM Inference — runs models completely offline, no API required.

Supports:
- llama.cpp via llama-cpp-python (GGUF models)
- HuggingFace transformers for compatible models
- Ollama as a local server

Integrates with CogniAgent's LLMGateway so agents can run completely offline.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from cogni_agent.core.errors import LLMError
from cogni_agent.core.interfaces import LLMGateway as BaseLLMGateway
from cogni_agent.core.types import LLMConfig, LLMResponse, LLMToolCall, Message


class LocalLLMError(LLMError):
    """Raised when local inference fails."""


def _detect_gpu_memory() -> int:
    """Detect available GPU memory in MB. Returns 0 if no GPU."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return 0


def _recommend_model() -> dict:
    """Recommend a model based on available hardware."""
    gpu_mem = _detect_gpu_memory()
    ram = 0
    try:
        import psutil
        ram = psutil.virtual_memory().available // (1024 * 1024)
    except ImportError:
        ram = 8192  # assume 8GB

    # Model recommendations based on available memory
    if gpu_mem >= 24000:
        return {
            "model": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
            "repo": "Qwen/Qwen2.5-14B-Instruct-GGUF",
            "n_gpu_layers": 35,
            "description": "Best quality, ~14B params, needs 24GB+ VRAM",
        }
    elif gpu_mem >= 12000:
        return {
            "model": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
            "n_gpu_layers": 25,
            "description": "Good quality, ~7B params, needs 12GB+ VRAM",
        }
    elif gpu_mem >= 6000:
        return {
            "model": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
            "n_gpu_layers": 15,
            "description": "Decent quality, 6GB VRAM, partial GPU offload",
        }
    elif ram >= 16000:
        return {
            "model": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
            "n_gpu_layers": 0,
            "description": "7B on CPU only, needs 16GB+ RAM",
        }
    elif ram >= 8000:
        return {
            "model": "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
            "repo": "Qwen/Qwen2.5-3B-Instruct-GGUF",
            "n_gpu_layers": 0,
            "description": "Lightweight 3B on CPU, needs 8GB+ RAM",
        }
    else:
        return {
            "model": "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
            "repo": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
            "n_gpu_layers": 0,
            "description": "Minimal 1.5B on CPU, needs 4GB+ RAM",
        }


class LlamaCppGateway(BaseLLMGateway):
    """Local LLM inference via llama-cpp-python.

    Runs GGUF models locally — no internet or API keys required.

    Usage:
        gateway = LlamaCppGateway(model_path="models/qwen-7b.gguf")

        # Or auto-download recommended model
        gateway = await LlamaCppGateway.create(model_name="Qwen2.5-7B")
    """

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
        verbose: bool = False,
    ):
        self._model_path = Path(model_path)
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._verbose = verbose
        self._model = None

    @classmethod
    async def create(
        cls,
        model_name: str = "",
        models_dir: str = "models",
        n_ctx: int = 4096,
        verbose: bool = False,
    ) -> LlamaCppGateway:
        """Create a local LLM gateway.

        If model_name is empty, auto-recommends based on hardware.
        Downloads the model if not found locally.
        """
        models_path = Path(models_dir)
        models_path.mkdir(parents=True, exist_ok=True)

        if not model_name:
            rec = _recommend_model()
            model_name = rec["model"]
            n_gpu_layers = rec["n_gpu_layers"]
            print(f"📋 Recommended model: {model_name} ({rec['description']})")
            print(f"   GPU layers: {n_gpu_layers}")
        else:
            n_gpu_layers = _detect_gpu_memory() // 500 if _detect_gpu_memory() > 0 else 0

        model_path = models_path / model_name

        if not model_path.exists():
            print(f"⬇️  Downloading {model_name}...")
            cls._download_model(model_name, str(model_path))

        return cls(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=verbose,
        )

    @staticmethod
    def _download_model(model_name: str, target_path: str) -> None:
        """Download a GGUF model from HuggingFace."""
        try:
            from huggingface_hub import hf_hub_download

            # Map friendly name to HF repo
            repo_map = {
                "Qwen2.5-7B-Instruct-Q4_K_M.gguf": "Qwen/Qwen2.5-7B-Instruct-GGUF",
                "Qwen2.5-3B-Instruct-Q4_K_M.gguf": "Qwen/Qwen2.5-3B-Instruct-GGUF",
                "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
                "Qwen2.5-14B-Instruct-Q4_K_M.gguf": "Qwen/Qwen2.5-14B-Instruct-GGUF",
            }

            repo = repo_map.get(model_name, "Qwen/Qwen2.5-7B-Instruct-GGUF")

            print(f"   Downloading from HuggingFace: {repo}/{model_name}")
            downloaded = hf_hub_download(
                repo_id=repo,
                filename=model_name,
                local_dir=os.path.dirname(target_path),
                local_dir_use_symlinks=False,
            )
            print(f"✅ Downloaded to: {downloaded}")

        except ImportError:
            raise ImportError(
                "Downloading models requires huggingface-hub:\n"
                "  pip install huggingface-hub"
            )
        except Exception as exc:
            raise LocalLLMError(f"Failed to download model: {exc}")

    def _ensure_loaded(self):
        """Lazy-load the model."""
        if self._model is not None:
            return

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "Local LLM inference requires llama-cpp-python:\n"
                "  pip install llama-cpp-python\n\n"
                "For GPU support:\n"
                "  CMAKE_ARGS=\"-DLLAMA_CUDA=on\" pip install llama-cpp-python"
            )

        print(f"📦 Loading model: {self._model_path}")
        print(f"   Context: {self._n_ctx}, GPU Layers: {self._n_gpu_layers}")

        start = time.time()
        self._model = Llama(
            model_path=str(self._model_path),
            n_ctx=self._n_ctx,
            n_gpu_layers=self._n_gpu_layers,
            verbose=self._verbose,
        )
        elapsed = time.time() - start
        print(f"✅ Model loaded in {elapsed:.1f}s")

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        config_override: LLMConfig | None = None,
    ) -> LLMResponse:
        self._ensure_loaded()

        # Format messages for llama.cpp chat format
        formatted = []
        for m in messages:
            formatted.append({"role": m.role, "content": m.content})

        # Add system prompt if tools are available
        if tools:
            tool_descriptions = []
            for t in tools:
                name = t.get("function", {}).get("name", "unknown")
                desc = t.get("function", {}).get("description", "")
                tool_descriptions.append(f"- {name}: {desc}")

            tools_prompt = (
                "\n\nYou have access to the following tools:\n" +
                "\n".join(tool_descriptions) +
                "\nTo use a tool, respond with a JSON object: "
                '{"tool": "tool_name", "arguments": {...}}'
            )

            if formatted and formatted[0]["role"] == "system":
                formatted[0]["content"] += tools_prompt
            else:
                formatted.insert(0, {"role": "system", "content": tools_prompt.strip()})

        start = time.monotonic()

        try:
            response = self._model.create_chat_completion(
                messages=formatted,
                temperature=config_override.temperature if config_override else 0.7,
                max_tokens=config_override.max_tokens if config_override else 4096,
            )
        except Exception as exc:
            raise LocalLLMError(f"Local inference failed: {exc}")

        elapsed = int((time.monotonic() - start) * 1000)
        choice = response.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")

        # Parse local tool calls from structured JSON in content
        tool_calls: list[LLMToolCall] = []
        if content and tools:
            import re
            # Check for JSON tool call in the response
            json_pattern = r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}'
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                tool_name = match.group(1)
                try:
                    tool_args = json.loads(match.group(2))
                except json.JSONDecodeError:
                    tool_args = {}
                tool_calls.append(LLMToolCall(
                    id=f"local_{int(time.time())}",
                    name=tool_name,
                    arguments=json.dumps(tool_args),
                ))
                # Clean the tool call from the content
                content = content[:match.start()] + content[match.end():]
                content = content.strip().strip(",").strip()

        return LLMResponse(
            content=content or "",
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            model=f"local:{self._model_path.name}",
            usage={
                "input_tokens": response.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": response.get("usage", {}).get("completion_tokens", 0),
            },
            latency_ms=elapsed,
        )


class OllamaGateway(BaseLLMGateway):
    """Connect to a local Ollama instance for offline inference.

    Usage:
        gateway = OllamaGateway(model="llama3.1", base_url="http://localhost:11434")
    """

    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        config_override: LLMConfig | None = None,
    ) -> LLMResponse:
        import httpx

        formatted = [{"role": m.role, "content": m.content} for m in messages]

        if tools:
            tool_descriptions = []
            for t in tools:
                name = t.get("function", {}).get("name", "unknown")
                desc = t.get("function", {}).get("description", "")
                tool_descriptions.append(f"- {name}: {desc}")
            tools_hint = (
                "\n\nAvailable tools:\n" + "\n".join(tool_descriptions)
            )
            if formatted and formatted[0]["role"] == "system":
                formatted[0]["content"] += tools_hint

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self._base_url}/api/chat", json={
                    "model": self._model,
                    "messages": formatted,
                    "stream": False,
                    "options": {
                        "temperature": config_override.temperature if config_override else 0.7,
                    },
                })
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            raise LocalLLMError(
                f"Cannot connect to Ollama at {self._base_url}\n"
                f"Make sure Ollama is running.\n"
                f"  ollama serve\n"
                f"  ollama pull {self._model}"
            )
        except Exception as exc:
            raise LocalLLMError(f"Ollama request failed: {exc}")

        elapsed = int((time.monotonic() - start) * 1000)
        msg = data.get("message", {})
        content = msg.get("content", "")

        tool_calls: list[LLMToolCall] = []
        if content and tools:
            import re
            json_pattern = r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}'
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                tool_name = match.group(1)
                try:
                    tool_args = json.loads(match.group(2))
                except json.JSONDecodeError:
                    tool_args = {}
                tool_calls.append(LLMToolCall(
                    id=f"ollama_{int(time.time())}",
                    name=tool_name,
                    arguments=json.dumps(tool_args),
                ))
                content = content[:match.start()] + content[match.end():]

        return LLMResponse(
            content=content.strip() or "",
            tool_calls=tool_calls,
            finish_reason="stop",
            model=f"ollama:{self._model}",
            usage={"input_tokens": 0, "output_tokens": 0},
            latency_ms=elapsed,
        )


def get_local_gateway(model_type: str = "auto", **kwargs) -> BaseLLMGateway:
    """Get the best local LLM gateway for your hardware.

    Args:
        model_type: "auto" (recommend), "llamacpp" (direct GGUF), "ollama" (Ollama server)

    Returns:
        A configured local LLM gateway instance.
    """
    if model_type == "ollama":
        return OllamaGateway(**kwargs)

    if model_type == "llamacpp":
        return LlamaCppGateway(**kwargs)

    # Auto-detect
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            print("✅ Ollama detected, using OllamaGateway")
            return OllamaGateway(**kwargs)
    except Exception:
        pass

    try:
        import llama_cpp  # noqa: F401
        print("✅ llama-cpp-python detected, using LlamaCppGateway")
        return LlamaCppGateway(**kwargs)
    except ImportError:
        pass

    raise ImportError(
        "No local inference engine found.\n"
        "Install one of:\n"
        "  pip install llama-cpp-python  (for GGUF models)\n"
        "  # or\n"
        "  pip install ollama  (for Ollama server)"
    )