"""Search 子图状态"""

from typing import TypedDict, Optional
from ..base import BaseSubgraphState


class SearchSubgraphState(TypedDict):
    """搜索子图状态"""
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

    # 搜索特定字段
    search_query: Optional[str]
    search_results: list
    sources: list
    max_results: int
