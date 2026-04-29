"""Trip 子图工具定义

使用高德地图 POI 搜索 API。
"""

import httpx
from ...tools.base import ToolResult
from ...core.config import settings


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


async def search_poi(keyword: str, city: str, city_limit: bool = True) -> ToolResult:
    """搜索 POI（景点、酒店等）- 使用高德 POI 文字搜索接口

    Args:
        keyword: 搜索关键词（如 "景点"、"酒店"、"公园"）
        city: 城市名称
        city_limit: 是否限制在城市范围内

    Returns:
        ToolResult 包含 POI 列表
    """
    if not settings.amap_api_key:
        return ToolResult(
            success=False,
            error="AMAP_API_KEY 未配置，无法搜索 POI",
            source="amap"
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {
            "key": settings.amap_api_key,
            "keywords": keyword,
            "city": city,
            "citylimit": str(city_limit).lower(),
            "offset": 10,
            "output": "json"
        }

        response = await client.get(
            "https://restapi.amap.com/v3/place/text",
            params=params
        )
        result = response.json()

        if result.get("status") == "1" and result.get("pois"):
            pois = result["pois"]
            formatted = [
                {
                    "name": p.get("name", ""),
                    "address": p.get("address", ""),
                    "type": p.get("type", ""),
                    "location": p.get("location", ""),
                    "tel": p.get("tel", ""),
                    "rating": p.get("biz_ext", {}).get("rating", ""),
                    "cost": p.get("biz_ext", {}).get("cost", ""),
                }
                for p in pois[:10]
            ]
            return ToolResult(
                success=True,
                data={"results": formatted, "total": int(result.get("count", 0))},
                source="amap"
            )
        else:
            return ToolResult(
                success=False,
                error=f"POI 搜索失败: {result.get('info', '未找到结果')}",
                source="amap"
            )
