"""配置管理模块"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    """应用配置"""

    # 应用基本配置
    app_name: str = "Universal Life Agent"
    app_version: str = "1.0.0"
    debug: bool = False

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS配置
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # LLM配置
    llm_model_id: str = "gpt-4"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_temperature: float = 0.7

    # 高德地图 API
    amap_api_key: str = ""

    # Tavily 搜索 API
    tavily_api_key: str = ""

    # GitHub Token
    github_token: str = ""

    # 日志配置
    log_level: str = "INFO"

    # 重试配置
    max_retry: int = 3
    router_confidence_threshold: float = 0.7

    # ============ 记忆系统配置 ============

    # 记忆系统开关
    memory_enabled: bool = True
    memory_fallback_on_error: bool = True  # 出错时是否降级为无记忆模式

    # Embedding 配置
    embedding_provider: str = "openai"  # openai/sentence-transformer
    embedding_model: str = "embedding-3"
    embedding_dimension: int = 2048

    # Redis 配置（短期记忆）
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False  # 默认关闭，需要时开启
    redis_ttl_session: int = 3600  # 会话 TTL (秒)
    redis_ttl_context: int = 1800  # 上下文 TTL (秒)
    redis_ttl_feedback: int = 86400  # 反馈 TTL (秒)

    # Milvus 配置（长期记忆）
    milvus_enabled: bool = False  # 默认关闭，需要时开启
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection_name: str = "universal_agent_memories"
    milvus_index_type: str = "HNSW"  # HNSW/IVF_FLAT/IVF_SQ8
    milvus_metric_type: str = "COSINE"

    # 记忆检索配置
    memory_retrieve_threshold: float = 0.3  # 触发检索的最低条件
    memory_max_results: int = 10
    memory_min_score: float = 0.6  # 最低相关性分数
    memory_compression_enabled: bool = True
    memory_max_items_in_bundle: int = 5

    # 记忆存储配置（judge 决策阈值）
    memory_store_importance_threshold: float = 0.7  # 重要性阈值
    memory_store_confidence_threshold: float = 0.6  # 置信度阈值
    memory_auto_upgrade_to_long_term: bool = False  # 是否自动升级到长期记忆

    # 记忆类型配置（哪些类型需要检索）
    memory_retrieve_on_preference: bool = True  # 偏好类请求
    memory_retrieve_on_low_confidence: bool = True  # 低置信度时
    memory_retrieve_on_multi_step: bool = True  # 多步任务
    memory_retrieve_on_keywords: List[str] = [
        "上次", "之前", "延续", "记得", "习惯", "通常",
        "last time", "before", "remember", "usually"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def get_cors_origins_list(self) -> List[str]:
        """获取CORS origins列表"""
        return [origin.strip() for origin in self.cors_origins.split(',')]

    def is_tool_available(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        tool_keys = {
            "amap": self.amap_api_key,
            "tavily": self.tavily_api_key,
            "github": self.github_token,
        }
        return bool(tool_keys.get(tool_name))


# 创建全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def validate_config():
    """验证配置是否完整"""
    errors = []
    warnings = []

    if not settings.llm_api_key:
        errors.append("LLM_API_KEY 未配置")

    if not settings.amap_api_key:
        warnings.append("AMAP_API_KEY 未配置，天气/旅行功能可能无法使用")

    if not settings.tavily_api_key:
        warnings.append("TAVILY_API_KEY 未配置，搜索功能将不可用")

    if not settings.github_token:
        warnings.append("GITHUB_TOKEN 未配置，GitHub 搜索可能受速率限制")

    # 记忆系统配置检查
    if settings.memory_enabled:
        if settings.redis_enabled:
            try:
                import redis
                # 尝试连接测试
                # 实际连接在 memory 模块初始化时进行
            except ImportError:
                warnings.append("Redis 已启用但 redis-py 未安装，短期记忆将不可用")

        if settings.milvus_enabled:
            try:
                import pymilvus
            except ImportError:
                warnings.append("Milvus 已启用但 pymilvus 未安装，长期记忆将不可用")

        if not settings.redis_enabled and not settings.milvus_enabled:
            warnings.append("记忆系统已启用但 Redis 和 Milvus 都未启用，记忆功能将使用内存存储（重启丢失）")

    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")

    return True


def print_config():
    """打印当前配置(隐藏敏感信息)"""
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_name}")
    print(f"框架: LangChain + LangGraph")
    print(f"服务器: {settings.host}:{settings.port}")
    print(f"LLM API Key: {'已配置' if settings.llm_api_key else '未配置'}")
    print(f"LLM Model: {settings.llm_model_id}")
    print(f"高德 API: {'已配置' if settings.amap_api_key else '未配置'}")
    print(f"Tavily API: {'已配置' if settings.tavily_api_key else '未配置'}")
    print(f"GitHub Token: {'已配置' if settings.github_token else '未配置'}")
    print(f"日志级别: {settings.log_level}")

    # 记忆系统配置
    print(f"\n记忆系统:")
    print(f"  记忆系统: {'启用' if settings.memory_enabled else '禁用'}")
    print(f"  Embedding: {settings.embedding_provider}")
    print(f"  Redis: {'启用' if settings.redis_enabled else '禁用'}")
    print(f"  Milvus: {'启用' if settings.milvus_enabled else '禁用'}")
