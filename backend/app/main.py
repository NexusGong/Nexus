"""
FastAPI主应用文件
聊天内容智能分析平台的后端服务入口
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

from app.config import settings
from app.core.logging import setup_logging
from app.core.errors import register_exception_handlers
from app.database import create_tables
from app.api import chat, cards, auth, characters, character_chat, card_mode
from app.services.screenshot_service import startup_screenshot_service, shutdown_screenshot_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    在应用启动和关闭时执行必要的操作
    """
    # 启动时执行
    logger.info("🚀 启动聊天内容智能分析平台后端服务")
    
    # 创建数据库表
    try:
        create_tables()
        logger.info("✅ 数据库表创建成功")
        
        # 初始化AI角色
        try:
            from app.utils.init_characters import init_characters
            init_characters()
            logger.info("✅ AI角色初始化成功")
        except Exception as e:
            logger.warning(f"⚠️  AI角色初始化失败: {e}")
    except Exception as e:
        logger.error(f"❌ 数据库表创建失败: {e}")
    
    # 验证API配置
    # 启动Playwright浏览器以便复用
    try:
        await startup_screenshot_service()
    except Exception as e:
        logger.warning(f"⚠️  Playwright 启动失败（不影响主服务）：{e}")
    try:
        if not settings.deepseek_api_key or not settings.doubao_api_key:
            logger.warning("⚠️  API密钥未配置，部分功能可能不可用")
        else:
            logger.info("✅ API配置验证成功")
    except Exception as e:
        logger.warning(f"⚠️  API配置验证失败: {e}")
    
    # 验证OCR服务配置
    try:
        from app.services.ocr_service import volc_ocr_service, doubao_ocr_service
        if volc_ocr_service:
            logger.info("✅ 火山引擎OCR服务已就绪")
        if doubao_ocr_service:
            logger.info("✅ 豆包OCR服务已就绪")
    except Exception as e:
        logger.warning(f"⚠️  OCR服务检查失败: {e}")
    
    yield
    
    # 关闭时执行
    try:
        await shutdown_screenshot_service()
    except Exception as e:
        logger.warning(f"⚠️  Playwright 关闭失败：{e}")
    logger.info("🛑 聊天内容智能分析平台后端服务已关闭")


# 初始化日志（保持与原有级别语义一致）
setup_logging(settings.debug)

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于AI的聊天内容多维度分析平台，支持图片OCR识别和智能回复建议生成",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 配置可信主机中间件
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )


"""
全局异常处理器注册（行为保持不变）
"""
register_exception_handlers(app, debug=settings.debug)


# 健康检查端点
@app.get("/health")
async def health_check():
    """
    健康检查端点
    用于监控服务状态
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug
    }


# 根路径端点
@app.get("/")
async def root():
    """
    根路径端点
    返回API基本信息
    """
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else "文档仅在调试模式下可用",
        "api_prefix": "/api"
    }


# 注册API路由
app.include_router(chat.router)
app.include_router(cards.router)
app.include_router(auth.router)
app.include_router(characters.router)
app.include_router(character_chat.router)
app.include_router(card_mode.router)


# 启动服务器
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
