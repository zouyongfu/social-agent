"""Tests for social-agent core framework."""

import os
import pytest
import asyncio

# Add src to path
sys_path = os.path.join(os.path.dirname(__file__), "..", "src")
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)


class TestConfig:
    """Test configuration management."""

    def test_settings_load(self):
        from social_agent.config import Settings
        settings = Settings.load()
        assert settings is not None
        assert settings.llm.provider in ("openai", "claude", "dashscope", "zhipu", "ollama")

    def test_llm_config_from_env(self):
        from social_agent.config import LLMConfig
        # Test default
        config = LLMConfig.from_env()
        assert config.provider == "openai"

        # Test with env override
        os.environ["LLM_PROVIDER"] = "dashscope"
        config = LLMConfig.from_env()
        assert config.provider == "dashscope"
        assert config.model == "qwen-plus"
        os.environ.pop("LLM_PROVIDER", None)

    def test_settings_data_dir(self):
        from social_agent.config import Settings
        settings = Settings.load()
        data_dir = settings.ensure_data_dir()
        assert data_dir.exists()
        # Clean up
        data_dir.rmdir()

    def test_platform_config(self):
        from social_agent.config import PlatformConfig
        config = PlatformConfig(name="weibo", cookie="test")
        assert config.name == "weibo"
        assert config.enabled is True


class TestLLM:
    """Test LLM adapter layer."""

    def test_create_adapter_openai(self):
        from social_agent.llm import create_llm_adapter, OpenAIAdapter
        adapter = create_llm_adapter()
        assert isinstance(adapter, OpenAIAdapter)

    def test_create_adapter_claude(self):
        from social_agent.llm import create_llm_adapter, ClaudeAdapter, LLMConfig
        config = LLMConfig(provider="claude", api_key="test")
        adapter = create_llm_adapter(config)
        assert isinstance(adapter, ClaudeAdapter)

    def test_message_dataclass(self):
        from social_agent.llm import Message
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_llm_response_dataclass(self):
        from social_agent.llm import LLMResponse
        resp = LLMResponse(content="Hi", model="gpt-4")
        assert resp.content == "Hi"
        assert resp.model == "gpt-4"


class TestPlugin:
    """Test plugin system."""

    def test_plugin_meta(self):
        from social_agent.plugin import PluginMeta, PluginType, ActionScope
        meta = PluginMeta(
            name="test",
            plugin_type=PluginType.PLATFORM,
            supported_actions=[ActionScope.READ, ActionScope.WRITE],
        )
        assert meta.name == "test"
        assert meta.plugin_type == PluginType.PLATFORM
        assert len(meta.supported_actions) == 2

    def test_plugin_manager_register(self):
        from social_agent.plugin import PluginManager, BasePlugin, PluginMeta, PluginType

        class DummyPlugin(BasePlugin):
            meta = PluginMeta(name="dummy", plugin_type=PluginType.TOOL)

        pm = PluginManager()
        pm.register(DummyPlugin)

        plugins = pm.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "dummy"

    def test_plugin_manager_get_by_type(self):
        from social_agent.plugin import PluginManager, BasePlugin, PluginMeta, PluginType

        class ToolPlugin(BasePlugin):
            meta = PluginMeta(name="tool1", plugin_type=PluginType.TOOL)

        class PlatformPlugin(BasePlugin):
            meta = PluginMeta(name="plat1", plugin_type=PluginType.PLATFORM)

        pm = PluginManager()
        pm.register(ToolPlugin)
        pm.register(PlatformPlugin)

        # Get registered classes by type won't work without loading
        # This tests the registration itself
        assert len(pm.list_plugins()) == 2


class TestContentEngine:
    """Test content generation engine."""

    def test_platform_guides(self):
        from social_agent.content import PLATFORM_GUIDES
        assert "weibo" in PLATFORM_GUIDES
        assert "xiaohongshu" in PLATFORM_GUIDES
        assert "douyin" in PLATFORM_GUIDES
        assert "bilibili" in PLATFORM_GUIDES
        assert "zhihu" in PLATFORM_GUIDES

    def test_content_request(self):
        from social_agent.content import ContentRequest
        req = ContentRequest(
            topic="AI news",
            platforms=["weibo", "xiaohongshu"],
            style="casual",
            keywords=["AI", "科技"],
        )
        assert req.topic == "AI news"
        assert len(req.platforms) == 2
        assert len(req.keywords) == 2

    def test_generated_content(self):
        from social_agent.content import GeneratedContent
        content = GeneratedContent(
            platform="weibo",
            text="Test content",
            hashtags=["AI", "科技"],
            title="AI News",
        )
        assert content.platform == "weibo"
        assert len(content.hashtags) == 2

    def test_build_system_prompt(self):
        from social_agent.config import LLMConfig
        from social_agent.llm import OpenAIAdapter
        from social_agent.content import ContentEngine

        llm = OpenAIAdapter(LLMConfig())
        engine = ContentEngine(llm)
        prompt = engine._build_system_prompt("weibo", "casual")
        assert "weibo" in prompt
        assert "casual" in prompt


class TestScheduler:
    """Test task scheduler."""

    def test_add_task(self):
        from social_agent.scheduler import TaskScheduler

        async def dummy():
            pass

        scheduler = TaskScheduler()
        task = scheduler.add_task(
            task_id="test1",
            name="Test Task",
            func=dummy,
            interval_seconds=60,
        )
        assert task.id == "test1"
        assert task.name == "Test Task"

    def test_list_tasks(self):
        from social_agent.scheduler import TaskScheduler

        async def dummy():
            pass

        scheduler = TaskScheduler()
        scheduler.add_task("t1", "Task 1", dummy, interval_seconds=60)
        scheduler.add_task("t2", "Task 2", dummy, cron="0 9 * * *")

        tasks = scheduler.list_tasks()
        assert len(tasks) == 2

    def test_remove_task(self):
        from social_agent.scheduler import TaskScheduler

        async def dummy():
            pass

        scheduler = TaskScheduler()
        scheduler.add_task("t1", "Task 1", dummy)
        scheduler.remove_task("t1")
        assert len(scheduler.list_tasks()) == 0

    def test_enable_disable_task(self):
        from social_agent.scheduler import TaskScheduler

        async def dummy():
            pass

        scheduler = TaskScheduler()
        scheduler.add_task("t1", "Task 1", dummy)
        scheduler.enable_task("t1", enabled=False)
        assert scheduler.list_tasks()[0]["enabled"] is False


class TestAgent:
    """Test SocialAgent orchestrator."""

    def test_create_agent(self):
        from social_agent.config import Settings
        from social_agent.agent import SocialAgent

        settings = Settings.load()
        agent = SocialAgent(settings)
        status = agent.get_status()
        assert status["initialized"] is False
        assert "llm_provider" in status

    def test_trending_topic_dataclass(self):
        from social_agent.agent import TrendingTopic
        topic = TrendingTopic(
            platform="weibo",
            title="AI News",
            hot_score=10000,
        )
        assert topic.platform == "weibo"
        assert topic.hot_score == 10000

    def test_publish_result_dataclass(self):
        from social_agent.agent import PublishResult
        result = PublishResult(
            platform="weibo",
            success=True,
            post_id="123",
            url="https://weibo.com/detail/123",
        )
        assert result.success is True

    def test_analysis_report_dataclass(self):
        from social_agent.agent import AnalysisReport
        report = AnalysisReport(period="7d")
        assert report.period == "7d"
        assert report.total_posts == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
