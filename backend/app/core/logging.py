"""
日志配置模块
提供统一的日志初始化入口，便于后续扩展（如请求ID、JSON日志等）。
"""

from loguru import logger
import sys


def setup_logging(debug: bool = True) -> None:
    """根据运行模式配置日志级别和输出。

    Args:
        debug: 是否为调试模式。
    """
    # 清空已有的 sink，避免重复初始化时日志重复输出
    logger.remove()

    level = "DEBUG" if debug else "INFO"
    logger.add(sys.stderr, level=level, backtrace=debug, diagnose=debug)

    # 预留扩展点：可在此添加 JSON sink、文件轮转、请求ID注入等









