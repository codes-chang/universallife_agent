"""工具适配器 - MCP 和 API 工具的适配器实现"""

import json
from typing import Any, Dict, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .base import BaseTool, ToolResult, APITool


# ============ LangChain 工具适配器 ============

class LangChainToolAdapter(BaseTool):
    """LangChain StructuredTool 适配器

    将 LangChain 的 StructuredTool 包装为统一的 BaseTool 接口。
    """

    def __init__(self, langchain_tool: StructuredTool, mock_mode: bool = False):
        super().__init__(mock_mode=mock_mode)
        self._lc_tool = langchain_tool
        self._name = langchain_tool.name

    @property
    def description(self) -> str:
        return self._lc_tool.description

    @property
    def schema(self) -> Dict[str, Any]:
        # 从 LangChain 工具的 args_schema 提取 schema
        if hasattr(self._lc_tool, 'args_schema') and self._lc_tool.args_schema:
            return self._lc_tool.args_schema.model_json_schema()
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        """执行 LangChain 工具"""
        try:
            if self.mock_mode:
                return await self._mock_execute(**kwargs)

            # 调用 LangChain 工具
            if hasattr(self._lc_tool, 'acall'):
                result = await self._lc_tool.acall(**kwargs)
            elif hasattr(self._lc_tool, 'ainvoke'):
                result = await self._lc_tool.ainvoke(**kwargs)
            elif hasattr(self._lc_tool, '_run'):
                result = self._lc_tool._run(**kwargs)
            else:
                result = str(self._lc_tool)

            return ToolResult(
                success=True,
                data=result,
                source=self._lc_tool.name
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                source=self._lc_tool.name
            )

    async def is_available(self) -> bool:
        """LangChain 工具总是可用的（除非在 Mock 模式下）"""
        return True or self.mock_mode


# ============ 高德地图工具 ============

class AmapWeatherParams(BaseModel):
    """高德天气查询参数"""
    city: str = Field(..., description="城市名称")


class AmapWeatherTool(APITool):
    """高德天气查询工具"""

    def __init__(self, api_key: str = "", mock_mode: bool = False):
        super().__init__(
            api_key=api_key,
            base_url="https://restapi.amap.com/v3",
            mock_mode=mock_mode
        )

    @property
    def description(self) -> str:
        return "查询城市天气预报，支持查询未来几天的天气情况"

    @property
    def schema(self) -> Dict[str, Any]:
        return AmapWeatherParams.model_json_schema()

    async def execute(self, city: str, **kwargs) -> ToolResult:
        """查询天气"""
        try:
            if self.mock_mode:
                return await self._mock_execute(city=city)

            result = await self._http_get(
                "/weather/weatherInfo",
                params={"key": self.api_key, "city": city, "extensions": "all"}
            )

            if result.get("status") == "1" and result.get("forecasts"):
                forecast = result["forecasts"][0]
                return ToolResult(
                    success=True,
                    data={
                        "city": forecast.get("city"),
                        "weather": forecast.get("casts", [])
                    },
                    source="amap"
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"天气查询失败: {result.get('info', 'Unknown error')}",
                    source="amap"
                )
        except Exception as e:
            return ToolResult(success=False, error=str(e), source="amap")

    async def _mock_execute(self, city: str, **kwargs) -> ToolResult:
        """Mock 天气数据"""
        mock_data = {
            "city": city,
            "weather": [
                {"date": "2026-03-25", "dayweather": "晴", "nightweather": "晴", "daytemp": "20", "nighttemp": "10"},
                {"date": "2026-03-26", "dayweather": "多云", "nightweather": "阴", "daytemp": "18", "nighttemp": "12"},
                {"date": "2026-03-27", "dayweather": "小雨", "nightweather": "小雨", "daytemp": "15", "nighttemp": "10"},
            ]
        }
        return ToolResult(success=True, data=mock_data, source="amap-mock")


# ============ Tavily 搜索工具 ============

class TavilySearchParams(BaseModel):
    """Tavily 搜索参数"""
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=5, description="最大结果数")


class TavilySearchTool(APITool):
    """Tavily 搜索工具"""

    def __init__(self, api_key: str = "", mock_mode: bool = False):
        super().__init__(
            api_key=api_key,
            base_url="https://api.tavily.com",
            mock_mode=mock_mode
        )

    @property
    def description(self) -> str:
        return "使用 Tavily API 进行网络搜索，获取最新信息"

    @property
    def schema(self) -> Dict[str, Any]:
        return TavilySearchParams.model_json_schema()

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """执行搜索"""
        try:
            if self.mock_mode:
                return await self._mock_execute(query=query, max_results=max_results)

            result = await self._http_post(
                "/search",
                data={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic"
                }
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": result.get("results", []),
                    "answer": result.get("answer", "")
                },
                source="tavily"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), source="tavily")

    async def _mock_execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """Mock 搜索数据"""
        mock_results = [
            {
                "title": f"关于 '{query}' 的搜索结果 1",
                "url": "https://example.com/1",
                "content": f"这是关于 {query} 的模拟搜索结果...",
                "score": 0.95
            },
            {
                "title": f"关于 '{query}' 的搜索结果 2",
                "url": "https://example.com/2",
                "content": f"更多关于 {query} 的信息...",
                "score": 0.85
            }
        ]
        return ToolResult(
            success=True,
            data={"query": query, "results": mock_results[:max_results], "answer": f"这是关于 '{query}' 的模拟搜索摘要。"},
            source="tavily-mock"
        )


# ============ GitHub 工具 ============

class GitHubSearchParams(BaseModel):
    """GitHub 搜索参数"""
    query: str = Field(..., description="搜索查询")
    repo_only: bool = Field(default=True, description="仅搜索仓库")


class GitHubSearchTool(APITool):
    """GitHub 搜索工具"""

    def __init__(self, token: str = "", mock_mode: bool = False):
        super().__init__(
            api_key=token,
            base_url="https://api.github.com",
            mock_mode=mock_mode
        )

    @property
    def description(self) -> str:
        return "搜索 GitHub 仓库和代码"

    @property
    def schema(self) -> Dict[str, Any]:
        return GitHubSearchParams.model_json_schema()

    async def execute(self, query: str, repo_only: bool = True, **kwargs) -> ToolResult:
        """搜索 GitHub"""
        try:
            if self.mock_mode:
                return await self._mock_execute(query=query, repo_only=repo_only)

            search_type = "repositories" if repo_only else "code"
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.api_key:
                headers["Authorization"] = f"token {self.api_key}"

            result = await self._http_get(
                f"/search/{search_type}",
                params={"q": query, "per_page": 5},
                headers=headers
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "type": search_type,
                    "results": result.get("items", [])
                },
                source="github"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), source="github")

    async def _mock_execute(self, query: str, repo_only: bool = True, **kwargs) -> ToolResult:
        """Mock GitHub 数据"""
        mock_results = [
            {
                "name": f"{query}-repo",
                "full_name": f"user/{query}-repo",
                "description": f"这是一个关于 {query} 的模拟仓库",
                "stargazers_count": 1000,
                "language": "Python",
                "html_url": f"https://github.com/user/{query}-repo"
            }
        ]
        return ToolResult(
            success=True,
            data={"query": query, "type": "repositories" if repo_only else "code", "results": mock_results},
            source="github-mock"
        )


# ============ arXiv 工具 ============

class ArxivSearchParams(BaseModel):
    """arXiv 搜索参数"""
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=5, description="最大结果数")


class ArxivSearchTool(BaseTool):
    """arXiv 论文搜索工具"""

    def __init__(self, mock_mode: bool = False):
        super().__init__(mock_mode=mock_mode)

    @property
    def description(self) -> str:
        return "搜索 arXiv 学术论文"

    @property
    def schema(self) -> Dict[str, Any]:
        return ArxivSearchParams.model_json_schema()

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """搜索 arXiv"""
        try:
            if self.mock_mode:
                return await self._mock_execute(query=query, max_results=max_results)

            import arxiv
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )

            results = []
            for paper in search.results():
                results.append({
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors],
                    "summary": paper.summary,
                    "published": paper.published.isoformat(),
                    "url": paper.entry_id,
                    "pdf_url": paper.pdf_url
                })

            return ToolResult(
                success=True,
                data={"query": query, "results": results},
                source="arxiv"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), source="arxiv")

    async def _mock_execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """Mock arXiv 数据"""
        mock_results = [
            {
                "title": f"A Paper About {query}",
                "authors": ["Author 1", "Author 2"],
                "summary": f"This is a simulated abstract for a paper about {query}...",
                "published": "2026-01-01T00:00:00",
                "url": f"http://arxiv.org/abs/{query}123",
                "pdf_url": f"http://arxiv.org/pdf/{query}123.pdf"
            }
        ]
        return ToolResult(
            success=True,
            data={"query": query, "results": mock_results[:max_results]},
            source="arxiv-mock"
        )
