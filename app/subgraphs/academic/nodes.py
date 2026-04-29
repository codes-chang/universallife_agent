"""Academic 子图节点实现"""

import re
from ...services.llm_service import get_llm
from ...services.academic_service import get_academic_service
from ...core.logging import logger
from .state import AcademicSubgraphState


async def build_plan_node(state: AcademicSubgraphState) -> AcademicSubgraphState:
    """规划节点 - 分析学术需求"""
    logger.info("[Academic] 正在分析需求...")

    task_input = state.get("task_input", "")

    # 分析查询类型
    if "GitHub" in task_input or "github" in task_input.lower() or "仓库" in task_input or "代码" in task_input:
        state["query_type"] = "github"

        # 提取仓库名
        # 匹配 owner/repo 格式
        pattern = r'([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)'
        matches = re.findall(pattern, task_input)
        if matches:
            state["repository"] = "/".join(matches[0])
        else:
            state["repository"] = task_input.replace("GitHub", "").replace("github", "").strip()

        state["plan"] = f"搜索 GitHub 仓库: {state['repository']}"

    elif "论文" in task_input or "arXiv" in task_input or "arxiv" in task_input.lower():
        state["query_type"] = "arxiv"

        # 提取搜索关键词
        keywords = task_input.replace("论文", "").replace("arXiv", "").replace("arxiv", "").strip()
        state["paper_id"] = keywords

        state["plan"] = f"搜索 arXiv 论文: {keywords}"

    else:
        # 默认 GitHub 搜索
        state["query_type"] = "github"
        state["repository"] = task_input
        state["plan"] = f"搜索学术资源: {task_input}"

    return state


async def execute_tools_node(state: AcademicSubgraphState) -> AcademicSubgraphState:
    """工具执行节点 - 执行学术查询"""
    logger.info(f"[Academic] 正在执行 {state.get('query_type')} 查询...")

    query_type = state.get("query_type", "")

    try:
        academic_service = get_academic_service()

        if query_type == "github":
            repo = state.get("repository", "")

            # 检查是否是完整的仓库名 (owner/repo)
            if "/" in repo and len(repo.split("/")) == 2:
                # 获取仓库详情
                owner, name = repo.split("/")
                repo_data = await academic_service.get_github_repo(owner, name)

                formatted = format_github_repo(repo_data)
                state["intermediate_result"] = formatted
                state["search_results"] = [repo_data]

            else:
                # 搜索仓库
                search_result = await academic_service.search_github(repo, max_results=5)

                formatted = academic_service.format_github_results(search_result)
                state["intermediate_result"] = formatted
                state["search_results"] = search_result.get("results", [])

        elif query_type == "arxiv":
            query = state.get("paper_id", "")
            search_result = await academic_service.search_arxiv(query, max_results=5)

            formatted = academic_service.format_arxiv_results(search_result)
            state["intermediate_result"] = formatted
            state["search_results"] = search_result.get("results", [])

        else:
            state["intermediate_result"] = "请明确您要查询的资源类型（GitHub 仓库或 arXiv 论文）"

    except Exception as e:
        logger.error(f"[Academic] 查询失败: {e}")
        state["intermediate_result"] = f"查询失败: {str(e)}"

    return state


async def synthesize_result_node(state: AcademicSubgraphState) -> AcademicSubgraphState:
    """结果合成节点 - 整理学术信息"""
    logger.info("[Academic] 正在整理结果...")

    intermediate = state.get("intermediate_result", "")
    if intermediate and len(intermediate) > 20:
        state["final_result"] = intermediate
    else:
        state["final_result"] = "学术资源查询完成，请查看详细结果。"

    # 添加来源信息
    query_type = state.get("query_type", "")
    source_info = "\n\n数据来源: " + ("GitHub" if query_type == "github" else "arXiv")
    state["final_result"] += source_info

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
