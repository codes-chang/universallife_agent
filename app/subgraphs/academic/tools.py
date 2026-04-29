"""Academic 子图工具定义"""

from ...tools.base import ToolResult
from ...core.config import settings


async def search_github(query: str, max_results: int = 5) -> ToolResult:
    """搜索 GitHub 仓库"""
    from ...services.academic_service import get_academic_service

    service = get_academic_service()
    result = await service.search_github(query, max_results=max_results)

    return ToolResult(
        success=True,
        data=result,
        source=result.get("source", "github")
    )


async def search_arxiv(query: str, max_results: int = 5) -> ToolResult:
    """搜索 arXiv 论文"""
    from ...services.academic_service import get_academic_service

    service = get_academic_service()
    result = await service.search_arxiv(query, max_results=max_results)

    return ToolResult(
        success=True,
        data=result,
        source=result.get("source", "arxiv")
    )
