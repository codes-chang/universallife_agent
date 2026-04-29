"""Outfit 子图 - 穿搭建议"""

import json
from langgraph.graph import StateGraph, START, END
from .state import OutfitSubgraphState
from . import nodes
from ..base import BaseSubgraph
from ...core.logging import logger
from ...memory.models import MemoryCandidate, MemoryType, MemoryScope


class OutfitSubgraph(BaseSubgraph):
    """穿搭子图

    根据天气、场合提供穿搭建议，支持记忆功能。
    """

    def __init__(self):
        super().__init__("outfit")

    def get_state_class(self) -> type:
        return OutfitSubgraphState

    def get_system_prompt(self) -> str:
        return """你是专业的穿搭顾问。你的任务是根据天气、场合为用户提供合适的穿搭建议。

请考虑：
1. 天气条件（温度、降水、风力）
2. 穿搭场合（通勤、休闲、运动、正式）
3. 个人风格偏好
4. 实用性和舒适度

提供具体的穿搭建议，包括：
- 上装（外套、内搭）
- 下装（裤子、裙子）
- 鞋子
- 配饰（帽子、包、饰品等）

每件单品需说明推荐理由。
"""

    async def execute_domain_tools(self, state: OutfitSubgraphState) -> str:
        """执行领域特定工具"""
        from ...services.weather_service import get_weather_service

        location = state.get("location", "上海")
        weather_service = get_weather_service()
        weather_data = await weather_service.get_weather(location, days=1)

        return json.dumps({
            "location": location,
            "weather": weather_data
        }, ensure_ascii=False)

    async def generate_candidate_memories(self, state: OutfitSubgraphState) -> OutfitSubgraphState:
        """生成穿搭相关的候选记忆"""
        candidates = []

        task_input = state.get("task_input", "")
        intermediate_result = state.get("intermediate_result", "")

        # 尝试提取用户偏好
        preference_keywords = {
            "风格": ["休闲", "正式", "运动", "简约", "复古", "街头"],
            "颜色": ["黑色", "白色", "灰色", "蓝色", "红色", "绿色"],
            "场合": ["通勤", "约会", "运动", "旅行", "正式"]
        }

        extracted_preferences = []
        for pref_type, keywords in preference_keywords.items():
            for keyword in keywords:
                if keyword in task_input:
                    extracted_preferences.append(f"{pref_type}: {keyword}")

        # 生成偏好候选记忆
        for pref in extracted_preferences:
            candidate = MemoryCandidate(
                content=f"用户穿搭偏好: {pref}",
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.DOMAIN,
                domain="outfit",
                importance=0.7,
                confidence=0.75,
                source="subgraph:outfit",
                metadata={"preference_type": "style", "original_query": task_input}
            )
            candidates.append(candidate.model_dump())

        # 如果执行成功，生成经验记忆
        final_result = state.get("final_result", "")
        if final_result and "失败" not in final_result:
            experience_candidate = MemoryCandidate(
                content=f"成功完成穿搭建议任务: {task_input[:50]}...",
                memory_type=MemoryType.TASK_EPISODE,
                scope=MemoryScope.DOMAIN,
                domain="outfit",
                importance=0.5,
                confidence=0.6,
                source="subgraph:outfit",
                metadata={"task_type": "outfit_advice"}
            )
            candidates.append(experience_candidate.model_dump())

        # 更新状态
        state["candidate_memories"] = candidates

        if candidates:
            logger.info(f"[OutfitSubgraph] 生成 {len(candidates)} 个候选记忆")

        return state


def create_outfit_subgraph() -> StateGraph:
    """创建穿搭子图工作流"""
    workflow = StateGraph(OutfitSubgraphState)

    workflow.add_node("build_plan", nodes.build_plan_node)
    workflow.add_node("execute_tools", nodes.execute_tools_node)
    workflow.add_node("synthesize_result", nodes.synthesize_result_node)

    workflow.add_edge(START, "build_plan")
    workflow.add_edge("build_plan", "execute_tools")
    workflow.add_edge("execute_tools", "synthesize_result")
    workflow.add_edge("synthesize_result", END)

    return workflow.compile()


# 全局实例
_outfit_subgraph = None


def get_outfit_subgraph() -> OutfitSubgraph:
    """获取穿搭子图实例"""
    global _outfit_subgraph
    if _outfit_subgraph is None:
        _outfit_subgraph = OutfitSubgraph()
    return _outfit_subgraph
