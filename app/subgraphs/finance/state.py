"""Finance 子图状态"""

from typing import TypedDict, Optional
from ..base import BaseSubgraphState


class FinanceSubgraphState(TypedDict):
    """金融子图状态"""
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

    # 金融特定字段
    query_type: Optional[str]  # stock, price_compare, exchange_rate
    symbol: Optional[str]
    price_data: Optional[dict]
    product_name: Optional[str]
