"""恢复与降级逻辑测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestHandleNegativeFeedback:
    """测试处理负反馈"""

    @pytest.mark.asyncio
    async def test_handle_negative_feedback_marks_failure(self):
        """测试负反馈标记当前意图为失败"""
        from app.graph.recovery import handle_negative_feedback

        state = {
            "user_feedback": "你理解错了",
            "active_domain": "outfit",
            "route_history": [
                {"intent": "outfit", "confidence": 0.8}
            ],
            "subgraph_outputs": {
                "outfit": {"result": "一些穿搭建议"}
            }
        }

        # Mock route_with_higher_confidence to avoid real routing
        with patch("app.graph.recovery.route_with_higher_confidence", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {
                "active_domain": "search",
                "route_history": [
                    {"intent": "outfit", "confidence": 0.8, "failed": True, "failure_reason": "用户负反馈: 你理解错了"}
                ],
                "subgraph_outputs": {}
            }

            result = await handle_negative_feedback(state)

        # 检查 route_history 中对应意图被标记为 failed
        assert result["route_history"][0]["failed"] is True
        assert "负反馈" in result["route_history"][0]["failure_reason"]

    @pytest.mark.asyncio
    async def test_handle_negative_feedback_clears_outputs(self):
        """测试负反馈清空子图输出"""
        from app.graph.recovery import handle_negative_feedback

        state = {
            "user_feedback": "不是这个意思",
            "active_domain": "search",
            "route_history": [
                {"intent": "search", "confidence": 0.7}
            ],
            "subgraph_outputs": {
                "search": {"result": "搜索结果"}
            }
        }

        with patch("app.graph.recovery.route_with_higher_confidence", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {
                "active_domain": "search",
                "route_history": state["route_history"],
                "subgraph_outputs": {}
            }

            result = await handle_negative_feedback(state)

        assert result["subgraph_outputs"] == {}


class TestHandleReviewFailure:
    """测试处理审查失败"""

    @pytest.mark.asyncio
    async def test_handle_review_failure_adds_improvement_hints(self):
        """测试审查失败时添加改进建议"""
        from app.graph.recovery import handle_review_failure

        state = {
            "user_query": "帮我搭配穿搭",
            "active_domain": "outfit",
            "review_result": {
                "passed": False,
                "violations": ["缺少天气信息"],
                "suggestions": ["添加天气相关建议", "考虑季节因素"]
            },
            "subgraph_outputs": {
                "outfit": {"result": "穿 T 恤和短裤"}
            }
        }

        result = await handle_review_failure(state)

        # user_query 应该被追加了改进建议
        assert "改进要求" in result["user_query"]
        assert "添加天气相关建议" in result["user_query"]
        assert "考虑季节因素" in result["user_query"]

    @pytest.mark.asyncio
    async def test_handle_review_failure_clears_domain_output(self):
        """测试审查失败时清空该域的输出"""
        from app.graph.recovery import handle_review_failure

        state = {
            "user_query": "查询股票",
            "active_domain": "finance",
            "review_result": {
                "passed": False,
                "violations": ["缺少数据"],
                "suggestions": ["补充实时数据"]
            },
            "subgraph_outputs": {
                "finance": {"result": "一些金融数据"}
            }
        }

        result = await handle_review_failure(state)

        assert "finance" not in result["subgraph_outputs"]

    @pytest.mark.asyncio
    async def test_handle_review_failure_preserves_other_domains(self):
        """测试审查失败时不影响其他域的输出"""
        from app.graph.recovery import handle_review_failure

        state = {
            "user_query": "查询股票",
            "active_domain": "finance",
            "review_result": {
                "passed": False,
                "violations": ["缺少数据"],
                "suggestions": ["补充数据"]
            },
            "subgraph_outputs": {
                "finance": {"result": "金融数据"},
                "search": {"result": "搜索结果"}  # 其他域的输出
            }
        }

        result = await handle_review_failure(state)

        assert "search" in result["subgraph_outputs"]
        assert "finance" not in result["subgraph_outputs"]


class TestGracefulDegradation:
    """测试优雅降级"""

    @pytest.mark.asyncio
    async def test_graceful_degradation_with_existing_result(self):
        """测试有现有结果时的降级"""
        from app.graph.recovery import graceful_degradation

        state = {
            "active_domain": "outfit",
            "subgraph_outputs": {
                "outfit": {
                    "result": "建议穿防水外套和深色长裤"
                }
            }
        }

        result = await graceful_degradation(state)

        assert result["final_answer"] == "建议穿防水外套和深色长裤"

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_result(self):
        """测试无现有结果时的降级（使用默认响应）"""
        from app.graph.recovery import graceful_degradation

        state = {
            "active_domain": "finance",
            "subgraph_outputs": {}
        }

        result = await graceful_degradation(state)

        assert result["final_answer"] is not None
        assert "金融" in result["final_answer"] or "finance" in result["final_answer"]

    @pytest.mark.asyncio
    async def test_graceful_degradation_unknown_domain(self):
        """测试未知域的降级"""
        from app.graph.recovery import graceful_degradation

        state = {
            "active_domain": "unknown",
            "subgraph_outputs": {}
        }

        result = await graceful_degradation(state)

        assert result["final_answer"] is not None
        assert "无法" in result["final_answer"]

    @pytest.mark.asyncio
    async def test_graceful_degradation_outfit_default(self):
        """测试穿搭域默认响应"""
        from app.graph.recovery import graceful_degradation

        state = {
            "active_domain": "outfit",
            "subgraph_outputs": {}
        }

        result = await graceful_degradation(state)

        assert "穿搭" in result["final_answer"] or "outfit" in result["final_answer"]

    @pytest.mark.asyncio
    async def test_graceful_degradation_search_default(self):
        """测试搜索域默认响应"""
        from app.graph.recovery import graceful_degradation

        state = {
            "active_domain": "search",
            "subgraph_outputs": {}
        }

        result = await graceful_degradation(state)

        assert "搜索" in result["final_answer"] or "search" in result["final_answer"]


class TestRecoveryNode:
    """测试恢复节点入口"""

    @pytest.mark.asyncio
    async def test_recovery_with_negative_feedback(self):
        """测试恢复节点检测负反馈并处理"""
        from app.graph.recovery import recovery_node

        state = {
            "user_feedback": "你理解错了",
            "review_result": {"passed": True},
            "active_domain": "outfit",
            "retry_count": 0,
            "route_history": [],
            "subgraph_outputs": {}
        }

        with patch("app.graph.recovery.handle_negative_feedback", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = {
                "retry_count": 1,
                "subgraph_outputs": {},
                "route_history": []
            }

            result = await recovery_node(state)

        mock_handle.assert_called_once()
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_recovery_with_review_failure(self):
        """测试恢复节点处理审查失败"""
        from app.graph.recovery import recovery_node

        state = {
            "user_feedback": "",
            "review_result": {"passed": False},
            "active_domain": "finance",
            "retry_count": 1,
            "user_query": "查询股票",
            "subgraph_outputs": {
                "finance": {"result": "数据"}
            }
        }

        result = await recovery_node(state)

        assert result["retry_count"] == 2
        assert "改进要求" in result["user_query"]

    @pytest.mark.asyncio
    async def test_recovery_increments_retry_count(self):
        """测试恢复节点增加重试计数"""
        from app.graph.recovery import recovery_node

        state = {
            "user_feedback": "",
            "review_result": {"passed": True},
            "active_domain": "outfit",
            "retry_count": 2,
            "subgraph_outputs": {}
        }

        result = await recovery_node(state)

        assert result["retry_count"] == 3


class TestGenerateDefaultResponse:
    """测试默认响应生成"""

    def test_generate_default_response_outfit(self):
        """测试穿搭域默认响应"""
        from app.graph.recovery import generate_default_response

        response = generate_default_response({"active_domain": "outfit"})
        assert "穿搭" in response

    def test_generate_default_response_search(self):
        """测试搜索域默认响应"""
        from app.graph.recovery import generate_default_response

        response = generate_default_response({"active_domain": "search"})
        assert "搜索" in response

    def test_generate_default_response_finance(self):
        """测试金融域默认响应"""
        from app.graph.recovery import generate_default_response

        response = generate_default_response({"active_domain": "finance"})
        assert "金融" in response

    def test_generate_default_response_academic(self):
        """测试学术域默认响应"""
        from app.graph.recovery import generate_default_response

        response = generate_default_response({"active_domain": "academic"})
        assert "学术" in response

    def test_generate_default_response_trip(self):
        """测试旅行域默认响应"""
        from app.graph.recovery import generate_default_response

        response = generate_default_response({"active_domain": "trip"})
        assert "旅行" in response

    def test_generate_default_response_unknown(self):
        """测试未知域默认响应"""
        from app.graph.recovery import generate_default_response

        response = generate_default_response({"active_domain": "unknown"})
        assert "无法" in response or "抱歉" in response
