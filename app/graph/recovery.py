"""恢复与重路由逻辑"""

from datetime import datetime

from ..core.logging import logger
from .router import detect_negative_feedback


async def recovery_node(state: dict) -> dict:
    """
    恢复节点 - 处理审查失败或负反馈情况

    Args:
        state: 当前主图状态

    Returns:
        更新后的状态
    """
    logger.info("[Recovery] 正在执行恢复逻辑...")

    user_feedback = state.get("user_feedback", "")
    review_result = state.get("review_result", {})
    active_domain = state.get("active_domain", "")

    # 增加重试计数
    state["retry_count"] = state.get("retry_count", 0) + 1

    # 如果有负反馈，触发重路由
    if user_feedback and detect_negative_feedback(user_feedback):
        logger.info("[Recovery] 检测到负反馈，触发重路由")
        state = await handle_negative_feedback(state)
        return state

    # 如果审查不通过，触发回溯
    if not review_result.get("passed", True):
        logger.info("[Recovery] 审查不通过，触发回溯")
        return await handle_review_failure(state)

    # 默认返回原状态
    return state


async def handle_negative_feedback(state: dict) -> dict:
    """
    处理负反馈

    Args:
        state: 当前主图状态

    Returns:
        更新后的状态
    """
    user_feedback = state.get("user_feedback", "")
    route_history = state.get("route_history", [])

    # 标记当前意图为失败
    current_intent = state.get("active_domain", "")
    for attempt in route_history:
        if attempt["intent"] == current_intent:
            attempt["failed"] = True
            attempt["failure_reason"] = f"用户负反馈: {user_feedback}"

    state["route_history"] = route_history

    # 触发重路由
    from .router import route_with_higher_confidence
    state = await route_with_higher_confidence(state)

    # 清空子图输出以便重新执行
    state["subgraph_outputs"] = {}

    return state


async def handle_review_failure(state: dict) -> dict:
    """
    处理审查失败

    Args:
        state: 当前主图状态

    Returns:
        更新后的状态
    """
    review_result = state.get("review_result", {})
    violations = review_result.get("violations", [])
    suggestions = review_result.get("suggestions", [])

    logger.info(f"[Recovery] 审查失败原因: {violations}")

    # 将审查意见注入到子图输入中
    active_domain = state.get("active_domain", "")
    subgraph_outputs = state.get("subgraph_outputs", {})

    # 添加改进建议到任务输入
    original_query = state.get("user_query", "")
    improvement_hint = f"\n\n改进要求:\n" + "\n".join(f"- {s}" for s in suggestions)

    state["user_query"] = original_query + improvement_hint

    # 清空该域的输出，强制重新执行
    if active_domain in subgraph_outputs:
        del subgraph_outputs[active_domain]

    state["subgraph_outputs"] = subgraph_outputs

    return state


async def graceful_degradation(state: dict) -> dict:
    """
    优雅降级 - 达到最大重试次数后返回当前最佳结果

    Args:
        state: 当前主图状态

    Returns:
        更新后的状态
    """
    logger.info("[Recovery] 达到最大重试次数，执行优雅降级")

    active_domain = state.get("active_domain", "")
    subgraph_outputs = state.get("subgraph_outputs", {})

    # 获取当前域的输出
    domain_output = subgraph_outputs.get(active_domain, {})
    result = domain_output.get("result", "")

    if not result:
        # 如果没有输出，生成默认响应
        result = generate_default_response(state)

    state["final_answer"] = result

    return state


def generate_default_response(state: dict) -> str:
    """生成默认响应"""
    active_domain = state.get("active_domain", "unknown")
    user_query = state.get("user_query", "")

    responses = {
        "outfit": f"抱歉，我暂时无法为您的穿搭需求提供建议。请提供更多关于地点、场合的信息。",
        "search": f"抱歉，搜索服务暂时不可用。您可以尝试稍后重试或使用其他搜索引擎。",
        "finance": f"抱歉，金融查询服务暂时不可用。请稍后重试。",
        "academic": f"抱歉，学术资源查询服务暂时不可用。请稍后重试。",
        "trip": f"抱歉，旅行规划服务暂时不可用。请提供更多关于目的地和时间的信息。",
        "unknown": f"抱歉，我暂时无法处理您的请求。请尝试更具体地描述您的需求。"
    }

    return responses.get(active_domain, responses["unknown"])
