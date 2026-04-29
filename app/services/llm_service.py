"""LLM 服务模块 - 支持 OpenAI 兼容 API 和 Mock 模式"""

import os
import json
from typing import Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import LLMResult
from pydantic import BaseModel

from ..core.config import settings
from ..core.logging import logger


# ============ 全局 LLM 实例 ============

_llm_instance: Optional[ChatOpenAI] = None
_mock_llm_instance: Optional["MockLLM"] = None


class MockLLMResponse(BaseModel):
    """Mock LLM 响应"""
    content: str
    tool_calls: List[dict] = []


class MockLLM:
    """Mock LLM 实现

    用于测试和开发，不调用真实 API。
    """

    def __init__(self, model: str = "mock-model", temperature: float = 0.7):
        self.model_name = model
        self.temperature = temperature
        logger.info(f"🔧 使用 Mock LLM: {model}")

    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> AIMessage:
        """Mock 调用"""
        # 解析输入生成 Mock 响应
        user_content = self._extract_user_content(messages)
        response_content = self._generate_mock_response(user_content)

        return AIMessage(content=response_content)

    def _extract_user_content(self, messages: List[BaseMessage]) -> str:
        """提取用户消息内容"""
        for msg in messages:
            if isinstance(msg, HumanMessage):
                return str(msg.content)
        return ""

    def _generate_mock_response(self, content: str) -> str:
        """生成 Mock 响应"""
        # 根据关键词生成相应的 Mock 响应
        if "穿搭" in content or "搭配" in content:
            return self._mock_outfit_response(content)
        elif "搜索" in content or "查找" in content:
            return self._mock_search_response(content)
        elif "股票" in content or "价格" in content:
            return self._mock_finance_response(content)
        elif "GitHub" in content or "论文" in content:
            return self._mock_academic_response(content)
        elif "旅行" in content or "旅游" in content:
            return self._mock_trip_response(content)
        elif "intent" in content.lower() or "路由" in content:
            return self._mock_router_response(content)
        elif "review" in content.lower() or "审查" in content:
            return self._mock_review_response(content)
        else:
            return f"这是一个 Mock 响应，针对您的查询：{content[:50]}..."

    def _mock_router_response(self, content: str) -> str:
        """Mock 路由器响应"""
        if "穿搭" in content or "搭配" in content:
            intent = "outfit"
        elif "搜索" in content or "查找" in content:
            intent = "search"
        elif "股票" in content or "价格" in content or "买" in content:
            intent = "finance"
        elif "GitHub" in content or "代码" in content or "论文" in content:
            intent = "academic"
        elif "旅行" in content or "旅游" in content or "景点" in content:
            intent = "trip"
        else:
            intent = "unknown"

        return json.dumps({
            "primary_intent": intent,
            "secondary_intents": [],
            "confidence": 0.85,
            "reasoning": f"基于关键词分析，识别为 {intent} 意图",
            "constraints": {}
        }, ensure_ascii=False)

    def _mock_review_response(self, content: str) -> str:
        """Mock 审查器响应"""
        return json.dumps({
            "passed": True,
            "score": 0.8,
            "violations": [],
            "critique": "Mock 审查通过",
            "suggestions": []
        }, ensure_ascii=False)

    def _mock_outfit_response(self, content: str) -> str:
        """Mock 穿搭响应"""
        return json.dumps({
            "location": "上海",
            "weather": "小雨",
            "temperature": "15°C",
            "outfit": {
                "top": "防水外套",
                "bottom": "深色长裤",
                "shoes": "防水鞋",
                "accessories": ["雨伞"]
            },
            "advice": "雨天建议穿着防水材质的衣物"
        }, ensure_ascii=False)

    def _mock_search_response(self, content: str) -> str:
        """Mock 搜索响应"""
        return f"为您找到以下相关信息：\n\n1. 关于 '{content[:20]}...' 的搜索结果\n2. 更多相关信息...\n\n来源: Mock 搜索引擎"

    def _mock_finance_response(self, content: str) -> str:
        """Mock 金融响应"""
        return json.dumps({
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 178.50,
            "change": 2.30,
            "source": "Mock Yahoo Finance",
            "timestamp": "2026-03-24T12:00:00"
        }, ensure_ascii=False)

    def _mock_academic_response(self, content: str) -> str:
        """Mock 学术响应"""
        return f"为您找到以下学术资源：\n\nGitHub 仓库: langchain-ai/langgraph\n描述: LangGraph 是一个用于构建有状态多 actor LLM 应用的库\n星标: 15000+\n语言: Python"

    def _mock_trip_response(self, content: str) -> str:
        """Mock 旅行响应"""
        return f"为您规划的旅行方案：\n\n第1天: 参观著名景点A\n第2天: 游览景点B\n\n住宿推荐: 示例酒店\n交通建议: 公共交通\n\n来源: Mock 旅行规划服务"

    def bind_tools(self, tools: List[Any]) -> "MockLLM":
        """Mock 绑定工具（无操作）"""
        return self

    def with_structured_output(self, schema: Any) -> "MockLLM":
        """Mock 结构化输出（无操作）"""
        return self


def get_llm(use_mock: bool = None) -> ChatOpenAI | MockLLM:
    """
    获取 LLM 实例（单例模式）

    Args:
        use_mock: 是否使用 Mock 模式。如果不指定，使用配置文件设置。

    Returns:
        ChatOpenAI 或 MockLLM 实例
    """
    global _llm_instance, _mock_llm_instance

    # 确定是否使用 Mock
    if use_mock is None:
        use_mock = settings.mock_mode

    if use_mock:
        if _mock_llm_instance is None:
            _mock_llm_instance = MockLLM(
                model=settings.llm_model_id + "-mock",
                temperature=settings.llm_temperature
            )
        return _mock_llm_instance

    if _llm_instance is None:
        # 检查必要配置
        if not settings.llm_api_key:
            logger.warning("⚠️  LLM_API_KEY 未配置，回退到 Mock 模式")
            return get_llm(use_mock=True)

        try:
            _llm_instance = ChatOpenAI(
                model=settings.llm_model_id,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                temperature=settings.llm_temperature
            )
            logger.info(f"✅ LLM 服务初始化成功: {_llm_instance.model_name}")
        except Exception as e:
            logger.error(f"❌ LLM 服务初始化失败: {e}")
            logger.info("🔧 回退到 Mock 模式")
            return get_llm(use_mock=True)

    return _llm_instance


def reset_llm():
    """重置 LLM 实例（用于测试）"""
    global _llm_instance, _mock_llm_instance
    _llm_instance = None
    _mock_llm_instance = None


# ============ 结构化输出辅助函数 ============

async def call_llm_with_structured_output(
    prompt: str,
    system_prompt: str = None,
    output_schema: type[BaseModel] = None,
    use_mock: bool = None
) -> dict:
    """
    调用 LLM 并获取结构化输出

    Args:
        prompt: 用户提示
        system_prompt: 系统提示
        output_schema: 输出 Schema（Pydantic 模型）
        use_mock: 是否使用 Mock 模式

    Returns:
        解析后的结构化数据（字典格式）
    """
    llm = get_llm(use_mock=use_mock)

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
    use_mock: bool = None
):
    """
    流式调用 LLM

    Args:
        prompt: 用户提示
        system_prompt: 系统提示
        use_mock: 是否使用 Mock 模式

    Yields:
        响应片段
    """
    llm = get_llm(use_mock=use_mock)

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
