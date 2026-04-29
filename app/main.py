"""Universal Life Agent - FastAPI 主应用"""

import sys
import io
import logging
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 确保 .env 文件被加载（从项目根目录）
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings, print_config, validate_config
from .core.logging import logger
from .api.routes import router as chat_router

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 LangGraph 的全场景通用智能助手 API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("\n" + "=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 60)

    # 打印配置信息
    print_config()

    # 验证配置
    try:
        validate_config()
        print("\n✅ 配置验证通过")
    except ValueError as e:
        print(f"\n❌ 配置验证失败:\n{e}")
        print("\n请检查 .env 文件并确保所有必要的配置项都已设置")
        raise

    # 初始化主图（预热）
    try:
        from .graph.main_graph import get_main_graph_runner
        runner = get_main_graph_runner()
        print("\n✅ 主图初始化完成")
    except Exception as e:
        print(f"\n⚠️  主图初始化警告: {e}")

    print("\n" + "=" * 60)
    print("📚 API 文档: http://localhost:8000/docs")
    print("📖 ReDoc 文档: http://localhost:8000/redoc")
    print("🔍 健康检查: http://localhost:8000/api/health")
    print("=" * 60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("\n" + "=" * 60)
    print("👋 应用正在关闭...")
    print("=" * 60 + "\n")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "mock_mode": settings.mock_mode
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
