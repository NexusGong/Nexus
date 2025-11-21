"""
用户角色解锁模型
记录用户解锁的角色
"""

from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class UserCharacter(Base):
    """用户角色解锁表"""
    
    __tablename__ = "user_characters"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="ID")
    
    # 外键
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    character_id = Column(Integer, ForeignKey("ai_characters.id", ondelete="CASCADE"), nullable=False, comment="角色ID")
    
    # 拥有状态
    is_owned = Column(Boolean, default=False, comment="是否已拥有")
    
    # 时间戳
    owned_at = Column(DateTime(timezone=True), nullable=True, comment="获得时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 唯一约束：一个用户只能有一条角色记录
    __table_args__ = (
        UniqueConstraint('user_id', 'character_id', name='uq_user_character'),
    )
    
    # 关联关系
    user = relationship("User", back_populates="user_characters")
    character = relationship("AICharacter", back_populates="user_characters")
    
    def __repr__(self):
        return f"<UserCharacter(user_id={self.user_id}, character_id={self.character_id}, is_owned={self.is_owned})>"

