"""
数据库连接和会话管理模块
负责数据库引擎创建、会话管理和连接池配置
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.sql_echo,  # 控制是否打印SQL语句
    pool_pre_ping=True,   # 连接前检查连接是否有效
    pool_recycle=3600,    # 连接回收时间(秒)
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    用于FastAPI的依赖注入系统
    
    Yields:
        Session: SQLAlchemy数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    创建所有数据库表
    在应用启动时调用
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    删除所有数据库表
    仅在开发或测试时使用
    """
    Base.metadata.drop_all(bind=engine)

