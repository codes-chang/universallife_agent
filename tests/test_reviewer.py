"""审查器测试"""

import pytest
from app.graph.reviewer import reviewer_node, parse_review_response, should_retry, HARD_RULES


@pytest.mark.asyncio
async def test_reviewer_pass():
    """测试审查通过"""
    state = {
        "active_domain": "outfit",
        "subgraph_outputs": {
            "outfit": {
                "result": """
                👔 上海 穿搭建议
                🌤️ 天气: 小雨，15°C
                📍 场合: 通勤
                📦 推荐搭配:
                  • 上装: 防水外套
                  • 下装: 深色长裤
                  • 鞋子: 防水鞋
                💡 建议: 注意雨天携带雨具
                """
            }
        },
        "user_query": "明天上海下雨，帮我搭配通勤穿搭",
        "critique_history": []
    }

    result = await reviewer_node(state)

    assert result["review_result"] is not None
    assert "passed" in result["review_result"]


@pytest.mark.asyncio
async def test_reviewer_fail_missing_weather():
    """测试审查失败：缺少天气信息"""
    state = {
        "active_domain": "outfit",
        "subgraph_outputs": {
            "outfit": {
                "result": "建议穿着 T 恤和短裤"
            }
        },
        "user_query": "明天上海下雨，帮我搭配通勤穿搭",
        "critique_history": []
    }

    result = await reviewer_node(state)

    assert result["review_result"] is not None
    # 审查应该识别出缺少天气匹配


def test_parse_review_response():
    """测试解析审查器响应"""
    json_response = '''```json
    {
      "passed": true,
      "score": 0.85,
      "violations": [],
      "critique": "输出符合所有规则",
      "suggestions": []
    }
    ```'''

    result = parse_review_response(json_response)

    assert result["passed"] is True
    assert result["score"] == 0.85
    assert len(result["violations"]) == 0


def test_should_retry():
    """测试重试判断"""
    # 审查不通过，未达到最大重试次数
    state = {
        "review_result": {"passed": False},
        "retry_count": 1,
        "max_retry": 3
    }
    assert should_retry(state) is True

    # 审查通过
    state = {
        "review_result": {"passed": True},
        "retry_count": 1,
        "max_retry": 3
    }
    assert should_retry(state) is False

    # 达到最大重试次数
    state = {
        "review_result": {"passed": False},
        "retry_count": 3,
        "max_retry": 3
    }
    assert should_retry(state) is False


def test_hard_rules_exist():
    """测试硬规则定义"""
    assert "outfit" in HARD_RULES
    assert "search" in HARD_RULES
    assert "finance" in HARD_RULES
    assert "academic" in HARD_RULES
    assert "trip" in HARD_RULES

    for domain, rules in HARD_RULES.items():
        assert "name" in rules
        assert "rules" in rules
        assert len(rules["rules"]) > 0
