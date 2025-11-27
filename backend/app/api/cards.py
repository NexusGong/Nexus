"""
分析卡片相关API路由
处理分析卡片的生成、管理和导出功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user_optional, get_client_info
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    创建分析卡片
    
    Args:
        card_data: 卡片创建数据
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AnalysisCardResponse: 创建的分析卡片
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        # 验证对话是否存在（如果提供了conversation_id）
        conversation_time = None
        if card_data.conversation_id:
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
            conversation_time=conversation_time,
            session_token=session_token if not current_user else None
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
    request: Request,
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
        request: FastAPI请求对象
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
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        # 构建查询
        query = db.query(AnalysisCard)
        
        # 如果用户已登录，只返回该用户的卡片
        if current_user:
            query = query.filter(AnalysisCard.user_id == current_user.id)
        else:
            # 未登录用户只返回该 session_token 的卡片
            # 如果 session_token 为空，则只返回 session_token 为 NULL 的卡片（历史数据）
            # 如果 session_token 不为空，返回该 session_token 的卡片或 session_token 为 NULL 的卡片（历史数据）
            if session_token:
                from sqlalchemy import or_
                query = query.filter(
                    AnalysisCard.user_id.is_(None),
                    or_(
                        AnalysisCard.session_token == session_token,
                        AnalysisCard.session_token.is_(None)
                    )
                )
            else:
                # session_token 为空时，只返回 session_token 为 NULL 的卡片
                query = query.filter(
                    AnalysisCard.user_id.is_(None),
                    AnalysisCard.session_token.is_(None)
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取特定分析卡片详情
    
    Args:
        card_id: 卡片ID
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AnalysisCardResponse: 卡片详情
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user:
            # 登录用户只能访问自己的卡片
            if card.user_id != current_user.id:
                if not card.is_public:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限访问此卡片"
                    )
        else:
            # 未登录用户只能访问自己的 session_token 的卡片
            # 如果卡片的 session_token 为 NULL（历史数据），允许所有未登录用户访问
            if card.user_id is not None:
                if not card.is_public:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限访问此卡片"
                    )
            # 如果卡片的 session_token 为 NULL（历史数据），允许访问
            # 如果卡片的 session_token 不为 NULL，必须匹配
            elif card.session_token is not None and card.session_token != session_token:
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    更新分析卡片
    
    Args:
        card_id: 卡片ID
        card_update: 卡片更新数据
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        AnalysisCardResponse: 更新后的卡片
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user:
            # 登录用户只能修改自己的卡片
            if card.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限修改此卡片"
                )
        else:
            # 未登录用户只能修改自己的 session_token 的卡片
            # 如果卡片的 session_token 为 NULL（历史数据），允许所有未登录用户修改
            if card.user_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限修改此卡片"
                )
            # 如果卡片的 session_token 为 NULL（历史数据），允许修改
            # 如果卡片的 session_token 不为 NULL，必须匹配
            if card.session_token is not None and card.session_token != session_token:
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    删除分析卡片
    
    Args:
        card_id: 卡片ID
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        dict: 删除结果
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user:
            # 登录用户只能删除自己的卡片
            if card.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限删除此卡片"
                )
        else:
            # 未登录用户只能删除自己的 session_token 的卡片
            # 如果卡片的 session_token 为 NULL（历史数据），允许所有未登录用户删除
            if card.user_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限删除此卡片"
                )
            # 如果卡片的 session_token 为 NULL（历史数据），允许删除
            # 如果卡片的 session_token 不为 NULL，必须匹配
            if card.session_token is not None and card.session_token != session_token:
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    导出分析卡片为图片
    
    Args:
        card_id: 卡片ID
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        StreamingResponse: 图片文件流
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        card = db.query(AnalysisCard).filter(AnalysisCard.id == card_id).first()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 检查权限
        if current_user:
            # 登录用户只能导出自己的卡片
            if card.user_id != current_user.id:
                if not card.is_public:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限导出此卡片"
                    )
        else:
            # 未登录用户只能导出自己的 session_token 的卡片
            # 如果卡片的 session_token 为 NULL（历史数据），允许所有未登录用户导出
            if card.user_id is not None:
                if not card.is_public:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限导出此卡片"
                    )
            # 如果卡片的 session_token 为 NULL（历史数据），允许导出
            # 如果卡片的 session_token 不为 NULL，必须匹配
            elif card.session_token is not None and card.session_token != session_token:
                if not card.is_public:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限导出此卡片"
                    )
        
        # 获取用户时区
        from app.utils.helpers import get_user_timezone_from_request
        user_timezone = get_user_timezone_from_request(dict(request.headers)) if request else "Asia/Shanghai"
        
        # 生成图片（Playwright渲染）
        from app.utils.helpers import format_time_for_user
        from app.services.screenshot_service import generate_card_image_with_playwright
        created_str = format_time_for_user(card.created_at, user_timezone).replace('年', '-').replace('月', '-').replace('日', '')
        image_data = await generate_card_image_with_playwright(card, created_str)
        
        # 更新导出统计（兼容历史数据为NULL的情况）
        card.export_count = (card.export_count or 0) + 1
        from datetime import datetime, timezone
        card.last_exported_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"导出卡片图片: {card_id}")
        
        # 生成文件名：主题+具体时间（仅ASCII），并提供UTF-8编码的filename*
        from app.utils.helpers import format_time_for_user
        import re
        from urllib.parse import quote
        ascii_title = re.sub(r'[^A-Za-z0-9 _-]+', '', card.title or '').strip()
        ascii_title = ascii_title.replace(' ', '_')[:30] or 'card'
        timestamp = format_time_for_user(card.created_at, user_timezone).replace(' ', '_').replace(':', '-')
        filename_ascii = f"{ascii_title}_{timestamp}.png"
        filename_utf8 = quote(filename_ascii)

        return StreamingResponse(
            io.BytesIO(image_data),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{filename_utf8}",
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


# PDF 导出功能已下线

