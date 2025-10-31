"""
消息模型
定义消息相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Message(Base):
    """消息表模型"""
    
    __tablename__ = "messages"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="消息ID")
    
    # 外键关联
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, comment="会话ID")
    
    # 消息基本信息
    role = Column(String(20), nullable=False, comment="消息角色: user/assistant/system")
    content = Column(Text, nullable=False, comment="消息内容")
    
    # 消息类型和来源
    message_type = Column(String(20), default="text", comment="消息类型: text/image/analysis")
    source = Column(String(50), nullable=True, comment="消息来源: manual/ocr/ai_generated")
    
    # 图片相关（如果是图片消息）
    image_url = Column(String(500), nullable=True, comment="图片URL")
    image_ocr_result = Column(Text, nullable=True, comment="图片OCR识别结果")
    
    # AI分析相关
    analysis_result = Column(JSON, nullable=True, comment="AI分析结果")
    analysis_metadata = Column(JSON, nullable=True, comment="分析元数据")
    
    # 消息状态
    is_processed = Column(Boolean, default=False, comment="是否已处理")
    is_archived = Column(Boolean, default=False, comment="是否已归档")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', type='{self.message_type}')>"

