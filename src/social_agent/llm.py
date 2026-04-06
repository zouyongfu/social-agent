"""
LLM adapter layer - unified interface for multiple LLM providers.

Supports: OpenAI, Claude, DashScope (Qwen), Zhipu (GLM), Ollama (local)
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from .config import LLMConfig


@dataclass
class Message:
    """A chat message."""

    role: str  # system / user / assistant
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from an LLM."""

    content: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMAdapter(ABC):
    """Base class for LLM adapters."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response."""
        ...

    async def simple_chat(self, prompt: str, system: str = "") -> str:
        """Simple one-shot chat interface."""
        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        response = await self.chat(messages)
        return response.content


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI-compatible API adapter (works with OpenAI, DashScope, GLM, etc.)."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    base_url=self.config.base_url,
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60.0,
                )
            except ImportError:
                raise ImportError("httpx is required. Install with: pip install httpx")
        return self._client

    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        client = self._get_client()
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        payload.update(kwargs)

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.config.model),
            usage=data.get("usage", {}),
        )

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        payload.update(kwargs)

        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class ClaudeAdapter(BaseLLMAdapter):
    """Anthropic Claude API adapter."""

    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx is required. Install with: pip install httpx")

        # Claude uses a different API format
        system_msg = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        payload = {
            "model": self.config.model,
            "messages": chat_msgs,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data["content"][0]["text"],
            model=data.get("model", self.config.model),
            usage={
                "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                "output_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
        )

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        # Claude streaming - simplified implementation
        response = await self.chat(messages, temperature, max_tokens, stream=True, **kwargs)
        yield response.content


def create_llm_adapter(config: Optional[LLMConfig] = None) -> BaseLLMAdapter:
    """Factory function to create the appropriate LLM adapter."""
    if config is None:
        config = LLMConfig.from_env()

    if config.provider == "claude":
        return ClaudeAdapter(config)
    else:
        # OpenAI-compatible (openai, dashscope, zhipu, ollama)
        return OpenAIAdapter(config)
