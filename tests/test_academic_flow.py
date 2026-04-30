"""Academic 子图流程测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.subgraphs.academic.state import AcademicSubgraphState


def _make_academic_state(task_input: str = "查找 langgraph GitHub 仓库") -> AcademicSubgraphState:
    """构建学术子图测试状态"""
    return {
        "task_input": task_input,
        "domain": "academic",
        "plan": None,
        "tool_calls": [],
        "intermediate_result": None,
        "final_result": None,
        "critique": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "query_type": None,
        "repository": None,
        "paper_id": None,
        "search_results": []
    }


class TestAcademicBuildPlanNode:
    """测试学术子图规划节点"""

    @pytest.mark.asyncio
    async def test_github_search_type_detection(self):
        """测试 GitHub 搜索类型检测"""
        from app.subgraphs.academic.nodes import build_plan_node

        state = _make_academic_state("查找 langgraph GitHub 仓库")
        result = await build_plan_node(state)

        assert result["query_type"] == "github"
        assert result["plan"] is not None
        assert "GitHub" in result["plan"]

    @pytest.mark.asyncio
    async def test_github_search_with_owner_repo(self):
        """测试包含 owner/repo 格式的 GitHub 搜索"""
        from app.subgraphs.academic.nodes import build_plan_node

        state = _make_academic_state("查找 langchain-ai/langgraph GitHub 仓库")
        result = await build_plan_node(state)

        assert result["query_type"] == "github"
        assert result["repository"] == "langchain-ai/langgraph"

    @pytest.mark.asyncio
    async def test_arxiv_search_type_detection(self):
        """测试 arXiv 搜索类型检测"""
        from app.subgraphs.academic.nodes import build_plan_node

        state = _make_academic_state("搜索 transformer 论文 arxiv")
        result = await build_plan_node(state)

        assert result["query_type"] == "arxiv"
        assert result["paper_id"] is not None
        assert "arxiv" in result["plan"].lower() or "arXiv" in result["plan"]

    @pytest.mark.asyncio
    async def test_arxiv_paper_keyword_detection(self):
        """测试论文关键词检测"""
        from app.subgraphs.academic.nodes import build_plan_node

        state = _make_academic_state("关于大语言模型的论文")
        result = await build_plan_node(state)

        assert result["query_type"] == "arxiv"

    @pytest.mark.asyncio
    async def test_code_keyword_detection(self):
        """测试代码关键词检测"""
        from app.subgraphs.academic.nodes import build_plan_node

        state = _make_academic_state("搜索 agent 代码")
        result = await build_plan_node(state)

        assert result["query_type"] == "github"

    @pytest.mark.asyncio
    async def test_default_to_github_search(self):
        """测试默认回退到 GitHub 搜索"""
        from app.subgraphs.academic.nodes import build_plan_node

        state = _make_academic_state("langgraph")
        result = await build_plan_node(state)

        assert result["query_type"] == "github"


class TestAcademicExecuteToolsNode:
    """测试学术子图工具执行节点"""

    @pytest.mark.asyncio
    async def test_execute_github_search(self):
        """测试 GitHub 搜索执行"""
        from app.subgraphs.academic.nodes import execute_tools_node

        mock_academic_service = MagicMock()
        mock_academic_service.search_github = AsyncMock(return_value={
            "query": "langgraph",
            "total_count": 1,
            "results": [
                {
                    "name": "langgraph",
                    "full_name": "langchain-ai/langgraph",
                    "description": "LangGraph library",
                    "language": "Python",
                    "stars": 15000,
                    "url": "https://github.com/langchain-ai/langgraph"
                }
            ]
        })
        mock_academic_service.format_github_results = MagicMock(
            return_value="1. langchain-ai/langgraph\n   Python | Stars: 15000"
        )

        state = _make_academic_state()
        state["query_type"] = "github"
        state["repository"] = "langgraph"

        with patch("app.subgraphs.academic.nodes.get_academic_service", return_value=mock_academic_service):
            result = await execute_tools_node(state)

        assert result["intermediate_result"] is not None
        assert "langgraph" in result["intermediate_result"]
        assert len(result["search_results"]) == 1

    @pytest.mark.asyncio
    async def test_execute_github_repo_detail(self):
        """测试 GitHub 仓库详情查询（owner/repo 格式）"""
        from app.subgraphs.academic.nodes import execute_tools_node

        mock_academic_service = MagicMock()
        mock_academic_service.get_github_repo = AsyncMock(return_value={
            "name": "langgraph",
            "full_name": "langchain-ai/langgraph",
            "description": "LangGraph library",
            "language": "Python",
            "stars": 15000,
            "forks": 2000,
            "url": "https://github.com/langchain-ai/langgraph",
            "source": "github"
        })

        state = _make_academic_state()
        state["query_type"] = "github"
        state["repository"] = "langchain-ai/langgraph"

        with patch("app.subgraphs.academic.nodes.get_academic_service", return_value=mock_academic_service):
            result = await execute_tools_node(state)

        assert result["intermediate_result"] is not None
        assert "langchain-ai/langgraph" in result["intermediate_result"]
        mock_academic_service.get_github_repo.assert_called_once_with("langchain-ai", "langgraph")

    @pytest.mark.asyncio
    async def test_execute_arxiv_search(self):
        """测试 arXiv 搜索执行"""
        from app.subgraphs.academic.nodes import execute_tools_node

        mock_academic_service = MagicMock()
        mock_academic_service.search_arxiv = AsyncMock(return_value={
            "query": "transformer",
            "total_count": 1,
            "results": [
                {
                    "title": "Attention Is All You Need",
                    "authors": ["Vaswani"],
                    "summary": "We propose a new network architecture.",
                    "arxiv_url": "https://arxiv.org/abs/1706.03762"
                }
            ]
        })
        mock_academic_service.format_arxiv_results = MagicMock(
            return_value="1. Attention Is All You Need\n   作者: Vaswani"
        )

        state = _make_academic_state()
        state["query_type"] = "arxiv"
        state["paper_id"] = "transformer"

        with patch("app.subgraphs.academic.nodes.get_academic_service", return_value=mock_academic_service):
            result = await execute_tools_node(state)

        assert result["intermediate_result"] is not None
        assert "Attention" in result["intermediate_result"]
        assert len(result["search_results"]) == 1

    @pytest.mark.asyncio
    async def test_execute_tools_failure(self):
        """测试工具执行失败"""
        from app.subgraphs.academic.nodes import execute_tools_node

        mock_academic_service = MagicMock()
        mock_academic_service.search_github = AsyncMock(side_effect=Exception("API 不可用"))

        state = _make_academic_state()
        state["query_type"] = "github"
        state["repository"] = "test"

        with patch("app.subgraphs.academic.nodes.get_academic_service", return_value=mock_academic_service):
            result = await execute_tools_node(state)

        assert "失败" in result["intermediate_result"]

    @pytest.mark.asyncio
    async def test_execute_unknown_query_type(self):
        """测试未知查询类型"""
        from app.subgraphs.academic.nodes import execute_tools_node

        state = _make_academic_state()
        state["query_type"] = "unknown_type"

        with patch("app.subgraphs.academic.nodes.get_academic_service", return_value=MagicMock()):
            result = await execute_tools_node(state)

        assert "明确" in result["intermediate_result"]


class TestAcademicFormatGithubRepo:
    """测试 GitHub 仓库格式化"""

    def test_format_github_repo(self):
        """测试仓库信息格式化"""
        from app.subgraphs.academic.nodes import format_github_repo

        repo_data = {
            "full_name": "langchain-ai/langgraph",
            "description": "Build stateful, multi-actor applications with LLMs",
            "language": "Python",
            "stars": 15000,
            "forks": 2000,
            "url": "https://github.com/langchain-ai/langgraph",
            "updated_at": "2026-03-20T10:00:00Z",
            "source": "github"
        }

        result = format_github_repo(repo_data)

        assert "langchain-ai/langgraph" in result
        assert "Python" in result
        assert "15,000" in result
        assert "2,000" in result
        assert "https://github.com" in result
