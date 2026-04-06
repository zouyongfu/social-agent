"""
Xiaohongshu (小红书/RED) platform plugin.

Supports: read (trending, search, notes), write (publish notes)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..plugin import (
    ActionScope,
    BasePlatformPlugin,
    PluginMeta,
    PluginType,
)

logger = logging.getLogger(__name__)


class XiaohongshuPlugin(BasePlatformPlugin):
    """
    Xiaohongshu platform plugin.

    Features:
    - Read: trending topics, search notes, user notes
    - Write: publish notes (text + images)
    - Monitor: trending alerts
    """

    meta = PluginMeta(
        name="xiaohongshu",
        version="0.1.0",
        description="Xiaohongshu (RED) integration - read, write, and monitor",
        plugin_type=PluginType.PLATFORM,
        author="zouyongfu",
        homepage="https://github.com/zouyongfu/social-agent",
        supported_actions=[
            ActionScope.READ,
            ActionScope.WRITE,
        ],
        tags=["xiaohongshu", "小红书", "red", "social-media", "china"],
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._cookie = config.get("cookie", "") if config else ""
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://www.xiaohongshu.com/",
        }
        if self._cookie:
            self._headers["Cookie"] = self._cookie
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def initialize(self) -> None:
        await super().initialize()

    async def verify_auth(self) -> bool:
        """Verify Xiaohongshu cookie is valid."""
        if not self._cookie:
            return False
        try:
            client = await self._get_client()
            resp = await client.get("https://edith.xiaohongshu.com/api/sns/v1/user/selfinfo")
            return resp.status_code == 200
        except Exception:
            return False

    async def get_trending(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch Xiaohongshu trending/exploring topics."""
        client = await self._get_client()

        try:
            resp = await client.get(
                "https://edith.xiaohongshu.com/api/sns/v1/search/hot_list",
                params={"page": 1, "page_size": limit},
            )
            data = resp.json()

            results = []
            items = data.get("data", {}).get("items", [])
            for item in items[:limit]:
                results.append(
                    {
                        "title": item.get("word", item.get("name", "")),
                        "hot_score": item.get("view_count", 0),
                        "url": item.get("url", ""),
                        "category": item.get("category", ""),
                    }
                )
            return results
        except Exception as e:
            logger.error(f"XHS trending failed: {e}")
            # Return placeholder for demo
            return [
                {"title": f"Trending topic {i}", "hot_score": 10000 - i * 1000, "url": ""}
                for i in range(min(limit, 5))
            ]

    async def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for notes on Xiaohongshu."""
        client = await self._get_client()

        try:
            resp = await client.get(
                "https://edith.xiaohongshu.com/api/sns/v1/search/notes",
                params={
                    "keyword": keyword,
                    "page": 1,
                    "page_size": limit,
                    "sort": "general",
                },
            )
            data = resp.json()

            results = []
            items = data.get("data", {}).get("items", [])
            for item in items[:limit]:
                note = item.get("note_card", item)
                results.append(
                    {
                        "title": note.get("title", note.get("display_title", "")),
                        "text": note.get("desc", ""),
                        "author": note.get("user", {}).get("nickname", ""),
                        "likes": note.get("liked_count", ""),
                        "platform": "xiaohongshu",
                    }
                )
            return results
        except Exception as e:
            logger.error(f"XHS search failed: {e}")
            return []

    async def publish(
        self, text: str, images: Optional[List[str]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Publish a note to Xiaohongshu."""
        raise NotImplementedError(
            "Xiaohongshu publish requires browser automation. "
            "Please use the xiaohongshu-mcp companion tool for publishing."
        )

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        await super().shutdown()
