"""Milvus 长期记忆存储层

实现基于 Milvus 的长期记忆存储，支持：
- 向量检索
- 元数据过滤
- 跨会话记忆持久化
"""

import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from .interfaces import ILongTermStore
from .models import MemoryItem, MemoryType, MemoryScope
from .embeddings import get_global_embedding_provider
from ..core.logging import logger
from ..core.config import get_settings


class MilvusLongTermStore(ILongTermStore):
    """Milvus 长期记忆存储实现"""

    # Collection 名称
    COLLECTION_NAME = "universal_agent_memories"

    # 字段名称
    FIELD_ID = "memory_id"
    FIELD_USER_ID = "user_id"
    FIELD_MEMORY_TYPE = "memory_type"
    FIELD_SCOPE = "scope"
    FIELD_DOMAIN = "domain"
    FIELD_CONTENT = "content"
    FIELD_SUMMARY = "summary"
    FIELD_IMPORTANCE = "importance"
    FIELD_CONFIDENCE = "confidence"
    FIELD_CREATED_AT = "created_at"
    FIELD_UPDATED_AT = "updated_at"
    FIELD_METADATA = "metadata"
    FIELD_EMBEDDING = "embedding"
    FIELD_EXPIRES_AT = "expires_at"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
        enabled: Optional[bool] = None
    ):
        settings = get_settings()
        self.host = host or settings.milvus_host
        self.port = port or settings.milvus_port
        self.collection_name = collection_name or settings.milvus_collection_name
        self.enabled = enabled if enabled is not None else settings.milvus_enabled
        self._client = None
        self._collection = None
        self._mock_storage: Dict[str, MemoryItem] = {}  # Mock 存储（降级使用）
        self._embedding_provider = get_global_embedding_provider()

    async def initialize(self) -> bool:
        """初始化 Milvus 连接和集合"""
        if not self.enabled:
            logger.info("[MilvusStore] Milvus 未启用，使用 Mock 存储")
            return True

        try:
            from pymilvus import MilvusClient, DataType

            # 创建 Milvus 客户端
            self._client = MilvusClient(
                uri=f"http://{self.host}:{self.port}"
            )

            # 检查集合是否存在
            if not self._client.has_collection(self.collection_name):
                logger.info(f"[MilvusStore] 创建集合: {self.collection_name}")
                self._create_collection()
            else:
                self._collection = self._client

            logger.info(f"[MilvusStore] Milvus 连接成功: {self.host}:{self.port}")
            return True

        except ImportError:
            logger.warning("[MilvusStore] pymilvus 未安装，使用 Mock 存储")
            self.enabled = False
            return True
        except Exception as e:
            logger.error(f"[MilvusStore] Milvus 连接失败: {e}，使用 Mock 存储")
            self.enabled = False
            return True

    def _create_collection(self):
        """创建 Collection"""
        from pymilvus import MilvusClient

        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=False
        )

        # 添加标量字段
        schema.add_field(field_name=self.FIELD_ID, datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(field_name=self.FIELD_USER_ID, datatype=DataType.VARCHAR, max_length=100)
        schema.add_field(field_name=self.FIELD_MEMORY_TYPE, datatype=DataType.VARCHAR, max_length=50)
        schema.add_field(field_name=self.FIELD_SCOPE, datatype=DataType.VARCHAR, max_length=20)
        schema.add_field(field_name=self.FIELD_DOMAIN, datatype=DataType.VARCHAR, max_length=50)
        schema.add_field(field_name=self.FIELD_CONTENT, datatype=DataType.VARCHAR, max_length=2000)
        schema.add_field(field_name=self.FIELD_SUMMARY, datatype=DataType.VARCHAR, max_length=500)
        schema.add_field(field_name=self.FIELD_IMPORTANCE, datatype=DataType.DOUBLE)
        schema.add_field(field_name=self.FIELD_CONFIDENCE, datatype=DataType.DOUBLE)
        schema.add_field(field_name=self.FIELD_CREATED_AT, datatype=DataType.VARCHAR, max_length=50)
        schema.add_field(field_name=self.FIELD_UPDATED_AT, datatype=DataType.VARCHAR, max_length=50)
        schema.add_field(field_name=self.FIELD_METADATA, datatype=DataType.VARCHAR, max_length=1000)
        schema.add_field(field_name=self.FIELD_EXPIRES_AT, datatype=DataType.VARCHAR, max_length=50)

        # 添加向量字段
        embedding_dim = self._embedding_provider.get_dimension()
        schema.add_field(
            field_name=self.FIELD_EMBEDDING,
            datatype=DataType.FLOAT_VECTOR,
            dim=embedding_dim
        )

        # 创建集合
        settings = get_settings()
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name=self.FIELD_EMBEDDING,
            index_type=settings.milvus_index_type,
            metric_type=settings.milvus_metric_type
        )

        self._client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params
        )

        logger.info(f"[MilvusStore] 集合创建成功，向量维度: {embedding_dim}")

    async def close(self) -> None:
        """关闭 Milvus 连接"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("[MilvusStore] Milvus 连接已关闭")

    async def is_available(self) -> bool:
        """检查 Milvus 是否可用"""
        if not self.enabled or self._client is None:
            return False
        try:
            return self._client.has_collection(self.collection_name)
        except Exception:
            return False

    # ============ 辅助方法 ============

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成文本向量"""
        try:
            return await self._embedding_provider.embed(text)
        except Exception as e:
            logger.warning(f"[MilvusStore] 生成 embedding 失败: {e}")
            return None

    def _item_to_dict(self, item: MemoryItem) -> Dict[str, Any]:
        """将 MemoryItem 转换为 Milvus 插入格式"""
        return {
            self.FIELD_ID: item.id,
            self.FIELD_USER_ID: item.user_id,
            self.FIELD_MEMORY_TYPE: item.memory_type.value,
            self.FIELD_SCOPE: item.scope.value,
            self.FIELD_DOMAIN: item.domain or "",
            self.FIELD_CONTENT: item.content[:2000],  # 限制长度
            self.FIELD_SUMMARY: item.summary or "",
            self.FIELD_IMPORTANCE: float(item.importance),
            self.FIELD_CONFIDENCE: float(item.confidence),
            self.FIELD_CREATED_AT: item.created_at.isoformat(),
            self.FIELD_UPDATED_AT: item.updated_at.isoformat(),
            self.FIELD_METADATA: json.dumps(item.metadata, ensure_ascii=False),
            self.FIELD_EMBEDDING: item.embedding or [],
            self.FIELD_EXPIRES_AT: item.expires_at.isoformat() if item.expires_at else ""
        }

    def _dict_to_item(self, data: Dict[str, Any]) -> MemoryItem:
        """将 Milvus 查询结果转换为 MemoryItem"""
        return MemoryItem(
            id=data.get(self.FIELD_ID, ""),
            user_id=data.get(self.FIELD_USER_ID, ""),
            memory_type=MemoryType(data.get(self.FIELD_MEMORY_TYPE, "user_preference")),
            scope=MemoryScope(data.get(self.FIELD_SCOPE, "domain")),
            domain=data.get(self.FIELD_DOMAIN) or None,
            content=data.get(self.FIELD_CONTENT, ""),
            summary=data.get(self.FIELD_SUMMARY),
            importance=data.get(self.FIELD_IMPORTANCE, 0.5),
            confidence=data.get(self.FIELD_CONFIDENCE, 0.5),
            created_at=datetime.fromisoformat(data.get(self.FIELD_CREATED_AT, datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get(self.FIELD_UPDATED_AT, datetime.now().isoformat())),
            metadata=json.loads(data.get(self.FIELD_METADATA, "{}")),
            embedding=data.get(self.FIELD_EMBEDDING),
            expires_at=datetime.fromisoformat(data[self.FIELD_EXPIRES_AT]) if data.get(self.FIELD_EXPIRES_AT) else None
        )

    # ============ CRUD 操作 ============

    async def upsert(self, item: MemoryItem) -> bool:
        """插入或更新记忆项"""
        try:
            # 生成 embedding
            if not item.embedding:
                item.embedding = await self._generate_embedding(item.content)

            if self.enabled and self._client:
                data = self._item_to_dict(item)
                self._client.upsert(
                    collection_name=self.collection_name,
                    data=[data]
                )
            else:
                # Mock 存储
                self._mock_storage[item.id] = item

            logger.debug(f"[MilvusStore] 存储记忆: {item.id}")
            return True

        except Exception as e:
            logger.error(f"[MilvusStore] upsert 失败: {e}")
            # 降级到 Mock
            self._mock_storage[item.id] = item
            return False

    async def upsert_batch(self, items: List[MemoryItem]) -> int:
        """批量插入或更新"""
        success_count = 0

        for item in items:
            if await self.upsert(item):
                success_count += 1

        return success_count

    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取单个记忆项"""
        if self.enabled and self._client:
            try:
                results = self._client.query(
                    collection_name=self.collection_name,
                    filter=f'{self.FIELD_ID} == "{memory_id}"',
                    limit=1
                )
                if results:
                    return self._dict_to_item(results[0])
            except Exception as e:
                logger.warning(f"[MilvusStore] get 失败: {e}")
        else:
            # Mock 存储
            return self._mock_storage.get(memory_id)

        return None

    async def delete(self, memory_id: str) -> bool:
        """删除记忆项"""
        try:
            if self.enabled and self._client:
                self._client.delete(
                    collection_name=self.collection_name,
                    filter=f'{self.FIELD_ID} == "{memory_id}"'
                )
            else:
                self._mock_storage.pop(memory_id, None)

            return True
        except Exception as e:
            logger.warning(f"[MilvusStore] delete 失败: {e}")
            return False

    async def delete_by_filter(
        self,
        user_id: str,
        filters: Dict[str, Any]
    ) -> int:
        """按条件批量删除"""
        try:
            filter_parts = [f'{self.FIELD_USER_ID} == "{user_id}"']

            for key, value in filters.items():
                if key == "memory_type":
                    filter_parts.append(f'{self.FIELD_MEMORY_TYPE} == "{value}"')
                elif key == "domain":
                    filter_parts.append(f'{self.FIELD_DOMAIN} == "{value}"')
                elif key == "scope":
                    filter_parts.append(f'{self.FIELD_SCOPE} == "{value}"')

            filter_str = " && ".join(filter_parts)

            if self.enabled and self._client:
                self._client.delete(
                    collection_name=self.collection_name,
                    filter=filter_str
                )

            # Mock 删除
            to_delete = []
            for mid, item in self._mock_storage.items():
                if item.user_id == user_id:
                    match = True
                    for key, value in filters.items():
                        if getattr(item, key, None) != value:
                            match = False
                            break
                    if match:
                        to_delete.append(mid)

            for mid in to_delete:
                del self._mock_storage[mid]

            return len(to_delete)

        except Exception as e:
            logger.warning(f"[MilvusStore] delete_by_filter 失败: {e}")
            return 0

    # ============ 检索操作 ============

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[MemoryItem]:
        """向量搜索记忆"""
        try:
            # 生成查询向量
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                return []

            # 构建过滤条件
            filter_parts = [f'{self.FIELD_USER_ID} == "{user_id}"']

            # 过滤已过期的记忆
            now = datetime.now().isoformat()
            filter_parts.append(f'({self.FIELD_EXPIRES_AT} == "" || {self.FIELD_EXPIRES_AT} > "{now}")')

            if filters:
                if "memory_type" in filters:
                    filter_parts.append(f'{self.FIELD_MEMORY_TYPE} == "{filters["memory_type"]}"')
                if "domain" in filters:
                    filter_parts.append(f'{self.FIELD_DOMAIN} == "{filters["domain"]}"')
                if "scope" in filters:
                    filter_parts.append(f'{self.FIELD_SCOPE} == "{filters["scope"]}"')

            filter_str = " && ".join(filter_parts)

            results = []
            if self.enabled and self._client:
                results = self._client.search(
                    collection_name=self.collection_name,
                    data=[query_embedding],
                    limit=limit,
                    filter=filter_str,
                    output_fields=[
                        self.FIELD_ID, self.FIELD_USER_ID, self.FIELD_MEMORY_TYPE,
                        self.FIELD_SCOPE, self.FIELD_DOMAIN, self.FIELD_CONTENT,
                        self.FIELD_SUMMARY, self.FIELD_IMPORTANCE, self.FIELD_CONFIDENCE,
                        self.FIELD_CREATED_AT, self.FIELD_UPDATED_AT, self.FIELD_METADATA,
                        self.FIELD_EMBEDDING, self.FIELD_EXPIRES_AT
                    ]
                )

                # 处理结果
                items = []
                for result in results[0]:  # 第一个查询的结果
                    if result['distance'] >= min_score:
                        item_data = result['entity']
                        item = self._dict_to_item(item_data)
                        item.relevance = result['distance']
                        items.append(item)
                return items
            else:
                # Mock 向量搜索（简单文本匹配）
                items = []
                for item in list(self._mock_storage.values())[:limit]:
                    if item.user_id != user_id:
                        continue

                    # 检查过滤条件
                    if filters:
                        if "memory_type" in filters and item.memory_type != filters["memory_type"]:
                            continue
                        if "domain" in filters and item.domain != filters["domain"]:
                            continue
                        if "scope" in filters and item.scope != filters["scope"]:
                            continue

                    # 简单相关性计算（关键词匹配）
                    score = self._simple_similarity(query, item.content)
                    if score >= min_score:
                        item.relevance = score
                        items.append(item)

                items.sort(key=lambda x: x.relevance, reverse=True)
                return items

        except Exception as e:
            logger.error(f"[MilvusStore] search 失败: {e}")
            return []

    def _simple_similarity(self, query: str, content: str) -> float:
        """简单的文本相似度计算"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        intersection = query_words & content_words
        return len(intersection) / len(query_words)

    async def search_by_metadata(
        self,
        user_id: str,
        filters: Dict[str, Any],
        limit: int = 10
    ) -> List[MemoryItem]:
        """按元数据搜索"""
        # 复用 search 方法，使用空查询
        return await self.search(
            user_id=user_id,
            query=" ".join(str(v) for v in filters.values()),
            limit=limit,
            filters=filters,
            min_score=0.0
        )

    async def get_recent_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryItem]:
        """获取最近的记忆"""
        filters = {}
        if memory_type:
            filters["memory_type"] = memory_type.value if isinstance(memory_type, str) else memory_type.value
        if domain:
            filters["domain"] = domain

        # 使用 search 并按时间排序
        items = await self.search(
            user_id=user_id,
            query="",
            limit=limit * 2,  # 获取更多然后排序
            filters=filters,
            min_score=0.0
        )

        # 按创建时间排序
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items[:limit]

    async def get_user_preferences(
        self,
        user_id: str,
        domain: Optional[str] = None
    ) -> List[MemoryItem]:
        """获取用户偏好记忆"""
        filters = {"memory_type": MemoryType.USER_PREFERENCE.value}
        if domain:
            filters["domain"] = domain

        return await self.search(
            user_id=user_id,
            query="preference",
            limit=20,
            filters=filters,
            min_score=0.0
        )

    async def get_episode_memories(
        self,
        user_id: str,
        domain: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 10
    ) -> List[MemoryItem]:
        """获取任务经历记忆"""
        filters = {}

        if success is True:
            filters["memory_type"] = MemoryType.TASK_SUCCESS.value
        elif success is False:
            filters["memory_type"] = MemoryType.TASK_FAILURE.value
        else:
            filters["memory_type"] = MemoryType.TASK_EPISODE.value

        if domain:
            filters["domain"] = domain

        return await self.search(
            user_id=user_id,
            query="task episode",
            limit=limit,
            filters=filters,
            min_score=0.0
        )

    # ============ 统计与维护 ============

    async def count_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> int:
        """统计记忆数量"""
        count = 0

        for item in self._mock_storage.values():
            if item.user_id == user_id:
                if memory_type is None or item.memory_type == memory_type:
                    count += 1

        return count

    async def update_access_time(self, memory_id: str) -> bool:
        """更新访问时间"""
        try:
            if self.enabled and self._client:
                now = datetime.now().isoformat()
                self._client.update(
                    collection_name=self.collection_name,
                    data={self.FIELD_ID: memory_id, self.FIELD_UPDATED_AT: now}
                )

            return True
        except Exception as e:
            logger.warning(f"[MilvusStore] update_access_time 失败: {e}")
            return False

    async def cleanup_expired(self) -> int:
        """清理过期记忆"""
        count = 0
        now = datetime.now()

        to_delete = []
        for mid, item in self._mock_storage.items():
            if item.expires_at and item.expires_at < now:
                to_delete.append(mid)

        for mid in to_delete:
            del self._mock_storage[mid]
            count += 1

        return count


# ============ 全局单例 ============

_milvus_store: Optional[MilvusLongTermStore] = None


async def get_milvus_store() -> MilvusLongTermStore:
    """获取 Milvus 存储单例"""
    global _milvus_store
    if _milvus_store is None:
        _milvus_store = MilvusLongTermStore()
        await _milvus_store.initialize()
    return _milvus_store
