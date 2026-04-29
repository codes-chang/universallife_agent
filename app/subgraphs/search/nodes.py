"""Search 子图节点实现"""

from ...services.llm_service import get_llm
from ...services.search_service import get_search_service
from ...core.logging import logger
from .state import SearchSubgraphState


async def build_plan_node(state: SearchSubgraphState) -> SearchSubgraphState:
    """规划节点 - 分析搜索需求"""
    logger.info("[Search] 正在分析搜索需求...")

    task_input = state.get("task_input", "")

    # 直接使用用户输入作为搜索查询
    state["search_query"] = task_input
    state["max_results"] = 5
    state["plan"] = f"搜索关于 '{task_input}' 的相关信息"

    return state


async def execute_tools_node(state: SearchSubgraphState) -> SearchSubgraphState:
    """工具执行节点 - 执行搜索"""
    logger.info("[Search] 正在执行搜索...")

    query = state.get("search_query", "")
    max_results = state.get("max_results", 5)

    try:
        search_service = get_search_service()
        search_result = await search_service.search(query, max_results=max_results)

        state["search_results"] = search_result.get("results", [])
        state["sources"] = [r.get("url", "") for r in search_result.get("results", [])]

        # 格式化中间结果
        formatted = search_service.format_search_results(search_result)
        state["intermediate_result"] = formatted

    except Exception as e:
        logger.error(f"[Search] 搜索失败: {e}")
        state["intermediate_result"] = f"搜索 '{query}' 时遇到问题: {str(e)}"

    return state


async def synthesize_result_node(state: SearchSubgraphState) -> SearchSubgraphState:
    """结果合成节点 - 整理搜索结果"""
    logger.info("[Search] 正在整理搜索结果...")

    # 如果中间结果已经格式化，直接使用
    intermediate = state.get("intermediate_result", "")
    if intermediate and len(intermediate) > 50:
        state["final_result"] = intermediate
    else:
        state["final_result"] = f"为您找到关于 '{state.get('search_query', '')}' 的相关信息，请查看详细结果。"

    return state
