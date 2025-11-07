"""
验证码模型
定义验证码相关的数据库表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class VerificationCode(Base):
    """验证码表模型"""
    
    __tablename__ = "verification_codes"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="验证码ID")
    
    # 联系方式（邮箱或手机号）
    contact = Column(String(100), nullable=False, index=True, comment="联系方式（邮箱或手机号）")
    
    # 验证码信息
    code = Column(String(10), nullable=False, comment="验证码")
    code_type = Column(String(20), nullable=False, comment="验证码类型: register/login")
    
    # 验证码状态
    is_used = Column(Boolean, default=False, comment="是否已使用")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    def __repr__(self):
        return f"<VerificationCode(id={self.id}, contact='{self.contact}', type='{self.code_type}')>"

