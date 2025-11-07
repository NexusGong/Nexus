"""
认证相关Schema
定义认证API的请求和响应模型
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    contact: str = Field(..., description="联系方式（邮箱或手机号）")
    code_type: str = Field(..., description="验证码类型: register/login")
    
    @field_validator("code_type")
    @classmethod
    def validate_code_type(cls, v: str) -> str:
        if v not in ["register", "login"]:
            raise ValueError("code_type必须是register或login")
        return v


class SendCodeResponse(BaseModel):
    """发送验证码响应"""
    success: bool
    message: str
    resend_interval: int = Field(default=60, description="重发间隔(秒)")


class RegisterRequest(BaseModel):
    """注册请求"""
    contact: str = Field(..., description="联系方式（邮箱或手机号）")
    code: str = Field(..., min_length=4, max_length=10, description="验证码")
    username: str = Field(..., min_length=2, max_length=50, description="用户名")


class LoginRequest(BaseModel):
    """登录请求"""
    contact: str = Field(..., description="联系方式（邮箱或手机号）")
    code: str = Field(..., min_length=4, max_length=10, description="验证码")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """更新用户资料请求"""
    username: Optional[str] = Field(None, min_length=2, max_length=50, description="用户名")
    avatar_url: Optional[str] = Field(None, max_length=100000, description="头像URL（base64编码）")


class AuthResponse(BaseModel):
    """认证响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UsageStatsResponse(BaseModel):
    """使用统计响应"""
    ocr_fast: dict
    ocr_quality: dict
    conversation: dict
    chat_analysis: dict

