"""记忆系统模块

提供分层记忆机制：
- 工作记忆（Working Memory）：LangGraph state 内的运行时信息
- 短期记忆（Short-term Memory）：Redis 存储的会话级别记忆
- 长期记忆（Long-term Memory）：Milvus 存储的跨会话记忆

核心组件：
- models: 数据模型定义
- interfaces: 抽象接口
- redis_store: 短期存储实现
- milvus_store: 长期存储实现
- embeddings: 向量嵌入提供者
- compressor: 记忆压缩器
- manager: 记忆管理器（检索）
- judge: 记忆审查器（存储决策）
"""

from .models import (
    # 枚举
    MemoryType,
    MemoryScope,
    StorageTarget,

    # 数据模型
    MemoryItem,
    MemoryCandidate,
    MemoryBundle,
    MemoryDecision,
    MemoryRetrievalRequest,
    MemoryRetrievalResult,
    SessionCheckpoint,
    RecentContext,
    UserPreferenceMemory,
    EpisodeMemory,
)

from .interfaces import (
    IEmbeddingProvider,
    IShortTermStore,
    ILongTermStore,
    IMemoryManager,
    IMemoryJudge,
)

from .redis_store import RedisShortTermStore, get_redis_store
from .milvus_store import MilvusLongTermStore, get_milvus_store
from .embeddings import (
    get_embedding_provider,
    get_global_embedding_provider,
    get_embedding,
    get_embeddings
)
from .compressor import (
    MemoryCompressor,
    compress_memory_bundle,
    deduplicate_and_rank
)
from .manager import (
    MemoryManager,
    memory_manager_node,
    prepare_memory_for_subgraph,
    retrieve_memory_for_user
)
from .judge import (
    MemoryJudge,
    memory_judge_node,
    judge_and_store,
    create_preference_candidate,
    create_episode_candidate
)

__all__ = [
    # 枚举
    "MemoryType",
    "MemoryScope",
    "StorageTarget",

    # 数据模型
    "MemoryItem",
    "MemoryCandidate",
    "MemoryBundle",
    "MemoryDecision",
    "MemoryRetrievalRequest",
    "MemoryRetrievalResult",
    "SessionCheckpoint",
    "RecentContext",
    "UserPreferenceMemory",
    "EpisodeMemory",

    # 接口
    "IEmbeddingProvider",
    "IShortTermStore",
    "ILongTermStore",
    "IMemoryManager",
    "IMemoryJudge",

    # 存储
    "RedisShortTermStore",
    "MilvusLongTermStore",
    "get_redis_store",
    "get_milvus_store",

    # Embedding
    "get_embedding_provider",
    "get_global_embedding_provider",
    "get_embedding",
    "get_embeddings",

    # 压缩
    "MemoryCompressor",
    "compress_memory_bundle",
    "deduplicate_and_rank",

    # 管理
    "MemoryManager",
    "memory_manager_node",
    "prepare_memory_for_subgraph",
    "retrieve_memory_for_user",

    # 审查
    "MemoryJudge",
    "memory_judge_node",
    "judge_and_store",
    "create_preference_candidate",
    "create_episode_candidate",
]
