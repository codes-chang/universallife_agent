"""Trip 子图状态"""

from typing import TypedDict, Optional
from ..base import BaseSubgraphState


class TripSubgraphState(TypedDict):
    """旅行子图状态"""
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

    # 旅行特定字段
    city: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    travel_days: Optional[int]
    preferences: list
    weather_info: Optional[dict]
    attractions: list
    hotels: list
