"""记忆审查器节点

主图记忆质量控制节点，负责：
- 接收子图输出的 candidate memories
- 评分（相关性、持久性、用户特异性、新颖性）
- 决定存储目标（none/redis/milvus/both）
- 防止垃圾写入长期记忆
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import difflib

from .models import (
    MemoryCandidate, MemoryDecision, MemoryItem,
    MemoryType, MemoryScope, StorageTarget
)
from .interfaces import IMemoryJudge
from .redis_store import RedisShortTermStore, get_redis_store
from .milvus_store import MilvusLongTermStore, get_milvus_store
from ..core.logging import logger
from ..core.config import get_settings


class MemoryJudge(IMemoryJudge):
    """记忆审查器

    决定记忆候选是否值得存储，以及存储到哪里
    """

    # 评分权重
    RELEVANCE_WEIGHT = 0.3
    DURABILITY_WEIGHT = 0.3
    USER_SPECIFICITY_WEIGHT = 0.2
    NOVELTY_WEIGHT = 0.2

    # 阈值
    LONG_TERM_THRESHOLD = 0.7  # 高于此值才存储到 Milvus
    SHORT_TERM_THRESHOLD = 0.4  # 高于此值存储到 Redis

    def __init__(
        self,
        short_term_store: Optional[RedisShortTermStore] = None,
        long_term_store: Optional[MilvusLongTermStore] = None
    ):
        self._short_term_store = short_term_store
        self._long_term_store = long_term_store
        self._existing_memories_cache: Dict[str, List[MemoryItem]] = {}

    async def judge(
        self,
        candidate: MemoryCandidate,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MemoryDecision:
        """审查单个记忆候选"""
        # 获取现有记忆用于新颖性计算
        existing = await self._get_existing_memories(user_id, candidate.domain)

        # 计算各项分数
        relevance = self.calculate_relevance(candidate)
        durability = self.calculate_durability(candidate)
        user_specificity = self.calculate_user_specificity(candidate)
        novelty = self.calculate_novelty(candidate, existing)

        # 综合分数
        final_score = (
            relevance * self.RELEVANCE_WEIGHT +
            durability * self.DURABILITY_WEIGHT +
            user_specificity * self.USER_SPECIFICITY_WEIGHT +
            novelty * self.NOVELTY_WEIGHT
        )

        # 填充分数
        candidate.relevance_score = relevance
        candidate.durability_score = durability
        candidate.user_specificity_score = user_specificity
        candidate.novelty_score = novelty
        candidate.final_score = final_score

        # 决定存储目标
        target = self._decide_target(candidate, final_score)

        # 生成决策
        decision = MemoryDecision(
            candidate=candidate,
            target=target,
            reason=self._generate_reason(candidate, target, final_score),
            scores={
                "relevance": relevance,
                "durability": durability,
                "user_specificity": user_specificity,
                "novelty": novelty,
                "final": final_score
            }
        )

        # 如果决定存储，转换并添加 MemoryItem
        if target != StorageTarget.NONE:
            decision.memory_item = self._candidate_to_item(candidate, user_id)

        return decision

    async def judge_batch(
        self,
        candidates: List[MemoryCandidate],
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[MemoryDecision]:
        """批量审查记忆候选"""
        decisions = []

        for candidate in candidates:
            decision = await self.judge(candidate, user_id, context)
            decisions.append(decision)

        return decisions

    def calculate_relevance(self, candidate: MemoryCandidate) -> float:
        """计算相关性分数

        相关性高的特征：
        - 内容具体（不是泛泛而谈）
        - 包含具体数值、名称、地点等
        - 与特定领域相关
        """
        score = 0.5  # 基础分

        content = candidate.content.lower()

        # 包含具体信息加分
        specific_indicators = [
            r"\d+",  # 数字
            r"[a-z0-9]{10,}",  # ID 或代码
            r"[a-z]+://",  # URL
        ]

        import re
        for pattern in specific_indicators:
            if re.search(pattern, content):
                score += 0.1

        # 长度适中（太短或太长都不好）
        length = len(candidate.content)
        if 50 <= length <= 500:
            score += 0.1
        elif length < 20:
            score -= 0.2

        # 包含关键词加分
        if candidate.domain:
            domain_keywords = {
                "outfit": ["穿搭", "衣服", "风格", "颜色", "搭配"],
                "finance": ["价格", "预算", "股票", "金额", "购买"],
                "academic": ["论文", "代码", "仓库", "研究", "算法"],
                "trip": ["景点", "酒店", "路线", "旅行", "行程"],
                "search": ["搜索", "查找", "信息", "资料"]
            }
            keywords = domain_keywords.get(candidate.domain, [])
            if any(kw in content for kw in keywords):
                score += 0.15

        return min(max(score, 0.0), 1.0)

    def calculate_durability(self, candidate: MemoryCandidate) -> float:
        """计算持久性分数

        持久性高的特征：
        - 是用户偏好（而非临时状态）
        - 是成功经验（可以复用）
        - 是领域知识（相对稳定）
        - 不是会话相关的临时信息
        """
        score = 0.5  # 基础分

        # 根据记忆类型调整
        durable_types = [
            MemoryType.USER_PREFERENCE,
            MemoryType.USER_PROFILE,
            MemoryType.DOMAIN_KNOWLEDGE,
            MemoryType.DOMAIN_PATTERN,
            MemoryType.TASK_SUCCESS
        ]

        if candidate.memory_type in durable_types:
            score += 0.3
        elif candidate.memory_type == MemoryType.SESSION_CONTEXT:
            score -= 0.3
        elif candidate.memory_type == MemoryType.USER_FEEDBACK:
            score -= 0.1

        # 偏好类和知识类持久性更高
        if candidate.memory_type == MemoryType.USER_PREFERENCE:
            score += 0.2
        elif candidate.memory_type == MemoryType.DOMAIN_KNOWLEDGE:
            score += 0.15

        return min(max(score, 0.0), 1.0)

    def calculate_user_specificity(self, candidate: MemoryCandidate) -> float:
        """计算用户特异性分数

        特异性高的特征：
        - 包含个人偏好信息
        - 包含用户特定约束
        - 不是通用知识
        """
        score = 0.5  # 基础分

        content = candidate.content.lower()

        # 包含个人化指标
        personal_indicators = [
            "我喜欢", "我偏好", "我不喜欢", "我习惯",
            "我的", "我通常", "我一般",
            "i like", "i prefer", "i usually", "my"
        ]

        for indicator in personal_indicators:
            if indicator in content:
                score += 0.15
                break

        # 偏好类型本身就是用户特异的
        if candidate.memory_type == MemoryType.USER_PREFERENCE:
            score += 0.3
        elif candidate.memory_type == MemoryType.USER_CONSTRAINT:
            score += 0.25

        return min(max(score, 0.0), 1.0)

    def calculate_novelty(
        self,
        candidate: MemoryCandidate,
        existing_memories: List[MemoryItem]
    ) -> float:
        """计算新颖性分数

        新颖性高的特征：
        - 与现有记忆不重复
        - 提供新的信息
        - 不是已有记忆的简单变体
        """
        if not existing_memories:
            return 1.0  # 没有现有记忆，完全是新的

        # 检查与现有记忆的相似度
        max_similarity = 0.0

        for existing in existing_memories:
            similarity = self._compute_similarity(candidate.content, existing.content)
            max_similarity = max(max_similarity, similarity)

            # 如果找到非常相似的，提前结束
            if max_similarity > 0.9:
                break

        # 新颖性 = 1 - 最大相似度
        novelty = 1.0 - max_similarity

        return max(novelty, 0.0)

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度"""
        # 使用简单的序列匹配
        matcher = difflib.SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

    def _decide_target(self, candidate: MemoryCandidate, final_score: float) -> StorageTarget:
        """决定存储目标"""
        settings = get_settings()

        # 检查阈值
        importance_ok = candidate.importance >= settings.memory_store_importance_threshold
        confidence_ok = candidate.confidence >= settings.memory_store_confidence_threshold

        # 不满足基础条件，不存储
        if not (importance_ok or confidence_ok) and final_score < 0.3:
            return StorageTarget.NONE

        # 会话类总是只存短期
        if candidate.memory_type in [MemoryType.SESSION_CONTEXT, MemoryType.SESSION_SUMMARY]:
            return StorageTarget.REDIS

        # 高分数 + 高重要性和置信度 -> 长期存储
        if (final_score >= self.LONG_TERM_THRESHOLD and
            importance_ok and confidence_ok):
            return StorageTarget.MILVUS

        # 中等分数 -> 短期存储
        if final_score >= self.SHORT_TERM_THRESHOLD:
            return StorageTarget.REDIS

        # 自动升级选项
        if settings.memory_auto_upgrade_to_long_term and candidate.importance > 0.8:
            return StorageTarget.BOTH

        return StorageTarget.NONE

    def _generate_reason(
        self,
        candidate: MemoryCandidate,
        target: StorageTarget,
        final_score: float
    ) -> str:
        """生成决策原因"""
        if target == StorageTarget.NONE:
            return f"分数 {final_score:.2f} 过低，不值得存储"
        elif target == StorageTarget.REDIS:
            return f"分数 {final_score:.2f}，适合短期存储"
        elif target == StorageTarget.MILVUS:
            return f"分数 {final_score:.2f}，适合长期存储"
        elif target == StorageTarget.BOTH:
            return f"分数 {final_score:.2f}，同时存储到短期和长期"
        return "未知决策"

    def _candidate_to_item(self, candidate: MemoryCandidate, user_id: str) -> MemoryItem:
        """将候选转换为记忆项"""
        import uuid

        return MemoryItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            memory_type=candidate.memory_type,
            scope=candidate.scope,
            domain=candidate.domain,
            content=candidate.content,
            summary=candidate.content[:200] + "..." if len(candidate.content) > 200 else candidate.content,
            importance=candidate.importance,
            confidence=candidate.confidence,
            relevance=candidate.relevance_score or 0.5,
            created_at=candidate.created_at,
            metadata=candidate.metadata
        )

    async def _get_existing_memories(
        self,
        user_id: str,
        domain: Optional[str]
    ) -> List[MemoryItem]:
        """获取现有记忆（带缓存）"""
        cache_key = f"{user_id}:{domain or 'all'}"

        if cache_key in self._existing_memories_cache:
            return self._existing_memories_cache[cache_key]

        memories = []

        if self._long_term_store:
            try:
                memories = await self._long_term_store.search(
                    user_id=user_id,
                    query="",
                    limit=50,
                    filters={"domain": domain} if domain else None,
                    min_score=0.0
                )
            except Exception as e:
                logger.warning(f"[MemoryJudge] 获取现有记忆失败: {e}")

        self._existing_memories_cache[cache_key] = memories
        return memories

    async def apply_decision(
        self,
        decision: MemoryDecision,
        user_id: str
    ) -> bool:
        """应用存储决策"""
        if decision.target == StorageTarget.NONE:
            return True

        memory_item = decision.memory_item
        if not memory_item:
            logger.warning("[MemoryJudge] 决策有 target 但没有 memory_item")
            return False

        try:
            success = True

            # 存储到 Redis
            if decision.target in [StorageTarget.REDIS, StorageTarget.BOTH]:
                if self._short_term_store:
                    # 根据类型选择存储方式
                    if memory_item.memory_type == MemoryType.USER_PREFERENCE:
                        await self._short_term_store.set_temp_preference(
                            user_id,
                            f"{memory_item.domain or 'global'}_pref",
                            memory_item.content,
                            ttl=86400
                        )
                    elif memory_item.memory_type == MemoryType.USER_FEEDBACK:
                        await self._short_term_store.save_feedback(
                            user_id,
                            memory_item.content,
                            domain=memory_item.domain
                        )
                    else:
                        # 其他类型存到会话上下文
                        await self._short_term_store.save_session_context(
                            user_id,
                            user_id,
                            {"memory": memory_item.content},
                            ttl=3600
                        )

            # 存储到 Milvus
            if decision.target in [StorageTarget.MILVUS, StorageTarget.BOTH]:
                if self._long_term_store:
                    await self._long_term_store.upsert(memory_item)

            logger.info(
                f"[MemoryJudge] 存储成功: {decision.target} - "
                f"{memory_item.memory_type.value}"
            )

            return success

        except Exception as e:
            logger.error(f"[MemoryJudge] 存储失败: {e}")
            return False


# ============ 主图节点函数 ============

async def memory_judge_node(state: dict) -> dict:
    """记忆审查节点 - 主图节点

    在子图执行后，审查候选记忆并决定是否存储

    Args:
        state: 主图状态

    Returns:
        更新后的状态
    """
    try:
        session_id = state.get("session_id", "default")
        user_id = session_id
        subgraph_outputs = state.get("subgraph_outputs", {})
        active_domain = state.get("active_domain", "")

        # 从子图输出中提取候选记忆
        candidate_memories = []

        for domain, output in subgraph_outputs.items():
            if isinstance(output, dict) and "candidate_memories" in output:
                candidates = output["candidate_memories"]
                if isinstance(candidates, list):
                    candidate_memories.extend(candidates)

        if not candidate_memories:
            logger.debug("[MemoryJudge] 没有候选记忆需要审查")
            state["memory_decisions"] = []
            return state

        logger.info(f"[MemoryJudge] 开始审查 {len(candidate_memories)} 个候选记忆...")

        # 创建审查器
        judge = MemoryJudge()

        # 审查每个候选
        decisions = []
        for candidate_data in candidate_memories:
            # 转换为 MemoryCandidate
            if isinstance(candidate_data, dict):
                candidate = MemoryCandidate(**candidate_data)
            else:
                candidate = candidate_data

            decision = await judge.judge(candidate, user_id)
            decisions.append(decision)

            # 应用决策
            await judge.apply_decision(decision, user_id)

        # 统计
        stored_long = sum(1 for d in decisions if d.target in [StorageTarget.MILVUS, StorageTarget.BOTH])
        stored_short = sum(1 for d in decisions if d.target in [StorageTarget.REDIS, StorageTarget.BOTH])
        skipped = sum(1 for d in decisions if d.target == StorageTarget.NONE)

        logger.info(
            f"[MemoryJudge] 审查完成: "
            f"{stored_long} 长期, {stored_short - stored_long} 短期, {skipped} 跳过"
        )

        state["memory_decisions"] = [
            {
                "candidate": d.candidate.content[:50],
                "target": d.target.value,
                "score": d.final_score,
                "reason": d.reason
            }
            for d in decisions
        ]

    except Exception as e:
        logger.error(f"[MemoryJudge] 节点执行失败: {e}")
        state["memory_decisions"] = []

    return state


# ============ 便捷函数 ============

async def judge_and_store(
    candidates: List[MemoryCandidate],
    user_id: str
) -> List[MemoryDecision]:
    """便捷函数：审查并存储候选记忆"""
    judge = MemoryJudge()

    decisions = await judge.judge_batch(candidates, user_id)

    # 应用所有决策
    for decision in decisions:
        await judge.apply_decision(decision, user_id)

    return decisions


def create_preference_candidate(
    content: str,
    domain: str,
    importance: float = 0.7,
    user_id: str = "default"
) -> MemoryCandidate:
    """便捷函数：创建偏好类候选记忆"""
    return MemoryCandidate(
        content=content,
        memory_type=MemoryType.USER_PREFERENCE,
        scope=MemoryScope.DOMAIN,
        domain=domain,
        importance=importance,
        confidence=0.8,
        source=f"subgraph:{domain}",
        metadata={"type": "preference"}
    )


def create_episode_candidate(
    content: str,
    domain: str,
    success: bool,
    importance: float = 0.6
) -> MemoryCandidate:
    """便捷函数：创建经历类候选记忆"""
    memory_type = MemoryType.TASK_SUCCESS if success else MemoryType.TASK_FAILURE

    return MemoryCandidate(
        content=content,
        memory_type=memory_type,
        scope=MemoryScope.DOMAIN,
        domain=domain,
        importance=importance,
        confidence=0.7,
        source=f"subgraph:{domain}",
        metadata={"type": "episode", "success": success}
    )
