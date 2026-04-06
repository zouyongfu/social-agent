"""
Plugin system - the core extensibility mechanism.

Every platform, tool, and capability is a plugin.
Community can create and share plugins.
"""

from __future__ import annotations

import importlib
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type


class PluginType(Enum):
    """Types of plugins."""

    PLATFORM = "platform"  # Social media platform (weibo, xiaohongshu, etc.)
    CONTENT = "content"  # Content generator/style
    ANALYZER = "analyzer"  # Data analyzer
    NOTIFIER = "notifier"  # Notification channel
    STORAGE = "storage"  # Data storage backend
    TOOL = "tool"  # Utility tool


class ActionScope(Enum):
    """Scope of actions a platform plugin supports."""

    READ = "read"  # Can read/monitor content
    WRITE = "write"  # Can create/publish content
    INTERACT = "interact"  # Can like/comment/reply
    ANALYZE = "analyze"  # Can access analytics data


@dataclass
class PluginMeta:
    """Metadata about a plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    plugin_type: PluginType = PluginType.PLATFORM
    author: str = ""
    homepage: str = ""
    supported_actions: List[ActionScope] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class BasePlugin(ABC):
    """Base class for all plugins."""

    # Subclasses must define their metadata
    meta: PluginMeta

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the plugin. Called before first use."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Clean up resources."""
        self._initialized = False

    @property
    def is_ready(self) -> bool:
        return self._initialized

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)


class BasePlatformPlugin(BasePlugin):
    """
    Base class for platform plugins.

    Platform plugins implement the interface to interact with a specific
    social media platform (e.g., Weibo, Xiaohongshu, Douyin).
    """

    @abstractmethod
    async def verify_auth(self) -> bool:
        """Verify authentication is still valid."""
        ...

    @abstractmethod
    async def get_trending(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch trending/hot topics from the platform."""
        ...

    @abstractmethod
    async def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for content on the platform."""
        ...


class BaseContentPlugin(BasePlugin):
    """Base class for content generation plugins."""

    @abstractmethod
    async def generate(
        self,
        topic: str,
        platform: str = "",
        style: str = "professional",
        **kwargs,
    ) -> str:
        """Generate content for the given topic."""
        ...

    @abstractmethod
    async def adapt(self, content: str, from_platform: str, to_platform: str) -> str:
        """Adapt content from one platform style to another."""
        ...


class BaseAnalyzerPlugin(BasePlugin):
    """Base class for analytics plugins."""

    @abstractmethod
    async def analyze_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single post's performance."""
        ...

    @abstractmethod
    async def get_insights(self, platform: str, period: str = "7d") -> Dict[str, Any]:
        """Get aggregated insights for a platform."""
        ...


class PluginManager:
    """
    Manages discovery, loading, and lifecycle of plugins.
    """

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}

    def register(self, plugin_class: Type[BasePlugin]) -> None:
        """Register a plugin class."""
        if hasattr(plugin_class, "meta"):
            name = plugin_class.meta.name
        else:
            name = plugin_class.__name__
        self._plugin_classes[name] = plugin_class

    def discover_plugins(self, package_path: str = "social_agent.plugins") -> None:
        """Auto-discover plugins from the plugins package."""
        try:
            pkg = importlib.import_module(package_path)
            pkg_path = Path(pkg.__file__).parent

            for item in pkg_path.iterdir():
                if item.is_dir() and not item.name.startswith("_"):
                    try:
                        mod = importlib.import_module(f"{package_path}.{item.name}")
                        for attr_name in dir(mod):
                            attr = getattr(mod, attr_name)
                            if (
                                inspect.isclass(attr)
                                and issubclass(attr, BasePlugin)
                                and attr is not BasePlugin
                                and hasattr(attr, "meta")
                            ):
                                self.register(attr)
                    except Exception:
                        continue
        except ImportError:
            pass

    async def load_plugin(self, name: str, config: Optional[Dict] = None) -> BasePlugin:
        """Load and initialize a plugin by name."""
        if name in self._plugins:
            return self._plugins[name]

        cls = self._plugin_classes.get(name)
        if not cls:
            raise ValueError(
                f"Plugin '{name}' not found. Available: {list(self._plugin_classes.keys())}"
            )

        plugin = cls(config=config)
        await plugin.initialize()
        self._plugins[name] = plugin
        return plugin

    async def unload_plugin(self, name: str) -> None:
        """Unload and shutdown a plugin."""
        plugin = self._plugins.pop(name, None)
        if plugin:
            await plugin.shutdown()

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a loaded plugin."""
        return self._plugins.get(name)

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """Get all loaded plugins of a specific type."""
        return [
            p
            for p in self._plugins.values()
            if hasattr(p, "meta") and p.meta.plugin_type == plugin_type
        ]

    def list_plugins(self) -> List[Dict[str, str]]:
        """List all available plugins (both registered and loaded)."""
        result = []
        for name, cls in self._plugin_classes.items():
            meta = cls.meta if hasattr(cls, "meta") else None
            result.append(
                {
                    "name": name,
                    "type": meta.plugin_type.value if meta else "unknown",
                    "description": meta.description if meta else "",
                    "loaded": name in self._plugins,
                }
            )
        return result

    async def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        for name in list(self._plugins.keys()):
            await self.unload_plugin(name)
