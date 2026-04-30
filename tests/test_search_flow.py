"""Search 子图流程测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.subgraphs.search.state import SearchSubgraphState


def _make_search_state(task_input: str = "搜索 LangChain 最新教程") -> SearchSubgraphState:
    """构建搜索子图测试状态"""
    return {
        "task_input": task_input,
        "domain": "search",
        "plan": None,
        "tool_calls": [],
        "intermediate_result": None,
        "final_result": None,
        "critique": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "search_query": None,
        "search_results": [],
        "sources": [],
        "max_results": 5
    }


class TestSearchBuildPlanNode:
    """测试搜索子图规划节点"""

    @pytest.mark.asyncio
    async def test_build_plan_sets_search_query(self):
        """测试规划节点设置搜索查询"""
        from app.subgraphs.search.nodes import build_plan_node

        state = _make_search_state("搜索 LangChain 最新教程")
        result = await build_plan_node(state)

        assert result["search_query"] == "搜索 LangChain 最新教程"
        assert result["max_results"] == 5
        assert result["plan"] is not None
        assert "LangChain" in result["plan"]

    @pytest.mark.asyncio
    async def test_build_plan_with_different_query(self):
        """测试不同查询的规划"""
        from app.subgraphs.search.nodes import build_plan_node

        state = _make_search_state("Python 异步编程指南")
        result = await build_plan_node(state)

        assert result["search_query"] == "Python 异步编程指南"
        assert "Python" in result["plan"]


class TestSearchExecuteToolsNode:
    """测试搜索子图工具执行节点"""

    @pytest.mark.asyncio
    async def test_execute_tools_success(self):
        """测试搜索工具执行成功"""
        from app.subgraphs.search.nodes import execute_tools_node

        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value={
            "results": [
                {
                    "title": "LangChain Documentation",
                    "url": "https://docs.langchain.com",
                    "snippet": "LangChain is a framework...",
                    "score": 0.95,
                    "published_date": "2026-01-15"
                }
            ],
            "answer": "LangChain is a framework"
        })
        mock_search_service.format_search_results = MagicMock(
            return_value="搜索结果:\n1. LangChain Documentation\n   链接: https://docs.langchain.com"
        )

        state = _make_search_state()
        state["search_query"] = "LangChain"
        state["max_results"] = 5

        with patch("app.subgraphs.search.nodes.get_search_service", return_value=mock_search_service):
            result = await execute_tools_node(state)

        assert result["intermediate_result"] is not None
        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["title"] == "LangChain Documentation"
        assert result["sources"] == ["https://docs.langchain.com"]

    @pytest.mark.asyncio
    async def test_execute_tools_failure(self):
        """测试搜索工具执行失败"""
        from app.subgraphs.search.nodes import execute_tools_node

        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(side_effect=Exception("API 连接失败"))

        state = _make_search_state()
        state["search_query"] = "test"
        state["max_results"] = 5

        with patch("app.subgraphs.search.nodes.get_search_service", return_value=mock_search_service):
            result = await execute_tools_node(state)

        assert "遇到问题" in result["intermediate_result"]


class TestSearchSynthesizeResultNode:
    """测试搜索子图结果合成节点"""

    @pytest.mark.asyncio
    async def test_synthesize_with_intermediate_result(self):
        """测试有中间结果时的合成"""
        from app.subgraphs.search.nodes import synthesize_result_node

        long_intermediate = "搜索结果:\n1. LangChain Documentation\n" + "x" * 100

        state = _make_search_state()
        state["search_query"] = "LangChain"
        state["intermediate_result"] = long_intermediate

        result = await synthesize_result_node(state)

        assert result["final_result"] == long_intermediate

    @pytest.mark.asyncio
    async def test_synthesize_with_short_intermediate_result(self):
        """测试中间结果过短时的合成"""
        from app.subgraphs.search.nodes import synthesize_result_node

        state = _make_search_state()
        state["search_query"] = "LangChain"
        state["intermediate_result"] = "短结果"

        result = await synthesize_result_node(state)

        assert "LangChain" in result["final_result"]

    @pytest.mark.asyncio
    async def test_synthesize_with_empty_intermediate(self):
        """测试无中间结果时的合成"""
        from app.subgraphs.search.nodes import synthesize_result_node

        state = _make_search_state()
        state["search_query"] = "test query"
        state["intermediate_result"] = ""

        result = await synthesize_result_node(state)

        assert result["final_result"] is not None
        assert "test query" in result["final_result"]
