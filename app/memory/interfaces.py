"""记忆存储抽象接口

定义记忆系统的抽象接口，实现可替换的存储层设计。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from .models import (
    MemoryItem, MemoryCandidate, MemoryBundle,
    MemoryRetrievalRequest, MemoryRetrievalResult,
    MemoryScope, MemoryType, SessionCheckpoint
)


# ============ Embedding 提供者接口 ============

class IEmbeddingProvider(ABC):
    """Embedding 提供者抽象接口"""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """生成单个文本的向量表示"""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量表示"""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """获取向量维度"""
        pass


# ============ 短期存储接口 ============

class IShortTermStore(ABC):
    """短期存储接口（Redis 实现）

    用于存储：
    - 会话上下文
    - 最近反馈
    - 子图中间结果
    - 临时偏好
    - 检查点
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化存储连接"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭存储连接"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """检查存储是否可用"""
        pass

    # ============ 会话相关 ============

    @abstractmethod
    async def save_session_context(
        self,
        session_id: str,
        user_id: str,
        context: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """保存会话上下文"""
        pass

    @abstractmethod
    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话上下文"""
        pass

    @abstractmethod
    async def add_to_history(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """添加对话历史"""
        pass

    @abstractmethod
    async def get_recent_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取最近的历史记录"""
        pass

    # ============ 反馈相关 ============

    @abstractmethod
    async def save_feedback(
        self,
        user_id: str,
        feedback: str,
        domain: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """保存用户反馈"""
        pass

    @abstractmethod
    async def get_recent_feedback(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取最近的反馈"""
        pass

    # ============ 子图结果缓存 ============

    @abstractmethod
    async def cache_subgraph_result(
        self,
        user_id: str,
        domain: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """缓存子图执行结果"""
        pass

    @abstractmethod
    async def get_cached_result(
        self,
        user_id: str,
        domain: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的子图结果"""
        pass

    # ============ 临时偏好 ============

    @abstractmethod
    async def set_temp_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """设置临时偏好"""
        pass

    @abstractmethod
    async def get_temp_preference(
        self,
        user_id: str,
        key: str
    ) -> Optional[Any]:
        """获取临时偏好"""
        pass

    @abstractmethod
    async def get_all_temp_preferences(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """获取所有临时偏好"""
        pass

    # ============ 检查点 ============

    @abstractmethod
    async def save_checkpoint(
        self,
        session_id: str,
        checkpoint: SessionCheckpoint
    ) -> bool:
        """保存检查点"""
        pass

    @abstractmethod
    async def get_checkpoint(
        self,
        session_id: str
    ) -> Optional[SessionCheckpoint]:
        """获取检查点"""
        pass

    @abstractmethod
    async def clear_session(self, session_id: str) -> bool:
        """清除会话数据"""
        pass


# ============ 长期存储接口 ============

class ILongTermStore(ABC):
    """长期存储接口（Milvus 实现）

    用于存储：
    - 用户长期偏好
    - 用户画像
    - 任务经历
    - 成功策略
    - 领域知识
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化存储连接和集合"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭存储连接"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """检查存储是否可用"""
        pass

    # ============ 基础 CRUD ============

    @abstractmethod
    async def upsert(self, item: MemoryItem) -> bool:
        """插入或更新记忆项"""
        pass

    @abstractmethod
    async def upsert_batch(self, items: List[MemoryItem]) -> int:
        """批量插入或更新"""
        pass

    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取单个记忆项"""
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """删除记忆项"""
        pass

    @abstractmethod
    async def delete_by_filter(
        self,
        user_id: str,
        filters: Dict[str, Any]
    ) -> int:
        """按条件批量删除"""
        pass

    # ============ 检索 ============

    @abstractmethod
    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[MemoryItem]:
        """向量搜索记忆"""
        pass

    @abstractmethod
    async def search_by_metadata(
        self,
        user_id: str,
        filters: Dict[str, Any],
        limit: int = 10
    ) -> List[MemoryItem]:
        """按元数据搜索"""
        pass

    @abstractmethod
    async def get_recent_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryItem]:
        """获取最近的记忆"""
        pass

    @abstractmethod
    async def get_user_preferences(
        self,
        user_id: str,
        domain: Optional[str] = None
    ) -> List[MemoryItem]:
        """获取用户偏好记忆"""
        pass

    @abstractmethod
    async def get_episode_memories(
        self,
        user_id: str,
        domain: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 10
    ) -> List[MemoryItem]:
        """获取任务经历记忆"""
        pass

    # ============ 统计与维护 ============

    @abstractmethod
    async def count_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> int:
        """统计记忆数量"""
        pass

    @abstractmethod
    async def update_access_time(self, memory_id: str) -> bool:
        """更新访问时间"""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """清理过期记忆"""
        pass


# ============ 记忆管理器接口 ============

class IMemoryManager(ABC):
    """记忆管理器接口

    协调短期和长期存储，提供统一的数据访问接口
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化记忆管理器"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭记忆管理器"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        request: MemoryRetrievalRequest
    ) -> MemoryBundle:
        """检索记忆并返回压缩的记忆束"""
        pass

    @abstractmethod
    async def store(
        self,
        candidate: MemoryCandidate,
        user_id: str
    ) -> MemoryDecision:
        """存储记忆候选（经过审查）"""
        pass

    @abstractmethod
    async def store_batch(
        self,
        candidates: List[MemoryCandidate],
        user_id: str
    ) -> List[MemoryDecision]:
        """批量存储记忆候选"""
        pass

    @abstractmethod
    async def should_retrieve_memory(
        self,
        user_query: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> bool:
        """判断是否需要检索记忆"""
        pass


# ============ 记忆审查器接口 ============

class IMemoryJudge(ABC):
    """记忆审查器接口

    决定记忆候选是否值得存储，以及存储到哪里
    """

    @abstractmethod
    async def judge(
        self,
        candidate: MemoryCandidate,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MemoryDecision:
        """审查单个记忆候选"""
        pass

    @abstractmethod
    async def judge_batch(
        self,
        candidates: List[MemoryCandidate],
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[MemoryDecision]:
        """批量审查记忆候选"""
        pass

    @abstractmethod
    def calculate_relevance(self, candidate: MemoryCandidate) -> float:
        """计算相关性分数"""
        pass

    @abstractmethod
    def calculate_durability(self, candidate: MemoryCandidate) -> float:
        """计算持久性分数（是否值得长期存储）"""
        pass

    @abstractmethod
    def calculate_user_specificity(self, candidate: MemoryCandidate) -> float:
        """计算用户特异性分数"""
        pass

    @abstractmethod
    def calculate_novelty(
        self,
        candidate: MemoryCandidate,
        existing_memories: List[MemoryItem]
    ) -> float:
        """计算新颖性分数"""
        pass
