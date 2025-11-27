"""
分析相关的Pydantic模式
定义分析结果和卡片的请求和响应数据结构
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field
from app.schemas.base import BaseSchema, TimestampMixin, IDMixin


class AnalysisResult(BaseSchema):
    """分析结果模式"""
    
    intent: Dict[str, Any] = Field(..., description="意图分析")
    sentiment: Dict[str, Any] = Field(..., description="情感分析")
    tone: Dict[str, Any] = Field(..., description="语气分析")
    relationship: Dict[str, Any] = Field(..., description="关系分析")
    subtext: Dict[str, Any] = Field(..., description="潜台词分析")
    key_points: List[str] = Field(..., description="关键信息提取")
    context_analysis: Dict[str, Any] = Field(..., description="上下文分析")


class ResponseSuggestion(BaseSchema):
    """回复建议模式"""
    
    type: str = Field(..., description="建议类型")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    examples: List[str] = Field(..., description="示例回复")


class AnalysisCardBase(BaseSchema):
    """分析卡片基础模式"""
    
    title: str = Field(..., min_length=1, max_length=200, description="卡片标题")
    description: Optional[str] = Field(None, description="卡片描述")
    original_content: str = Field(..., description="原始聊天内容")
    analysis_data: AnalysisResult = Field(..., description="分析结果数据")
    response_suggestions: Optional[List[ResponseSuggestion]] = Field(None, description="回复建议")
    context_mode: Optional[str] = Field(None, description="分析时的情景模式")
    card_template: str = Field(default="default", description="卡片模板")


class AnalysisCardCreate(AnalysisCardBase):
    """创建分析卡片请求模式"""
    
    conversation_id: Optional[int] = Field(None, description="会话ID（卡片模式可以为空）")


class AnalysisCardUpdate(BaseSchema):
    """更新分析卡片请求模式"""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="卡片标题")
    description: Optional[str] = Field(None, description="卡片描述")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")
    is_public: Optional[bool] = Field(None, description="是否公开")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class AnalysisCardResponse(AnalysisCardBase, IDMixin, TimestampMixin):
    """分析卡片响应模式"""
    
    user_id: Optional[int] = Field(None, description="用户ID")
    conversation_id: int = Field(..., description="会话ID")
    is_favorite: bool = Field(..., description="是否收藏")
    is_public: bool = Field(..., description="是否公开")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    export_count: int = Field(..., description="导出次数")
    last_exported_at: Optional[datetime] = Field(None, description="最后导出时间")


class AnalysisCardListResponse(BaseSchema):
    """分析卡片列表响应模式"""
    
    cards: List[AnalysisCardResponse]
    total: int
    page: int
    size: int


class OCRRequest(BaseSchema):
    """OCR识别请求模式"""
    
    image_url: Optional[str] = Field(None, description="图片URL")
    image_base64: Optional[str] = Field(None, description="图片Base64编码")


class OCRResponse(BaseSchema):
    """OCR识别响应模式"""
    
    text: str = Field(..., description="识别出的文本")
    confidence: float = Field(..., description="识别置信度")
    language: str = Field(..., description="识别语言")
    metadata: Dict[str, Any] = Field(..., description="识别元数据")

