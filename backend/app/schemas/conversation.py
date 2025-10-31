"""
对话会话相关的Pydantic模式
定义对话会话的请求和响应数据结构
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field
from app.schemas.base import BaseSchema, TimestampMixin, IDMixin


class ConversationBase(BaseSchema):
    """对话会话基础模式"""
    
    title: str = Field(..., min_length=1, max_length=200, description="会话标题")
    description: Optional[str] = Field(None, description="会话描述")
    context_mode: str = Field(default="general", description="情景模式")
    analysis_focus: Optional[Dict[str, Any]] = Field(None, description="分析重点配置")


class ConversationCreate(ConversationBase):
    """创建对话会话请求模式"""
    pass


class ConversationUpdate(BaseSchema):
    """更新对话会话请求模式"""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="会话标题")
    description: Optional[str] = Field(None, description="会话描述")
    context_mode: Optional[str] = Field(None, description="情景模式")
    analysis_focus: Optional[Dict[str, Any]] = Field(None, description="分析重点配置")
    is_active: Optional[str] = Field(None, description="会话状态")


class ConversationResponse(ConversationBase, IDMixin, TimestampMixin):
    """对话会话响应模式"""
    
    user_id: Optional[int] = Field(None, description="用户ID")
    is_active: str = Field(..., description="会话状态")
    message_count: int = Field(..., description="消息数量")
    analysis_count: int = Field(..., description="分析次数")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")


class ConversationListResponse(BaseSchema):
    """对话会话列表响应模式"""
    
    conversations: List[ConversationResponse]
    total: int
    page: int
    size: int

