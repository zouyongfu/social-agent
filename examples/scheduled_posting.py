"""
Example: Scheduled automated posting workflow.

Usage:
    python examples/scheduled_posting.py
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

    # Schedule a daily post at 9:00 AM
    agent.schedule_daily_post(
        task_id="morning_post",
        topic="今日科技资讯分享",
        platforms=["weibo"],
        hour=9,
        minute=0,
        style="professional",
    )
    print("Scheduled daily post at 9:00 AM")

    # Schedule trending monitoring every 30 minutes
    agent.schedule_trending_monitor(
        task_id="trending_alert",
        keywords=["AI", "人工智能", "大模型"],
        interval_minutes=30,
    )
    print("Scheduled trending monitor every 30 minutes")

    # Show all scheduled tasks
    print("\n=== Scheduled Tasks ===")
    for task in agent.scheduler.list_tasks():
        print(f"  [{task['id']}] {task['name']}")
        print(f"    Schedule: {task['cron'] or f'every {task['interval_seconds']}s'}")
        print(f"    Enabled: {task['enabled']}")

    await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
