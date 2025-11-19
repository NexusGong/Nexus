"""
AI角色相关API路由
处理AI角色的查询和管理功能
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.ai_character import AICharacter
from app.schemas.character import AICharacterResponse, AICharacterListResponse
from loguru import logger

router = APIRouter(prefix="/api/characters", tags=["AI角色"])


@router.get("/", response_model=AICharacterListResponse)
async def get_characters(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取AI角色列表
    
    Args:
        category: 角色分类筛选（original/classic/anime）
        db: 数据库会话
        
    Returns:
        AICharacterListResponse: 角色列表
    """
    try:
        query = db.query(AICharacter).filter(AICharacter.is_active == True)
        
        # 分类筛选
        if category:
            query = query.filter(AICharacter.category == category)
        
        characters = query.order_by(AICharacter.rarity.desc(), AICharacter.created_at.asc()).all()
        
        return AICharacterListResponse(
            characters=[AICharacterResponse.model_validate(char) for char in characters],
            total=len(characters)
        )
        
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色列表失败"
        )


@router.get("/{character_id}", response_model=AICharacterResponse)
async def get_character(
    character_id: int,
    db: Session = Depends(get_db)
):
    """
    获取特定AI角色详情
    
    Args:
        character_id: 角色ID
        db: 数据库会话
        
    Returns:
        AICharacterResponse: 角色详情
    """
    try:
        character = db.query(AICharacter).filter(
            AICharacter.id == character_id,
            AICharacter.is_active == True
        ).first()
        
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )
        
        return AICharacterResponse.model_validate(character)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色详情失败"
        )

