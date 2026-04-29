"""语义路由器 - 识别用户意图并路由到相应子图"""

import json
import asyncio
from typing import TypedDict, Literal
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from ..core.state import RouterResult, RouteAttempt
from ..core.prompts import ROUTER_SYSTEM_PROMPT, ROUTER_RETRIES_PROMPT
from ..core.logging import logger
from ..services.llm_service import get_llm


# 支持的意图类型
SUPPORTED_INTENTS = ["outfit", "search", "finance", "academic", "trip", "unknown"]


async def route_intent_node(state: dict) -> dict:
    """
    路由节点 - 识别用户意图

    Args:
        state: 当前主图状态

    Returns:
        更新后的状态
    """
    user_query = state.get("user_query", "")
    route_history = state.get("route_history", [])
    failed_intents = [r["intent"] for r in route_history if r.get("failed", False)]
    memory_context = state.get("memory_context")

    logger.info(f"[Router] 正在路由用户查询: {user_query[:50]}...")

    try:
        llm = get_llm()

        # 构建基础系统提示
        system_prompt = ROUTER_SYSTEM_PROMPT

        # 如果有记忆上下文，添加到提示中
        if memory_context:
            system_prompt += f"""

以下是与用户相关的历史记忆，可以帮助更准确地识别意图：

{memory_context}

请结合这些记忆来判断用户当前的意图。
"""

        # 如果有失败的路由历史，在提示中包含
        if failed_intents:
            retry_prompt = ROUTER_RETRIES_PROMPT.format(
                failed_intent=failed_intents[-1] if failed_intents else "",
                user_feedback=state.get("user_feedback", ""),
                original_query=user_query,
                failed_intents=str(failed_intents)
            )
            system_prompt += "\n\n" + retry_prompt

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]

        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)

        # 解析 JSON 结果
        router_result = parse_router_response(content)

        # 检查置信度
        confidence = router_result.get("confidence", 0.0)

        # 如果置信度低于阈值且没有重试过，触发重路由
        if confidence < 0.7 and state.get("retry_count", 0) < 2:
            logger.info(f"[Router] 置信度 {confidence} 低于阈值，触发重路由")
            # 记录低置信度路由
            state["route_history"] = route_history + [{
                "intent": router_result.get("primary_intent"),
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "failed": False,
                "failure_reason": "Low confidence"
            }]
            state["retry_count"] = state.get("retry_count", 0) + 1
            # 重新路由
            return await route_with_higher_confidence(state)

        # 记录路由尝试
        route_attempt: RouteAttempt = {
            "intent": router_result.get("primary_intent"),
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "failed": False,
            "failure_reason": None
        }

        state["router_result"] = router_result
        state["route_history"] = route_history + [route_attempt]
        state["active_domain"] = router_result.get("primary_intent")

        logger.info(f"[Router] 路由到: {router_result.get('primary_intent')} (置信度: {confidence})")

    except Exception as e:
        logger.error(f"[Router] 路由失败: {e}")
        # 默认路由到 search
        state["router_result"] = {
            "primary_intent": "search",
            "secondary_intents": [],
            "confidence": 0.5,
            "reasoning": "路由失败，使用默认路由",
            "constraints": {}
        }
        state["active_domain"] = "search"

    return state


async def route_with_higher_confidence(state: dict) -> dict:
    """
    重路由 - 使用更强的提示尝试获取更高置信度
    """
    user_query = state.get("user_query", "")

    logger.info("[Router] 尝试重路由...")

    try:
        llm = get_llm()

        # 更明确的提示
        prompt = f"""请仔细分析以下用户查询，确定最合适的意图类型。

支持的意图类型：
1. outfit - 穿搭建议（关键词: 穿搭、搭配、衣服、穿什么）
2. search - 全网搜索（关键词: 搜索、查找、找）
3. finance - 金融购物（关键词: 股票、价格、多少钱、买）
4. academic - 学术办公（关键词: GitHub、论文、代码）
5. trip - 旅行规划（关键词: 旅行、旅游、景点）

用户查询: {user_query}

请直接输出最合适的意图类型（outfit/search/finance/academic/trip）。
"""

        response = await llm.ainvoke([
            SystemMessage(content="你是意图分类专家。请直接输出最合适的意图类型。"),
            HumanMessage(content=prompt)
        ])

        content = response.content if hasattr(response, 'content') else str(response).strip().lower()

        # 从响应中提取意图
        for intent in SUPPORTED_INTENTS:
            if intent in content:
                state["active_domain"] = intent
                state["router_result"] = {
                    "primary_intent": intent,
                    "secondary_intents": [],
                    "confidence": 0.8,
                    "reasoning": f"通过重路由识别为 {intent}",
                    "constraints": {}
                }
                logger.info(f"[Router] 重路由成功: {intent}")
                break
        else:
            # 仍无法确定，使用 search 作为默认
            state["active_domain"] = "search"
            state["router_result"] = {
                "primary_intent": "search",
                "secondary_intents": [],
                "confidence": 0.6,
                "reasoning": "重路由后仍不确定，使用默认",
                "constraints": {}
            }

    except Exception as e:
        logger.error(f"[Router] 重路由失败: {e}")
        state["active_domain"] = "search"

    return state


def parse_router_response(content: str) -> dict:
    """解析路由器响应"""
    # 尝试提取 JSON
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        content = content[start:end].strip()
    elif "{" in content:
        start = content.find("{")
        end = content.rfind("}") + 1
        content = content[start:end]

    try:
        result = json.loads(content)

        # 验证 primary_intent
        primary_intent = result.get("primary_intent", "unknown")
        if primary_intent not in SUPPORTED_INTENTS:
            primary_intent = "unknown"

        result["primary_intent"] = primary_intent
        return result

    except json.JSONDecodeError:
        # JSON 解析失败，尝试从文本中提取
        content_lower = content.lower()
        for intent in SUPPORTED_INTENTS:
            if intent in content_lower:
                return {
                    "primary_intent": intent,
                    "secondary_intents": [],
                    "confidence": 0.7,
                    "reasoning": f"从文本中识别为 {intent}",
                    "constraints": {}
                }

        # 默认返回 unknown
        return {
            "primary_intent": "unknown",
            "secondary_intents": [],
            "confidence": 0.5,
            "reasoning": "无法解析路由结果",
            "constraints": {}
        }


def detect_negative_feedback(feedback: str) -> bool:
    """
    检测负反馈

    Args:
        feedback: 用户反馈文本

    Returns:
        是否为负反馈
    """
    from ..core.prompts import NEGATIVE_FEEDBACK_KEYWORDS

    feedback_lower = feedback.lower()
    for keyword in NEGATIVE_FEEDBACK_KEYWORDS:
        if keyword.lower() in feedback_lower:
            return True

    return False
