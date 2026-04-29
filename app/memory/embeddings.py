"""Embedding 提供者实现

支持多种 embedding 模型，可替换设计。
"""

import asyncio
from typing import List, Optional
from abc import ABC, abstractmethod

from .interfaces import IEmbeddingProvider
from ..core.logging import logger
from ..core.config import get_settings


class MockEmbeddingProvider(IEmbeddingProvider):
    """Mock Embedding 提供者 - 用于测试和降级"""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        logger.warning("[Embedding] 使用 Mock Embedding 提供者")

    async def embed(self, text: str) -> List[float]:
        """生成伪随机向量（基于文本哈希）"""
        import hashlib
        # 使用哈希生成确定性的伪随机向量
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()

        # 转换为向量
        vector = []
        for i in range(self.dimension):
            # 使用哈希的不同部分生成值
            byte_idx = (i * 2) % len(hash_hex)
            val = int(hash_hex[byte_idx:byte_idx+2], 16) / 255.0
            vector.append(val)

        # 归一化
        norm = sum(x * x for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成"""
        return await asyncio.gather(*[self.embed(text) for text in texts])

    def get_dimension(self) -> int:
        return self.dimension


class OpenAIEmbeddingProvider(IEmbeddingProvider):
    """OpenAI Embedding 提供者"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self._dimension = 1536 if "3-small" in model else 3072

        try:
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(
                model=model,
                openai_api_key=api_key,
                base_url=base_url
            )
            logger.info(f"[Embedding] 使用 OpenAI Embedding: {model}")
        except ImportError:
            logger.error("[Embedding] langchain-openai 未安装")
            self.embeddings = None

    async def embed(self, text: str) -> List[float]:
        if self.embeddings is None:
            raise RuntimeError("OpenAI Embeddings 不可用")

        result = await self.embeddings.aembed_query(text)
        return result

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.embeddings is None:
            raise RuntimeError("OpenAI Embeddings 不可用")

        result = await self.embeddings.aembed_documents(texts)
        return result

    def get_dimension(self) -> int:
        return self._dimension


class SentenceTransformerProvider(IEmbeddingProvider):
    """Sentence Transformers Embedding 提供者（本地模型）"""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384  # MiniLM-L12 的默认维度

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"[Embedding] 使用 Sentence Transformer: {model_name}")
        except ImportError:
            logger.warning("[Embedding] sentence-transformers 未安装，将使用 Mock")
        except Exception as e:
            logger.warning(f"[Embedding] Sentence Transformer 加载失败: {e}")

    def _ensure_model(self):
        if self._model is None:
            raise RuntimeError("Sentence Transformer 模型不可用")

    async def embed(self, text: str) -> List[float]:
        self._ensure_model()
        # 在线程池中运行以避免阻塞
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._model.encode, text)
        return result.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._ensure_model()
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._model.encode, texts)
        return [r.tolist() for r in result]

    def get_dimension(self) -> int:
        return self._dimension


# ============ 工厂函数 ============

def get_embedding_provider(
    provider: Optional[str] = None,
    **kwargs
) -> IEmbeddingProvider:
    """获取 Embedding 提供者

    Args:
        provider: 提供者类型 (openai/sentence-transformer/mock)
        **kwargs: 额外参数

    Returns:
        Embedding 提供者实例
    """
    settings = get_settings()
    provider = provider or getattr(settings, 'embedding_provider', 'mock')

    if provider == "openai":
        return OpenAIEmbeddingProvider(
            model=kwargs.get('model', 'text-embedding-3-small'),
            api_key=kwargs.get('api_key', settings.llm_api_key),
            base_url=kwargs.get('base_url', settings.llm_base_url)
        )
    elif provider == "sentence-transformer":
        return SentenceTransformerProvider(
            model_name=kwargs.get('model_name', 'paraphrase-multilingual-MiniLM-L12-v2')
        )
    else:  # mock
        return MockEmbeddingProvider(dimension=kwargs.get('dimension', 1536))


# 全局单例
_embedding_provider: Optional[IEmbeddingProvider] = None


def get_global_embedding_provider() -> IEmbeddingProvider:
    """获取全局 Embedding 提供者单例"""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = get_embedding_provider()
    return _embedding_provider


async def get_embedding(text: str) -> List[float]:
    """获取文本的 embedding（便捷函数）"""
    provider = get_global_embedding_provider()
    return await provider.embed(text)


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """批量获取 embedding（便捷函数）"""
    provider = get_global_embedding_provider()
    return await provider.embed_batch(texts)
