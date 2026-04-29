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
    """工具基类"""

    def __init__(self):
        self._name = self.__class__.__name__

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

    async def is_available(self) -> bool:
        return await self._check_availability()

    async def _check_availability(self) -> bool:
        return True


class APITool(BaseTool):
    """API 工具基类"""

    def __init__(self, api_key: str = "", base_url: str = ""):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url

    async def _check_availability(self) -> bool:
        return bool(self.api_key)

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
    """工具集合"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_available(self) -> list[str]:
        return list(self._tools.keys())

    async def get_available_tools(self) -> list[BaseTool]:
        available = []
        for tool in self._tools.values():
            if await tool.is_available():
                available.append(tool)
        return available

    def get_tool_schemas(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema
            }
            for tool in self._tools.values()
        ]
