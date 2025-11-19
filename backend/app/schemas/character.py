"""
角色相关Schema
定义AI角色相关的请求和响应模式
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampMixin, IDMixin


class AICharacterBase(BaseSchema):
    """角色基础模式"""
    name: str = Field(..., description="角色名称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    description: Optional[str] = Field(None, description="角色描述")
    personality: str = Field(..., description="性格特点")
    speaking_style: str = Field(..., description="说话风格")
    background: Optional[str] = Field(None, description="背景故事")
    category: str = Field(default="original", description="分类：original/classic/anime")
    rarity: str = Field(default="common", description="稀有度：common/rare/epic/legendary")


class AICharacterResponse(AICharacterBase, IDMixin, TimestampMixin):
    """角色响应模式"""
    is_active: bool
    system_prompt: Optional[str] = None  # 不返回给前端，仅内部使用


class AICharacterListResponse(BaseSchema):
    """角色列表响应模式"""
    characters: List[AICharacterResponse]
    total: int


class CharacterConversationCreate(BaseSchema):
    """创建角色对话请求"""
    character_id: int = Field(..., description="角色ID")
    title: Optional[str] = Field(None, description="对话标题")


class CharacterConversationBase(BaseSchema):
    """角色对话基础模式"""
    user_id: Optional[int]
    character_id: int
    title: Optional[str]
    context_summary: Optional[str]
    message_count: int


class CharacterConversationResponse(CharacterConversationBase, IDMixin, TimestampMixin):
    """角色对话响应模式"""
    character: Optional[AICharacterResponse] = None


class CharacterConversationListResponse(BaseSchema):
    """角色对话列表响应模式"""
    conversations: List[CharacterConversationResponse]
    total: int
    page: int
    size: int


class CharacterMessageCreate(BaseSchema):
    """创建角色消息请求"""
    conversation_id: int = Field(..., description="对话ID")
    message: str = Field(..., description="消息内容")


class CharacterMessageBase(BaseSchema):
    """角色消息基础模式"""
    conversation_id: int
    role: str
    content: str
    created_at: datetime


class CharacterMessageResponse(CharacterMessageBase, IDMixin):
    """角色消息响应模式"""
    pass


class CharacterChatResponse(BaseSchema):
    """角色对话响应"""
    message: CharacterMessageResponse
    conversation: CharacterConversationResponse


class GenerateCardFromChatRequest(BaseSchema):
    """从角色对话生成卡片请求"""
    conversation_id: int = Field(..., description="对话ID")
    title: Optional[str] = Field(None, description="卡片标题")

