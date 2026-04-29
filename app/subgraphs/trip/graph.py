"""Trip 子图 - 旅行规划

从现有 helloagents-trip-planner 项目迁移并改造。
"""

from langgraph.graph import StateGraph, START, END
from .state import TripSubgraphState
from . import nodes
from ..base import BaseSubgraph
from ...core.logging import logger
from ...memory.models import MemoryCandidate, MemoryType, MemoryScope


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

    async def generate_candidate_memories(self, state: TripSubgraphState) -> TripSubgraphState:
        """生成旅行相关的候选记忆"""
        candidates = []

        task_input = state.get("task_input", "")

        # 提取旅行偏好关键词
        preference_keywords = {
            "旅行节奏": ["休闲", "紧凑", "深度游", "打卡", "慢游", "自由行"],
            "住宿偏好": ["酒店", "民宿", "青旅", "度假村", "快捷", "高档"],
            "出行方式": ["自驾", "高铁", "飞机", "徒步", "骑行", "公共交通"],
            "目的地偏好": ["海边", "山区", "城市", "古镇", "自然", "文化"]
        }

        extracted_preferences = []
        for pref_type, keywords in preference_keywords.items():
            for keyword in keywords:
                if keyword in task_input:
                    extracted_preferences.append(f"{pref_type}: {keyword}")

        # 生成偏好候选记忆
        for pref in extracted_preferences:
            candidate = MemoryCandidate(
                content=f"用户旅行偏好: {pref}",
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.DOMAIN,
                domain="trip",
                importance=0.7,
                confidence=0.75,
                source="subgraph:trip",
                metadata={"preference_type": "trip_style", "original_query": task_input}
            )
            candidates.append(candidate.model_dump())

        # 如果执行成功，生成经验记忆
        final_result = state.get("final_result", "")
        if final_result and "失败" not in final_result:
            experience_candidate = MemoryCandidate(
                content=f"成功完成旅行规划任务: {task_input[:50]}...",
                memory_type=MemoryType.TASK_EPISODE,
                scope=MemoryScope.DOMAIN,
                domain="trip",
                importance=0.5,
                confidence=0.6,
                source="subgraph:trip",
                metadata={"task_type": "trip_planning"}
            )
            candidates.append(experience_candidate.model_dump())

        # 更新状态
        state["candidate_memories"] = candidates

        if candidates:
            logger.info(f"[TripSubgraph] 生成 {len(candidates)} 个候选记忆")

        return state


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
