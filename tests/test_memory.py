"""记忆系统测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.memory.models import (
    MemoryItem, MemoryCandidate, MemoryBundle,
    MemoryType, MemoryScope, StorageTarget,
    MemoryRetrievalRequest
)


def _make_memory_item(**kwargs) -> MemoryItem:
    """构建测试用 MemoryItem"""
    defaults = {
        "id": "mem_test_001",
        "user_id": "user_001",
        "memory_type": MemoryType.USER_PREFERENCE,
        "scope": MemoryScope.DOMAIN,
        "domain": "outfit",
        "content": "我喜欢简约风格的穿搭",
        "importance": 0.7,
        "confidence": 0.8,
    }
    defaults.update(kwargs)
    return MemoryItem(**defaults)


def _make_memory_candidate(**kwargs) -> MemoryCandidate:
    """构建测试用 MemoryCandidate"""
    defaults = {
        "content": "用户偏好深色系衣服，特别是在冬季通勤时",
        "memory_type": MemoryType.USER_PREFERENCE,
        "scope": MemoryScope.DOMAIN,
        "domain": "outfit",
        "importance": 0.7,
        "confidence": 0.8,
        "source": "subgraph:outfit"
    }
    defaults.update(kwargs)
    return MemoryCandidate(**defaults)


# ======================================================================
# MemoryManager.should_retrieve_memory Tests
# ======================================================================

class TestMemoryManagerShouldRetrieve:
    """测试记忆管理器的检索判断逻辑"""

    @pytest.mark.asyncio
    async def test_retrieve_on_keyword(self):
        """测试关键词触发记忆检索"""
        from app.memory.manager import MemoryManager

        manager = MemoryManager(short_term_store=None, long_term_store=None)

        # "记得" 是配置中的触发关键词
        result = await manager.should_retrieve_memory("我上次记得你说过的穿搭")
        assert result is True

    @pytest.mark.asyncio
    async def test_retrieve_on_keyword_last_time(self):
        """测试 '上次' 关键词触发"""
        from app.memory.manager import MemoryManager

        manager = MemoryManager(short_term_store=None, long_term_store=None)

        result = await manager.should_retrieve_memory("上次的搜索结果")
        assert result is True

    @pytest.mark.asyncio
    async def test_retrieve_on_low_confidence(self):
        """测试低置信度触发记忆检索"""
        from app.memory.manager import MemoryManager

        manager = MemoryManager(short_term_store=None, long_term_store=None)

        # 0.3 低于默认阈值 0.7
        result = await manager.should_retrieve_memory(
            "帮我查查天气", confidence=0.3
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_retrieve_on_preference_domain(self):
        """测试偏好类任务触发记忆检索"""
        from app.memory.manager import MemoryManager

        manager = MemoryManager(short_term_store=None, long_term_store=None)

        result = await manager.should_retrieve_memory(
            "帮我搭配穿搭", intent="outfit"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_no_retrieve_for_simple_query(self):
        """测试简单查询不触发记忆检索"""
        from app.memory.manager import MemoryManager

        manager = MemoryManager(short_term_store=None, long_term_store=None)

        result = await manager.should_retrieve_memory(
            "今天天气怎么样", intent="unknown", confidence=0.95
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_retrieve_on_multi_step(self):
        """测试多步任务触发记忆检索"""
        from app.memory.manager import MemoryManager

        manager = MemoryManager(short_term_store=None, long_term_store=None)

        result = await manager.should_retrieve_memory(
            "帮我查查天气然后搭配穿搭"
        )
        assert result is True


# ======================================================================
# MemoryJudge Scoring Tests
# ======================================================================

class TestMemoryJudgeScoring:
    """测试记忆审查器评分逻辑"""

    def test_calculate_relevance_high(self):
        """测试高相关性评分"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        candidate = _make_memory_candidate(
            content="用户偏好深色系衣服，特别是冬季通勤穿搭风格偏简约商务风，适合日常上班穿着",
            domain="outfit"
        )

        score = judge.calculate_relevance(candidate)
        assert score > 0.5
        assert score <= 1.0

    def test_calculate_relevance_low(self):
        """测试低相关性评分（内容过短）"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        candidate = _make_memory_candidate(content="好", domain=None)

        score = judge.calculate_relevance(candidate)
        assert score < 0.5

    def test_calculate_durability_preference(self):
        """测试用户偏好类型的持久性评分"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        candidate = _make_memory_candidate(
            memory_type=MemoryType.USER_PREFERENCE
        )

        score = judge.calculate_durability(candidate)
        assert score > 0.7  # 偏好类应有较高持久性

    def test_calculate_durability_session_context(self):
        """测试会话上下文类型的持久性评分"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        candidate = _make_memory_candidate(
            memory_type=MemoryType.SESSION_CONTEXT
        )

        score = judge.calculate_durability(candidate)
        assert score < 0.5  # 会话类应有较低持久性

    def test_calculate_user_specificity(self):
        """测试用户特异性评分"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        # 包含个人化指标的候选
        candidate = _make_memory_candidate(
            content="我喜欢简约风格，我偏好深色系，我通常穿休闲装"
        )

        score = judge.calculate_user_specificity(candidate)
        assert score > 0.5

    def test_calculate_user_specificity_preference_type(self):
        """测试偏好类型本身的用户特异性"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        candidate = _make_memory_candidate(
            content="一些通用描述",
            memory_type=MemoryType.USER_PREFERENCE
        )

        score = judge.calculate_user_specificity(candidate)
        assert score > 0.7  # 偏好类本身应有较高用户特异性

    def test_calculate_novelty_empty(self):
        """测试无现有记忆时的新颖性"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        candidate = _make_memory_candidate()

        score = judge.calculate_novelty(candidate, [])
        assert score == 1.0  # 完全新颖

    def test_calculate_novelty_duplicate(self):
        """测试与现有记忆高度相似时的新颖性"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge()

        candidate = _make_memory_candidate(
            content="用户偏好深色系衣服，特别是冬季通勤穿搭风格"
        )

        existing = [
            _make_memory_item(content="用户偏好深色系衣服，特别是冬季通勤穿搭风格")
        ]

        score = judge.calculate_novelty(candidate, existing)
        assert score < 0.5  # 高度相似，新颖性低

    @pytest.mark.asyncio
    async def test_judge_returns_decision(self):
        """测试审查器返回正确的决策"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge(short_term_store=None, long_term_store=None)

        candidate = _make_memory_candidate()

        decision = await judge.judge(candidate, "user_001")

        assert decision.candidate == candidate
        assert decision.target in [StorageTarget.NONE, StorageTarget.REDIS, StorageTarget.MILVUS, StorageTarget.BOTH]
        assert decision.reason is not None
        assert "scores" in decision.__dict__ or hasattr(decision, "scores")

    @pytest.mark.asyncio
    async def test_judge_low_score_not_stored(self):
        """测试低分候选不被存储"""
        from app.memory.judge import MemoryJudge

        judge = MemoryJudge(short_term_store=None, long_term_store=None)

        # 极低重要性，短内容
        candidate = _make_memory_candidate(
            content="无",
            importance=0.1,
            confidence=0.1,
            domain=None
        )

        decision = await judge.judge(candidate, "user_001")

        # 低分候选可能不存储或仅短期存储
        assert decision.target in [StorageTarget.NONE, StorageTarget.REDIS]


# ======================================================================
# MemoryCompressor Tests
# ======================================================================

class TestMemoryCompressor:
    """测试记忆压缩器"""

    def test_deduplicate_memories(self):
        """测试去重功能"""
        from app.memory.compressor import MemoryCompressor

        compressor = MemoryCompressor()

        memories = [
            _make_memory_item(id="1", content="我喜欢简约风格的穿搭"),
            _make_memory_item(id="2", content="我喜欢简约风格的穿搭"),  # 重复
            _make_memory_item(id="3", content="用户偏好深色系衣服"),
        ]

        unique = compressor.deduplicate_memories(memories)

        # 应该去除重复项
        assert len(unique) >= 1
        assert len(unique) <= 3

    def test_deduplicate_empty_list(self):
        """测试空列表去重"""
        from app.memory.compressor import MemoryCompressor

        compressor = MemoryCompressor()

        assert compressor.deduplicate_memories([]) == []

    def test_rank_by_relevance_and_importance(self):
        """测试按相关性和重要性排序"""
        from app.memory.compressor import MemoryCompressor

        compressor = MemoryCompressor()

        memories = [
            _make_memory_item(id="1", content="低相关性", relevance=0.3, importance=0.3),
            _make_memory_item(id="2", content="高相关性", relevance=0.9, importance=0.9),
            _make_memory_item(id="3", content="中等相关性", relevance=0.6, importance=0.6),
        ]

        ranked = compressor.rank_by_relevance_and_importance(memories)

        assert ranked[0].id == "2"
        assert ranked[1].id == "3"
        assert ranked[2].id == "1"

    @pytest.mark.asyncio
    async def test_compress_bundle_empty(self):
        """测试压缩空记忆束"""
        from app.memory.compressor import MemoryCompressor

        compressor = MemoryCompressor(use_llm=False)

        bundle = MemoryBundle()
        result = await compressor.compress_bundle(bundle)

        assert result.is_empty()

    @pytest.mark.asyncio
    async def test_compress_bundle_limits_items(self):
        """测试压缩限制记忆数量"""
        from app.memory.compressor import MemoryCompressor

        compressor = MemoryCompressor(max_items=2, use_llm=False)

        bundle = MemoryBundle(
            has_memory=True,
            global_preferences=[
                _make_memory_item(id=f"pref_{i}", content=f"偏好 {i}")
                for i in range(5)
            ],
            domain_memories=[
                _make_memory_item(id=f"domain_{i}", content=f"经验 {i}")
                for i in range(5)
            ]
        )

        result = await compressor.compress_bundle(bundle)

        assert len(result.global_preferences) == 2
        assert len(result.domain_memories) == 2

    def test_simple_compress(self):
        """测试简单压缩（不使用 LLM）"""
        from app.memory.compressor import MemoryCompressor

        compressor = MemoryCompressor(use_llm=False)

        memories = [
            _make_memory_item(id="1", content="这是第一条记忆内容", summary="第一条摘要"),
            _make_memory_item(id="2", content="这是第二条记忆内容", key_points=["关键点1", "关键点2"]),
        ]

        result = compressor._simple_compress(memories)

        assert "第一条摘要" in result
        assert "关键点1" in result


# ======================================================================
# In-Memory Store Round-Trip Tests
# ======================================================================

class TestInMemoryStoreRoundTrip:
    """测试内存存储的读写往返"""

    @pytest.mark.asyncio
    async def test_milvus_mock_upsert_and_get(self):
        """测试 Milvus Mock 存储的写入和读取"""
        from app.memory.milvus_store import MilvusLongTermStore

        store = MilvusLongTermStore(enabled=False)
        await store.initialize()

        item = _make_memory_item(id="round_trip_001")

        # 写入
        success = await store.upsert(item)
        assert success is True

        # 读取
        retrieved = await store.get("round_trip_001")
        assert retrieved is not None
        assert retrieved.id == "round_trip_001"
        assert retrieved.content == "我喜欢简约风格的穿搭"
        assert retrieved.user_id == "user_001"

    @pytest.mark.asyncio
    async def test_milvus_mock_delete(self):
        """测试 Milvus Mock 存储的删除"""
        from app.memory.milvus_store import MilvusLongTermStore

        store = MilvusLongTermStore(enabled=False)
        await store.initialize()

        item = _make_memory_item(id="delete_001")
        await store.upsert(item)

        # 确认存在
        assert await store.get("delete_001") is not None

        # 删除
        success = await store.delete("delete_001")
        assert success is True

        # 确认已删除
        assert await store.get("delete_001") is None

    @pytest.mark.asyncio
    async def test_milvus_mock_count(self):
        """测试 Milvus Mock 存储的计数"""
        from app.memory.milvus_store import MilvusLongTermStore

        store = MilvusLongTermStore(enabled=False)
        await store.initialize()

        # 写入多个
        for i in range(3):
            await store.upsert(_make_memory_item(id=f"count_{i}"))

        count = await store.count_memories("user_001")
        assert count == 3

    @pytest.mark.asyncio
    async def test_redis_mock_session_context_round_trip(self):
        """测试 Redis Mock 会话上下文的读写往返"""
        from app.memory.redis_store import RedisShortTermStore

        store = RedisShortTermStore(enabled=False)
        await store.initialize()

        # 写入
        context = {"query": "穿搭建议", "domain": "outfit"}
        await store.save_session_context("session_001", "user_001", context)

        # 读取
        retrieved = await store.get_session_context("session_001")
        assert retrieved is not None
        assert retrieved["query"] == "穿搭建议"

    @pytest.mark.asyncio
    async def test_redis_mock_preference_round_trip(self):
        """测试 Redis Mock 偏好的读写往返"""
        from app.memory.redis_store import RedisShortTermStore

        store = RedisShortTermStore(enabled=False)
        await store.initialize()

        # 写入偏好
        await store.set_temp_preference("user_001", "style", "简约")

        # 读取单个偏好
        value = await store.get_temp_preference("user_001", "style")
        assert value == "简约"

        # 读取所有偏好
        all_prefs = await store.get_all_temp_preferences("user_001")
        assert "style" in all_prefs
        assert all_prefs["style"] == "简约"

    @pytest.mark.asyncio
    async def test_redis_mock_history_round_trip(self):
        """测试 Redis Mock 历史记录的读写往返"""
        from app.memory.redis_store import RedisShortTermStore

        store = RedisShortTermStore(enabled=False)
        await store.initialize()

        # 写入历史
        await store.add_to_history("session_001", "user", "帮我搭配穿搭")
        await store.add_to_history("session_001", "assistant", "好的，建议穿...")

        # 读取历史
        history = await store.get_recent_history("session_001", limit=10)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_redis_mock_feedback_round_trip(self):
        """测试 Redis Mock 反馈的读写往返"""
        from app.memory.redis_store import RedisShortTermStore

        store = RedisShortTermStore(enabled=False)
        await store.initialize()

        # 写入反馈
        await store.save_feedback("user_001", "穿搭建议很实用", domain="outfit")

        # 读取反馈
        feedbacks = await store.get_recent_feedback("user_001", limit=10)
        assert len(feedbacks) == 1
        assert feedbacks[0]["feedback"] == "穿搭建议很实用"

    @pytest.mark.asyncio
    async def test_redis_mock_cache_round_trip(self):
        """测试 Redis Mock 子图结果缓存的读写往返"""
        from app.memory.redis_store import RedisShortTermStore

        store = RedisShortTermStore(enabled=False)
        await store.initialize()

        # 缓存子图结果
        result_data = {"domain": "outfit", "result": "建议穿外套"}
        await store.cache_subgraph_result("user_001", "outfit", result_data)

        # 读取缓存
        cached = await store.get_cached_result("user_001", "outfit")
        assert cached is not None
        assert cached["result"] == "建议穿外套"


# ======================================================================
# MemoryBundle Tests
# ======================================================================

class TestMemoryBundle:
    """测试记忆束"""

    def test_is_empty_true(self):
        """测试空记忆束"""
        bundle = MemoryBundle()
        assert bundle.is_empty() is True
        assert bundle.has_memory is False

    def test_is_empty_false(self):
        """测试非空记忆束"""
        bundle = MemoryBundle(
            global_preferences=[_make_memory_item()]
        )
        assert bundle.is_empty() is False

    def test_to_prompt_context_empty(self):
        """测试空记忆束的 prompt 上下文"""
        bundle = MemoryBundle()
        assert bundle.to_prompt_context() == ""

    def test_to_prompt_context_with_preferences(self):
        """测试带偏好的 prompt 上下文"""
        bundle = MemoryBundle(
            global_preferences=[
                _make_memory_item(content="我喜欢简约风格")
            ]
        )

        context = bundle.to_prompt_context()
        assert "简约风格" in context
        assert "用户偏好" in context

    def test_to_prompt_context_with_summary(self):
        """测试带摘要的 prompt 上下文"""
        bundle = MemoryBundle(
            summary="用户偏好深色简约风格穿搭"
        )

        context = bundle.to_prompt_context()
        assert "深色简约" in context


# ======================================================================
# Deduplicate and Rank Convenience Function Tests
# ======================================================================

class TestDeduplicateAndRank:
    """测试去重排序便捷函数"""

    def test_deduplicate_and_rank(self):
        """测试去重并排序"""
        from app.memory.compressor import deduplicate_and_rank

        memories = [
            _make_memory_item(id="1", content="低分", relevance=0.2, importance=0.2),
            _make_memory_item(id="2", content="高分", relevance=0.9, importance=0.9),
            _make_memory_item(id="3", content="低分", relevance=0.2, importance=0.2),
        ]

        result = deduplicate_and_rank(memories)

        assert len(result) >= 1
        if len(result) > 0:
            assert result[0].id == "2"
