"""
分析卡片模型
定义分析结果卡片相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AnalysisCard(Base):
    """分析卡片表模型"""
    
    __tablename__ = "analysis_cards"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="卡片ID")
    
    # 外键关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="用户ID")
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, comment="会话ID（普通对话，角色对话和卡片模式为NULL）")
    session_token = Column(String(255), nullable=True, index=True, comment="会话Token（非登录用户使用）")
    
    # 卡片基本信息
    title = Column(String(200), nullable=False, comment="卡片标题")
    description = Column(Text, nullable=True, comment="卡片描述")
    
    # 分析结果数据
    original_content = Column(Text, nullable=False, comment="原始聊天内容")
    analysis_data = Column(JSON, nullable=False, comment="分析结果数据")
    response_suggestions = Column(JSON, nullable=True, comment="回复建议")
    
    # 卡片配置
    context_mode = Column(String(50), nullable=True, comment="分析时的情景模式")
    analysis_focus = Column(JSON, nullable=True, comment="分析重点")
    card_template = Column(String(50), default="default", comment="卡片模板")
    
    # 卡片状态
    is_favorite = Column(Boolean, default=False, comment="是否收藏")
    is_public = Column(Boolean, default=False, comment="是否公开")
    tags = Column(JSON, nullable=True, comment="标签列表")
    
    # 导出相关
    export_count = Column(Integer, default=0, comment="导出次数")
    last_exported_at = Column(DateTime(timezone=True), nullable=True, comment="最后导出时间")
    
    # 时间戳
    conversation_time = Column(DateTime(timezone=True), nullable=True, comment="对话时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="保存时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    user = relationship("User", back_populates="analysis_cards")
    conversation = relationship("Conversation", back_populates="analysis_cards")
    
    def __repr__(self):
        return f"<AnalysisCard(id={self.id}, title='{self.title}')>"

