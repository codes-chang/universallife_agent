"""工具注册中心"""

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


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._collections: Dict[str, ToolCollection] = {
            "outfit": ToolCollection(),
            "search": ToolCollection(),
            "finance": ToolCollection(),
            "academic": ToolCollection(),
            "trip": ToolCollection(),
        }
        self._global_collection = ToolCollection()
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认工具"""
        from ..core.config import settings

        # Outfit 工具
        self.register_tool("outfit", "weather", AmapWeatherTool, api_key=settings.amap_api_key)

        # Search 工具
        self.register_tool("search", "tavily_search", TavilySearchTool, api_key=settings.tavily_api_key)

        # Academic 工具
        self.register_tool("academic", "github_search", GitHubSearchTool, token=settings.github_token)
        self.register_tool("academic", "arxiv_search", ArxivSearchTool)

        # Trip 工具
        self.register_tool("trip", "weather", AmapWeatherTool, api_key=settings.amap_api_key)

    def register_tool(
        self,
        domain: str,
        name: str,
        tool_class: type,
        **kwargs
    ) -> None:
        """注册工具"""
        tool = tool_class(**kwargs)
        self._collections[domain].register(tool)
        self._global_collection.register(tool)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._global_collection.get(name)

    def get_domain_tools(self, domain: str) -> List[BaseTool]:
        collection = self._collections.get(domain)
        if collection:
            return list(collection._tools.values())
        return []

    async def get_available_domain_tools(self, domain: str) -> List[BaseTool]:
        collection = self._collections.get(domain)
        if collection:
            return await collection.get_available_tools()
        return []

    def list_all_tools(self) -> Dict[str, List[str]]:
        return {
            domain: collection.list_available()
            for domain, collection in self._collections.items()
        }

    async def get_langchain_tools(self, domain: str = None) -> List[StructuredTool]:
        """获取 LangChain 格式的工具列表"""
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

        fields = {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        for field_name, field_info in properties.items():
            field_type = str
            default = ... if field_name in required else None
            description = field_info.get("description", "")
            fields[field_name] = (field_type, Field(default=default, description=description))

        return type("DynamicSchema", (BaseModel,), fields)


# ============ 全局注册表实例 ============

_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表实例"""
    global _global_registry

    if _global_registry is None:
        _global_registry = ToolRegistry()

    return _global_registry


def reset_tool_registry():
    """重置全局工具注册表（用于测试）"""
    global _global_registry
    _global_registry = None
