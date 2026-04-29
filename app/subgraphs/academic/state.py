"""Academic 子图状态"""

from typing import TypedDict, Optional
from ..base import BaseSubgraphState


class AcademicSubgraphState(TypedDict):
    """学术子图状态"""
    # 基础字段
    task_input: str
    domain: str
    plan: Optional[str]
    tool_calls: list
    intermediate_result: Optional[str]
    final_result: Optional[str]
    critique: Optional[str]
    iteration_count: int
    max_iterations: int

    # 学术特定字段
    query_type: Optional[str]  # github, arxiv, pdf
    repository: Optional[str]
    paper_id: Optional[str]
    search_results: list
