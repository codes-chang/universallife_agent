"""Academic 子图 - 学术办公"""

from .state import AcademicSubgraphState
from . import nodes
from ..base import BaseSubgraph
from ...core.logging import logger
from ...memory.models import MemoryCandidate, MemoryType, MemoryScope


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

    async def generate_candidate_memories(self, state: AcademicSubgraphState) -> AcademicSubgraphState:
        """生成学术相关的候选记忆"""
        candidates = []

        task_input = state.get("task_input", "")

        # 提取学术偏好关键词
        preference_keywords = {
            "研究方向": ["NLP", "CV", "强化学习", "大模型", "图神经网络", "联邦学习", "多模态"],
            "编程语言": ["Python", "Java", "C++", "Rust", "Go", "TypeScript"],
            "资源类型": ["论文", "代码", "数据集", "教程", "开源项目", "工具库"]
        }

        extracted_preferences = []
        for pref_type, keywords in preference_keywords.items():
            for keyword in keywords:
                if keyword.lower() in task_input.lower():
                    extracted_preferences.append(f"{pref_type}: {keyword}")

        # 生成偏好候选记忆
        for pref in extracted_preferences:
            candidate = MemoryCandidate(
                content=f"用户学术偏好: {pref}",
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.DOMAIN,
                domain="academic",
                importance=0.7,
                confidence=0.75,
                source="subgraph:academic",
                metadata={"preference_type": "academic_style", "original_query": task_input}
            )
            candidates.append(candidate.model_dump())

        # 如果执行成功，生成经验记忆
        final_result = state.get("final_result", "")
        if final_result and "失败" not in final_result:
            experience_candidate = MemoryCandidate(
                content=f"成功完成学术搜索任务: {task_input[:50]}...",
                memory_type=MemoryType.TASK_EPISODE,
                scope=MemoryScope.DOMAIN,
                domain="academic",
                importance=0.5,
                confidence=0.6,
                source="subgraph:academic",
                metadata={"task_type": "academic_search"}
            )
            candidates.append(experience_candidate.model_dump())

        # 更新状态
        state["candidate_memories"] = candidates

        if candidates:
            logger.info(f"[AcademicSubgraph] 生成 {len(candidates)} 个候选记忆")

        return state


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


_academic_subgraph = None


def get_academic_subgraph() -> AcademicSubgraph:
    """获取学术子图实例"""
    global _academic_subgraph
    if _academic_subgraph is None:
        _academic_subgraph = AcademicSubgraph()
    return _academic_subgraph
