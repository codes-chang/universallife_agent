"""日志配置模块"""

import sys
import logging
from pathlib import Path
from loguru import logger as loguru_logger
from datetime import datetime

from .config import settings


# ============ 日志配置 ============

def setup_logging():
    """配置日志系统"""
    # 移除默认的 handler
    loguru_logger.remove()

    # 添加控制台输出
    loguru_logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )

    # 添加文件输出（可选）
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    loguru_logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention="7 days",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    # 添加错误日志
    loguru_logger.add(
        log_dir / "error.log",
        rotation="10 MB",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    return loguru_logger


# 创建 logger 实例
logger = setup_logging()


# ============ 日志上下文管理器 ============

class LogContext:
    """日志上下文管理器"""

    def __init__(self, domain: str, session_id: str = None):
        self.domain = domain
        self.session_id = session_id

    def __enter__(self):
        loguru_logger.bind(domain=self.domain, session=self.session_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            loguru_logger.error(f"Error in {self.domain}: {exc_val}")

    def info(self, message: str, **kwargs):
        loguru_logger.info(f"[{self.domain}] {message}", **kwargs)

    def debug(self, message: str, **kwargs):
        loguru_logger.debug(f"[{self.domain}] {message}", **kwargs)

    def warning(self, message: str, **kwargs):
        loguru_logger.warning(f"[{self.domain}] {message}", **kwargs)

    def error(self, message: str, **kwargs):
        loguru_logger.error(f"[{self.domain}] {message}", **kwargs)


# ============ 执行追踪 ============

class ExecutionTracer:
    """执行追踪器"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id
        self.trace = []

    def add_step(
        self,
        step: str,
        domain: str = None,
        status: str = "running",
        details: dict = None
    ):
        """添加执行步骤"""
        self.trace.append({
            "step": step,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "details": details or {}
        })

    def get_trace(self) -> list:
        """获取执行轨迹"""
        return self.trace

    def clear(self):
        """清空轨迹"""
        self.trace = []
