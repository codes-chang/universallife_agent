"""Search 子图 - 全网搜索"""

from langgraph.graph import StateGraph, START, END
from .state import SearchSubgraphState
from . import nodes
from ..base import BaseSubgraph
from ...core.logging import logger
from ...memory.models import MemoryCandidate, MemoryType, MemoryScope


class SearchSubgraph(BaseSubgraph):
    """搜索子图

    使用 Tavily API 进行网络搜索。
    """

    def __init__(self):
        super().__init__("search")

    def get_state_class(self) -> type:
        return SearchSubgraphState

    def get_system_prompt(self) -> str:
        return """你是专业的信息搜索助手。帮助用户找到相关信息并整理成易读的摘要。

你的任务：
1. 理解用户的搜索意图
2. 使用搜索工具获取信息
3. 筛选最相关的结果
4. 整理成清晰的摘要

注意事项：
- 所有信息必须注明来源
- 标注信息的时间戳
- 不能编造不存在的信息
"""

    async def execute_domain_tools(self, state: SearchSubgraphState) -> str:
        """执行搜索工具"""
        from ...services.search_service import get_search_service

        query = state.get("search_query", state.get("task_input", ""))
        max_results = state.get("max_results", 5)

        search_service = get_search_service()
        search_result = await search_service.search(query, max_results=max_results)

        return search_service.format_search_results(search_result)

    async def generate_candidate_memories(self, state: SearchSubgraphState) -> SearchSubgraphState:
        """生成搜索相关的候选记忆"""
        candidates = []

        task_input = state.get("task_input", "")

        # 提取搜索偏好关键词
        preference_keywords = {
            "来源偏好": ["学术", "新闻", "官方", "博客", "论坛", "wiki"],
            "内容类型": ["教程", "论文", "文档", "代码", "数据", "报告"],
            "语言偏好": ["中文", "英文", "日文", "双语"]
        }

        extracted_preferences = []
        for pref_type, keywords in preference_keywords.items():
            for keyword in keywords:
                if keyword in task_input:
                    extracted_preferences.append(f"{pref_type}: {keyword}")

        # 生成偏好候选记忆
        for pref in extracted_preferences:
            candidate = MemoryCandidate(
                content=f"用户搜索偏好: {pref}",
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.DOMAIN,
                domain="search",
                importance=0.7,
                confidence=0.75,
                source="subgraph:search",
                metadata={"preference_type": "search_style", "original_query": task_input}
            )
            candidates.append(candidate.model_dump())

        # 如果执行成功，生成经验记忆
        final_result = state.get("final_result", "")
        if final_result and "失败" not in final_result:
            experience_candidate = MemoryCandidate(
                content=f"成功完成搜索任务: {task_input[:50]}...",
                memory_type=MemoryType.TASK_EPISODE,
                scope=MemoryScope.DOMAIN,
                domain="search",
                importance=0.5,
                confidence=0.6,
                source="subgraph:search",
                metadata={"task_type": "web_search"}
            )
            candidates.append(experience_candidate.model_dump())

        # 更新状态
        state["candidate_memories"] = candidates

        if candidates:
            logger.info(f"[SearchSubgraph] 生成 {len(candidates)} 个候选记忆")

        return state


def create_search_subgraph() -> StateGraph:
    """创建搜索子图工作流"""
    workflow = StateGraph(SearchSubgraphState)

    workflow.add_node("build_plan", nodes.build_plan_node)
    workflow.add_node("execute_tools", nodes.execute_tools_node)
    workflow.add_node("synthesize_result", nodes.synthesize_result_node)

    workflow.add_edge(START, "build_plan")
    workflow.add_edge("build_plan", "execute_tools")
    workflow.add_edge("execute_tools", "synthesize_result")
    workflow.add_edge("synthesize_result", END)

    return workflow.compile()


_search_subgraph = None


def get_search_subgraph() -> SearchSubgraph:
    """获取搜索子图实例"""
    global _search_subgraph
    if _search_subgraph is None:
        _search_subgraph = SearchSubgraph()
    return _search_subgraph
