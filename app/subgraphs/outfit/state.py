"""Outfit 子图状态"""

from typing import TypedDict, Optional
from ..base import BaseSubgraphState


class OutfitSubgraphState(TypedDict):
    """穿搭子图状态"""
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

    # 穿搭特定字段
    location: Optional[str]
    weather_condition: Optional[dict]
    style_preference: Optional[str]
    occasion: Optional[str]
    gender: Optional[str]
