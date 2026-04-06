"""
Weibo platform plugin - full-featured Weibo integration.

Supports: read (trending, search, user posts), write (publish, repost, comment, like)
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ..plugin import (
    ActionScope,
    BasePlatformPlugin,
    PluginMeta,
    PluginType,
)

logger = logging.getLogger(__name__)

# Weibo API endpoints
WEIBO_API = {
    "trending": "https://weibo.com/ajax/side/hotSearch",
    "search": "https://s.weibo.com/weibo",
    "user_info": "https://weibo.com/ajax/statuses/mymblog",
    "publish": "https://weibo.com/ajax/statuses/update",
    "repost": "https://weibo.com/ajax/statuses/repost",
    "comment": "https://weibo.com/ajax/comments/create",
    "like": "https://weibo.com/ajax/statuses/like",
    "upload_image": "https://picupload.weibo.com/interface/pic_upload.php",
}

# Mobile API endpoints (more stable)
WEIBO_MOBILE_API = {
    "trending": "https://m.weibo.cn/api/container/getIndex?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot",
}


class WeiboPlugin(BasePlatformPlugin):
    """
    Full-featured Weibo platform plugin.

    Features:
    - Read: trending topics, search, user posts, comments
    - Write: publish posts, repost, comment, like
    - Monitor: real-time trending alerts
    """

    meta = PluginMeta(
        name="weibo",
        version="0.1.0",
        description="Full-featured Weibo integration - read, write, monitor, and analyze",
        plugin_type=PluginType.PLATFORM,
        author="zouyongfu",
        homepage="https://github.com/zouyongfu/social-agent",
        supported_actions=[
            ActionScope.READ,
            ActionScope.WRITE,
            ActionScope.INTERACT,
            ActionScope.ANALYZE,
        ],
        tags=["weibo", "微博", "social-media", "china"],
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._cookie = config.get("cookie", "") if config else ""
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://weibo.com/",
            "Accept": "application/json, text/plain, */*",
        }
        if self._cookie:
            self._headers["Cookie"] = self._cookie

        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    headers=self._headers,
                    timeout=30.0,
                    follow_redirects=True,
                )
            except ImportError:
                raise ImportError("httpx is required. Install with: pip install httpx")
        return self._client

    async def initialize(self) -> None:
        await super().initialize()
        client = await self._get_client()

        # Test authentication
        auth_valid = await self.verify_auth()
        if not auth_valid:
            logger.warning("Weibo authentication may be invalid. Check your cookie.")

    async def verify_auth(self) -> bool:
        """Verify Weibo cookie is still valid."""
        try:
            client = await self._get_client()
            resp = await client.get("https://weibo.com/ajax/statuses/mymblog", params={"page": 1})
            data = resp.json()

            # If we get data back, we're authenticated
            if data.get("data") is not None:
                return True

            # Check for specific error codes
            if data.get("ok") == 0:
                return False

            return True
        except Exception as e:
            logger.error(f"Weibo auth verification failed: {e}")
            return False

    async def get_trending(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch Weibo hot search trending topics."""
        client = await self._get_client()

        # Try desktop API first
        try:
            resp = await client.get(WEIBO_API["trending"])
            data = resp.json()

            if data.get("ok") == 1 and "data" in data:
                realtime = data["data"].get("realtime", [])
                results = []
                for item in realtime[:limit]:
                    word = item.get("word", "")
                    # Remove emoji tags
                    word = re.sub(r'<[^>]+>', '', word)
                    results.append({
                        "title": word,
                        "hot_score": item.get("num", 0),
                        "url": f"https://s.weibo.com/weibo?q=%23{word}%23",
                        "label": item.get("label_name", ""),
                        "category": item.get("category", ""),
                        "raw_data": item,
                    })
                return results
        except Exception as e:
            logger.debug(f"Desktop trending API failed: {e}")

        # Fallback to mobile API
        try:
            resp = await client.get(WEIBO_MOBILE_API["trending"])
            data = resp.json()

            if data.get("ok") == 1:
                cards = data.get("data", {}).get("cards", [])
                card_group = []
                for card in cards:
                    if card.get("card_group"):
                        card_group.extend(card["card_group"])

                results = []
                for item in card_group[:limit]:
                    desc = item.get("desc", "")
                    results.append({
                        "title": desc,
                        "hot_score": item.get("pic_num", 0),
                        "url": item.get("scheme", ""),
                        "label": item.get("card_addition", {}).get("title", "") if item.get("card_addition") else "",
                    })
                return results
        except Exception as e:
            logger.error(f"Mobile trending API also failed: {e}")

        return []

    async def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for posts on Weibo."""
        client = await self._get_client()

        try:
            params = {
                "q": keyword,
                "typeall": 1,
                "suball": 1,
                "timescope": "custom:2026-01-01:2026-12-31",
                "page": 1,
            }
            resp = await client.get(WEIBO_API["search"], params=params)
            # Parse HTML response for search results
            html = resp.text

            results = []
            # Extract post data from HTML
            posts = re.findall(r'<div class="card-wrap[^"]*"(.*?)</div>\s*</div>', html, re.DOTALL)
            for post_html in posts[:limit]:
                text_match = re.search(r'<p[^>]*class="txt"[^>]*>(.*?)</p>', post_html, re.DOTALL)
                author_match = re.search(r'<a[^>]*class="name"[^>]*>(.*?)</a>', post_html)
                if text_match:
                    text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()
                    author = author_match.group(1).strip() if author_match else ""
                    results.append({
                        "title": text[:100],
                        "text": text,
                        "author": author,
                        "platform": "weibo",
                    })

            return results
        except Exception as e:
            logger.error(f"Weibo search failed: {e}")
            return []

    async def publish(self, text: str, images: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Publish a new post to Weibo.

        Args:
            text: Post content
            images: Optional list of image URLs or file paths to upload

        Returns:
            Dict with post id and URL
        """
        client = await self._get_client()

        if not self._cookie:
            raise ValueError("Weibo cookie not configured. Cannot publish.")

        # Upload images if provided
        pic_ids = []
        if images:
            for img in images:
                pic_id = await self._upload_image(client, img)
                if pic_id:
                    pic_ids.append(pic_id)

        payload: Dict[str, Any] = {
            "content": text,
            "visible": 0,  # Public
            "share_id": "",
            "utf8": "",
        }

        if pic_ids:
            payload["pic_ids"] = json.dumps(pic_ids)

        resp = await client.post(WEIBO_API["publish"], data=payload)
        data = resp.json()

        if data.get("ok") == 1:
            post_id = data.get("data", {}).get("mid", "")
            return {
                "id": post_id,
                "url": f"https://weibo.com/detail/{post_id}" if post_id else "",
            }
        else:
            raise Exception(f"Weibo publish failed: {data.get('msg', 'Unknown error')}")

    async def repost(self, post_id: str, comment: str = "", **kwargs) -> Dict[str, Any]:
        """
        Repost a Weibo post.

        Args:
            post_id: The post ID to repost
            comment: Optional comment to add

        Returns:
            Dict with result info
        """
        client = await self._get_client()

        payload = {
            "id": post_id,
            "comment": comment,
            "dualPost": 0,
        }

        resp = await client.post(WEIBO_API["repost"], data=payload)
        data = resp.json()

        if data.get("ok") == 1:
            return {"id": data.get("data", {}).get("mid", ""), "success": True}
        else:
            raise Exception(f"Weibo repost failed: {data.get('msg', 'Unknown error')}")

    async def comment(self, post_id: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Comment on a Weibo post.

        Args:
            post_id: The post ID to comment on
            content: Comment content

        Returns:
            Dict with comment info
        """
        client = await self._get_client()

        payload = {
            "id": post_id,
            "comment": content,
        }

        resp = await client.post(WEIBO_API["comment"], data=payload)
        data = resp.json()

        if data.get("ok") == 1:
            return {"id": str(data.get("data", "")), "success": True}
        else:
            raise Exception(f"Weibo comment failed: {data.get('msg', 'Unknown error')}")

    async def like(self, post_id: str, **kwargs) -> Dict[str, Any]:
        """
        Like a Weibo post.

        Args:
            post_id: The post ID to like

        Returns:
            Dict with result info
        """
        client = await self._get_client()

        payload = {
            "id": post_id,
        }

        resp = await client.post(WEIBO_API["like"], data=payload)
        data = resp.json()

        if data.get("ok") == 1:
            return {"success": True}
        else:
            raise Exception(f"Weibo like failed: {data.get('msg', 'Unknown error')}")

    async def get_user_posts(self, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """Get current user's posts."""
        client = await self._get_client()

        try:
            resp = await client.get(
                WEIBO_API["user_info"],
                params={"page": page, "feature": 0},
            )
            data = resp.json()

            posts = []
            if data.get("data", {}).get("list"):
                for item in data["data"]["list"][:limit]:
                    posts.append({
                        "id": item.get("id", ""),
                        "text": item.get("text_raw", item.get("text", "")),
                        "created_at": item.get("created_at", ""),
                        "reposts_count": item.get("reposts_count", 0),
                        "comments_count": item.get("comments_count", 0),
                        "attitudes_count": item.get("attitudes_count", 0),
                        "source": item.get("source", ""),
                    })
            return posts
        except Exception as e:
            logger.error(f"Failed to get user posts: {e}")
            return []

    async def _upload_image(self, client, image_source: str) -> Optional[str]:
        """Upload an image to Weibo and return pic_id."""
        try:
            import httpx

            files = {}
            if image_source.startswith(("http://", "https://")):
                # Download image first
                img_resp = await client.get(image_source)
                if img_resp.status_code == 200:
                    files = {"pic": ("image.jpg", img_resp.content, "image/jpeg")}
            else:
                # Local file
                with open(image_source, "rb") as f:
                    files = {"pic": ("image.jpg", f.read(), "image/jpeg")}

            if not files:
                return None

            resp = await client.post(
                WEIBO_API["upload_image"],
                data={"type": "ajax", "json": "1"},
                files=files,
            )
            data = resp.json()
            return data.get("data", {}).get("pics", {}).get("pic_1", {}).get("pid", "")
        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            return None

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        await super().shutdown()
