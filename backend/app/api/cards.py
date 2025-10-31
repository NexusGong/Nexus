"""
分析卡片相关API路由
处理分析卡片的生成、管理和导出功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user_optional
from app.models.user import User
from app.models.conversation import Conversation
from app.models.analysis_card import AnalysisCard
from app.schemas.analysis import AnalysisCardCreate, AnalysisCardUpdate, AnalysisCardResponse, AnalysisCardListResponse
from app.services.card_service import card_service
from loguru import logger
import io

router = APIRouter(prefix="/api/cards", tags=["分析卡片"])


@router.post("/", response_model=AnalysisCardResponse)
async def create_analysis_card(
    card_data: AnalysisCardCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    创建分析卡片
    
    Args:
        card_data: 卡片创建数据
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AnalysisCardResponse: 创建的分析卡片
    """
    try:
        # 验证对话是否存在
        conversation = db.query(Conversation).filter(Conversation.id == card_data.conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 获取对话时间（最新用户消息的时间）
        from app.models.message import Message
        latest_user_message = db.query(Message).filter(
            Message.conversation_id == card_data.conversation_id,
            Message.role == 'user'
        ).order_by(Message.created_at.desc()).first()
        
        conversation_time = latest_user_message.created_at if latest_user_message else None
        
        # 创建分析卡片
        db_card = AnalysisCard(
            title=card_data.title,
            description=card_data.description,
            original_content=card_data.original_content,
            analysis_data=card_data.analysis_data.model_dump(),
            response_suggestions=[suggestion.model_dump() for suggestion in card_data.response_suggestions] if card_data.response_suggestions else None,
            context_mode=card_data.context_mode,
            card_template=card_data.card_template,
            user_id=current_user.id if current_user else None,
            conversation_id=card_data.conversation_id,
            conversation_time=conversation_time
        )
        
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        
        logger.info(f"创建分析卡片: {db_card.id}")
        
        return AnalysisCardResponse.model_validate(db_card)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建分析卡片失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建分析卡片失败"
        )


@router.get("/", response_model=AnalysisCardListResponse)
async def get_analysis_cards(
    page: int = 1,
    size: int = 20,
    tags: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取分析卡片列表
    
    Args:
        page: 页码
        size: 每页大小
        tags: 标签筛选（逗号分隔）
        is_favorite: 是否收藏
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AnalysisCardListResponse: 卡片列表
    """
    try:
        # 构建查询
        query = db.query(AnalysisCard)
        
        # 如果用户已登录，只返回该用户的卡片
        if current_user:
            query = query.filter(AnalysisCard.user_id == current_user.id)
        else:
            # 未登录用户返回公开卡片和匿名用户创建的卡片
            query = query.filter(
                (AnalysisCard.is_public == True) | 
                (AnalysisCard.user_id.is_(None))
            )
        
        # 标签筛选
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                query = query.filter(AnalysisCard.tags.contains([tag]))
        
        # 收藏筛选
        if is_favorite is not None:
            query = query.filter(AnalysisCard.is_favorite == is_favorite)
        
        # 分页查询
        total = query.count()
        cards = query.order_by(AnalysisCard.created_at.desc()).offset((page - 1) * size).limit(size).all()
        
        return AnalysisCardListResponse(
            cards=[AnalysisCardResponse.model_validate(card) for card in cards],
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"获取卡片列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取卡片列表失败"
        )


@router.get("/{card_id}", response_model=AnalysisCardResponse)
async def get_analysis_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取特定分析卡片详情
    
    Args:
        card_id: 卡片ID
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AnalysisCardResponse: 卡片详情
    """
    try:
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user and card.user_id != current_user.id:
            if not card.is_public:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此卡片"
                )
        
        return AnalysisCardResponse.model_validate(card)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取卡片详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取卡片详情失败"
        )


@router.put("/{card_id}", response_model=AnalysisCardResponse)
async def update_analysis_card(
    card_id: int,
    card_update: AnalysisCardUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    更新分析卡片
    
    Args:
        card_id: 卡片ID
        card_update: 卡片更新数据
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AnalysisCardResponse: 更新后的卡片
    """
    try:
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user and card.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限修改此卡片"
            )
        
        # 更新字段
        update_data = card_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)
        
        db.commit()
        db.refresh(card)
        
        logger.info(f"更新分析卡片: {card_id}")
        
        return AnalysisCardResponse.model_validate(card)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新卡片失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新卡片失败"
        )


@router.delete("/{card_id}")
async def delete_analysis_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    删除分析卡片
    
    Args:
        card_id: 卡片ID
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        dict: 删除结果
    """
    try:
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user and card.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此卡片"
            )
        
        db.delete(card)
        db.commit()
        
        logger.info(f"删除分析卡片: {card_id}")
        
        return {"message": "卡片删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除卡片失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除卡片失败"
        )


@router.get("/{card_id}/export/image")
async def export_card_as_image(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    request: Request = None
):
    """
    导出分析卡片为图片
    
    Args:
        card_id: 卡片ID
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        StreamingResponse: 图片文件流
    """
    try:
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user and card.user_id != current_user.id:
            if not card.is_public:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限导出此卡片"
                )
        
        # 获取用户时区
        from app.utils.helpers import get_user_timezone_from_request
        user_timezone = get_user_timezone_from_request(dict(request.headers)) if request else "Asia/Shanghai"
        
        # 生成图片
        image_data = await card_service.generate_card_image(card, user_timezone)
        
        # 更新导出统计
        card.export_count += 1
        db.commit()
        
        logger.info(f"导出卡片图片: {card_id}")
        
        # 生成文件名：主题+具体时间
        from app.utils.helpers import format_time_for_user
        safe_title = "".join(c for c in card.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:30]  # 限制长度
        timestamp = format_time_for_user(card.created_at, user_timezone).replace(' ', '_').replace(':', '-')
        filename = f"{safe_title}_{timestamp}.png"
        
        return StreamingResponse(
            io.BytesIO(image_data),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
                "Content-Type": "image/png"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出卡片图片失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="导出卡片图片失败"
        )


@router.get("/{card_id}/export/pdf")
async def export_card_as_pdf(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    request: Request = None
):
    """
    导出分析卡片为PDF
    
    Args:
        card_id: 卡片ID
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        StreamingResponse: PDF文件流
    """
    try:
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user and card.user_id != current_user.id:
            if not card.is_public:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限导出此卡片"
                )
        
        # 获取用户时区
        from app.utils.helpers import get_user_timezone_from_request
        user_timezone = get_user_timezone_from_request(dict(request.headers)) if request else "Asia/Shanghai"
        
        # 生成PDF
        pdf_data = await card_service.generate_card_pdf(card, user_timezone)
        
        # 更新导出统计
        card.export_count += 1
        db.commit()
        
        logger.info(f"导出卡片PDF: {card_id}")
        
        # 生成文件名：主题+具体时间
        from app.utils.helpers import format_time_for_user
        safe_title = "".join(c for c in card.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:30]  # 限制长度
        timestamp = format_time_for_user(card.created_at, user_timezone).replace(' ', '_').replace(':', '-')
        filename = f"{safe_title}_{timestamp}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
                "Content-Type": "application/pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出卡片PDF失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="导出卡片PDF失败"
        )

