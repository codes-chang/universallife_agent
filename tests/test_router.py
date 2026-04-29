"""路由器测试"""

import pytest
from app.graph.router import route_intent_node, parse_router_response, detect_negative_feedback


@pytest.mark.asyncio
async def test_route_outfit_intent():
    """测试路由到 outfit 意图"""
    state = {
        "user_query": "明天上海下雨，帮我搭配一套适合通勤的穿搭",
        "route_history": [],
        "retry_count": 0
    }

    result = await route_intent_node(state)

    assert result["active_domain"] == "outfit"
    assert result["router_result"]["primary_intent"] == "outfit"
    assert result["router_result"]["confidence"] > 0.5


@pytest.mark.asyncio
async def test_route_search_intent():
    """测试路由到 search 意图"""
    state = {
        "user_query": "搜索 LangChain 最新教程",
        "route_history": [],
        "retry_count": 0
    }

    result = await route_intent_node(state)

    assert result["active_domain"] == "search"
    assert result["router_result"]["primary_intent"] == "search"


@pytest.mark.asyncio
async def test_route_finance_intent():
    """测试路由到 finance 意图"""
    state = {
        "user_query": "查询 AAPL 股票价格",
        "route_history": [],
        "retry_count": 0
    }

    result = await route_intent_node(state)

    assert result["active_domain"] == "finance"
    assert result["router_result"]["primary_intent"] == "finance"


@pytest.mark.asyncio
async def test_route_academic_intent():
    """测试路由到 academic 意图"""
    state = {
        "user_query": "查找 langgraph GitHub 仓库",
        "route_history": [],
        "retry_count": 0
    }

    result = await route_intent_node(state)

    assert result["active_domain"] == "academic"
    assert result["router_result"]["primary_intent"] == "academic"


@pytest.mark.asyncio
async def test_route_trip_intent():
    """测试路由到 trip 意图"""
    state = {
        "user_query": "规划北京 3 天旅行",
        "route_history": [],
        "retry_count": 0
    }

    result = await route_intent_node(state)

    assert result["active_domain"] == "trip"
    assert result["router_result"]["primary_intent"] == "trip"


def test_parse_router_response_json():
    """测试解析路由器 JSON 响应"""
    json_response = '''```json
    {
      "primary_intent": "outfit",
      "secondary_intents": ["weather"],
      "confidence": 0.95,
      "reasoning": "用户询问穿搭建议",
      "constraints": {"location": "上海"}
    }
    ```'''

    result = parse_router_response(json_response)

    assert result["primary_intent"] == "outfit"
    assert result["confidence"] == 0.95
    assert "上海" in str(result["constraints"])


def test_parse_router_response_text():
    """测试解析纯文本路由器响应"""
    text_response = "根据分析，这是一个关于穿搭的请求，应该路由到 outfit 模块"

    result = parse_router_response(text_response)

    assert result["primary_intent"] == "outfit"


def test_detect_negative_feedback():
    """测试检测负反馈"""
    assert detect_negative_feedback("你理解错了") is True
    assert detect_negative_feedback("不是这个意思") is True
    assert detect_negative_feedback("你跑偏了") is True
    assert detect_negative_feedback("谢谢，这很有帮助") is False
    assert detect_negative_feedback("继续") is False
