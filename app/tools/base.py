"""工具基类定义"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from pydantic import BaseModel
from datetime import datetime


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    source: str = "unknown"
    timestamp: str = ""

    def __init__(self, **data):
        data["timestamp"] = datetime.now().isoformat()
        super().__init__(**data)


class BaseTool(ABC):
    """工具基类

    所有工具必须继承此类并实现相关方法。
    支持真实 API 和 Mock 两种模式。
    """

    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._name = self.__class__.__name__

    @property
    def name(self) -> str:
        """工具名称"""
        return self._name

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """工具参数 Schema (JSON Schema 格式)"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    async def is_available(self) -> bool:
        """检查工具是否可用

        检查 API Key 是否配置、服务是否可达等。
        在 Mock 模式下始终返回 True。
        """
        if self.mock_mode:
            return True
        return await self._check_availability()

    async def _check_availability(self) -> bool:
        """检查工具可用性的具体实现（子类可覆盖）"""
        return True

    async def _mock_execute(self, **kwargs) -> ToolResult:
        """Mock 执行（子类可覆盖）"""
        return ToolResult(
            success=True,
            data={"mock": True, "message": f"Mock result for {self.name}"},
            source="mock"
        )


class APITool(BaseTool):
    """API 工具基类

    用于封装 REST API 调用的工具。
    """

    def __init__(self, api_key: str = "", base_url: str = "", mock_mode: bool = False):
        super().__init__(mock_mode=mock_mode)
        self.api_key = api_key
        self.base_url = base_url

    async def _check_availability(self) -> bool:
        """检查 API Key 是否配置"""
        return bool(self.api_key) or self.mock_mode

    async def _http_get(self, endpoint: str, params: dict = None, headers: dict = None) -> dict:
        """执行 HTTP GET 请求"""
        import httpx

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        default_headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        headers = {**default_headers, **(headers or {})}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _http_post(self, endpoint: str, data: dict = None, headers: dict = None) -> dict:
        """执行 HTTP POST 请求"""
        import httpx

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        default_headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        headers = {**default_headers, **(headers or {})}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()


class ToolCollection:
    """工具集合

    管理多个工具，提供统一的访问接口。
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_available(self) -> list[str]:
        """列出所有可用工具"""
        return list(self._tools.keys())

    async def get_available_tools(self) -> list[BaseTool]:
        """获取所有可用的工具（经过可用性检查）"""
        available = []
        for tool in self._tools.values():
            if await tool.is_available():
                available.append(tool)
        return available

    def get_tool_schemas(self) -> list[dict]:
        """获取所有工具的 Schema"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema
            }
            for tool in self._tools.values()
        ]
