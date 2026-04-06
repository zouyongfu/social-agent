"""
Example: Monitor Weibo trending topics and auto-generate content.

Usage:
    python examples/monitor_trending.py
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from social_agent.config import Settings
from social_agent.agent import SocialAgent


async def main():
    # Load settings (reads from .env)
    settings = Settings.load()

    # Create agent
    agent = SocialAgent(settings)

    # Initialize (loads plugins)
    await agent.initialize()

    print("=== Social Agent Status ===")
    status = agent.get_status()
    print(f"LLM: {status['llm_provider']} / {status['llm_model']}")
    print(f"Platforms: {status['platforms']}")
    print(f"Plugins: {[p['name'] for p in status['loaded_plugins']]}")
    print()

    # Get trending topics
    print("=== Weibo Trending ===")
    trending = await agent.get_trending(platform="weibo", limit=10)
    for i, topic in enumerate(trending, 1):
        print(f"  {i}. {topic.title} (score: {topic.hot_score})")
    print()

    # Generate content based on top trending topic
    if trending:
        top_topic = trending[0].title
        print(f"=== Generating content for: {top_topic} ===")
        contents = await agent.create_content(
            topic=top_topic,
            platforms=["weibo"],
            style="casual",
        )
        for content in contents:
            print(f"\n[{content.platform}]")
            print(content.text)
            if content.hashtags:
                print(f"Tags: {' '.join('#' + t for t in content.hashtags)}")

    # Cleanup
    await agent.shutdown()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
