"""Search 子图工具定义"""

from ...tools.adapters import TavilySearchTool
from ...tools.base import ToolResult
from ...core.config import settings


def get_search_tools():
    """获取搜索子图的工具列表"""
    return [
        TavilySearchTool(api_key=settings.tavily_api_key)
    ]


async def execute_search(query: str, max_results: int = 5) -> ToolResult:
    """执行搜索（工具函数）"""
    from ...services.search_service import get_search_service

    service = get_search_service()
    result = await service.search(query, max_results=max_results)

    return ToolResult(
        success=True,
        data=result,
        source="tavily"
    )
