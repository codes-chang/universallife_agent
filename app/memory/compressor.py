"""记忆压缩器

将检索到的记忆压缩为更紧凑的形式，减少 token 消耗。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import MemoryItem, MemoryBundle
from ..core.logging import logger
from ..services.llm_service import get_llm
from langchain_core.messages import HumanMessage, SystemMessage


class MemoryCompressor:
    """记忆压缩器

    负责将多个记忆项压缩为更紧凑的表示
    """

    def __init__(self, max_items: int = 5, use_llm: bool = True):
        self.max_items = max_items
        self.use_llm = use_llm

    async def compress_bundle(self, bundle: MemoryBundle) -> MemoryBundle:
        """压缩记忆束

        Args:
            bundle: 原始记忆束

        Returns:
            压缩后的记忆束
        """
        if bundle.is_empty():
            return bundle

        # 限制数量
        compressed_bundle = MemoryBundle(
            has_memory=bundle.has_memory,
            global_preferences=bundle.global_preferences[:self.max_items],
            domain_memories=bundle.domain_memories[:self.max_items],
            recent_context=bundle.recent_context[:self.max_items],
            recent_feedback=bundle.recent_feedback[:3],  # 反馈限制更少
            user_constraints=bundle.user_constraints[:3],
            retrieval_metadata=bundle.retrieval_metadata
        )

        # 如果启用 LLM，生成摘要
        if self.use_llm:
            compressed_bundle.summary = await self._generate_summary(compressed_bundle)

        return compressed_bundle

    async def compress_memories(self, memories: List[MemoryItem]) -> str:
        """将多个记忆压缩为一段文字

        Args:
            memories: 记忆列表

        Returns:
            压缩后的文本
        """
        if not memories:
            return ""

        # 限制数量
        memories = memories[:self.max_items]

        if not self.use_llm:
            # 简单压缩：提取关键点
            return self._simple_compress(memories)

        # 使用 LLM 压缩
        return await self._llm_compress(memories)

    def _simple_compress(self, memories: List[MemoryItem]) -> str:
        """简单压缩（不使用 LLM）"""
        parts = []
        for m in memories:
            if m.summary:
                parts.append(f"- {m.summary}")
            elif m.key_points:
                parts.append(f"- {m.key_points[0]}")
            else:
                # 截断内容
                content = m.content[:80] + "..." if len(m.content) > 80 else m.content
                parts.append(f"- {content}")

        return "\n".join(parts)

    async def _llm_compress(self, memories: List[MemoryItem]) -> str:
        """使用 LLM 压缩"""
        try:
            llm = get_llm()

            # 构建输入
            memory_texts = []
            for i, m in enumerate(memories, 1):
                memory_texts.append(f"{i}. {m.content}")

            prompt = f"""请将以下 {len(memories)} 条记忆压缩为简洁的摘要，保留关键信息：

{chr(10).join(memory_texts)}

要求：
1. 提取最重要的 3-5 个关键点
2. 每个点不超过 20 字
3. 使用列表格式
4. 省略冗余信息

直接输出摘要，不要额外说明。
"""

            response = await llm.ainvoke([
                SystemMessage(content="你是信息摘要专家，擅长提取关键信息。"),
                HumanMessage(content=prompt)
            ])

            return response.content if hasattr(response, 'content') else str(response)

        except Exception as e:
            logger.warning(f"[Compressor] LLM 压缩失败，使用简单压缩: {e}")
            return self._simple_compress(memories)

    async def _generate_summary(self, bundle: MemoryBundle) -> str:
        """生成记忆束的摘要"""
        try:
            llm = get_llm()

            parts = []

            if bundle.global_preferences:
                prefs = await self.compress_memories(bundle.global_preferences)
                if prefs:
                    parts.append(f"**用户偏好**\n{prefs}")

            if bundle.domain_memories:
                domain = await self.compress_memories(bundle.domain_memories)
                if domain:
                    parts.append(f"**相关经验**\n{domain}")

            if bundle.user_constraints:
                constraints = "\n".join(f"- {m.content}" for m in bundle.user_constraints)
                parts.append(f"**用户约束**\n{constraints}")

            if bundle.recent_feedback:
                feedbacks = "\n".join(
                    f"- {f.get('feedback', f.get('content', ''))[:50]}"
                    for f in bundle.recent_feedback[-3:]
                )
                parts.append(f"**最近反馈**\n{feedbacks}")

            return "\n\n".join(parts) if parts else None

        except Exception as e:
            logger.warning(f"[Compressor] 生成摘要失败: {e}")
            return None

    def deduplicate_memories(
        self,
        memories: List[MemoryItem],
        similarity_threshold: float = 0.85
    ) -> List[MemoryItem]:
        """去重相似的记忆

        Args:
            memories: 记忆列表
            similarity_threshold: 相似度阈值

        Returns:
            去重后的记忆列表
        """
        if not memories:
            return []

        unique_memories = []
        seen_contents = set()

        for memory in memories:
            # 使用内容的前100字符作为简单去重依据
            content_key = memory.content[:100].lower().strip()

            # 检查是否相似
            is_duplicate = False
            for seen in seen_contents:
                if self._text_similarity(content_key, seen) > similarity_threshold:
                    is_duplicate = True
                    # 保留重要性更高的
                    break

            if not is_duplicate:
                unique_memories.append(memory)
                seen_contents.add(content_key)

        return unique_memories

    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算（基于词重叠）"""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def rank_by_relevance_and_importance(
        self,
        memories: List[MemoryItem]
    ) -> List[MemoryItem]:
        """按相关性和重要性排序记忆

        Args:
            memories: 记忆列表

        Returns:
            排序后的记忆列表
        """
        def score(memory: MemoryItem) -> float:
            # 综合分数 = 相关性 * 0.6 + 重要性 * 0.3 + 访问频率因子 * 0.1
            access_factor = min(memory.access_count / 10.0, 1.0)
            return (
                memory.relevance * 0.6 +
                memory.importance * 0.3 +
                access_factor * 0.1
            )

        return sorted(memories, key=score, reverse=True)


# ============ 便捷函数 ============

async def compress_memory_bundle(bundle: MemoryBundle) -> MemoryBundle:
    """压缩记忆束（便捷函数）"""
    compressor = MemoryCompressor()
    return await compressor.compress_bundle(bundle)


def deduplicate_and_rank(memories: List[MemoryItem]) -> List[MemoryItem]:
    """去重并排序记忆（便捷函数）"""
    compressor = MemoryCompressor()
    unique = compressor.deduplicate_memories(memories)
    return compressor.rank_by_relevance_and_importance(unique)
