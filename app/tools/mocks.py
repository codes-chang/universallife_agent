"""Mock 工具实现

当真实 API 不可用时，使用 Mock 数据进行测试和开发。
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta

from .base import BaseTool, ToolResult


class MockToolRegistry:
    """Mock 工具注册表

    存储各类工具的 Mock 数据模板。
    """

    # 穿搭 Mock 数据
    OUTFIT_MOCKS = {
        "rainy": {
            "location": "上海",
            "weather": "小雨",
            "temperature": "15°C",
            "outfit": {
                "top": "防水外套",
                "bottom": "深色长裤",
                "shoes": "防水鞋/雨靴",
                "accessories": ["雨伞", "防水背包套"]
            },
            "advice": "雨天建议穿着防水材质的衣物，搭配雨伞和防水鞋。"
        },
        "sunny": {
            "location": "北京",
            "weather": "晴",
            "temperature": "25°C",
            "outfit": {
                "top": "轻便T恤",
                "bottom": "休闲裤/牛仔裤",
                "shoes": "运动鞋/帆布鞋",
                "accessories": ["太阳镜", "防晒帽"]
            },
            "advice": "晴天适合穿着轻便透气的衣物，注意防晒。"
        },
        "cold": {
            "location": "哈尔滨",
            "weather": "多云",
            "temperature": "-5°C",
            "outfit": {
                "top": "羽绒服/厚外套",
                "bottom": "加绒长裤",
                "shoes": "保暖靴",
                "accessories": ["围巾", "手套", "帽子"]
            },
            "advice": "寒冷天气需要穿着保暖的衣物，多层穿搭更保暖。"
        }
    }

    # 搜索 Mock 数据
    SEARCH_MOCKS = {
        "default": [
            {
                "title": "示例搜索结果 1",
                "url": "https://example.com/1",
                "snippet": "这是模拟的搜索结果摘要...",
                "source": "example.com",
                "timestamp": datetime.now().isoformat()
            },
            {
                "title": "示例搜索结果 2",
                "url": "https://example.com/2",
                "snippet": "这是另一个模拟的搜索结果...",
                "source": "example.com",
                "timestamp": datetime.now().isoformat()
            }
        ]
    }

    # 金融 Mock 数据
    FINANCE_MOCKS = {
        "stock": {
            "AAPL": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 178.50,
                "change": 2.30,
                "change_percent": 1.30,
                "timestamp": datetime.now().isoformat(),
                "source": "yahoo-finance-mock"
            },
            "TSLA": {
                "symbol": "TSLA",
                "name": "Tesla Inc.",
                "price": 245.80,
                "change": -5.20,
                "change_percent": -2.07,
                "timestamp": datetime.now().isoformat(),
                "source": "yahoo-finance-mock"
            }
        },
        "price_compare": {
            "product": "示例商品",
            "prices": [
                {"platform": "京东", "price": 299.00, "url": "https://jd.com/example"},
                {"platform": "淘宝", "price": 289.00, "url": "https://taobao.com/example"},
                {"platform": "拼多多", "price": 279.00, "url": "https://pinduoduo.com/example"}
            ],
            "best_price": 279.00,
            "best_source": "拼多多"
        }
    }

    # 学术 Mock 数据
    ACADEMIC_MOCKS = {
        "github": [
            {
                "name": "langgraph",
                "full_name": "langchain-ai/langgraph",
                "description": "LangGraph is a library for building stateful, multi-actor applications with LLMs",
                "stargazers_count": 15000,
                "language": "Python",
                "url": "https://github.com/langchain-ai/langgraph",
                "updated_at": datetime.now().isoformat()
            },
            {
                "name": "langchain",
                "full_name": "langchain-ai/langchain",
                "description": "Building applications with LLMs through composability",
                "stargazers_count": 85000,
                "language": "Python",
                "url": "https://github.com/langchain-ai/langchain",
                "updated_at": datetime.now().isoformat()
            }
        ],
        "arxiv": [
            {
                "title": "Attention Is All You Need",
                "authors": ["Vaswani, A.", "Shazeer, N.", "Parmar, N."],
                "summary": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                "published": "2017-06-12T00:00:00",
                "arxiv_url": "http://arxiv.org/abs/1706.03762",
                "pdf_url": "http://arxiv.org/pdf/1706.03762.pdf"
            }
        ]
    }

    # 旅行 Mock 数据
    TRIP_MOCKS = {
        "attractions": [
            {
                "name": "示例景点1",
                "address": "示例地址1",
                "description": "这是一个著名的景点...",
                "category": "历史文化",
                "rating": 4.5
            },
            {
                "name": "示例景点2",
                "address": "示例地址2",
                "description": "另一个不错的景点...",
                "category": "自然风光",
                "rating": 4.3
            }
        ],
        "hotels": [
            {
                "name": "示例酒店",
                "address": "酒店地址",
                "price_range": "300-500元",
                "rating": "4.5",
                "type": "经济型酒店"
            }
        ]
    }

    @classmethod
    def get_outfit_mock(cls, weather: str = "sunny", location: str = "未知") -> Dict[str, Any]:
        """获取穿搭 Mock 数据"""
        if weather == "雨" or weather == "rain":
            mock = cls.OUTFIT_MOCKS["rainy"].copy()
        elif "冷" in weather or int(weather.get("temp", 20)) < 10:
            mock = cls.OUTFIT_MOCKS["cold"].copy()
        else:
            mock = cls.OUTFIT_MOCKS["sunny"].copy()
        mock["location"] = location
        return mock

    @classmethod
    def get_search_mock(cls, query: str = "") -> List[Dict[str, Any]]:
        """获取搜索 Mock 数据"""
        results = cls.SEARCH_MOCKS["default"].copy()
        for r in results:
            r["title"] = f"关于 '{query}' 的搜索结果"
            r["snippet"] = f"这是关于 {query} 的模拟搜索结果..."
        return results

    @classmethod
    def get_finance_mock(cls, symbol: str = "AAPL") -> Dict[str, Any]:
        """获取金融 Mock 数据"""
        return cls.FINANCE_MOCKS["stock"].get(symbol.upper(), cls.FINANCE_MOCKS["stock"]["AAPL"])

    @classmethod
    def get_academic_mock(cls, source: str = "github", query: str = "") -> List[Dict[str, Any]]:
        """获取学术 Mock 数据"""
        if source == "github":
            return cls.ACADEMIC_MOCKS["github"]
        else:
            return cls.ACADEMIC_MOCKS["arxiv"]


class MockWeatherTool(BaseTool):
    """Mock 天气工具"""

    @property
    def description(self) -> str:
        return "Mock 天气查询工具"

    @property
    def schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"city": {"type": "string"}}}

    async def execute(self, city: str, **kwargs) -> ToolResult:
        """执行 Mock 天气查询"""
        mock_data = {
            "city": city,
            "weather": MockToolRegistry.OUTFIT_MOCKS["sunny"],
            "forecast": [
                {"date": (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d"),
                 "dayweather": "晴", "nightweather": "晴",
                 "daytemp": "25", "nighttemp": "15"}
                for i in range(3)
            ]
        }
        return ToolResult(success=True, data=mock_data, source="mock")


class MockSearchTool(BaseTool):
    """Mock 搜索工具"""

    @property
    def description(self) -> str:
        return "Mock 搜索工具"

    @property
    def schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"query": {"type": "string"}}}

    async def execute(self, query: str, **kwargs) -> ToolResult:
        """执行 Mock 搜索"""
        results = MockToolRegistry.get_search_mock(query)
        return ToolResult(success=True, data={"results": results}, source="mock")


class MockFinanceTool(BaseTool):
    """Mock 金融工具"""

    @property
    def description(self) -> str:
        return "Mock 金融查询工具"

    @property
    def schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"symbol": {"type": "string"}}}

    async def execute(self, symbol: str = "AAPL", **kwargs) -> ToolResult:
        """执行 Mock 金融查询"""
        data = MockToolRegistry.get_finance_mock(symbol)
        return ToolResult(success=True, data=data, source="mock")


class MockAcademicTool(BaseTool):
    """Mock 学术工具"""

    @property
    def description(self) -> str:
        return "Mock 学术资源查询工具"

    @property
    def schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"query": {"type": "string"}}}

    async def execute(self, query: str, source: str = "github", **kwargs) -> ToolResult:
        """执行 Mock 学术查询"""
        results = MockToolRegistry.get_academic_mock(source, query)
        return ToolResult(success=True, data={"results": results, "source": source}, source="mock")
