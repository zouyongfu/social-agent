"""
Content generation engine - AI-powered content creation and adaptation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .llm import BaseLLMAdapter, Message, create_llm_adapter


# Platform-specific content guidelines
PLATFORM_GUIDES = {
    "weibo": {
        "max_length": 2000,
        "style": "concise, engaging, with hashtags",
        "tips": "Use 2-3 relevant hashtags, keep it under 140 chars for best engagement, add emojis sparingly",
        "content_types": ["text", "image+text", "video", "article"],
    },
    "xiaohongshu": {
        "max_length": 1000,
        "style": "lifestyle, authentic, detail-oriented, with emoji",
        "tips": "Use 5-8 relevant tags, add product/brand tags, include call-to-action",
        "content_types": ["image+text", "video"],
    },
    "douyin": {
        "max_length": 300,
        "style": "catchy, emotional, trending",
        "tips": "Hook in first 3 seconds, use trending sounds, add location tags",
        "content_types": ["short_video", "live"],
    },
    "bilibili": {
        "max_length": 2000,
        "style": "informative, entertaining, community-oriented",
        "tips": "Add timestamps for long videos, engage with danmaku, cross-post highlights",
        "content_types": ["long_video", "short_video", "article"],
    },
    "zhihu": {
        "max_length": 50000,
        "style": "knowledgeable, well-structured, evidence-based",
        "tips": "Cite sources, use structured formatting, add images/charts",
        "content_types": ["article", "answer", "video"],
    },
}


@dataclass
class ContentRequest:
    """Request for content generation."""

    topic: str
    platforms: List[str] = field(default_factory=lambda: ["weibo"])
    style: str = "professional"  # professional / casual / humorous / emotional
    tone: str = ""  # Custom tone description
    keywords: List[str] = field(default_factory=list)
    target_length: int = 0  # 0 = auto
    reference_text: str = ""  # Reference material to base content on
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedContent:
    """Generated content for a platform."""

    platform: str
    text: str
    hashtags: List[str] = field(default_factory=list)
    title: str = ""
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContentEngine:
    """
    AI-powered content generation and cross-platform adaptation engine.
    """

    def __init__(self, llm: Optional[BaseLLMAdapter] = None):
        self.llm = llm or create_llm_adapter()

    def _build_system_prompt(self, platform: str, style: str) -> str:
        """Build platform-specific system prompt."""
        guide = PLATFORM_GUIDES.get(platform, {})
        return f"""你是一位专业的社交媒体内容创作者，擅长为{platform}平台创作内容。

## 平台特征
- 最大长度: {guide.get('max_length', '2000')}字
- 风格: {guide.get('style', '自然流畅')}
- 支持的内容类型: {', '.join(guide.get('content_types', ['文本']))}
- 发布技巧: {guide.get('tips', '无特殊要求')}

## 写作风格
当前要求的风格: {style}

## 输出格式
请以JSON格式输出:
{{
    "text": "正文内容",
    "hashtags": ["话题标签1", "话题标签2"],
    "title": "标题（如适用）",
    "summary": "一句话摘要"
}}

注意:
- 正文内容要自然流畅，不要有AI痕迹
- 话题标签要热门且相关
- 根据平台特点调整内容长度和风格
- 只输出JSON，不要其他内容"""

    async def generate(self, request: ContentRequest) -> List[GeneratedContent]:
        """
        Generate content for one or more platforms.

        Args:
            request: Content generation request

        Returns:
            List of generated content, one per platform
        """
        results = []

        # First, generate a base idea/draft
        base_idea = await self._generate_base_idea(request)

        # Then adapt for each platform
        for platform in request.platforms:
            content = await self._generate_for_platform(request, platform, base_idea)
            results.append(content)

        return results

    async def _generate_base_idea(self, request: ContentRequest) -> str:
        """Generate a base content idea."""
        system = Message(
            role="system",
            content="你是一位创意策划师，擅长为社交媒体内容提供创意方向。请简洁地输出内容创意要点（100字以内）。",
        )
        user_content = f"主题: {request.topic}\n"
        if request.keywords:
            user_content += f"关键词: {', '.join(request.keywords)}\n"
        if request.reference_text:
            user_content += f"参考资料: {request.reference_text[:500]}\n"
        user_content += f"风格: {request.style}\n目标平台: {', '.join(request.platforms)}"

        return await self.llm.simple_chat(
            prompt=user_content,
            system=system.content,
        )

    async def _generate_for_platform(
        self, request: ContentRequest, platform: str, base_idea: str
    ) -> GeneratedContent:
        """Generate adapted content for a specific platform."""
        guide = PLATFORM_GUIDES.get(platform, {})
        max_len = request.target_length or guide.get("max_length", 2000)

        system_prompt = self._build_system_prompt(platform, request.style)

        user_content = f"""请根据以下创意方向，为{platform}平台创作一条内容:

## 创意方向
{base_idea}

## 要求
- 主题: {request.topic}
- 字数: 约{max_len}字
- 关键词: {', '.join(request.keywords) if request.keywords else '自动选择'}
"""

        if request.tone:
            user_content += f"- 语气要求: {request.tone}\n"

        raw_response = await self.llm.simple_chat(prompt=user_content, system=system_prompt)

        # Parse JSON response
        try:
            # Try to extract JSON from the response
            json_str = raw_response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())
            return GeneratedContent(
                platform=platform,
                text=data.get("text", raw_response),
                hashtags=data.get("hashtags", []),
                title=data.get("title", ""),
                summary=data.get("summary", ""),
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: return raw response as text
            return GeneratedContent(
                platform=platform,
                text=raw_response,
                hashtags=[request.topic],
            )

    async def adapt(self, content: str, from_platform: str, to_platform: str) -> GeneratedContent:
        """
        Adapt content from one platform style to another.

        Useful for cross-platform content distribution.
        """
        from_guide = PLATFORM_GUIDES.get(from_platform, {})
        to_guide = PLATFORM_GUIDES.get(to_platform, {})

        system = Message(
            role="system",
            content=f"""你是一位社交媒体内容改编专家。请将以下内容从{from_platform}的风格改编为{to_platform}的风格。

源平台特征: {from_guide.get('style', '')}
目标平台特征: {to_guide.get('style', '')}
目标平台最大长度: {to_guide.get('max_length', 2000)}字
目标平台技巧: {to_guide.get('tips', '')}

请以JSON格式输出:
{{"text": "改编后的内容", "hashtags": ["标签1", "标签2"]}}""",
        )

        raw = await self.llm.simple_chat(
            prompt=f"原始内容:\n{content}",
            system=system.content,
        )

        try:
            json_str = raw
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            data = json.loads(json_str.strip())
            return GeneratedContent(
                platform=to_platform,
                text=data.get("text", raw),
                hashtags=data.get("hashtags", []),
            )
        except (json.JSONDecodeError, KeyError):
            return GeneratedContent(platform=to_platform, text=raw)

    async def batch_generate_topics(self, niche: str, count: int = 5) -> List[str]:
        """Generate trending topic ideas for a given niche."""
        system = Message(
            role="system",
            content="你是一位社交媒体趋势分析师。请生成热门话题创意，每行一个，不要编号。",
        )
        prompt = f"请为以下领域生成{count}个适合在社交媒体上发布的话题创意:\n{niche}"

        raw = await self.llm.simple_chat(prompt=prompt, system=system.content)
        return [line.strip() for line in raw.strip().split("\n") if line.strip()]
