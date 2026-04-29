"""Academic 子图 - 学术办公"""

from langgraph.graph import StateGraph, START, END
from .state import AcademicSubgraphState
from . import nodes
from ..base import BaseSubgraph


class AcademicSubgraph(BaseSubgraph):
    """学术子图

    提供 GitHub 仓库搜索、arXiv 论文搜索等功能。
    """

    def __init__(self):
        super().__init__("academic")

    def get_state_class(self) -> type:
        return AcademicSubgraphState

    def get_system_prompt(self) -> str:
        return """你是专业的学术资源助手。帮助用户查找 GitHub 仓库、arXiv 论文等学术资源。

你的任务：
1. 理解用户要查找的资源类型
2. 使用相应的工具（GitHub API、arXiv API 等）
3. 整理关键信息（描述、星标数、摘要等）

注意事项：
- 所有资源必须提供访问链接
- 论文必须包含摘要
- 仓库必须包含描述和统计信息
"""

    async def execute_domain_tools(self, state: AcademicSubgraphState) -> str:
        """执行学术工具"""
        from ...services.academic_service import get_academic_service

        query_type = state.get("query_type", "")
        query = state.get("task_input", "")

        academic_service = get_academic_service()

        if query_type == "github":
            repo = state.get("repository", query)
            if "/" in repo and len(repo.split("/")) == 2:
                owner, name = repo.split("/")
                repo_data = await academic_service.get_github_repo(owner, name)
                return format_github_repo(repo_data)
            else:
                search_result = await academic_service.search_github(repo, max_results=5)
                return academic_service.format_github_results(search_result)
        elif query_type == "arxiv":
            paper_query = state.get("paper_id", query)
            search_result = await academic_service.search_arxiv(paper_query, max_results=5)
            return academic_service.format_arxiv_results(search_result)
        else:
            # 默认执行 GitHub 搜索
            search_result = await academic_service.search_github(query, max_results=5)
            return academic_service.format_github_results(search_result)


def format_github_repo(repo_data: dict) -> str:
    """格式化 GitHub 仓库信息"""
    name = repo_data.get("full_name", repo_data.get("name", ""))
    desc = repo_data.get("description", "")
    lang = repo_data.get("language", "Unknown")
    stars = repo_data.get("stars", repo_data.get("stargazers_count", 0))
    forks = repo_data.get("forks", repo_data.get("forks_count", 0))
    url = repo_data.get("url", repo_data.get("html_url", ""))
    updated = repo_data.get("updated_at", "")

    parts = [
        f"📁 {name}",
        ""
    ]

    if desc:
        parts.append(f"📝 {desc}")
        parts.append("")

    parts.append(f"💻 语言: {lang}")
    parts.append(f"⭐ Stars: {stars:,}")
    parts.append(f"🔱 Forks: {forks:,}")
    parts.append(f"🔗 {url}")

    if updated:
        parts.append(f"📅 更新: {updated}")

    parts.append(f"\n数据来源: {repo_data.get('source', 'GitHub')}")

    return "\n".join(parts)


def create_academic_subgraph() -> StateGraph:
    """创建学术子图工作流"""
    workflow = StateGraph(AcademicSubgraphState)

    workflow.add_node("build_plan", nodes.build_plan_node)
    workflow.add_node("execute_tools", nodes.execute_tools_node)
    workflow.add_node("synthesize_result", nodes.synthesize_result_node)

    workflow.add_edge(START, "build_plan")
    workflow.add_edge("build_plan", "execute_tools")
    workflow.add_edge("execute_tools", "synthesize_result")
    workflow.add_edge("synthesize_result", END)

    return workflow.compile()


_academic_subgraph = None


def get_academic_subgraph() -> AcademicSubgraph:
    """获取学术子图实例"""
    global _academic_subgraph
    if _academic_subgraph is None:
        _academic_subgraph = AcademicSubgraph()
    return _academic_subgraph
