"""
基础模式类
定义通用的Pydantic模式基类
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """基础模式类"""
    
    model_config = ConfigDict(
        from_attributes=True,  # 支持从ORM对象创建
        validate_assignment=True,  # 赋值时验证
        arbitrary_types_allowed=True,  # 允许任意类型
    )


class TimestampMixin(BaseSchema):
    """时间戳混入类"""
    
    created_at: datetime
    updated_at: datetime


class IDMixin(BaseSchema):
    """ID混入类"""
    
    id: int

