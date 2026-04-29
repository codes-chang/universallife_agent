"""Trip 子图节点实现"""

import re
from ...services.llm_service import get_llm
from ...services.weather_service import get_weather_service
from ...core.logging import logger
from .state import TripSubgraphState


TRIP_PLANNER_PROMPT = """你是旅行规划专家。请根据以下信息生成详细的旅行计划：

基本信息:
- 城市: {city}
- 天数: {days}天
- 天气: {weather}

推荐景点:
{attractions}

推荐酒店:
{hotels}

请输出 JSON 格式的旅行计划，包含：
1. 每日行程安排（景点、餐饮）
2. 交通建议
3. 住宿建议
4. 实用提示

输出格式示例:
```json
{{
  "daily_plans": [
    {{
      "day": 1,
      "attractions": ["景点1", "景点2"],
      "meals": {{"breakfast": "早餐推荐", "lunch": "午餐推荐", "dinner": "晚餐推荐"}},
      "transportation": "交通方式"
    }}
  ],
  "accommodation": "住宿建议",
  "tips": ["提示1", "提示2"]
}}
```
"""


async def build_plan_node(state: TripSubgraphState) -> TripSubgraphState:
    """规划节点 - 分析旅行需求"""
    logger.info("[Trip] 正在分析旅行需求...")

    task_input = state.get("task_input", "")

    city_pattern = r'(?:去|游览|规划|旅游|旅行)\s*([a-zA-Z一-龥]+)(?:市|的)?'
    city_match = re.search(city_pattern, task_input)
    if city_match:
        state["city"] = city_match.group(1)
    else:
        words = task_input.split()
        state["city"] = words[0] if words else "北京"

    day_pattern = r'(\d+)\s*(?:天|日)'
    day_match = re.search(day_pattern, task_input)
    if day_match:
        state["travel_days"] = int(day_match.group(1))
    else:
        state["travel_days"] = 3

    state["plan"] = f"规划 {state['city']} {state['travel_days']} 日游"

    return state


async def execute_tools_node(state: TripSubgraphState) -> TripSubgraphState:
    """工具执行节点 - 获取天气和 POI 信息"""
    logger.info("[Trip] 正在获取旅行相关信息...")

    city = state.get("city", "北京")
    days = state.get("travel_days", 3)

    try:
        # 获取天气
        weather_service = get_weather_service()
        weather_data = await weather_service.get_weather(city, days=days)
        state["weather_info"] = weather_data
        state["intermediate_result"] = weather_service.get_weather_summary(weather_data)
    except Exception as e:
        logger.error(f"[Trip] 天气获取失败: {e}")
        state["intermediate_result"] = f"获取 {city} 天气信息时遇到问题"

    # 获取真实景点数据
    try:
        from .tools import search_poi

        attractions = []
        for keyword in ["景点", "公园", "博物馆"]:
            result = await search_poi(keyword, city)
            if result.success and result.data.get("results"):
                for poi in result.data["results"][:3]:
                    attractions.append({
                        "name": poi.get("name", ""),
                        "description": f"{poi.get('address', '')} | 评分: {poi.get('rating', 'N/A')}",
                        "type": poi.get("type", ""),
                    })

        state["attractions"] = attractions[:days * 2] if attractions else []
    except Exception as e:
        logger.warning(f"[Trip] 景点搜索失败: {e}")
        state["attractions"] = []

    # 获取真实酒店数据
    try:
        from .tools import search_poi

        result = await search_poi("酒店", city)
        if result.success and result.data.get("results"):
            state["hotels"] = [
                {
                    "name": h.get("name", ""),
                    "rating": h.get("rating", ""),
                    "price_range": h.get("cost", "价格未知"),
                    "location": h.get("address", ""),
                }
                for h in result.data["results"][:5]
            ]
        else:
            state["hotels"] = []
    except Exception as e:
        logger.warning(f"[Trip] 酒店搜索失败: {e}")
        state["hotels"] = []

    return state


async def synthesize_result_node(state: TripSubgraphState) -> TripSubgraphState:
    """结果合成节点 - 生成旅行计划"""
    logger.info("[Trip] 正在生成旅行计划...")

    try:
        llm = get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        city = state.get("city", "北京")
        days = state.get("travel_days", 3)
        weather_info = state.get("weather_info", {})
        attractions = state.get("attractions", [])
        hotels = state.get("hotels", [])

        # 构建天气摘要
        weather_text = ""
        if weather_info.get("casts"):
            weather_parts = []
            for cast in weather_info["casts"][:days]:
                weather_parts.append(f"{cast['date']}: {cast['day_weather']}, {cast['day_temp']}°C")
            weather_text = "\n".join(weather_parts)

        # 构建景点列表
        attractions_text = ""
        for i, attr in enumerate(attractions[:days * 2], 1):
            attractions_text += f"{i}. {attr['name']} - {attr['description']}\n"

        # 构建酒店列表
        hotels_text = ""
        for h in hotels[:3]:
            hotels_text += f"- {h['name']} ({h.get('rating', 'N/A')}分, {h.get('price_range', '')})\n"

        prompt = TRIP_PLANNER_PROMPT.format(
            city=city,
            days=days,
            weather=weather_text if weather_text else "天气良好",
            attractions=attractions_text if attractions_text else "暂无具体景点信息",
            hotels=hotels_text if hotels_text else "暂无具体酒店信息"
        )

        response = await llm.ainvoke([
            SystemMessage(content="你是旅行规划专家，请根据提供的真实数据生成实用的旅行计划。"),
            HumanMessage(content=prompt)
        ])

        content = response.content if hasattr(response, 'content') else str(response)

        # 构建最终结果
        result_parts = [
            f"{city} {days}日游旅行计划",
            "",
            "天气预报:",
        ]

        if weather_text:
            for line in weather_text.split("\n"):
                result_parts.append(f"  {line}")

        result_parts.extend(["", "推荐景点:"])
        for attr in attractions[:days * 2]:
            result_parts.append(f"  - {attr['name']}: {attr['description']}")

        if hotels:
            result_parts.extend(["", "推荐酒店:"])
            for h in hotels[:3]:
                result_parts.append(f"  - {h['name']} (评分: {h.get('rating', 'N/A')}, {h.get('price_range', '')})")

        result_parts.extend([
            "",
            "AI 行程建议:",
            content if content else "建议游览上述景点，品尝当地特色美食。",
            "",
            "温馨提示:",
            "  - 请提前查看景点开放时间和门票信息",
            "  - 注意天气变化，适当携带衣物",
            "  - 建议提前预订酒店",
            f"  - 数据来源: 高德地图 POI + 实时天气"
        ])

        state["final_result"] = "\n".join(result_parts)

    except Exception as e:
        logger.error(f"[Trip] 计划生成失败: {e}")
        city = state.get("city", "北京")
        days = state.get("travel_days", 3)
        state["final_result"] = f"为您规划的 {city} {days}日游行程。请查看上述景点和酒店推荐。"

    return state
