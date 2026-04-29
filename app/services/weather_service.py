"""天气服务 - 使用高德地图 API"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..core.config import settings
from ..core.logging import logger
from ..tools.mocks import MockToolRegistry


class WeatherService:
    """天气服务

    提供天气查询功能，支持真实 API 和 Mock 模式。
    """

    def __init__(self, api_key: str = None, mock_mode: bool = None):
        self.api_key = api_key or settings.amap_api_key
        if mock_mode is None:
            self.mock_mode = settings.mock_mode
        else:
            self.mock_mode = mock_mode

        self.base_url = "https://restapi.amap.com/v3"

    async def get_weather(self, city: str, days: int = 3) -> Dict[str, Any]:
        """
        获取城市天气预报

        Args:
            city: 城市名称
            days: 天数（1-4）

        Returns:
            天气数据字典
        """
        if self.mock_mode or not self.api_key:
            return await self._get_mock_weather(city, days)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "key": self.api_key,
                    "city": city,
                    "extensions": "all"  # 获取预报天气
                }
                response = await client.get(f"{self.base_url}/weather/weatherInfo", params=params)
                result = response.json()

                if result.get("status") == "1" and result.get("forecasts"):
                    forecast = result["forecasts"][0]
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
                else:
                    logger.warning(f"天气查询失败: {result.get('info', 'Unknown error')}")
                    return await self._get_mock_weather(city, days)

        except Exception as e:
            logger.error(f"天气查询异常: {e}")
            return await self._get_mock_weather(city, days)

    async def _get_mock_weather(self, city: str, days: int = 3) -> Dict[str, Any]:
        """获取 Mock 天气数据"""
        base_date = datetime.now()
        mock_weather_types = [
            {"day": "晴", "night": "晴", "temp_range": (20, 10)},
            {"day": "多云", "night": "阴", "temp_range": (18, 12)},
            {"day": "小雨", "night": "小雨", "temp_range": (15, 10)},
            {"day": "阴", "night": "多云", "temp_range": (17, 11)}
        ]

        casts = []
        for i in range(days):
            date = base_date + timedelta(days=i)
            weather = mock_weather_types[i % len(mock_weather_types)]

            casts.append({
                "date": date.strftime("%Y-%m-%d"),
                "week": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()],
                "day_weather": weather["day"],
                "night_weather": weather["night"],
                "day_temp": str(weather["temp_range"][0]),
                "night_temp": str(weather["temp_range"][1]),
                "day_wind": "南风1-3级",
                "night_wind": "南风1-3级"
            })

        return {
            "city": city,
            "province": "模拟省份",
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "casts": casts,
            "mock": True
        }

    def get_weather_summary(self, weather_data: Dict[str, Any]) -> str:
        """
        获取天气摘要文本

        Args:
            weather_data: 天气数据

        Returns:
            天气摘要文本
        """
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
