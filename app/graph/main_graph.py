"""主图 - 编排所有子图和节点"""

import asyncio
from datetime import datetime
from typing import Any

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage

from ..core.state import MainGraphState
from ..core.logging import logger
from ..core.prompts import SYNTHESIZER_SYSTEM_PROMPT
from ..services.llm_service import get_llm
from .router import route_intent_node
from .reviewer import reviewer_node, should_retry
from .recovery import recovery_node, graceful_degradation

# 记忆系统导入
from ..memory import memory_manager_node, prepare_memory_for_subgraph, memory_judge_node


# 子图导入
from ..subgraphs.outfit.graph import create_outfit_subgraph
from ..subgraphs.search.graph import create_search_subgraph
from ..subgraphs.finance.graph import create_finance_subgraph
from ..subgraphs.academic.graph import create_academic_subgraph
from ..subgraphs.trip.graph import create_trip_subgraph


def normalize_input_node(state: MainGraphState) -> MainGraphState:
    """
    输入归一化节点 - 清理和标准化用户输入

    Args:
        state: 主图状态

    Returns:
        更新后的状态
    """
    user_query = state.get("user_query", "")

    # 去除多余空白
    normalized = " ".join(user_query.strip().split())

    state["normalized_query"] = normalized

    logger.info(f"[MainGraph] 输入归一化: {user_query[:50]}...")

    return state


async def branch_to_subgraph_node(state: MainGraphState) -> MainGraphState:
    """
    分支到子图节点 - 根据路由结果执行相应子图

    Args:
        state: 主图状态

    Returns:
        更新后的状态
    """
    active_domain = state.get("active_domain", "unknown")
    user_query = state.get("user_query", "")
    router_result = state.get("router_result", {})
    memory_input = state.get("subgraph_memory_input")

    logger.info(f"[MainGraph] 执行 {active_domain} 子图...")

    try:
        # 获取并执行相应子图，传递记忆输入
        subgraph_result = await execute_subgraph(
            active_domain,
            user_query,
            router_result,
            memory_input
        )

        state["subgraph_outputs"] = state.get("subgraph_outputs", {})
        state["subgraph_outputs"][active_domain] = subgraph_result

    except Exception as e:
        logger.error(f"[MainGraph] 子图执行失败: {e}")
        state["subgraph_outputs"] = state.get("subgraph_outputs", {})
        state["subgraph_outputs"][active_domain] = {
            "result": f"执行失败: {str(e)}",
            "error": str(e)
        }

    return state


async def execute_subgraph(
    domain: str,
    task_input: str,
    router_result: dict,
    memory_input: dict = None
) -> dict:
    """
    执行指定域的子图

    Args:
        domain: 领域名称
        task_input: 任务输入
        router_result: 路由结果
        memory_input: 记忆输入

    Returns:
        子图执行结果
    """
    # 获取子图实例
    if domain == "outfit":
        from ..subgraphs.outfit.graph import get_outfit_subgraph
        subgraph = get_outfit_subgraph()
    elif domain == "search":
        from ..subgraphs.search.graph import get_search_subgraph
        subgraph = get_search_subgraph()
    elif domain == "finance":
        from ..subgraphs.finance.graph import get_finance_subgraph
        subgraph = get_finance_subgraph()
    elif domain == "academic":
        from ..subgraphs.academic.graph import get_academic_subgraph
        subgraph = get_academic_subgraph()
    elif domain == "trip":
        from ..subgraphs.trip.graph import get_trip_subgraph
        subgraph = get_trip_subgraph()
    else:
        # unknown 域，使用 search 作为默认
        from ..subgraphs.search.graph import get_search_subgraph
        subgraph = get_search_subgraph()

    # 执行子图，传递记忆输入
    result = await subgraph.run(task_input, memory_input=memory_input)

    return result


async def finalize_response_node(state: MainGraphState) -> MainGraphState:
    """
    最终响应节点 - 合成最终答案

    Args:
        state: 主图状态

    Returns:
        更新后的状态
    """
    logger.info("[MainGraph] 正在合成最终响应...")

    active_domain = state.get("active_domain", "unknown")
    subgraph_outputs = state.get("subgraph_outputs", {})
    router_result = state.get("router_result", {})

    # 获取子图输出
    domain_output = subgraph_outputs.get(active_domain, {})
    result = domain_output.get("result", "")

    if result:
        state["final_answer"] = result
    else:
        # 如果没有结果，生成默认响应
        state["final_answer"] = f"已完成 {active_domain} 领域的处理，但未能获取到有效结果。"

    return state


def route_condition(state: MainGraphState) -> str:
    """
    路由条件 - 决定下一步操作

    Args:
        state: 主图状态

    Returns:
        下一步节点名称
    """
    active_domain = state.get("active_domain", "unknown")

    # 映射到对应的子图节点
    domain_mapping = {
        "outfit": "outfit_subgraph",
        "search": "search_subgraph",
        "finance": "finance_subgraph",
        "academic": "academic_subgraph",
        "trip": "trip_subgraph"
    }

    return domain_mapping.get(active_domain, "search_subgraph")


def review_condition(state: MainGraphState) -> str:
    """
    审查条件 - 决定是否需要重试

    Args:
        state: 主图状态

    Returns:
        下一步操作: "recovery" 或 "finalize"
    """
    if should_retry(state):
        return "recovery"
    return "finalize"


def create_main_graph() -> StateGraph:
    """
    创建主图工作流

    主图流程（集成记忆系统）:
        START
          -> normalize_input
          -> memory_manager (检索记忆)
          -> route_intent
          -> prepare_memory (为子图准备记忆)
          -> branch_to_subgraph
          -> memory_judge (审查候选记忆)
          -> reviewer
            |-> [if pass] -> finalize_response -> END
            |-> [if fail] -> recovery -> reviewer

    Returns:
        编译后的 StateGraph
    """
    workflow = StateGraph(MainGraphState)

    # 添加节点
    workflow.add_node("normalize_input", normalize_input_node)
    workflow.add_node("memory_manager", memory_manager_node)
    workflow.add_node("route_intent", route_intent_node)
    workflow.add_node("prepare_memory", prepare_memory_for_subgraph)
    workflow.add_node("branch_to_subgraph", branch_to_subgraph_node)
    workflow.add_node("memory_judge", memory_judge_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("recovery", recovery_node)
    workflow.add_node("finalize_response", finalize_response_node)

    # 添加边
    workflow.add_edge(START, "normalize_input")
    workflow.add_edge("normalize_input", "memory_manager")
    workflow.add_edge("memory_manager", "route_intent")
    workflow.add_edge("route_intent", "prepare_memory")
    workflow.add_edge("prepare_memory", "branch_to_subgraph")
    workflow.add_edge("branch_to_subgraph", "memory_judge")
    workflow.add_edge("memory_judge", "reviewer")

    # 添加条件边
    workflow.add_conditional_edges(
        "reviewer",
        review_condition,
        {
            "recovery": "recovery",
            "finalize": "finalize_response"
        }
    )

    # 恢复后回到审查器
    workflow.add_edge("recovery", "reviewer")

    # 最终响应到结束
    workflow.add_edge("finalize_response", END)

    return workflow.compile()


# ============ 主图运行器 ============

class MainGraphRunner:
    """主图运行器 - 管理主图的执行"""

    def __init__(self):
        self.graph = create_main_graph()
        logger.info("✅ 主图初始化完成")

    async def run(self, user_query: str, session_id: str = None) -> dict:
        """
        运行主图

        Args:
            user_query: 用户查询
            session_id: 会话ID（可选）

        Returns:
            执行结果字典
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 开始处理用户查询: {user_query[:50]}...")
        logger.info(f"{'='*60}\n")

        # 使用 session_id 作为 user_id（简化处理）
        user_id = session_id or "default"

        # 构建初始状态
        initial_state: MainGraphState = {
            # 用户输入
            "user_query": user_query,
            "normalized_query": None,

            # 会话相关
            "session_id": session_id or user_id,
            "user_id": user_id,

            # 路由相关
            "router_result": None,
            "route_history": [],
            "active_domain": None,

            # 子图输出
            "subgraph_outputs": {},

            # 审查相关
            "review_result": None,
            "critique_history": [],

            # 最终输出
            "final_answer": None,

            # 用户反馈
            "user_feedback": None,

            # 重试控制
            "retry_count": 0,
            "max_retry": 3,

            # 记忆系统（初始化为空）
            "memory_bundle": None,
            "memory_context": None,
            "subgraph_memory_input": None,
            "memory_decisions": [],
            "candidate_memories": []
        }

        try:
            # 执行工作流
            final_state = initial_state
            async for output in self.graph.astream(initial_state):
                for node_name, node_output in output.items():
                    final_state = node_output
                    logger.debug(f"[MainGraph] 节点 {node_name} 完成")

            # 收集结果
            result = {
                "success": bool(final_state.get("final_answer")),
                "user_query": user_query,
                "router_result": final_state.get("router_result"),
                "active_domain": final_state.get("active_domain"),
                "subgraph_output": final_state.get("subgraph_outputs", {}).get(final_state.get("active_domain", ""), {}),
                "review_result": final_state.get("review_result"),
                "final_answer": final_state.get("final_answer", ""),
                "execution_trace": {
                    "route_history": final_state.get("route_history", []),
                    "critique_history": final_state.get("critique_history", []),
                    "retry_count": final_state.get("retry_count", 0),
                    "memory_decisions": final_state.get("memory_decisions", [])
                },
                "session_id": session_id,
                "memory_used": final_state.get("memory_bundle", {}).get("has_memory", False) if final_state.get("memory_bundle") else False
            }

            logger.info(f"\n{'='*60}")
            logger.info(f"✅ 查询处理完成")
            logger.info(f"   路由到: {final_state.get('active_domain')}")
            logger.info(f"   记忆: {'已使用' if result.get('memory_used') else '未使用'}")
            logger.info(f"{'='*60}\n")

            return result

        except Exception as e:
            logger.error(f"[MainGraph] 执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

            return {
                "success": False,
                "user_query": user_query,
                "error": str(e),
                "final_answer": f"抱歉，处理您的请求时遇到问题: {str(e)}"
            }


# 全局实例
_main_graph_runner = None


def get_main_graph_runner() -> MainGraphRunner:
    """获取主图运行器实例"""
    global _main_graph_runner
    if _main_graph_runner is None:
        _main_graph_runner = MainGraphRunner()
    return _main_graph_runner
