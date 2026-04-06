<div align="center">

# Social Agent

**AI-Powered Social Media Operations Framework**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](pyproject.toml)

Monitor, create, distribute, and analyze social media content across platforms — all powered by AI.

**English** | [中文](#中文介绍)

</div>

---

## What is Social Agent?

Social Agent is an open-source AI framework that automates social media operations across Chinese social platforms. It integrates LLM-powered content generation, multi-platform publishing, trending monitoring, and performance analytics into one unified framework.

**Core idea**: Write once, publish everywhere. Let AI handle the heavy lifting.

```
┌─────────────────────────────────────────────────────────┐
│                    Social Agent                          │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Monitor  │  │   Generate   │  │    Analyze        │  │
│  │ Trending │──│   Content    │──│   Performance     │  │
│  └────┬─────┘  └──────┬───────┘  └─────────┬─────────┘  │
│       │               │                    │             │
│  ┌────▼───────────────▼────────────────────▼─────────┐   │
│  │              Plugin System                         │   │
│  │  ┌────────┐ ┌─────────┐ ┌───────┐ ┌───────────┐  │   │
│  │  │ Weibo  │ │ Xiaohu  │ │Douyin │ │ Bilibili  │  │   │
│  │  │ 微博   │ │ 小红书  │ │ 抖音  │ │ B站       │  │   │
│  │  └────────┘ └─────────┘ └───────┘ └───────────┘  │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  LLM Layer: OpenAI | Claude | Qwen | GLM | Ollama│    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Features

- 🔥 **Trending Monitor** — Real-time trending topics from Weibo, Xiaohongshu, Douyin, Bilibili
- ✍️ **AI Content Generation** — Generate platform-specific content with style adaptation
- 📤 **Multi-Platform Publishing** — Create once, publish to multiple platforms
- 🔍 **Content Search** — Search across platforms in one unified interface
- 📊 **Performance Analytics** — Track and analyze your social media performance
- ⏰ **Scheduled Workflows** — Cron-based task scheduling for automated operations
- 🔌 **Plugin System** — Extensible architecture, community plugins welcome
- 🤖 **Multi-LLM Support** — OpenAI, Claude, Qwen, GLM, Ollama, and more

## Quick Start

### Installation

```bash
# Clone the repo
git clone https://github.com/zouyongfu/social-agent.git
cd social-agent

# Install with Weibo support (default)
pip install -e .

# Install with specific platform support
pip install -e ".[weibo]"        # Weibo
pip install -e ".[xiaohongshu]"  # Xiaohongshu
pip install -e ".[bilibili]"     # Bilibili
pip install -e ".[all]"          # All platforms

# For development
pip install -e ".[dev]"
```

### Configuration

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# LLM Provider (openai / claude / dashscope / zhipu / ollama)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# Or use free Chinese alternatives:
# LLM_PROVIDER=dashscope
# DASHSCOPE_API_KEY=sk-your-key-here

# Weibo cookie (required for reading trending + publishing)
WEIBO_COOKIE=your_weibo_cookie_here
```

### Basic Usage

**CLI Commands:**

```bash
# Check status
social-agent status

# Get trending topics
social-agent trending
social-agent trending --platform weibo --limit 20

# Generate content
social-agent generate --topic "AI tools for productivity" --platform weibo --style casual

# Generate for multiple platforms
social-agent generate -t "Today's tech news" -p weibo -p xiaohongshu

# Search across platforms
social-agent search --keyword "人工智能" --platform weibo

# Publish content
social-agent publish --topic "My thoughts on AI" --platform weibo
social-agent publish -t "AI review" -p weibo -p xiaohongshu --dry-run
```

**Python API:**

```python
import asyncio
from social_agent import SocialAgent, Settings

async def main():
    # Initialize agent
    settings = Settings.load()
    agent = SocialAgent(settings)
    await agent.initialize()

    # Monitor trending
    trending = await agent.get_trending(platform="weibo", limit=10)
    for topic in trending:
        print(f"🔥 {topic.title} (score: {topic.hot_score})")

    # Generate content for multiple platforms
    contents = await agent.create_content(
        topic="AI makes coding 10x faster",
        platforms=["weibo", "xiaohongshu"],
        style="casual",
        keywords=["AI", "效率", "编程"],
    )

    # Publish to all platforms
    for content in contents:
        result = await agent.publish(
            platform=content.platform,
            text=content.text,
            hashtags=content.hashtags,
        )
        print(f"{'✅' if result.success else '❌'} {content.platform}")

    await agent.shutdown()

asyncio.run(main())
```

### Cross-Platform Content Adaptation

```python
# Adapt content from one platform style to another
adapted = await agent.content_engine.adapt(
    content="Original Weibo post text here...",
    from_platform="weibo",
    to_platform="xiaohongshu",
)
print(adapted.text)  # Now in Xiaohongshu style
```

### Scheduled Automated Workflows

```python
# Daily post at 9 AM
agent.schedule_daily_post(
    task_id="morning_post",
    topic="每日科技资讯",
    platforms=["weibo"],
    hour=9,
    minute=0,
)

# Monitor trending every 30 minutes
agent.schedule_trending_monitor(
    task_id="trending_alert",
    keywords=["AI", "大模型", "GPT"],
    interval_minutes=30,
)

# Start the scheduler loop
await agent.scheduler.start()
```

## Architecture

```
social-agent/
├── src/social_agent/
│   ├── __init__.py          # Package init
│   ├── agent.py             # Core Agent orchestrator
│   ├── config.py            # Configuration management
│   ├── content.py           # Content generation engine
│   ├── llm.py               # LLM adapter layer
│   ├── plugin.py            # Plugin system
│   ├── scheduler.py         # Task scheduler
│   ├── cli.py               # Command-line interface
│   └── plugins/
│       ├── weibo/           # Weibo platform plugin
│       └── xiaohongshu/     # Xiaohongshu platform plugin
├── examples/                # Usage examples
├── tests/                   # Test suite
├── pyproject.toml           # Project config
└── .env.example             # Environment template
```

### Key Design Decisions

| Design | Rationale |
|--------|-----------|
| **Plugin-based** | Each platform is a self-contained plugin, easy to add/remove |
| **Async-first** | Built on asyncio for efficient concurrent operations |
| **Multi-LLM** | Not locked to any single provider, works with OpenAI/Claude/Qwen/GLM/Ollama |
| **No browser dependency** | Core reads via HTTP API, browser automation optional for publishing |

## Supported Platforms

| Platform | Read (Trending/Search) | Write (Publish) | Status |
|----------|:---:|:---:|--------|
| 微博 Weibo | ✅ | ✅ | Full support |
| 小红书 Xiaohongshu | ✅ | 🔄 | Read ready, publish via companion |
| 抖音 Douyin | 🔄 | 🔄 | Planned |
| B站 Bilibili | 🔄 | 🔄 | Planned |
| 知乎 Zhihu | 🔄 | 🔄 | Planned |

## LLM Providers

| Provider | Models | Setup |
|----------|--------|-------|
| OpenAI | GPT-4o, GPT-4o-mini | Set `OPENAI_API_KEY` |
| Anthropic Claude | Claude 3.5 Sonnet | Set `CLAUDE_API_KEY` |
| DashScope (Qwen) | Qwen-Plus, Qwen-Max | Set `DASHSCOPE_API_KEY`, free tier available |
| Zhipu (GLM) | GLM-4-Flash, GLM-4 | Set `ZHIPU_API_KEY`, free tier available |
| Ollama (Local) | Any local model | Set `OLLAMA_BASE_URL`, fully offline |

> 💡 For Chinese users, **DashScope (Qwen)** or **Zhipu (GLM)** offer free tiers and work great out of the box.

## Create Your Own Plugin

```python
from social_agent.plugin import BasePlatformPlugin, PluginMeta, PluginType, ActionScope

class DouyinPlugin(BasePlatformPlugin):
    meta = PluginMeta(
        name="douyin",
        version="0.1.0",
        description="Douyin (TikTok China) platform integration",
        plugin_type=PluginType.PLATFORM,
        supported_actions=[ActionScope.READ, ActionScope.WRITE],
        tags=["douyin", "tiktok", "china"],
    )

    async def verify_auth(self) -> bool:
        # Your auth check logic
        return True

    async def get_trending(self, limit: int = 10):
        # Your trending fetch logic
        return [{"title": "...", "hot_score": 1000}]

    async def search(self, keyword: str, limit: int = 20):
        # Your search logic
        return []

    async def publish(self, text: str, **kwargs):
        # Your publish logic
        return {"id": "...", "url": "..."}
```

## Roadmap

- [ ] **v0.2** — Douyin plugin, Bilibili plugin
- [ ] **v0.3** — MCP Server integration (use with Claude/Cursor)
- [ ] **v0.4** — Web dashboard for monitoring and analytics
- [ ] **v0.5** — Community plugin marketplace
- [ ] **v1.0** — Stable release with full multi-platform support

## Contributing

Contributions are welcome! Here's how you can help:

1. **New Platform Plugins** — Add support for Douyin, Bilibili, Zhihu, etc.
2. **Content Templates** — Share platform-specific content templates
3. **Analyzer Plugins** — Build analytics and reporting tools
4. **Documentation** — Improve guides, add tutorials
5. **Bug Reports** — Found a bug? Open an issue!

### Development Setup

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

[MIT](LICENSE) — Free for personal and commercial use.

---

<div align="center">

**Made with ❤️ by [zouyongfu](https://github.com/zouyongfu)**

If you find this project useful, please give it a ⭐!

</div>

---

## 中文介绍

### Social Agent 是什么？

Social Agent 是一个开源的 AI 社交媒体运营框架，支持一键监控热点、AI 生成内容、多平台分发、数据分析。

**核心理念**：写一次，发到处。让 AI 帮你搞定社交媒体运营。

### 核心功能

- 🔥 **热点监控** — 实时获取微博、小红书、抖音、B站热搜
- ✍️ **AI 内容生成** — 根据主题自动生成平台适配的内容
- 📤 **多平台发布** — 一条内容，自动适配多个平台风格并发布
- 🔍 **跨平台搜索** — 统一搜索接口，一次搜索覆盖所有平台
- 📊 **数据分析** — 追踪各平台运营数据，AI 生成优化建议
- ⏰ **定时任务** — 定时发博、定时监控热搜
- 🔌 **插件化架构** — 每个平台都是独立插件，社区可扩展
- 🤖 **多模型支持** — 支持 GPT、Claude、通义千问、智谱GLM、Ollama

### 快速上手

```bash
git clone https://github.com/zouyongfu/social-agent.git
cd social-agent
pip install -e ".[weibo]"
cp .env.example .env
# 编辑 .env 填入你的 API Key 和 Cookie
social-agent status
social-agent trending
```

### 使用场景

1. **自媒体运营** — AI 自动生成内容，定时发布到多个平台
2. **品牌营销** — 监控品牌相关热搜，快速响应
3. **竞品分析** — 追踪竞品动态，分析运营策略
4. **个人品牌** — 一键分发，扩大影响力
5. **内容创作** — AI 辅助创作，提高产出效率
