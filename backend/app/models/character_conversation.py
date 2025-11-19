"""
角色对话模型
定义角色对话相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class CharacterConversation(Base):
    """角色对话表模型"""
    
    __tablename__ = "character_conversations"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="对话ID")
    
    # 外键关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="用户ID")
    character_id = Column(Integer, ForeignKey("ai_characters.id"), nullable=False, comment="角色ID")
    session_token = Column(String(255), nullable=True, index=True, comment="会话Token（非登录用户使用）")
    
    # 对话信息
    title = Column(String(200), nullable=True, comment="对话标题")
    context_summary = Column(Text, nullable=True, comment="对话上下文摘要")
    message_count = Column(Integer, default=0, comment="消息数量")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    character = relationship("AICharacter", back_populates="conversations")
    messages = relationship("CharacterMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CharacterConversation(id={self.id}, character_id={self.character_id})>"

