"""
支付相关API
处理角色购买和付费解锁功能
"""

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

router = APIRouter(prefix="/api/payment", tags=["支付"])


@router.post("/purchase-character/{character_id}")
async def purchase_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    购买角色（模拟支付流程）
    
    Args:
        character_id: 角色ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        dict: 支付结果和角色解锁状态
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
        
        if user_character and user_character.is_owned:
            return {
                "message": "角色已拥有",
                "is_owned": True,
                "character_id": character_id,
                "payment_success": False
            }
        
        # 模拟支付流程
        # 1. 验证支付（这里模拟成功）
        logger.info(f"用户 {current_user.id} 开始购买角色 {character_id}，模拟支付流程...")
        
        # 2. 模拟支付延迟
        import asyncio
        await asyncio.sleep(1)  # 模拟支付处理时间
        
        # 3. 支付成功，解锁角色
        if user_character:
            user_character.is_owned = True
            user_character.owned_at = datetime.utcnow()
        else:
            user_character = UserCharacter(
                user_id=current_user.id,
                character_id=character_id,
                is_owned=True,
                owned_at=datetime.utcnow()
            )
            db.add(user_character)
        
        db.commit()
        logger.info(f"用户 {current_user.id} 成功购买角色 {character_id}")
        
        return {
            "message": "支付成功，角色已解锁",
            "is_owned": True,
            "character_id": character_id,
            "payment_success": True,
            "payment_id": f"PAY_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{current_user.id}_{character_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"购买角色失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="购买角色失败"
        )

