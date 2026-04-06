"""
Agent engine - the core orchestrator for social media operations.

Coordinates plugins, LLM, content generation, and scheduling
to provide a unified agent experience.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import Settings
from .content import ContentEngine, ContentRequest, GeneratedContent
from .llm import BaseLLMAdapter, create_llm_adapter
from .plugin import (
    BaseAnalyzerPlugin,
    BasePlatformPlugin,
    PluginManager,
    PluginType,
)
from .scheduler import TaskScheduler

logger = logging.getLogger(__name__)


@dataclass
class TrendingTopic:
    """A trending topic from any platform."""

    platform: str
    title: str
    hot_score: int = 0
    url: str = ""
    summary: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    """Result of a publish operation."""

    platform: str
    success: bool
    post_id: str = ""
    url: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisReport:
    """Analysis report for social media performance."""

    period: str = "7d"
    platforms: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    total_posts: int = 0
    total_engagement: int = 0
    recommendations: List[str] = field(default_factory=list)


class SocialAgent:
    """
    AI-powered social media operations agent.

    Main entry point for the framework. Orchestrates all capabilities:
    - Monitor trending topics across platforms
    - Generate AI-powered content
    - Publish to multiple platforms
    - Analyze performance
    - Schedule automated workflows
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.load()
        self.settings.ensure_data_dir()

        # Core components
        self.plugin_manager = PluginManager()
        self.llm: BaseLLMAdapter = create_llm_adapter(self.settings.llm)
        self.content_engine = ContentEngine(self.llm)
        self.scheduler = TaskScheduler(self.settings.scheduler.max_workers)

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the agent and all plugins."""
        if self._initialized:
            return

        # Discover and load plugins
        self.plugin_manager.discover_plugins()

        # Load enabled platform plugins
        for name, platform_config in self.settings.platforms.items():
            if platform_config.enabled:
                try:
                    await self.plugin_manager.load_plugin(
                        name,
                        config={"cookie": platform_config.cookie, **platform_config.extra},
                    )
                    logger.info(f"Platform plugin '{name}' loaded")
                except Exception as e:
                    logger.warning(f"Failed to load platform plugin '{name}': {e}")

        self._initialized = True
        logger.info("SocialAgent initialized")

    async def shutdown(self) -> None:
        """Shutdown the agent."""
        self.scheduler.stop()
        await self.plugin_manager.shutdown_all()
        if hasattr(self.llm, "close"):
            await self.llm.close()
        self._initialized = False
        logger.info("SocialAgent shutdown")

    # --- Trending / Monitor ---

    async def get_trending(
        self, platform: Optional[str] = None, limit: int = 10
    ) -> List[TrendingTopic]:
        """Get trending topics from platform(s)."""
        topics = []

        if platform:
            platforms = [platform]
        else:
            platforms = [
                p.meta.name for p in self.plugin_manager.get_plugins_by_type(PluginType.PLATFORM)
            ]

        for pname in platforms:
            plugin = self.plugin_manager.get_plugin(pname)
            if not isinstance(plugin, BasePlatformPlugin):
                continue
            try:
                raw_trending = await plugin.get_trending(limit=limit)
                for item in raw_trending:
                    topics.append(
                        TrendingTopic(
                            platform=pname,
                            title=item.get("title", item.get("word", "")),
                            hot_score=item.get("hot_score", item.get("num", 0)),
                            url=item.get("url", ""),
                            summary=item.get("summary", item.get("description", "")),
                            raw_data=item,
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to get trending from {pname}: {e}")

        # Sort by hot score
        topics.sort(key=lambda t: t.hot_score, reverse=True)
        return topics[:limit]

    async def monitor_and_alert(self, keywords: List[str], check_interval: int = 300) -> None:
        """Monitor trending topics for specific keywords and alert."""
        while True:
            trending = await self.get_trending(limit=50)
            matches = [t for t in trending if any(kw.lower() in t.title.lower() for kw in keywords)]
            if matches:
                logger.info(f"🔥 Found {len(matches)} trending matches for {keywords}")
                for match in matches:
                    logger.info(f"  [{match.platform}] {match.title} (score: {match.hot_score})")

            await asyncio.sleep(check_interval)

    # --- Content Generation ---

    async def create_content(
        self,
        topic: str,
        platforms: Optional[List[str]] = None,
        style: str = "professional",
        keywords: Optional[List[str]] = None,
        **kwargs,
    ) -> List[GeneratedContent]:
        """Generate content for one or more platforms."""
        if not platforms:
            platforms = list(self.settings.platforms.keys())

        request = ContentRequest(
            topic=topic,
            platforms=platforms,
            style=style,
            keywords=keywords or [],
            **kwargs,
        )
        return await self.content_engine.generate(request)

    async def create_and_publish(
        self,
        topic: str,
        platforms: Optional[List[str]] = None,
        style: str = "professional",
        **kwargs,
    ) -> List[PublishResult]:
        """Generate content and publish to platforms in one step."""
        contents = await self.create_content(topic, platforms, style, **kwargs)
        results = []

        for content in contents:
            result = await self.publish(content.platform, content.text, hashtags=content.hashtags)
            results.append(result)

        return results

    # --- Publishing ---

    async def publish(
        self,
        platform: str,
        text: str,
        hashtags: Optional[List[str]] = None,
        images: Optional[List[str]] = None,
        **kwargs,
    ) -> PublishResult:
        """Publish content to a specific platform."""
        plugin = self.plugin_manager.get_plugin(platform)
        if not plugin:
            return PublishResult(
                platform=platform,
                success=False,
                error=f"Platform '{platform}' not loaded",
            )

        if not isinstance(plugin, BasePlatformPlugin):
            return PublishResult(
                platform=platform,
                success=False,
                error=f"Plugin '{platform}' is not a platform plugin",
            )

        try:
            # Add hashtags to text if provided
            if hashtags:
                hash_text = " ".join(f"#{tag}" for tag in hashtags)
                if not text.endswith(hash_text):
                    text = f"{text}\n\n{hash_text}"

            result = await plugin.publish(text=text, images=images or [], **kwargs)
            return PublishResult(
                platform=platform,
                success=True,
                post_id=result.get("id", ""),
                url=result.get("url", ""),
                metadata=result,
            )
        except Exception as e:
            return PublishResult(
                platform=platform,
                success=False,
                error=str(e),
            )

    # --- Search ---

    async def search(
        self, keyword: str, platform: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for content across platforms."""
        results = []

        if platform:
            platforms = [platform]
        else:
            platforms = [
                p.meta.name for p in self.plugin_manager.get_plugins_by_type(PluginType.PLATFORM)
            ]

        for pname in platforms:
            plugin = self.plugin_manager.get_plugin(pname)
            if isinstance(plugin, BasePlatformPlugin):
                try:
                    items = await plugin.search(keyword, limit=limit)
                    for item in items:
                        item["_platform"] = pname
                    results.extend(items)
                except Exception as e:
                    logger.error(f"Search failed on {pname}: {e}")

        return results

    # --- Analysis ---

    async def analyze(self, platform: str = "", period: str = "7d") -> AnalysisReport:
        """Analyze social media performance."""
        report = AnalysisReport(period=period)

        analyzers = self.plugin_manager.get_plugins_by_type(PluginType.ANALYZER)
        for analyzer in analyzers:
            if isinstance(analyzer, BaseAnalyzerPlugin):
                try:
                    insights = await analyzer.get_insights(platform, period)
                    report.platforms[platform or "all"] = insights
                except Exception as e:
                    logger.error(f"Analysis failed: {e}")

        # Use LLM to generate recommendations
        if report.platforms:
            prompt = f"Based on the following social media analytics data, provide 3 actionable recommendations in Chinese:\n{report.platforms}"
            try:
                recs = await self.llm.simple_chat(prompt)
                report.recommendations = [
                    line.strip().lstrip("0123456789.-) ")
                    for line in recs.strip().split("\n")
                    if line.strip()
                ][:5]
            except Exception:
                report.recommendations = ["数据不足，建议继续积累"]

        return report

    # --- Scheduled Workflows ---

    def schedule_daily_post(
        self,
        task_id: str,
        topic: str,
        platforms: List[str],
        hour: int = 9,
        minute: int = 0,
        style: str = "professional",
    ) -> None:
        """Schedule a daily content generation and publishing task."""

        async def task():
            await self.create_and_publish(topic, platforms, style)

        self.scheduler.add_task(
            task_id=task_id,
            name=f"Daily post: {topic}",
            func=task,
            cron=f"{minute} {hour} * * *",
        )

    def schedule_trending_monitor(
        self,
        task_id: str,
        keywords: List[str],
        interval_minutes: int = 30,
    ) -> None:
        """Schedule a trending topic monitor."""

        async def task():
            trending = await self.get_trending(limit=50)
            matches = [t for t in trending if any(kw.lower() in t.title.lower() for kw in keywords)]
            if matches:
                for match in matches:
                    logger.info(
                        f"Trending alert: [{match.platform}] {match.title} "
                        f"(score: {match.hot_score})"
                    )

        self.scheduler.add_task(
            task_id=task_id,
            name=f"Trending monitor: {keywords}",
            func=task,
            interval_seconds=interval_minutes * 60,
        )

    # --- Info ---

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "initialized": self._initialized,
            "llm_provider": self.settings.llm.provider,
            "llm_model": self.settings.llm.model,
            "loaded_plugins": self.plugin_manager.list_plugins(),
            "scheduled_tasks": self.scheduler.list_tasks(),
            "platforms": list(self.settings.platforms.keys()),
        }
