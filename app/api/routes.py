"""API 路由定义"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from ..core.models import (
    ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse,
    RouterResultModel, ReviewResultModel, ExecutionTraceItem, ErrorResponse
)
from ..core.logging import logger
from ..graph.main_graph import get_main_graph_runner
from ..graph.router import detect_negative_feedback

router = APIRouter(prefix="/api", tags=["chat"])


# 会话存储（生产环境应使用 Redis 等）
_sessions = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口 - 处理用户查询

    Args:
        request: 聊天请求

    Returns:
        聊天响应
    """
    try:
        logger.info(f"[API] 收到聊天请求: {request.message[:50]}...")

        # 获取主图运行器
        runner = get_main_graph_runner()

        # 执行查询
        result = await runner.run(request.message, request.session_id)

        # 转换为响应模型
        router_result = None
        if result.get("router_result"):
            router_data = result["router_result"]
            router_result = RouterResultModel(**router_data)

        review_result = None
        if result.get("review_result"):
            review_data = result["review_result"]
            review_result = ReviewResultModel(**review_data)

        # 构建执行轨迹
        trace = []
        for attempt in result.get("execution_trace", {}).get("route_history", []):
            trace.append(ExecutionTraceItem(
                step="route",
                domain=attempt.get("intent"),
                timestamp=attempt.get("timestamp", ""),
                status="failed" if attempt.get("failed") else "success",
                details={"confidence": attempt.get("confidence")}
            ))

        for critique in result.get("execution_trace", {}).get("critique_history", []):
            trace.append(ExecutionTraceItem(
                step="review",
                domain=critique.get("domain"),
                timestamp=critique.get("timestamp", ""),
                status="failed" if not critique.get("passed") else "success",
                details={"score": critique.get("score"), "violations": critique.get("violations")}
            ))

        return ChatResponse(
            success=result.get("success", False),
            message="处理完成" if result.get("success") else "处理失败",
            router_result=router_result,
            active_domain=result.get("active_domain"),
            subgraph_output=result.get("subgraph_output"),
            review_result=review_result,
            final_answer=result.get("final_answer"),
            execution_trace=trace,
            session_id=request.session_id
        )

    except Exception as e:
        logger.error(f"[API] 聊天处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="处理请求时发生错误",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            ).model_dump()
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest):
    """
    反馈接口 - 处理用户负反馈并触发重路由

    Args:
        request: 反馈请求

    Returns:
        反馈响应
    """
    try:
        logger.info(f"[API] 收到用户反馈: {request.message[:50]}...")

        # 检测是否为负反馈
        is_negative = detect_negative_feedback(request.message)

        if not is_negative:
            return FeedbackResponse(
                success=True,
                message="感谢您的反馈",
                detected_negative=False,
                rerouted=False
            )

        # 如果有会话ID，获取上下文
        session_context = None
        if request.session_id and request.session_id in _sessions:
            session_context = _sessions[request.session_id]

        # 触发重路由
        if session_context:
            # 使用原查询重新处理
            original_query = session_context.get("last_query", "")
            state = session_context.get("last_state", {})

            # 添加用户反馈
            state["user_feedback"] = request.message

            # 重新处理
            from ..graph.recovery import handle_negative_feedback
            updated_state = await handle_negative_feedback(state)

            # 获取新的意图
            new_intent = updated_state.get("active_domain", "unknown")

            # 执行新的子图
            runner = get_main_graph_runner()
            result = await runner.run(original_query, request.session_id)

            return FeedbackResponse(
                success=True,
                message="已根据您的反馈重新处理",
                detected_negative=True,
                rerouted=True,
                new_intent=new_intent,
                response=result.get("final_answer")
            )
        else:
            return FeedbackResponse(
                success=True,
                message="负反馈已记录，但由于无会话上下文，无法重新处理",
                detected_negative=True,
                rerouted=False
            )

    except Exception as e:
        logger.error(f"[API] 反馈处理失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="处理反馈时发生错误",
                error_code="FEEDBACK_ERROR"
            ).model_dump()
        )


@router.get("/health")
async def health_check():
    """
    健康检查接口

    Returns:
        服务状态
    """
    from ..core.config import settings

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "llm_model": settings.llm_model_id
    }


@router.get("/")
async def root():
    """
    根路径

    Returns:
        服务信息
    """
    from ..core.config import settings

    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "基于 LangGraph 的全场景通用智能助手",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health"
    }
