"""
消息相关的Pydantic模式
定义消息的请求和响应数据结构
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import BaseSchema, TimestampMixin, IDMixin
from app.schemas.analysis import ResponseSuggestion


class MessageBase(BaseSchema):
    """消息基础模式"""
    
    role: str = Field(..., description="消息角色: user/assistant/system")
    content: str = Field(..., min_length=1, description="消息内容")
    message_type: str = Field(default="text", description="消息类型")
    source: Optional[str] = Field(None, description="消息来源")


class MessageCreate(MessageBase):
    """创建消息请求模式"""
    
    conversation_id: int = Field(..., description="会话ID")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_ocr_result: Optional[str] = Field(None, description="图片OCR识别结果")


class MessageUpdate(BaseSchema):
    """更新消息请求模式"""
    
    content: Optional[str] = Field(None, min_length=1, description="消息内容")
    analysis_result: Optional[Dict[str, Any]] = Field(None, description="AI分析结果")
    analysis_metadata: Optional[Dict[str, Any]] = Field(None, description="分析元数据")
    is_processed: Optional[bool] = Field(None, description="是否已处理")


class MessageResponse(MessageBase, IDMixin, TimestampMixin):
    """消息响应模式"""
    
    conversation_id: int = Field(..., description="会话ID")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_ocr_result: Optional[str] = Field(None, description="图片OCR识别结果")
    analysis_result: Optional[Dict[str, Any]] = Field(None, description="AI分析结果")
    analysis_metadata: Optional[Dict[str, Any]] = Field(None, description="分析元数据")
    is_processed: bool = Field(..., description="是否已处理")
    is_archived: bool = Field(..., description="是否已归档")


class ChatRequest(BaseSchema):
    """聊天请求模式"""
    
    conversation_id: int = Field(..., description="会话ID")
    message: str = Field(..., min_length=1, description="用户消息")
    context_mode: Optional[str] = Field(default="general", description="情景模式")
    analysis_focus: Optional[Dict[str, Any]] = Field(None, description="分析重点")


class CardModeAnalyzeRequest(BaseSchema):
    """卡片模式分析请求模式（不保存对话）"""
    
    message: str = Field(..., min_length=1, description="用户消息")
    context_mode: Optional[str] = Field(default="card_mode", description="情景模式")


class ChatResponse(BaseSchema):
    """聊天响应模式"""
    
    message: MessageResponse = Field(..., description="用户消息")
    analysis: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    suggestions: Optional[List[ResponseSuggestion]] = Field(None, description="回复建议")
