"""搜索服务 - 使用 Tavily API"""

import httpx
from typing import Optional, Dict, Any, List

from ..core.config import settings
from ..core.logging import logger


class SearchService:
    """搜索服务

    提供网络搜索功能，使用 Tavily API。
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.tavily_api_key
        self.base_url = "https://api.tavily.com"

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic"
    ) -> Dict[str, Any]:
        """执行网络搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数
            search_depth: 搜索深度 (basic/advanced)

        Returns:
            搜索结果字典
        """
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY 未配置，无法执行搜索")

        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_answer": True,
                "include_raw_content": False
            }

            response = await client.post(f"{self.base_url}/search", json=payload)
            result = response.json()

            return {
                "query": query,
                "answer": result.get("answer", ""),
                "results": self._format_tavily_results(result.get("results", [])),
                "source": "tavily"
            }

    def _format_tavily_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """格式化 Tavily 搜索结果"""
        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "score": r.get("score", 0.0),
                "published_date": r.get("published_date", "")
            })
        return formatted

    def format_search_results(self, search_data: Dict[str, Any]) -> str:
        """格式化搜索结果为文本"""
        if not search_data:
            return "无搜索结果"

        parts = []

        if search_data.get("answer"):
            parts.append(f"摘要:\n{search_data['answer']}\n")

        results = search_data.get("results", [])
        if results:
            parts.append("搜索结果:\n")
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                date = r.get("published_date", "")

                parts.append(f"{i}. {title}")
                if date:
                    parts.append(f"   日期: {date}")
                parts.append(f"   链接: {url}")
                parts.append(f"   摘要: {snippet[:100]}...")
                parts.append("")

        return "\n".join(parts)


# ============ 全局实例 ============

_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """获取搜索服务实例"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
