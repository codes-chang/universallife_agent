"""Search 子图 - 全网搜索"""

from langgraph.graph import StateGraph, START, END
from .state import SearchSubgraphState
from . import nodes
from ..base import BaseSubgraph


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
