"""
角色管理API
处理用户角色解锁和管理功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from app.database import get_db
from app.models.ai_character import AICharacter
from app.models.user_character import UserCharacter
from app.api.deps import get_current_user
from app.models.user import User
from loguru import logger

router = APIRouter(prefix="/api/character-management", tags=["角色管理"])


@router.get("/my-characters")
async def get_my_characters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的角色列表（包含解锁状态）
    
    Returns:
        List[dict]: 角色列表，每个角色包含解锁状态
    """
    try:
        # 获取所有角色
        all_characters = db.query(AICharacter).filter(AICharacter.is_active == True).all()
        
        # 获取用户已解锁的角色
        user_characters = db.query(UserCharacter).filter(
            UserCharacter.user_id == current_user.id
        ).all()
        
        # 创建拥有状态映射
        owned_map = {uc.character_id: uc.is_owned for uc in user_characters}
        
        # 构建响应
        result = []
        for char in all_characters:
            is_owned = owned_map.get(char.id, False)  # 默认未拥有
            result.append({
                "id": char.id,
                "name": char.name,
                "avatar_url": char.avatar_url,
                "description": char.description,
                "category": char.category,
                "rarity": char.rarity,
                "is_owned": is_owned,
                "owned_at": None
            })
            
            # 如果已拥有，添加获得时间
            if is_owned:
                user_char = next((uc for uc in user_characters if uc.character_id == char.id), None)
                if user_char and user_char.owned_at:
                    result[-1]["owned_at"] = user_char.owned_at.isoformat()
        
        return {"characters": result, "total": len(result)}
        
    except Exception as e:
        logger.error(f"获取用户角色列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色列表失败"
        )


@router.post("/own/{character_id}")
async def own_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获得角色（拥有角色）
    
    Args:
        character_id: 角色ID
        
    Returns:
        dict: 获得结果
    """
    try:
        # 检查角色是否存在
        character = db.query(AICharacter).filter(
            AICharacter.id == character_id,
            AICharacter.is_active == True
        ).first()
        
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )
        
        # 检查是否已拥有
        user_character = db.query(UserCharacter).filter(
            and_(
                UserCharacter.user_id == current_user.id,
                UserCharacter.character_id == character_id
            )
        ).first()
        
        if user_character:
            if user_character.is_owned:
                return {"message": "角色已拥有", "is_owned": True}
            # 更新拥有状态
            user_character.is_owned = True
            user_character.owned_at = datetime.utcnow()
        else:
            # 创建新的拥有记录
            user_character = UserCharacter(
                user_id=current_user.id,
                character_id=character_id,
                is_owned=True,
                owned_at=datetime.utcnow()
            )
            db.add(user_character)
        
        db.commit()
        logger.info(f"用户 {current_user.id} 获得角色 {character_id}")
        
        return {
            "message": "角色获得成功",
            "is_owned": True,
            "character_id": character_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获得角色失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获得角色失败"
        )

