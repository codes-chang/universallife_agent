"""记忆管理器节点

主图记忆治理节点，负责：
- 判断是否需要检索记忆
- 协调 Redis 和 Milvus 检索
- 压缩和整理记忆
- 生成 memory_bundle
"""

import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import (
    MemoryBundle, MemoryItem, MemoryRetrievalRequest,
    MemoryType, MemoryScope
)
from .interfaces import IMemoryManager
from .redis_store import RedisShortTermStore, get_redis_store
from .milvus_store import MilvusLongTermStore, get_milvus_store
from .compressor import MemoryCompressor, deduplicate_and_rank
from ..core.logging import logger
from ..core.config import get_settings


class MemoryManager(IMemoryManager):
    """记忆管理器

    协调短期和长期存储，提供统一的记忆访问接口
    """

    def __init__(
        self,
        short_term_store: Optional[RedisShortTermStore] = None,
        long_term_store: Optional[MilvusLongTermStore] = None
    ):
        self._short_term_store = short_term_store
        self._long_term_store = long_term_store
        self._compressor = MemoryCompressor()
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化记忆管理器"""
        if self._initialized:
            return True

        try:
            if not self._short_term_store:
                self._short_term_store = await get_redis_store()
            if not self._long_term_store:
                self._long_term_store = await get_milvus_store()

            self._initialized = True
            logger.info("[MemoryManager] 记忆管理器初始化完成")
            return True

        except Exception as e:
            logger.error(f"[MemoryManager] 初始化失败: {e}")
            return False

    async def close(self) -> None:
        """关闭记忆管理器"""
        if self._short_term_store:
            await self._short_term_store.close()
        if self._long_term_store:
            await self._long_term_store.close()

    async def retrieve(
        self,
        request: MemoryRetrievalRequest
    ) -> MemoryBundle:
        """检索记忆并返回压缩的记忆束"""
        try:
            await self.initialize()

            bundle = MemoryBundle()

            # 检索短期记忆（Redis）
            if request.retrieve_short_term:
                short_term_items = await self._retrieve_short_term(request)
                bundle.recent_context.extend(short_term_items[:5])

            # 检索长期记忆（Milvus）
            if request.retrieve_long_term:
                long_term_items = await self._retrieve_long_term(request)
                bundle.global_preferences.extend([
                    m for m in long_term_items
                    if m.memory_type == MemoryType.USER_PREFERENCE
                ][:3])
                bundle.domain_memories.extend([
                    m for m in long_term_items
                    if m.memory_type != MemoryType.USER_PREFERENCE
                ][:5])

            # 获取最近反馈
            if self._short_term_store:
                recent_feedback = await self._short_term_store.get_recent_feedback(
                    request.user_id,
                    limit=3
                )
                bundle.recent_feedback = recent_feedback

            # 获取用户约束
            if self._short_term_store:
                constraints = await self._short_term_store.get_all_temp_preferences(request.user_id)
                for key, value in constraints.items():
                    bundle.user_constraints.append(MemoryItem(
                        id=f"constraint_{key}",
                        user_id=request.user_id,
                        memory_type=MemoryType.USER_CONSTRAINT,
                        scope=MemoryScope.SESSION,
                        content=f"{key}: {value}",
                        summary=f"{key}: {value}",
                        importance=0.6,
                        confidence=0.8
                    ))

            # 去重和排序
            bundle.global_preferences = deduplicate_and_rank(bundle.global_preferences)
            bundle.domain_memories = deduplicate_and_rank(bundle.domain_memories)

            # 压缩
            if get_settings().memory_compression_enabled:
                bundle = await self._compressor.compress_bundle(bundle)

            bundle.has_memory = not bundle.is_empty()

            logger.info(
                f"[MemoryManager] 检索完成: "
                f"{len(bundle.global_preferences)} 偏好, "
                f"{len(bundle.domain_memories)} 经验, "
                f"{len(bundle.recent_context)} 上下文"
            )

            return bundle

        except Exception as e:
            logger.error(f"[MemoryManager] 检索失败: {e}")
            return MemoryBundle()

    async def _retrieve_short_term(
        self,
        request: MemoryRetrievalRequest
    ) -> List[Dict[str, Any]]:
        """检索短期记忆"""
        items = []

        if not self._short_term_store:
            return items

        try:
            # 获取会话历史（使用 session_id 作为 user_id 的变体）
            history = await self._short_term_store.get_recent_history(
                request.user_id,  # 实际应该是 session_id
                limit=5
            )
            items.extend(history)

            # 获取缓存的子图结果
            if request.domain:
                cached = await self._short_term_store.get_cached_result(
                    request.user_id,
                    request.domain
                )
                if cached:
                    items.append({
                        "type": "cached_result",
                        "domain": request.domain,
                        "data": cached
                    })

        except Exception as e:
            logger.warning(f"[MemoryManager] 短期记忆检索失败: {e}")

        return items

    async def _retrieve_long_term(
        self,
        request: MemoryRetrievalRequest
    ) -> List[MemoryItem]:
        """检索长期记忆"""
        items = []

        if not self._long_term_store:
            return items

        try:
            # 向量搜索
            items = await self._long_term_store.search(
                user_id=request.user_id,
                query=request.query,
                limit=request.max_results,
                filters=self._build_filters(request),
                min_score=get_settings().memory_min_score
            )

        except Exception as e:
            logger.warning(f"[MemoryManager] 长期记忆检索失败: {e}")

        return items

    def _build_filters(self, request: MemoryRetrievalRequest) -> Dict[str, Any]:
        """构建检索过滤器"""
        filters = {}

        if request.domain:
            filters["domain"] = request.domain

        if request.scope:
            filters["scope"] = request.scope.value if isinstance(request.scope, str) else request.scope

        return filters

    async def store(
        self,
        candidate,
        user_id: str
    ):
        """Store a memory candidate after judging"""
        from .judge import MemoryJudge
        judge = MemoryJudge(
            short_term_store=self._short_term_store,
            long_term_store=self._long_term_store
        )
        decision = await judge.judge(candidate, user_id)
        await judge.apply_decision(decision, user_id)
        return decision

    async def store_batch(
        self,
        candidates: list,
        user_id: str
    ) -> list:
        """Batch store memory candidates"""
        decisions = []
        for candidate in candidates:
            decision = await self.store(candidate, user_id)
            decisions.append(decision)
        return decisions

    async def should_retrieve_memory(
        self,
        user_query: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> bool:
        """判断是否需要检索记忆

        检查条件：
        1. 用户请求依赖历史偏好
        2. 路由置信度低
        3. 多步规划任务
        4. 用户显式提到"上次/之前/延续/记得"
        5. 强个性化任务
        """
        settings = get_settings()

        # 检查关键词
        for keyword in settings.memory_retrieve_on_keywords:
            if keyword.lower() in user_query.lower():
                logger.info(f"[MemoryManager] 检测到记忆关键词: {keyword}")
                return True

        # 低置信度时检索
        if confidence is not None and confidence < settings.router_confidence_threshold:
            logger.info(f"[MemoryManager] 低置信度触发记忆检索: {confidence}")
            return True

        # 偏好类任务
        if intent and settings.memory_retrieve_on_preference:
            preference_domains = ["outfit", "finance", "trip", "academic"]
            if intent in preference_domains:
                logger.info(f"[MemoryManager] 偏好类任务触发记忆检索: {intent}")
                return True

        # 多步规划任务（检测特定句式）
        multi_step_patterns = [
            r"然后", r"接着", r"之后", r"还要",
            r"then", r"after that", r"also"
        ]
        for pattern in multi_step_patterns:
            if re.search(pattern, user_query, re.IGNORECASE):
                logger.info("[MemoryManager] 检测到多步任务")
                return True

        return False

    async def _compressor(self) -> MemoryCompressor:
        """获取压缩器"""
        return self._compressor


# ============ 主图节点函数 ============

async def memory_manager_node(state: dict) -> dict:
    """记忆管理节点 - 主图节点

    在路由前检索相关记忆并注入到状态中

    Args:
        state: 主图状态

    Returns:
        更新后的状态
    """
    try:
        from .models import MemoryRetrievalRequest

        user_query = state.get("user_query", "")
        router_result = state.get("router_result", {})
        session_id = state.get("session_id", "default")

        # 获取用户 ID（简化处理，使用 session_id）
        user_id = session_id

        # 判断是否需要检索记忆
        manager = MemoryManager()
        should_retrieve = await manager.should_retrieve_memory(
            user_query=user_query,
            intent=router_result.get("primary_intent"),
            confidence=router_result.get("confidence")
        )

        memory_bundle = MemoryBundle()

        if should_retrieve:
            logger.info("[MemoryManager] 开始检索记忆...")

            # 构建检索请求
            request = MemoryRetrievalRequest(
                user_id=user_id,
                query=user_query,
                domain=router_result.get("primary_intent"),
                intent=router_result.get("primary_intent"),
                retrieve_short_term=True,
                retrieve_long_term=True,
                max_results=get_settings().memory_max_results
            )

            # 检索记忆
            memory_bundle = await manager.retrieve(request)

        # 注入到状态
        state["memory_bundle"] = memory_bundle

        # 如果有记忆摘要，添加到路由提示中
        if memory_bundle.summary:
            state["memory_context"] = memory_bundle.summary
        elif not memory_bundle.is_empty():
            state["memory_context"] = memory_bundle.to_prompt_context()
        else:
            state["memory_context"] = None

        logger.info(
            f"[MemoryManager] 记忆注入完成: "
            f"{'有记忆' if memory_bundle.has_memory else '无记忆'}"
        )

    except Exception as e:
        logger.error(f"[MemoryManager] 节点执行失败: {e}")
        state["memory_bundle"] = MemoryBundle()
        state["memory_context"] = None

    return state


async def prepare_memory_for_subgraph(state: dict) -> dict:
    """准备传递给子图的记忆

    在执行子图前，将记忆转换为子图可用的格式

    Args:
        state: 主图状态

    Returns:
        更新后的状态
    """
    memory_bundle = state.get("memory_bundle", MemoryBundle())

    # 将记忆转换为子图输入格式
    subgraph_memory_input = {
        "has_user_preferences": len(memory_bundle.global_preferences) > 0,
        "user_preferences": [
            {"content": m.content, "importance": m.importance}
            for m in memory_bundle.global_preferences
        ],
        "has_domain_memories": len(memory_bundle.domain_memories) > 0,
        "domain_memories": [
            {"content": m.content, "importance": m.importance}
            for m in memory_bundle.domain_memories
        ],
        "has_constraints": len(memory_bundle.user_constraints) > 0,
        "constraints": [m.content for m in memory_bundle.user_constraints],
        "context_summary": memory_bundle.summary
    }

    state["subgraph_memory_input"] = subgraph_memory_input

    return state


# ============ 便捷函数 ============

async def retrieve_memory_for_user(
    user_id: str,
    query: str,
    domain: Optional[str] = None,
    use_long_term: bool = True
) -> MemoryBundle:
    """便捷函数：为用户检索记忆"""
    from .models import MemoryRetrievalRequest

    manager = MemoryManager()

    request = MemoryRetrievalRequest(
        user_id=user_id,
        query=query,
        domain=domain,
        retrieve_short_term=True,
        retrieve_long_term=use_long_term
    )

    return await manager.retrieve(request)
