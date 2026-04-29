"""LLM 服务模块 - OpenAI 兼容 API"""

import json
from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel

from ..core.config import settings
from ..core.logging import logger


# ============ 全局 LLM 实例 ============

_llm_instance: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
    """获取 LLM 实例（单例模式）

    Returns:
        ChatOpenAI 实例
    """
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY 未配置，请在 .env 文件中设置")

    try:
        _llm_instance = ChatOpenAI(
            model=settings.llm_model_id,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=settings.llm_temperature
        )
        logger.info(f"LLM 服务初始化成功: {_llm_instance.model_name}")
    except Exception as e:
        raise RuntimeError(f"LLM 服务初始化失败: {e}") from e

    return _llm_instance


def reset_llm():
    """重置 LLM 实例（用于测试）"""
    global _llm_instance
    _llm_instance = None


# ============ 结构化输出辅助函数 ============

async def call_llm_with_structured_output(
    prompt: str,
    system_prompt: str = None,
    output_schema: type[BaseModel] = None,
) -> dict:
    """调用 LLM 并获取结构化输出

    Args:
        prompt: 用户提示
        system_prompt: 系统提示
        output_schema: 输出 Schema（Pydantic 模型）

    Returns:
        解析后的结构化数据（字典格式）
    """
    llm = get_llm()

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    try:
        if output_schema and hasattr(llm, 'with_structured_output'):
            structured_llm = llm.with_structured_output(output_schema)
            result = await structured_llm.ainvoke(messages)
            return result.model_dump() if hasattr(result, 'model_dump') else result
        else:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 尝试解析 JSON
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

            return json.loads(content)
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        raise


# ============ 流式输出辅助函数 ============

async def stream_llm_response(
    prompt: str,
    system_prompt: str = None,
):
    """流式调用 LLM

    Args:
        prompt: 用户提示
        system_prompt: 系统提示

    Yields:
        响应片段
    """
    llm = get_llm()

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    if hasattr(llm, 'astream'):
        async for chunk in llm.astream(messages):
            yield chunk
    else:
        result = await llm.ainvoke(messages)
        yield result
