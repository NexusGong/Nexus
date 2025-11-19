"""
角色消息模型
定义角色对话消息相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class CharacterMessage(Base):
    """角色消息表模型"""
    
    __tablename__ = "character_messages"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="消息ID")
    
    # 外键关联
    conversation_id = Column(Integer, ForeignKey("character_conversations.id"), nullable=False, comment="对话ID")
    
    # 消息内容
    role = Column(String(20), nullable=False, comment="角色：user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关联关系
    conversation = relationship("CharacterConversation", back_populates="messages")
    
    def __repr__(self):
        return f"<CharacterMessage(id={self.id}, role='{self.role}')>"

