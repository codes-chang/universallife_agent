"""状态模型定义"""

from typing import TypedDict, Annotated, Any, Optional, Literal
from langgraph.graph.message import add_messages


# ============ 记忆相关类型 ============

class MemoryBundle(TypedDict):
    """记忆束 - 传递给节点的压缩记忆集合"""
    has_memory: bool
    global_preferences: list[Any]  # List[MemoryItem]
    domain_memories: list[Any]
    recent_context: list[dict[str, Any]]
    recent_feedback: list[dict[str, Any]]
    user_constraints: list[Any]
    retrieval_metadata: dict[str, Any]
    summary: Optional[str]


# ============ 主图状态 ============

class RouterResult(TypedDict):
    """路由结果"""
    primary_intent: Literal["outfit", "search", "finance", "academic", "trip", "unknown"]
    secondary_intents: list[str]
    confidence: float
    reasoning: str
    constraints: dict[str, Any]


class RouteAttempt(TypedDict):
    """路由尝试记录"""
    intent: str
    confidence: float
    timestamp: str
    failed: bool
    failure_reason: Optional[str]


class Critique(TypedDict):
    """审查记录"""
    domain: str
    passed: bool
    score: float
    violations: list[str]
    critique: str
    timestamp: str


class MainGraphState(TypedDict):
    """主图状态"""

    # 用户输入
    user_query: str
    normalized_query: Optional[str]

    # 会话相关
    session_id: Optional[str]
    user_id: Optional[str]

    # 路由相关
    router_result: Optional[RouterResult]
    route_history: list[RouteAttempt]
    active_domain: Optional[str]

    # 子图输出
    subgraph_outputs: dict[str, Any]

    # 审查相关
    review_result: Optional[dict[str, Any]]
    critique_history: list[Critique]

    # 最终输出
    final_answer: Optional[str]

    # 用户反馈
    user_feedback: Optional[str]

    # 重试控制
    retry_count: int
    max_retry: int

    # ============ 记忆系统相关 ============

    # 记忆束 - 由 memory_manager 生成
    memory_bundle: Optional[MemoryBundle]

    # 记忆上下文 - 用于注入 prompt 的格式化记忆
    memory_context: Optional[str]

    # 子图记忆输入 - 传递给子图的记忆数据
    subgraph_memory_input: Optional[dict[str, Any]]

    # 记忆决策 - 由 memory_judge 生成的存储决策
    memory_decisions: list[dict[str, Any]]

    # 候选记忆 - 由子图生成，等待 judge 审查
    candidate_memories: list[Any]


# ============ 子图基类状态 ============

class ToolCall(TypedDict):
    """工具调用记录"""
    tool_name: str
    parameters: dict[str, Any]
    result: Optional[str]
    error: Optional[str]
    timestamp: str


class BaseSubgraphState(TypedDict):
    """子图基类状态"""

    # 任务输入
    task_input: str
    domain: str

    # 记忆输入（由主图提供）
    memory_input: Optional[dict[str, Any]]  # 包含 user_preferences, domain_memories, constraints 等

    # 规划
    plan: Optional[str]

    # 工具调用
    tool_calls: list[ToolCall]
    intermediate_result: Optional[str]

    # 最终结果
    final_result: Optional[str]

    # 审查
    critique: Optional[str]
    iteration_count: int
    max_iterations: int

    # 候选记忆（输出给主图 judge）
    candidate_memories: list[dict[str, Any]]


# ============ Outfit 子图状态 ============

class OutfitSubgraphState(BaseSubgraphState):
    """穿搭子图状态"""
    location: Optional[str]
    weather_condition: Optional[dict[str, Any]]
    style_preference: Optional[str]
    occasion: Optional[str]


# ============ Search 子图状态 ============

class SearchSubgraphState(BaseSubgraphState):
    """搜索子图状态"""
    search_query: Optional[str]
    search_results: list[dict[str, Any]]
    sources: list[str]


# ============ Finance 子图状态 ============

class FinanceSubgraphState(BaseSubgraphState):
    """金融子图状态"""
    query_type: Optional[str]  # stock, price_compare, etc.
    symbol: Optional[str]
    price_data: Optional[dict[str, Any]]


# ============ Academic 子图状态 ============

class AcademicSubgraphState(BaseSubgraphState):
    """学术子图状态"""
    query_type: Optional[str]  # github, arxiv, pdf
    repository: Optional[str]
    paper_id: Optional[str]


# ============ Trip 子图状态 ============

class TripSubgraphState(BaseSubgraphState):
    """旅行子图状态"""
    city: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    travel_days: Optional[int]
