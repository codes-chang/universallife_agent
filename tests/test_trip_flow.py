"""Trip 子图流程测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.subgraphs.trip.state import TripSubgraphState
from app.tools.base import ToolResult


def _make_trip_state(task_input: str = "规划北京 3 天旅行") -> TripSubgraphState:
    """构建旅行子图测试状态"""
    return {
        "task_input": task_input,
        "domain": "trip",
        "plan": None,
        "tool_calls": [],
        "intermediate_result": None,
        "final_result": None,
        "critique": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "city": None,
        "start_date": None,
        "end_date": None,
        "travel_days": None,
        "preferences": [],
        "weather_info": None,
        "attractions": [],
        "hotels": []
    }


class TestTripBuildPlanNode:
    """测试旅行子图规划节点"""

    @pytest.mark.asyncio
    async def test_city_extraction(self):
        """测试城市名提取"""
        from app.subgraphs.trip.nodes import build_plan_node

        state = _make_trip_state("规划北京 3 天旅行")
        result = await build_plan_node(state)

        assert result["city"] == "北京"

    @pytest.mark.asyncio
    async def test_city_extraction_shanghai(self):
        """测试提取上海"""
        from app.subgraphs.trip.nodes import build_plan_node

        state = _make_trip_state("去上海旅游 5 天")
        result = await build_plan_node(state)

        assert result["city"] == "上海"

    @pytest.mark.asyncio
    async def test_days_extraction(self):
        """测试天数提取"""
        from app.subgraphs.trip.nodes import build_plan_node

        state = _make_trip_state("规划北京 3 天旅行")
        result = await build_plan_node(state)

        assert result["travel_days"] == 3

    @pytest.mark.asyncio
    async def test_days_extraction_5(self):
        """测试提取 5 天"""
        from app.subgraphs.trip.nodes import build_plan_node

        state = _make_trip_state("去上海旅游 5 天")
        result = await build_plan_node(state)

        assert result["travel_days"] == 5

    @pytest.mark.asyncio
    async def test_default_days(self):
        """测试默认天数为 3"""
        from app.subgraphs.trip.nodes import build_plan_node

        state = _make_trip_state("去北京旅游")
        result = await build_plan_node(state)

        assert result["travel_days"] == 3

    @pytest.mark.asyncio
    async def test_plan_generated(self):
        """测试计划生成"""
        from app.subgraphs.trip.nodes import build_plan_node

        state = _make_trip_state("规划北京 3 天旅行")
        result = await build_plan_node(state)

        assert result["plan"] is not None
        assert "北京" in result["plan"]
        assert "3" in result["plan"]


class TestTripExecuteToolsNode:
    """测试旅行子图工具执行节点"""

    @pytest.mark.asyncio
    async def test_execute_tools_with_poi(self):
        """测试带 POI 数据的工具执行"""
        from app.subgraphs.trip.nodes import execute_tools_node

        mock_weather_service = MagicMock()
        mock_weather_service.get_weather = AsyncMock(return_value={
            "city": "北京",
            "province": "北京",
            "report_time": "2026-03-24 12:00:00",
            "casts": [
                {
                    "date": "2026-03-25",
                    "day_weather": "晴",
                    "night_weather": "晴",
                    "day_temp": "20",
                    "night_temp": "10"
                }
            ]
        })
        mock_weather_service.get_weather_summary = MagicMock(
            return_value="北京天气预报：\n2026-03-25: 白天晴 20°C, 夜间晴 10°C"
        )

        # Mock POI results for attractions
        attraction_result = ToolResult(
            success=True,
            data={
                "results": [
                    {"name": "故宫", "address": "北京市东城区", "type": "景点", "rating": "4.9"},
                    {"name": "天安门", "address": "北京市东城区", "type": "景点", "rating": "4.8"},
                    {"name": "颐和园", "address": "北京市海淀区", "type": "公园", "rating": "4.7"}
                ]
            },
            source="amap"
        )

        # Mock POI results for hotels
        hotel_result = ToolResult(
            success=True,
            data={
                "results": [
                    {"name": "北京饭店", "address": "北京市东城区", "rating": "4.5", "cost": "800"},
                    {"name": "王府井酒店", "address": "北京市东城区", "rating": "4.3", "cost": "600"}
                ]
            },
            source="amap"
        )

        state = _make_trip_state()
        state["city"] = "北京"
        state["travel_days"] = 3

        async def mock_search_poi(keyword, city):
            if keyword == "酒店":
                return hotel_result
            return attraction_result

        with patch("app.subgraphs.trip.nodes.get_weather_service", return_value=mock_weather_service), \
             patch("app.subgraphs.trip.nodes.search_poi", side_effect=mock_search_poi):
            result = await execute_tools_node(state)

        assert result["weather_info"] is not None
        assert result["weather_info"]["city"] == "北京"
        assert result["intermediate_result"] is not None
        assert "北京" in result["intermediate_result"]
        assert len(result["attractions"]) > 0
        assert result["attractions"][0]["name"] == "故宫"
        assert len(result["hotels"]) > 0
        assert result["hotels"][0]["name"] == "北京饭店"

    @pytest.mark.asyncio
    async def test_execute_tools_weather_failure(self):
        """测试天气获取失败时的降级处理"""
        from app.subgraphs.trip.nodes import execute_tools_node

        mock_weather_service = MagicMock()
        mock_weather_service.get_weather = AsyncMock(side_effect=Exception("天气 API 不可用"))

        state = _make_trip_state()
        state["city"] = "北京"
        state["travel_days"] = 3

        with patch("app.subgraphs.trip.nodes.get_weather_service", return_value=mock_weather_service), \
             patch("app.subgraphs.trip.tools.search_poi", side_effect=Exception("POI 不可用")):
            # The execute_tools_node uses a late import for search_poi:
            # from .tools import search_poi
            result = await execute_tools_node(state)

        assert "遇到问题" in result["intermediate_result"]
        assert result["attractions"] == []
        assert result["hotels"] == []

    @pytest.mark.asyncio
    async def test_execute_tools_empty_poi(self):
        """测试 POI 搜索返回空结果"""
        from app.subgraphs.trip.nodes import execute_tools_node

        mock_weather_service = MagicMock()
        mock_weather_service.get_weather = AsyncMock(return_value={
            "city": "测试城市",
            "casts": []
        })
        mock_weather_service.get_weather_summary = MagicMock(return_value="测试城市天气预报")

        empty_poi = ToolResult(success=False, data={"results": []}, source="amap")

        state = _make_trip_state()
        state["city"] = "测试城市"
        state["travel_days"] = 2

        with patch("app.subgraphs.trip.nodes.get_weather_service", return_value=mock_weather_service), \
             patch("app.subgraphs.trip.nodes.search_poi", return_value=empty_poi):
            result = await execute_tools_node(state)

        assert result["attractions"] == []
        assert result["hotels"] == []
