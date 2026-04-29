"""天气服务 - 使用高德地图 API"""

import httpx
from typing import Optional, Dict, Any

from ..core.config import settings
from ..core.logging import logger


class WeatherService:
    """天气服务

    提供天气查询功能，使用高德地图天气 API。
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.amap_api_key
        self.base_url = "https://restapi.amap.com/v3"

    async def get_weather(self, city: str, days: int = 3) -> Dict[str, Any]:
        """获取城市天气预报

        Args:
            city: 城市名称
            days: 天数（1-4）

        Returns:
            天气数据字典
        """
        if not self.api_key:
            raise ValueError("AMAP_API_KEY 未配置，无法查询天气")

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "key": self.api_key,
                "city": city,
                "extensions": "all"
            }
            response = await client.get(f"{self.base_url}/weather/weatherInfo", params=params)
            result = response.json()

            if result.get("status") != "1":
                error_info = result.get("info", "Unknown error")
                raise RuntimeError(f"高德天气 API 查询失败: {error_info}")

            forecasts = result.get("forecasts")
            if not forecasts:
                raise RuntimeError(f"未找到城市 '{city}' 的天气数据，请检查城市名称")

            forecast = forecasts[0]
            casts = forecast.get("casts", [])[:days]

            return {
                "city": forecast.get("city"),
                "province": forecast.get("province"),
                "report_time": forecast.get("reporttime"),
                "casts": [
                    {
                        "date": cast.get("date"),
                        "week": cast.get("week"),
                        "day_weather": cast.get("dayweather"),
                        "night_weather": cast.get("nightweather"),
                        "day_temp": cast.get("daytemp"),
                        "night_temp": cast.get("nighttemp"),
                        "day_wind": cast.get("daywinddirection", "") + cast.get("daywindpower", ""),
                        "night_wind": cast.get("nightwinddirection", "") + cast.get("nightwindpower", "")
                    }
                    for cast in casts
                ]
            }

    def get_weather_summary(self, weather_data: Dict[str, Any]) -> str:
        """获取天气摘要文本"""
        if not weather_data or "casts" not in weather_data:
            return "暂无天气信息"

        city = weather_data.get("city", "未知")
        casts = weather_data["casts"]

        summary_parts = [f"{city}天气预报：\n"]

        for cast in casts:
            date = cast.get("date", "")
            day_weather = cast.get("day_weather", "")
            night_weather = cast.get("night_weather", "")
            day_temp = cast.get("day_temp", "")
            night_temp = cast.get("night_temp", "")

            summary_parts.append(
                f"{date}: 白天{day_weather} {day_temp}°C, "
                f"夜间{night_weather} {night_temp}°C"
            )

        return "\n".join(summary_parts)

    def check_rain(self, weather_data: Dict[str, Any]) -> bool:
        """检查是否下雨"""
        if not weather_data or "casts" not in weather_data:
            return False

        for cast in weather_data["casts"]:
            day_weather = cast.get("day_weather", "")
            night_weather = cast.get("night_weather", "")
            if "雨" in day_weather or "雨" in night_weather:
                return True
        return False

    def get_temperature(self, weather_data: Dict[str, Any]) -> tuple[int, int]:
        """获取温度范围（最高温，最低温）"""
        if not weather_data or "casts" not in weather_data:
            return 25, 15

        max_temp = -100
        min_temp = 100

        for cast in weather_data["casts"]:
            try:
                day_temp = int(cast.get("day_temp", 0))
                night_temp = int(cast.get("night_temp", 0))
                max_temp = max(max_temp, day_temp)
                min_temp = min(min_temp, night_temp)
            except (ValueError, TypeError):
                continue

        return max_temp if max_temp > -100 else 25, min_temp if min_temp < 100 else 15


# ============ 全局实例 ============

_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """获取天气服务实例"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
