"""记忆数据模型定义

定义系统中所有记忆相关的数据结构，包括：
- 工作记忆（Working Memory）：当前运行的临时状态
- 短期记忆（Short-term Memory）：Redis 存储的会话级别记忆
- 长期记忆（Long-term Memory）：Milvus 存储的跨会话记忆
"""

from typing import Any, Optional, Literal, Dict, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Annotated


# ============ 记忆类型枚举 ============

class MemoryType(str, Enum):
    """记忆类型"""
    # 用户相关
    USER_PREFERENCE = "user_preference"  # 用户偏好
    USER_PROFILE = "user_profile"        # 用户画像
    USER_CONSTRAINT = "user_constraint"  # 用户约束

    # 任务相关
    TASK_EPISODE = "task_episode"        # 任务经历
    TASK_SUCCESS = "task_success"        # 成功经验
    TASK_FAILURE = "task_failure"        # 失败教训

    # 领域知识
    DOMAIN_KNOWLEDGE = "domain_knowledge"  # 领域知识
    DOMAIN_PATTERN = "domain_pattern"      # 领域模式

    # 会话相关
    SESSION_CONTEXT = "session_context"  # 会话上下文
    SESSION_SUMMARY = "session_summary"  # 会话摘要

    # 反馈相关
    USER_FEEDBACK = "user_feedback"      # 用户反馈
    CORRECTION = "correction"            # 纠正记录


class MemoryScope(str, Enum):
    """记忆范围"""
    GLOBAL = "global"      # 全局记忆，跨域可用
    DOMAIN = "domain"      # 领域记忆，仅特定域可用
    SESSION = "session"    # 会话记忆，仅当前会话可用


class StorageTarget(str, Enum):
    """存储目标"""
    NONE = "none"          # 不存储
    REDIS = "redis"        # 仅短期存储
    MILVUS = "milvus"      # 仅长期存储
    BOTH = "both"          # 同时存储到短期和长期


# ============ 核心记忆数据模型 ============

class MemoryItem(BaseModel):
    """记忆项 - 最小的记忆单元

    表示一条完整的记忆记录，可以存储到 Redis 或 Milvus
    """
    # 基础标识
    id: str = Field(default_factory=lambda: f"mem_{datetime.now().timestamp()}")
    user_id: str
    memory_type: MemoryType
    scope: MemoryScope
    domain: Optional[str] = None  # 关联的领域（outfit/finance/academic等）

    # 内容
    content: str = Field(..., description="记忆内容")
    summary: Optional[str] = Field(None, description="内容摘要")
    key_points: List[str] = Field(default_factory=list, description="关键点列表")

    # 元数据
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要性分数")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度")
    relevance: float = Field(default=0.5, ge=0.0, le=1.0, description="与当前任务的相关性")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = Field(default=0, description="访问次数")

    # 过期与淘汰
    ttl: Optional[int] = Field(None, description="TTL秒数（用于Redis）")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    # 扩展字段
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 向量相关
    embedding: Optional[List[float]] = Field(None, description="向量表示（仅Milvus使用）")

    class Config:
        use_enum_values = True


class MemoryCandidate(BaseModel):
    """记忆候选 - 待审查的记忆

    由子图生成，经过 memory_judge 审查后决定是否存储
    """
    # 内容
    content: str
    memory_type: MemoryType
    scope: MemoryScope
    domain: Optional[str] = None

    # 元数据
    importance: float = 0.5
    confidence: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 来源信息
    source: str = Field(..., description="来源（如 subgraph:outfit）")
    created_at: datetime = Field(default_factory=datetime.now)

    # 审查相关（由 judge 填充）
    relevance_score: Optional[float] = None
    durability_score: Optional[float] = None
    user_specificity_score: Optional[float] = None
    novelty_score: Optional[float] = None
    final_score: Optional[float] = None
    decision: Optional[StorageTarget] = None
    reason: Optional[str] = None


class MemoryBundle(BaseModel):
    """记忆束 - 传递给节点的压缩记忆集合

    主图向子图传递的记忆经过压缩和整理后的结构化数据
    """
    # 是否包含有效记忆
    has_memory: bool = False

    # 全局偏好（用户长期偏好）
    global_preferences: List[MemoryItem] = Field(default_factory=list)

    # 当前领域相关记忆
    domain_memories: List[MemoryItem] = Field(default_factory=list)

    # 最近上下文（短期记忆）
    recent_context: List[Dict[str, Any]] = Field(default_factory=list)

    # 最近反馈
    recent_feedback: List[Dict[str, Any]] = Field(default_factory=list)

    # 用户约束
    user_constraints: List[MemoryItem] = Field(default_factory=list)

    # 检索元数据
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict)

    # 压缩后的摘要（用于直接注入 prompt）
    summary: Optional[str] = None

    def is_empty(self) -> bool:
        """检查是否为空"""
        return not any([
            self.global_preferences,
            self.domain_memories,
            self.recent_context,
            self.recent_feedback,
            self.user_constraints
        ])

    def to_prompt_context(self) -> str:
        """转换为 prompt 注入格式"""
        if self.is_empty():
            return ""

        parts = []
        if self.summary:
            parts.append(f"# 记忆上下文\n{self.summary}")
        else:
            if self.global_preferences:
                prefs = "\n".join(f"- {m.content}" for m in self.global_preferences[:3])
                parts.append(f"# 用户偏好\n{prefs}")

            if self.domain_memories:
                domain_mem = "\n".join(f"- {m.content}" for m in self.domain_memories[:3])
                parts.append(f"# 相关经验\n{domain_mem}")

            if self.user_constraints:
                constraints = "\n".join(f"- {m.content}" for m in self.user_constraints)
                parts.append(f"# 用户约束\n{constraints}")

        return "\n\n".join(parts) if parts else ""


class MemoryDecision(BaseModel):
    """记忆存储决策

    由 memory_judge 做出的存储决策
    """
    candidate: MemoryCandidate
    target: StorageTarget
    reason: str

    # 评分详情
    scores: Dict[str, float] = Field(default_factory=dict)

    # 转换后的 MemoryItem（如果决定存储）
    memory_item: Optional[MemoryItem] = None

    # 时间戳
    decided_at: datetime = Field(default_factory=datetime.now)


# ============ 会话相关模型 ============

class SessionCheckpoint(BaseModel):
    """会话检查点 - 用于中断恢复"""
    session_id: str
    state_snapshot: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    node_name: Optional[str] = None


class RecentContext(BaseModel):
    """最近上下文 - 会话级别的短期上下文"""
    session_id: str
    turn_count: int
    recent_queries: List[str]
    recent_responses: List[str]
    active_domain: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class UserPreferenceMemory(BaseModel):
    """用户偏好记忆"""
    user_id: str
    preference_type: str  # 如: outfit_style, budget_range, travel_pace
    value: str
    confidence: float
    source: str  # 如: explicit, implicit, learned
    last_confirmed: Optional[datetime] = None


# ============ 任务经历记忆 ============

class EpisodeMemory(BaseModel):
    """任务经历记忆 - 记录完整的任务执行过程"""
    episode_id: str
    user_id: str
    domain: str

    # 任务信息
    query: str
    intent: str
    plan: Optional[str] = None

    # 执行结果
    result: str
    success: bool
    score: float

    # 经验提取
    learned_lessons: List[str] = Field(default_factory=list)
    effective_patterns: List[str] = Field(default_factory=list)
    pitfalls: List[str] = Field(default_factory=list)

    # 时间
    timestamp: datetime = Field(default_factory=datetime.now)


# ============ 检索请求与响应 ============

class MemoryRetrievalRequest(BaseModel):
    """记忆检索请求"""
    user_id: str
    query: str
    domain: Optional[str] = None
    intent: Optional[str] = None

    # 检索配置
    retrieve_long_term: bool = False
    retrieve_short_term: bool = True
    max_results: int = 10

    # 过滤条件
    memory_types: Optional[List[MemoryType]] = None
    scope: Optional[MemoryScope] = None

    # 向量检索配置
    use_vector_search: bool = False
    embedding_threshold: float = 0.7


class MemoryRetrievalResult(BaseModel):
    """记忆检索结果"""
    # 检索到的记忆
    items: List[MemoryItem]

    # 检索元数据
    source: str  # redis/milvus/hybrid
    total_count: int
    retrieval_time_ms: int

    # 质量指标
    avg_relevance: float
    avg_importance: float
