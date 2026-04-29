"""Trip 子图 - 旅行规划

从现有 helloagents-trip-planner 项目迁移并改造。
"""

from langgraph.graph import StateGraph, START, END
from .state import TripSubgraphState
from . import nodes
from ..base import BaseSubgraph


class TripSubgraph(BaseSubgraph):
    """旅行子图

    提供旅行规划功能，集成现有的旅行规划能力。
    """

    def __init__(self):
        super().__init__("trip")

    def get_state_class(self) -> type:
        return TripSubgraphState

    def get_system_prompt(self) -> str:
        return """你是专业的旅行规划助手。为用户制定详细的旅行计划。

你的任务：
1. 了解目的地和旅行时间
2. 搜索景点、酒店、天气信息
3. 安排合理的行程路线
4. 提供实用的旅行建议

输出格式：
- 每日行程（含景点、餐饮）
- 交通建议
- 住宿推荐
- 实用提示
"""

    async def execute_domain_tools(self, state: TripSubgraphState) -> str:
        """执行旅行工具"""
        from ...services.weather_service import get_weather_service

        city = state.get("city", "北京")
        days = state.get("travel_days", 3)

        weather_service = get_weather_service()
        weather_data = await weather_service.get_weather(city, days=days)

        # 生成旅行计划
        plan_parts = [
            f"🌍 {city} {days}日游旅行计划",
            "",
            "🌤️ 天气预报:",
        ]

        casts = weather_data.get("casts", [])
        for cast in casts[:days]:
            plan_parts.append(f"  {cast['date']}: {cast['day_weather']}, {cast['day_temp']}°C")

        plan_parts.extend([
            "",
            "📋 每日行程建议:",
        ])

        for i in range(days):
            plan_parts.append(f"\n第{i+1}天:")
            plan_parts.append("  • 游览当地著名景点")
            plan_parts.append("  • 品尝特色美食")
            plan_parts.append("  • 体验当地文化")

        plan_parts.extend([
            "",
            "🏨 住宿建议: 推荐市中心交通便利的酒店",
            "",
            "💡 温馨提示:",
            "  - 请提前查看景点开放时间",
            "  - 注意天气变化，适当携带衣物",
            "  - 建议提前预订门票和酒店"
        ])

        return "\n".join(plan_parts)


def create_trip_subgraph() -> StateGraph:
    """创建旅行子图工作流"""
    workflow = StateGraph(TripSubgraphState)

    workflow.add_node("build_plan", nodes.build_plan_node)
    workflow.add_node("execute_tools", nodes.execute_tools_node)
    workflow.add_node("synthesize_result", nodes.synthesize_result_node)

    workflow.add_edge(START, "build_plan")
    workflow.add_edge("build_plan", "execute_tools")
    workflow.add_edge("execute_tools", "synthesize_result")
    workflow.add_edge("synthesize_result", END)

    return workflow.compile()


_trip_subgraph = None


def get_trip_subgraph() -> TripSubgraph:
    """获取旅行子图实例"""
    global _trip_subgraph
    if _trip_subgraph is None:
        _trip_subgraph = TripSubgraph()
    return _trip_subgraph
