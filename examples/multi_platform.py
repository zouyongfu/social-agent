"""
Example: Multi-platform content distribution.

Generate content once, adapt and distribute to multiple platforms.

Usage:
    python examples/multi_platform.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from social_agent.config import Settings
from social_agent.agent import SocialAgent


async def main():
    settings = Settings.load()
    agent = SocialAgent(settings)
    await agent.initialize()

    # Define a topic
    topic = "分享一个提高工作效率的小技巧"
    platforms = ["weibo", "xiaohongshu"]

    # Generate content for multiple platforms at once
    print(f"=== Generating content: {topic} ===")
    contents = await agent.create_content(
        topic=topic,
        platforms=platforms,
        style="casual",
        keywords=["效率", "工作", "技巧"],
    )

    for content in contents:
        print(f"\n--- {content.platform.upper()} ---")
        print(f"Title: {content.title}")
        print(f"Text: {content.text[:200]}...")
        print(f"Tags: {', '.join(content.hashtags)}")

    # Cross-platform content adaptation example
    print("\n\n=== Content Adaptation Example ===")
    sample_text = "今天发现了一个超好用的AI工具，能帮我自动写微博！简直是自媒体工作者的福音，每天能省出好几个小时。推荐给大家试试！"

    print(f"Original (weibo style):\n{sample_text}\n")

    adapted = await agent.content_engine.adapt(
        content=sample_text,
        from_platform="weibo",
        to_platform="xiaohongshu",
    )

    print(f"Adapted (xiaohongshu style):\n{adapted.text}")

    await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
