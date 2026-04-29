"""Trip 子图节点实现

从现有 helloagents-trip-planner 项目迁移并简化。
"""

import re
from ...services.llm_service import get_llm
from ...services.weather_service import get_weather_service
from ...core.logging import logger
from .state import TripSubgraphState


# Trip 规划 Prompt
TRIP_PLANNER_PROMPT = """你是旅行规划专家。请根据以下信息生成详细的旅行计划：

基本信息:
- 城市: {city}
- 天数: {days}天
- 天气: {weather}

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

    # 提取城市
    city_pattern = r'(?:去|游览|规划|旅游|旅行)\s*([a-zA-Z\u4e00-\u9fa5]+)(?:市|的)?'
    city_match = re.search(city_pattern, task_input)
    if city_match:
        state["city"] = city_match.group(1)
    else:
        # 尝试从开头提取城市
        words = task_input.split()
        state["city"] = words[0] if words else "北京"

    # 提取天数
    day_pattern = r'(\d+)\s*(?:天|日)'
    day_match = re.search(day_pattern, task_input)
    if day_match:
        state["travel_days"] = int(day_match.group(1))
    else:
        state["travel_days"] = 3

    state["plan"] = f"规划 {state['city']} {state['travel_days']} 日游"

    return state


async def execute_tools_node(state: TripSubgraphState) -> TripSubgraphState:
    """工具执行节点 - 获取天气信息"""
    logger.info("[Trip] 正在获取旅行相关信息...")

    city = state.get("city", "北京")
    days = state.get("travel_days", 3)

    try:
        weather_service = get_weather_service()
        weather_data = await weather_service.get_weather(city, days=days)

        state["weather_info"] = weather_data

        # 获取天气摘要
        weather_summary = weather_service.get_weather_summary(weather_data)
        state["intermediate_result"] = weather_summary

        # 生成模拟景点推荐
        state["attractions"] = generate_mock_attractions(city, days)
        state["hotels"] = generate_mock_hotels(city)

    except Exception as e:
        logger.error(f"[Trip] 信息获取失败: {e}")
        state["intermediate_result"] = f"获取 {city} 旅行信息时遇到问题"

    return state


async def synthesize_result_node(state: TripSubgraphState) -> TripSubgraphState:
    """结果合成节点 - 生成旅行计划"""
    logger.info("[Trip] 正在生成旅行计划...")

    try:
        llm = get_llm()

        city = state.get("city", "北京")
        days = state.get("travel_days", 3)
        weather_info = state.get("weather_info", {})
        attractions = state.get("attractions", [])

        # 构建天气摘要
        weather_text = ""
        if weather_info.get("casts"):
            casts = weather_info["casts"]
            weather_parts = []
            for cast in casts[:days]:
                weather_parts.append(f"{cast['date']}: {cast['day_weather']}, {cast['day_temp']}°C")
            weather_text = "\n".join(weather_parts)

        # 构建景点列表
        attractions_text = ""
        for attr in attractions:
            attractions_text += f"- {attr['name']}: {attr['description']}\n"

        prompt = TRIP_PLANNER_PROMPT.format(
            city=city,
            days=days,
            weather=weather_text if weather_text else "天气良好"
        )

        prompt += f"\n推荐景点:\n{attractions_text}"

        response = await llm.ainvoke([
            SystemMessage(content="你是旅行规划专家"),
            HumanMessage(content=prompt)
        ])

        content = response.content if hasattr(response, 'content') else str(response)

        # 尝试解析为结构化结果
        result_parts = [
            f"🌍 {city} {days}日游旅行计划",
            "",
            "🌤️ 天气预报:",
        ]

        if weather_text:
            for line in weather_text.split("\n"):
                result_parts.append(f"  {line}")

        result_parts.extend([
            "",
            "📋 每日行程:",
        ])

        # 如果有景点信息，添加到结果中
        for i in range(days):
            result_parts.append(f"\n第{i+1}天:")
            # 从 attractions 中选择合适的景点
            day_attractions = [a for a in attractions if a.get("day") == i + 1]
            if not day_attractions:
                day_attractions = attractions[i*2:(i+1)*2] if len(attractions) > i*2 else [attractions[0]] if attractions else []

            for attr in day_attractions[:2]:
                result_parts.append(f"  • {attr['name']}: {attr['description']}")

            result_parts.append(f"  🍽️ 餐饮: 推荐{city}特色美食")
            result_parts.append(f"  🚗 交通: 建议使用公共交通/打车")

        # 添加住宿建议
        hotels = state.get("hotels", [])
        if hotels:
            result_parts.append("\n🏨 住宿建议:")
            result_parts.append(f"  推荐: {hotels[0]['name']}")

        result_parts.extend([
            "",
            "💡 温馨提示:",
            "  - 请提前查看景点开放时间",
            "  - 注意天气变化，适当携带衣物",
            "  - 建议提前预订门票和酒店"
        ])

        state["final_result"] = "\n".join(result_parts)

    except Exception as e:
        logger.error(f"[Trip] 计划生成失败: {e}")
        city = state.get("city", "北京")
        days = state.get("travel_days", 3)
        state["final_result"] = f"为您规划的 {city} {days}日游行程，建议游览当地著名景点，品尝特色美食。"

    return state


def generate_mock_attractions(city: str, days: int) -> list:
    """生成模拟景点数据"""
    attractions = []

    templates = [
        {"name": f"{city}博物馆", "description": "了解当地历史文化"},
        {"name": f"{city}公园", "description": "休闲放松的好去处"},
        {"name": f"{city}古街", "description": "感受传统风情"},
        {"name": f"{city}塔", "description": "地标性建筑"},
        {"name": f"{city}湖", "description": "美丽的自然风光"},
        {"name": f"{city}艺术中心", "description": "现代文化艺术"},
    ]

    for i in range(min(days * 2, len(templates))):
        attractions.append({
            "day": (i // 2) + 1,
            **templates[i]
        })

    return attractions


def generate_mock_hotels(city: str) -> list:
    """生成模拟酒店数据"""
    return [
        {
            "name": f"{city}大酒店",
            "rating": "4.5",
            "price_range": "300-500元",
            "location": f"{city}市中心"
        },
        {
            "name": f"{city}快捷酒店",
            "rating": "4.0",
            "price_range": "200-300元",
            "location": f"{city}火车站附近"
        }
    ]
