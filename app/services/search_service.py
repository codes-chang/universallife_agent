"""搜索服务 - 使用 Tavily API"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.config import settings
from ..core.logging import logger
from ..tools.mocks import MockToolRegistry


class SearchService:
    """搜索服务

    提供网络搜索功能，支持 Tavily API 和 Mock 模式。
    """

    def __init__(self, api_key: str = None, mock_mode: bool = None):
        self.api_key = api_key or settings.tavily_api_key
        if mock_mode is None:
            self.mock_mode = settings.mock_mode
        else:
            self.mock_mode = mock_mode

        self.base_url = "https://api.tavily.com"

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic"
    ) -> Dict[str, Any]:
        """
        执行网络搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数
            search_depth: 搜索深度 (basic/advanced)

        Returns:
            搜索结果字典
        """
        if self.mock_mode or not self.api_key:
            return await self._mock_search(query, max_results)

        try:
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

                if result.get("answer"):
                    return {
                        "query": query,
                        "answer": result.get("answer", ""),
                        "results": self._format_tavily_results(result.get("results", [])),
                        "source": "tavily"
                    }
                else:
                    return {
                        "query": query,
                        "answer": "",
                        "results": self._format_tavily_results(result.get("results", [])),
                        "source": "tavily"
                    }

        except Exception as e:
            logger.error(f"搜索异常: {e}")
            return await self._mock_search(query, max_results)

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

    async def _mock_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Mock 搜索"""
        mock_results = MockToolRegistry.get_search_mock(query)
        return {
            "query": query,
            "answer": f"这是关于 '{query}' 的模拟搜索摘要。根据搜索结果，{query} 是一个热门话题。",
            "results": mock_results[:max_results],
            "source": "mock"
        }

    def format_search_results(self, search_data: Dict[str, Any]) -> str:
        """格式化搜索结果为文本"""
        if not search_data:
            return "无搜索结果"

        parts = []

        if search_data.get("answer"):
            parts.append(f"📝 摘要:\n{search_data['answer']}\n")

        results = search_data.get("results", [])
        if results:
            parts.append("🔍 搜索结果:\n")
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                date = r.get("published_date", "")

                parts.append(f"{i}. {title}")
                if date:
                    parts.append(f"   📅 {date}")
                parts.append(f"   🔗 {url}")
                parts.append(f"   📄 {snippet[:100]}...")
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
