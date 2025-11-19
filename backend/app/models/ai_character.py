"""
AI角色模型
定义AI角色相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AICharacter(Base):
    """AI角色表模型"""
    
    __tablename__ = "ai_characters"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="角色ID")
    
    # 角色基本信息
    name = Column(String(100), nullable=False, comment="角色名称")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    description = Column(Text, nullable=True, comment="角色描述")
    personality = Column(Text, nullable=False, comment="性格特点")
    speaking_style = Column(Text, nullable=False, comment="说话风格")
    background = Column(Text, nullable=True, comment="背景故事")
    system_prompt = Column(Text, nullable=False, comment="系统提示词")
    
    # 角色分类
    category = Column(String(50), nullable=False, default="original", comment="分类：original/classic/anime")
    rarity = Column(String(20), default="common", comment="稀有度：common/rare/epic/legendary")
    
    # 角色状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    conversations = relationship("CharacterConversation", back_populates="character", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AICharacter(id={self.id}, name='{self.name}')>"

