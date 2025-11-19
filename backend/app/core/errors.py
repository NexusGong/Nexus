"""
统一异常处理注册模块
把异常处理集中在一个地方，便于维护，保持与历史行为一致。
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from loguru import logger


def register_exception_handlers(app: FastAPI, *, debug: bool) -> None:
    """注册全局异常处理器，保持与原有行为一致。"""

    @app.exception_handler(Exception)
    async def _global_exception_handler(request, exc):  # type: ignore[no-redef]
        logger.error(f"未处理的异常: {exc}")

        if debug:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"服务器内部错误: {str(exc)}",
                    "type": type(exc).__name__,
                },
            )
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})

















