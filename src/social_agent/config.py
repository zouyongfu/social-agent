"""
Global settings and configuration management.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openai"  # openai / claude / dashscope / zhipu / ollama
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048

    @classmethod
    def from_env(cls) -> "LLMConfig":
        provider = os.getenv("LLM_PROVIDER", "openai")
        config = cls(provider=provider)

        # OpenAI
        config.api_key = os.getenv("OPENAI_API_KEY", "")
        config.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # DashScope
        if provider == "dashscope":
            config.api_key = os.getenv("DASHSCOPE_API_KEY", "")
            config.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            config.model = "qwen-plus"

        # Zhipu
        elif provider == "zhipu":
            config.api_key = os.getenv("ZHIPU_API_KEY", "")
            config.base_url = "https://open.bigmodel.cn/api/paas/v4"
            config.model = "glm-4-flash"

        # Ollama (local)
        elif provider == "ollama":
            config.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            config.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

        # Claude
        elif provider == "claude":
            config.api_key = os.getenv("CLAUDE_API_KEY", "")

        return config


@dataclass
class PlatformConfig:
    """Configuration for a single platform."""

    name: str = ""
    enabled: bool = True
    cookie: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulerConfig:
    """Task scheduler configuration."""

    enabled: bool = True
    timezone: str = "Asia/Shanghai"
    max_workers: int = 3


@dataclass
class Settings:
    """Global application settings."""

    data_dir: Path = Path.home() / ".social-agent"
    llm: LLMConfig = field(default_factory=LLMConfig.from_env)
    platforms: Dict[str, PlatformConfig] = field(default_factory=dict)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    log_level: str = "INFO"

    # Content generation defaults
    default_style: str = "professional"  # professional / casual / humorous
    default_language: str = "zh-CN"
    max_content_length: int = 2000

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """Load settings from env vars and optional config file."""
        settings = cls()

        # Load from environment
        settings.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Load platform configs from env
        for platform_name in ["weibo", "xiaohongshu", "douyin", "bilibili", "zhihu"]:
            cookie = os.getenv(f"{platform_name.upper()}_COOKIE", "")
            if cookie:
                settings.platforms[platform_name] = PlatformConfig(
                    name=platform_name,
                    enabled=True,
                    cookie=cookie,
                )

        return settings

    def ensure_data_dir(self) -> Path:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir
