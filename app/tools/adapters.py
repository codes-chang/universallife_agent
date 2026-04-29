"""工具适配器 - API 工具的适配器实现"""

from typing import Any, Dict
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .base import BaseTool, ToolResult, APITool


# ============ LangChain 工具适配器 ============

class LangChainToolAdapter(BaseTool):
    """LangChain StructuredTool 适配器"""

    def __init__(self, langchain_tool: StructuredTool):
        super().__init__()
        self._lc_tool = langchain_tool
        self._name = langchain_tool.name

    @property
    def description(self) -> str:
        return self._lc_tool.description

    @property
    def schema(self) -> Dict[str, Any]:
        if hasattr(self._lc_tool, 'args_schema') and self._lc_tool.args_schema:
            return self._lc_tool.args_schema.model_json_schema()
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        """执行 LangChain 工具"""
        try:
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
        return True


# ============ 高德地图工具 ============

class AmapWeatherParams(BaseModel):
    """高德天气查询参数"""
    city: str = Field(..., description="城市名称")


class AmapWeatherTool(APITool):
    """高德天气查询工具"""

    def __init__(self, api_key: str = ""):
        super().__init__(
            api_key=api_key,
            base_url="https://restapi.amap.com/v3"
        )

    @property
    def description(self) -> str:
        return "查询城市天气预报，支持查询未来几天的天气情况"

    @property
    def schema(self) -> Dict[str, Any]:
        return AmapWeatherParams.model_json_schema()

    async def execute(self, city: str, **kwargs) -> ToolResult:
        """查询天气"""
        if not self.api_key:
            return ToolResult(success=False, error="AMAP_API_KEY 未配置", source="amap")

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


# ============ Tavily 搜索工具 ============

class TavilySearchParams(BaseModel):
    """Tavily 搜索参数"""
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=5, description="最大结果数")


class TavilySearchTool(APITool):
    """Tavily 搜索工具"""

    def __init__(self, api_key: str = ""):
        super().__init__(
            api_key=api_key,
            base_url="https://api.tavily.com"
        )

    @property
    def description(self) -> str:
        return "使用 Tavily API 进行网络搜索，获取最新信息"

    @property
    def schema(self) -> Dict[str, Any]:
        return TavilySearchParams.model_json_schema()

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """执行搜索"""
        if not self.api_key:
            return ToolResult(success=False, error="TAVILY_API_KEY 未配置", source="tavily")

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


# ============ GitHub 工具 ============

class GitHubSearchParams(BaseModel):
    """GitHub 搜索参数"""
    query: str = Field(..., description="搜索查询")
    repo_only: bool = Field(default=True, description="仅搜索仓库")


class GitHubSearchTool(APITool):
    """GitHub 搜索工具"""

    def __init__(self, token: str = ""):
        super().__init__(
            api_key=token,
            base_url="https://api.github.com"
        )

    @property
    def description(self) -> str:
        return "搜索 GitHub 仓库和代码"

    @property
    def schema(self) -> Dict[str, Any]:
        return GitHubSearchParams.model_json_schema()

    async def execute(self, query: str, repo_only: bool = True, **kwargs) -> ToolResult:
        """搜索 GitHub"""
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


# ============ arXiv 工具 ============

class ArxivSearchParams(BaseModel):
    """arXiv 搜索参数"""
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=5, description="最大结果数")


class ArxivSearchTool(BaseTool):
    """arXiv 论文搜索工具"""

    @property
    def description(self) -> str:
        return "搜索 arXiv 学术论文"

    @property
    def schema(self) -> Dict[str, Any]:
        return ArxivSearchParams.model_json_schema()

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """搜索 arXiv"""
        try:
            import arxiv
        except ImportError:
            return ToolResult(success=False, error="arxiv 库未安装", source="arxiv")

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
