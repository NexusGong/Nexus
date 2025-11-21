"""
AI角色相关API路由
处理AI角色的查询和管理功能
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.ai_character import AICharacter
from app.models.user_character import UserCharacter
from app.schemas.character import AICharacterResponse, AICharacterListResponse
from app.api.deps import get_current_user_optional
from app.models.user import User
from loguru import logger

router = APIRouter(prefix="/api/characters", tags=["AI角色"])


def calculate_character_availability(
    characters: list[AICharacter],
    current_user: Optional[User] = None,
    db: Optional[Session] = None
) -> dict[int, dict[str, bool]]:
    """
    计算角色可用性
    
    Args:
        characters: 角色列表
        current_user: 当前用户（可选）
        db: 数据库会话（可选，用于查询用户已解锁的角色）
        
    Returns:
        dict: {character_id: {"is_usable": bool, "is_locked": bool}}
    """
    availability = {}
    
    # 按稀有度分组
    legendary_chars = [c for c in characters if c.rarity == "legendary"]
    epic_chars = [c for c in characters if c.rarity == "epic"]
    rare_chars = [c for c in characters if c.rarity == "rare"]
    common_chars = [c for c in characters if c.rarity == "common"]
    
    # 获取用户已解锁的角色（如果已登录）
    unlocked_character_ids = set()
    if current_user and db:
        user_characters = db.query(UserCharacter).filter(
            UserCharacter.user_id == current_user.id,
            UserCharacter.is_owned == True
        ).all()
        unlocked_character_ids = {uc.character_id for uc in user_characters}
    
    if current_user:
        # 登录用户（未解锁）：第一个SSR + 第一个SR + 全部R可用
        # 其他SSR和SR需要解锁
        first_ssr_id = legendary_chars[0].id if legendary_chars else None
        first_sr_id = epic_chars[0].id if epic_chars else None
        
        for char in characters:
            if char.id in unlocked_character_ids:
                # 已解锁的角色
                availability[char.id] = {"is_usable": True, "is_locked": False}
            elif char.rarity == "legendary":
                # SSR角色：只有第一个可用，其他需要解锁
                availability[char.id] = {
                    "is_usable": char.id == first_ssr_id,
                    "is_locked": char.id != first_ssr_id
                }
            elif char.rarity == "epic":
                # SR角色：只有第一个可用，其他需要解锁
                availability[char.id] = {
                    "is_usable": char.id == first_sr_id,
                    "is_locked": char.id != first_sr_id
                }
            elif char.rarity in ["rare", "common"]:
                # R、N角色：全部可用
                availability[char.id] = {"is_usable": True, "is_locked": False}
            else:
                availability[char.id] = {"is_usable": False, "is_locked": True}
    else:
        # 未登录用户：只能使用R角色
        for char in characters:
            if char.rarity in ["rare", "common"]:
                # R、N角色：全部可用
                availability[char.id] = {"is_usable": True, "is_locked": False}
            else:
                # SSR和SR角色：全部锁定，需要登录
                availability[char.id] = {"is_usable": False, "is_locked": True}
    
    return availability


@router.get("/", response_model=AICharacterListResponse)
async def get_characters(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取AI角色列表（包含可用性信息）
    
    Args:
        category: 角色分类筛选（original/classic/anime/tv_series）
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AICharacterListResponse: 角色列表（包含可用性信息）
    """
    try:
        query = db.query(AICharacter).filter(AICharacter.is_active == True)
        
        # 分类筛选
        if category:
            query = query.filter(AICharacter.category == category)
        
        characters = query.order_by(AICharacter.rarity.desc(), AICharacter.created_at.asc()).all()
        
        # 计算角色可用性
        availability = calculate_character_availability(characters, current_user, db)
        
        # 构建响应，添加可用性信息
        character_responses = []
        for char in characters:
            char_dict = AICharacterResponse.model_validate(char).model_dump()
            if char.id in availability:
                char_dict["is_usable"] = availability[char.id]["is_usable"]
                char_dict["is_locked"] = availability[char.id]["is_locked"]
            else:
                char_dict["is_usable"] = False
                char_dict["is_locked"] = True
            character_responses.append(AICharacterResponse(**char_dict))
        
        return AICharacterListResponse(
            characters=character_responses,
            total=len(character_responses)
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

