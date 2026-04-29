"""Trip 子图工具定义

复用现有的高德地图工具。
"""

from ...tools.base import ToolResult


async def get_weather(city: str) -> ToolResult:
    """获取城市天气"""
    from ...services.weather_service import get_weather_service

    service = get_weather_service()
    result = await service.get_weather(city)

    return ToolResult(
        success=True,
        data=result,
        source="amap"
    )


async def search_poi(keyword: str, city: str) -> ToolResult:
    """搜索 POI（景点、酒店等）"""
    # Mock 实现，可以接入真实的高德 POI 搜索
    mock_results = [
        {
            "name": f"{city}{keyword}1",
            "address": f"{city}市xx路xx号",
            "type": keyword
        },
        {
            "name": f"{city}{keyword}2",
            "address": f"{city}市yy路yy号",
            "type": keyword
        }
    ]

    return ToolResult(
        success=True,
        data={"results": mock_results},
        source="mock"
    )
