"""
使用记录模型
定义用户使用记录相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class UsageRecord(Base):
    """使用记录表模型"""
    
    __tablename__ = "usage_records"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="记录ID")
    
    # 用户关联（可选，非登录用户为None）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="用户ID")
    
    # 非登录用户标识
    session_token = Column(String(64), nullable=True, index=True, comment="会话token（非登录用户使用）")
    ip_address = Column(String(45), nullable=True, index=True, comment="IP地址")
    
    # 使用类型
    usage_type = Column(String(50), nullable=False, index=True, comment="使用类型: ocr_fast/ocr_quality/chat_analysis")
    
    # 关联信息
    conversation_id = Column(Integer, nullable=True, comment="会话ID（用于聊天分析）")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="创建时间")
    
    # 关联关系
    user = relationship("User", backref="usage_records")
    
    def __repr__(self):
        return f"<UsageRecord(id={self.id}, type='{self.usage_type}', user_id={self.user_id})>"

