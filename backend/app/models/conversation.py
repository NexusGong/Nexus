"""
对话会话模型
定义对话会话相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Conversation(Base):
    """对话会话表模型"""
    
    __tablename__ = "conversations"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="会话ID")
    
    # 外键关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="用户ID")
    
    # 会话基本信息
    title = Column(String(200), nullable=False, comment="会话标题")
    description = Column(Text, nullable=True, comment="会话描述")
    
    # 会话配置
    context_mode = Column(String(50), default="general", comment="情景模式: general/work/intimate/social")
    analysis_focus = Column(JSON, nullable=True, comment="分析重点配置")
    
    # 会话状态
    is_active = Column(String(20), default="active", comment="会话状态: active/archived/deleted")
    
    # 统计信息
    message_count = Column(Integer, default=0, comment="消息数量")
    analysis_count = Column(Integer, default=0, comment="分析次数")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_message_at = Column(DateTime(timezone=True), nullable=True, comment="最后消息时间")
    
    # 关联关系
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    analysis_cards = relationship("AnalysisCard", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"

