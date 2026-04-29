"""Universal Life Agent - 启动脚本"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


async def main():
    """启动 Universal Life Agent 服务"""
    import uvicorn
    from app.core.config import settings, print_config

    print("\n" + "=" * 60)
    print("🚀 Universal Life Agent 启动中...")
    print("=" * 60)

    # 打印配置信息
    print_config()

    print("\n" + "=" * 60)
    print("📚 API 文档: http://localhost:8000/docs")
    print("📖 ReDoc 文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")

    # 启动服务
    config = uvicorn.Config(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
