"""学术服务 - GitHub + arXiv API"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.config import settings
from ..core.logging import logger


class AcademicService:
    """学术服务

    提供 GitHub 仓库搜索、arXiv 论文搜索等功能。
    """

    def __init__(self, github_token: str = None):
        self.github_token = github_token or settings.github_token
        self.github_api_url = "https://api.github.com"

    async def search_github(
        self,
        query: str,
        search_type: str = "repositories",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """搜索 GitHub

        Args:
            query: 搜索查询
            search_type: 搜索类型 (repositories/code/issues)
            max_results: 最大结果数

        Returns:
            搜索结果字典
        """
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "q": query,
                "per_page": min(max_results, 100)
            }

            response = await client.get(
                f"{self.github_api_url}/search/{search_type}",
                params=params,
                headers=headers
            )

            if response.status_code == 403:
                raise RuntimeError("GitHub API 速率限制，请配置 GITHUB_TOKEN 或稍后重试")

            response.raise_for_status()
            result = response.json()

            items = result.get("items", [])
            return {
                "query": query,
                "type": search_type,
                "total_count": result.get("total_count", 0),
                "results": self._format_github_results(items),
                "source": "github"
            }

    def _format_github_results(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """格式化 GitHub 搜索结果"""
        formatted = []
        for item in items:
            formatted.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "full_name": item.get("full_name"),
                "description": item.get("description", ""),
                "language": item.get("language", "Unknown"),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "url": item.get("html_url", ""),
                "updated_at": item.get("updated_at", "")
            })
        return formatted

    async def search_arxiv(
        self,
        query: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """搜索 arXiv 论文

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            搜索结果字典
        """
        try:
            import arxiv
        except ImportError:
            raise ImportError("arxiv 库未安装，请运行: pip install arxiv")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = []
        for paper in search.results():
            results.append({
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "summary": paper.summary.replace("\n", " "),
                "published": paper.published.isoformat(),
                "arxiv_url": paper.entry_id,
                "pdf_url": paper.pdf_url,
                "primary_category": paper.primary_category
            })

        return {
            "query": query,
            "total_count": len(results),
            "results": results,
            "source": "arxiv"
        }

    async def get_github_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """获取 GitHub 仓库详情

        Args:
            owner: 仓库所有者
            repo: 仓库名称

        Returns:
            仓库详情字典
        """
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.github_api_url}/repos/{owner}/{repo}",
                headers=headers
            )

            if response.status_code == 404:
                raise ValueError(f"GitHub 仓库 {owner}/{repo} 不存在")

            response.raise_for_status()
            result = response.json()

            return {
                "name": result.get("name"),
                "full_name": result.get("full_name"),
                "description": result.get("description", ""),
                "language": result.get("language", "Unknown"),
                "stars": result.get("stargazers_count", 0),
                "forks": result.get("forks_count", 0),
                "open_issues": result.get("open_issues_count", 0),
                "url": result.get("html_url", ""),
                "clone_url": result.get("clone_url", ""),
                "created_at": result.get("created_at", ""),
                "updated_at": result.get("updated_at", ""),
                "source": "github"
            }

    def format_github_results(self, data: Dict[str, Any]) -> str:
        """格式化 GitHub 搜索结果"""
        results = data.get("results", [])
        if not results:
            return "未找到相关仓库"

        parts = [f"找到 {data.get('total_count', 0)} 个仓库:\n"]

        for i, repo in enumerate(results[:5], 1):
            name = repo.get("full_name", repo.get("name", ""))
            desc = repo.get("description", "")
            lang = repo.get("language", "Unknown")
            stars = repo.get("stars", 0)
            url = repo.get("url", "")

            parts.append(f"{i}. {name}")
            if desc:
                parts.append(f"   描述: {desc}")
            parts.append(f"   {lang} | Stars: {stars}")
            parts.append(f"   链接: {url}")
            parts.append("")

        return "\n".join(parts)

    def format_arxiv_results(self, data: Dict[str, Any]) -> str:
        """格式化 arXiv 搜索结果"""
        results = data.get("results", [])
        if not results:
            return "未找到相关论文"

        parts = [f"找到 {data.get('total_count', 0)} 篇论文:\n"]

        for i, paper in enumerate(results[:5], 1):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            summary = paper.get("summary", "")
            url = paper.get("arxiv_url", "")

            parts.append(f"{i}. {title}")
            if authors:
                parts.append(f"   作者: {', '.join(authors[:3])}" + ("..." if len(authors) > 3 else ""))
            parts.append(f"   摘要: {summary[:150]}...")
            parts.append(f"   链接: {url}")
            parts.append("")

        return "\n".join(parts)


# ============ 全局实例 ============

_academic_service: Optional[AcademicService] = None


def get_academic_service() -> AcademicService:
    """获取学术服务实例"""
    global _academic_service
    if _academic_service is None:
        _academic_service = AcademicService()
    return _academic_service
