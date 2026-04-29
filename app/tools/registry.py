"""工具注册中心

集中管理所有工具的注册和获取。
"""

from typing import Dict, List, Optional, Any
from langchain_core.tools import StructuredTool

from .base import BaseTool, ToolCollection
from .adapters import (
    LangChainToolAdapter,
    AmapWeatherTool,
    TavilySearchTool,
    GitHubSearchTool,
    ArxivSearchTool
)
from .mocks import MockToolRegistry


class ToolRegistry:
    """工具注册中心

    管理所有工具的注册、获取和可用性检查。
    支持真实工具和 Mock 工具的切换。
    """

    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._collections: Dict[str, ToolCollection] = {
            "outfit": ToolCollection(),
            "search": ToolCollection(),
            "finance": ToolCollection(),
            "academic": ToolCollection(),
            "trip": ToolCollection(),
        }
        self._global_collection = ToolCollection()

        # 注册所有工具
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认工具"""

        # ============ Outfit 工具 ============
        self.register_tool("outfit", "weather", AmapWeatherTool)

        # ============ Search 工具 ============
        self.register_tool("search", "tavily_search", TavilySearchTool)

        # ============ Academic 工具 ============
        self.register_tool("academic", "github_search", GitHubSearchTool)
        self.register_tool("academic", "arxiv_search", ArxivSearchTool)

        # ============ Trip 工具 ============
        self.register_tool("trip", "weather", AmapWeatherTool)

    def register_tool(
        self,
        domain: str,
        name: str,
        tool_class: type,
        **kwargs
    ) -> None:
        """注册工具

        Args:
            domain: 领域名称 (outfit, search, finance, academic, trip)
            name: 工具名称
            tool_class: 工具类
            **kwargs: 工具初始化参数
        """
        tool_kwargs = {"mock_mode": self.mock_mode, **kwargs}
        tool = tool_class(**tool_kwargs)
        self._collections[domain].register(tool)
        self._global_collection.register(tool)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具（通过名称）"""
        return self._global_collection.get(name)

    def get_domain_tools(self, domain: str) -> List[BaseTool]:
        """获取指定领域的所有工具"""
        collection = self._collections.get(domain)
        if collection:
            return list(collection._tools.values())
        return []

    async def get_available_domain_tools(self, domain: str) -> List[BaseTool]:
        """获取指定领域可用的工具"""
        collection = self._collections.get(domain)
        if collection:
            return await collection.get_available_tools()
        return []

    def list_all_tools(self) -> Dict[str, List[str]]:
        """列出所有领域的工具"""
        return {
            domain: collection.list_available()
            for domain, collection in self._collections.items()
        }

    async def get_langchain_tools(self, domain: str = None) -> List[StructuredTool]:
        """获取 LangChain 格式的工具列表

        用于 LangChain/LangGraph 的 tool binding。
        """
        tools = []

        if domain:
            base_tools = await self.get_available_domain_tools(domain)
        else:
            base_tools = await self._global_collection.get_available_tools()

        for tool in base_tools:
            lc_tool = StructuredTool.from_function(
                func=lambda **kwargs: tool.execute(**kwargs),
                name=tool.name,
                description=tool.description,
                args_schema=self._create_args_schema(tool.schema),
                coroutine=lambda **kwargs: tool.execute(**kwargs)
            )
            tools.append(lc_tool)

        return tools

    def _create_args_schema(self, schema: Dict[str, Any]):
        """从 JSON Schema 创建 Pydantic 模型"""
        from pydantic import BaseModel, Field
        import inspect

        # 简化处理：使用动态创建 BaseModel 的方式
        fields = {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        for field_name, field_info in properties.items():
            field_type = str  # 简化类型处理
            default = ... if field_name in required else None
            description = field_info.get("description", "")
            fields[field_name] = (field_type, Field(default=default, description=description))

        return type("DynamicSchema", (BaseModel,), fields)


# ============ 全局注册表实例 ============

_global_registry: Optional[ToolRegistry] = None


def get_tool_registry(mock_mode: bool = None) -> ToolRegistry:
    """获取全局工具注册表实例

    Args:
        mock_mode: 是否使用 Mock 模式。如果不指定，使用环境变量配置。

    Returns:
        ToolRegistry 实例
    """
    global _global_registry

    if _global_registry is None:
        from ..core.config import settings
        if mock_mode is None:
            mock_mode = settings.mock_mode
        _global_registry = ToolRegistry(mock_mode=mock_mode)

    return _global_registry


def reset_tool_registry():
    """重置全局工具注册表（用于测试）"""
    global _global_registry
    _global_registry = None
