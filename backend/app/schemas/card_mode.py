"""
卡片模式相关Schema
定义卡片模式相关的请求和响应模式
"""

from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.base import BaseSchema


class GenerateCardRequest(BaseSchema):
    """生成卡片请求"""
    source: str = Field(default="history", description="来源：history/random")
    user_history_id: Optional[int] = Field(None, description="用户历史记录ID（可选）")


class GenerateCardResponse(BaseSchema):
    """生成卡片响应"""
    card_id: int
    message: str = "卡片生成成功"

