"""Redis 短期记忆存储层

实现基于 Redis 的短期记忆存储，支持：
- 会话上下文存储
- 对话历史
- 用户反馈
- 子图结果缓存
- 临时偏好
- 检查点
"""

import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .interfaces import IShortTermStore, SessionCheckpoint
from ..core.logging import logger
from ..core.config import get_settings


class RedisShortTermStore(IShortTermStore):
    """Redis 短期记忆存储实现"""

    # Redis key 前缀
    KEY_PREFIX = "ula:"
    SESSION_PREFIX = f"{KEY_PREFIX}session:"
    HISTORY_PREFIX = f"{KEY_PREFIX}history:"
    FEEDBACK_PREFIX = f"{KEY_PREFIX}feedback:"
    CACHE_PREFIX = f"{KEY_PREFIX}cache:"
    PREF_PREFIX = f"{KEY_PREFIX}pref:"
    CHECKPOINT_PREFIX = f"{KEY_PREFIX}checkpoint:"

    def __init__(
        self,
        url: Optional[str] = None,
        enabled: Optional[bool] = None
    ):
        settings = get_settings()
        self.url = url or settings.redis_url
        self.enabled = enabled if enabled is not None else settings.redis_enabled
        self._client = None
        self._mock_storage: Dict[str, Any] = {}  # Mock 存储（降级使用）

    async def initialize(self) -> bool:
        """初始化 Redis 连接"""
        if not self.enabled:
            logger.info("[RedisStore] Redis 未启用，使用 Mock 存储")
            return True

        try:
            import redis.asyncio as aioredis
            self._client = await aioredis.from_url(self.url, decode_responses=True)
            await self._client.ping()
            logger.info(f"[RedisStore] Redis 连接成功: {self.url}")
            return True
        except ImportError:
            logger.warning("[RedisStore] redis-py 未安装，使用 Mock 存储")
            self.enabled = False
            return True
        except Exception as e:
            logger.error(f"[RedisStore] Redis 连接失败: {e}，使用 Mock 存储")
            self.enabled = False
            return True

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("[RedisStore] Redis 连接已关闭")

    async def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        if not self.enabled or self._client is None:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    # ============ 辅助方法 ============

    def _make_key(self, prefix: str, *parts: str) -> str:
        """生成 Redis key"""
        return prefix + ":".join(str(p) for p in parts)

    async def _set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置值（支持 Mock）"""
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)

            if self.enabled and self._client:
                if ttl:
                    await self._client.setex(key, ttl, serialized)
                else:
                    await self._client.set(key, serialized)
            else:
                # Mock 存储
                self._mock_storage[key] = {
                    "value": value,
                    "expires": datetime.now() + timedelta(seconds=ttl) if ttl else None
                }

            return True
        except Exception as e:
            logger.warning(f"[RedisStore] 设置失败 {key}: {e}")
            return False

    async def _get(self, key: str) -> Optional[Any]:
        """获取值（支持 Mock）"""
        try:
            if self.enabled and self._client:
                value = await self._client.get(key)
                if value:
                    return json.loads(value)
            else:
                # Mock 存储
                data = self._mock_storage.get(key)
                if data:
                    if data["expires"] and datetime.now() > data["expires"]:
                        del self._mock_storage[key]
                        return None
                    return data["value"]

            return None
        except Exception as e:
            logger.warning(f"[RedisStore] 获取失败 {key}: {e}")
            return None

    async def _delete(self, key: str) -> bool:
        """删除值"""
        try:
            if self.enabled and self._client:
                await self._client.delete(key)
            else:
                self._mock_storage.pop(key, None)
            return True
        except Exception as e:
            logger.warning(f"[RedisStore] 删除失败 {key}: {e}")
            return False

    # ============ 会话相关 ============

    async def save_session_context(
        self,
        session_id: str,
        user_id: str,
        context: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """保存会话上下文"""
        settings = get_settings()
        ttl = ttl or settings.redis_ttl_session

        key = self._make_key(self.SESSION_PREFIX, session_id)
        data = {
            "user_id": user_id,
            "context": context,
            "updated_at": datetime.now().isoformat()
        }

        return await self._set(key, data, ttl)

    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话上下文"""
        key = self._make_key(self.SESSION_PREFIX, session_id)
        data = await self._get(key)
        return data.get("context") if data else None

    async def add_to_history(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """添加对话历史"""
        settings = get_settings()
        key = self._make_key(self.HISTORY_PREFIX, session_id)

        # 获取现有历史
        history = await self._get(key) or []

        # 添加新条目
        entry = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        history.append(entry)

        # 限制历史长度（保留最近 50 条）
        history = history[-50:]

        # 保存（使用 TTL）
        ttl = settings.redis_ttl_context
        return await self._set(key, history, ttl)

    async def get_recent_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取最近的历史记录"""
        key = self._make_key(self.HISTORY_PREFIX, session_id)
        history = await self._get(key) or []
        return history[-limit:] if history else []

    # ============ 反馈相关 ============

    async def save_feedback(
        self,
        user_id: str,
        feedback: str,
        domain: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """保存用户反馈"""
        settings = get_settings()
        ttl = ttl or settings.redis_ttl_feedback

        key = self._make_key(self.FEEDBACK_PREFIX, user_id)

        # 获取现有反馈
        feedbacks = await self._get(key) or []

        # 添加新反馈
        entry = {
            "feedback": feedback,
            "domain": domain,
            "timestamp": datetime.now().isoformat()
        }
        feedbacks.append(entry)

        # 限制数量
        feedbacks = feedbacks[-20:]

        return await self._set(key, feedbacks, ttl)

    async def get_recent_feedback(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取最近的反馈"""
        key = self._make_key(self.FEEDBACK_PREFIX, user_id)
        feedbacks = await self._get(key) or []
        return feedbacks[-limit:] if feedbacks else []

    # ============ 子图结果缓存 ============

    async def cache_subgraph_result(
        self,
        user_id: str,
        domain: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """缓存子图执行结果"""
        ttl = ttl or 600  # 默认 10 分钟

        key = self._make_key(self.CACHE_PREFIX, user_id, domain)
        data = {
            "result": result,
            "cached_at": datetime.now().isoformat()
        }

        return await self._set(key, data, ttl)

    async def get_cached_result(
        self,
        user_id: str,
        domain: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的子图结果"""
        key = self._make_key(self.CACHE_PREFIX, user_id, domain)
        data = await self._get(key)
        return data.get("result") if data else None

    # ============ 临时偏好 ============

    async def set_temp_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """设置临时偏好"""
        ttl = ttl or 86400  # 默认 24 小时

        redis_key = self._make_key(self.PREF_PREFIX, user_id)
        pref_data = await self._get(redis_key) or {}

        pref_data[key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }

        return await self._set(redis_key, pref_data, ttl)

    async def get_temp_preference(
        self,
        user_id: str,
        key: str
    ) -> Optional[Any]:
        """获取临时偏好"""
        redis_key = self._make_key(self.PREF_PREFIX, user_id)
        pref_data = await self._get(redis_key)

        if pref_data and key in pref_data:
            return pref_data[key].get("value")
        return None

    async def get_all_temp_preferences(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """获取所有临时偏好"""
        redis_key = self._make_key(self.PREF_PREFIX, user_id)
        pref_data = await self._get(redis_key) or {}

        return {k: v.get("value") for k, v in pref_data.items()}

    # ============ 检查点 ============

    async def save_checkpoint(
        self,
        session_id: str,
        checkpoint: SessionCheckpoint
    ) -> bool:
        """保存检查点"""
        key = self._make_key(self.CHECKPOINT_PREFIX, session_id)
        data = checkpoint.model_dump()
        ttl = 3600  # 检查点保留 1 小时

        return await self._set(key, data, ttl)

    async def get_checkpoint(
        self,
        session_id: str
    ) -> Optional[SessionCheckpoint]:
        """获取检查点"""
        key = self._make_key(self.CHECKPOINT_PREFIX, session_id)
        data = await self._get(key)

        if data:
            return SessionCheckpoint(**data)
        return None

    async def clear_session(self, session_id: str) -> bool:
        """清除会话数据"""
        keys = [
            self._make_key(self.SESSION_PREFIX, session_id),
            self._make_key(self.HISTORY_PREFIX, session_id),
            self._make_key(self.CHECKPOINT_PREFIX, session_id),
        ]

        if self.enabled and self._client:
            try:
                await self._client.delete(*keys)
            except Exception as e:
                logger.warning(f"[RedisStore] 清除会话失败: {e}")
        else:
            for key in keys:
                self._mock_storage.pop(key, None)

        return True


# ============ 全局单例 ============

_redis_store: Optional[RedisShortTermStore] = None


async def get_redis_store() -> RedisShortTermStore:
    """获取 Redis 存储单例"""
    global _redis_store
    if _redis_store is None:
        _redis_store = RedisShortTermStore()
        await _redis_store.initialize()
    return _redis_store
