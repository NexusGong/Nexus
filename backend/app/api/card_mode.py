"""
卡片模式相关API路由
处理卡片模式的卡片生成功能
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user_optional, get_client_info
from app.models.user import User
from app.models.analysis_card import AnalysisCard
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.card_mode import GenerateCardRequest, GenerateCardResponse
from app.services.ai_service import ai_service
from loguru import logger
import random

router = APIRouter(prefix="/api/card-mode", tags=["卡片模式"])


@router.post("/generate", response_model=GenerateCardResponse)
async def generate_card(
    card_request: GenerateCardRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    生成卡片（卡片模式）
    
    Args:
        card_request: 生成卡片请求
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        GenerateCardResponse: 生成的卡片信息
    """
    try:
        ip_address, session_token = get_client_info(request)
        
        # 根据source获取对话内容
        chat_content = ""
        conversation_time = None
        
        if card_request.source == "history" and card_request.user_history_id:
            # 从指定历史记录生成
            conversation = db.query(Conversation).filter(
                Conversation.id == card_request.user_history_id
            ).first()
            
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定的对话不存在"
                )
            
            # 检查权限
            if current_user:
                if conversation.user_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限访问此对话"
                    )
            else:
                if conversation.user_id is not None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限访问此对话"
                    )
            
            # 获取消息
            messages = db.query(Message).filter(
                Message.conversation_id == conversation.id,
                Message.role == "user"
            ).order_by(Message.created_at.desc()).limit(1).all()
            
            if messages:
                chat_content = messages[0].content
                conversation_time = messages[0].created_at
        else:
            # 随机从用户历史记录中选择
            query = db.query(Conversation).filter(Conversation.is_active == "active")
            
            if current_user:
                query = query.filter(Conversation.user_id == current_user.id)
            else:
                if session_token:
                    from sqlalchemy import or_
                    query = query.filter(
                        Conversation.user_id.is_(None),
                        or_(
                            Conversation.session_token == session_token,
                            Conversation.session_token.is_(None)
                        )
                    )
                else:
                    query = query.filter(
                        Conversation.user_id.is_(None),
                        Conversation.session_token.is_(None)
                    )
            
            conversations = query.all()
            
            if not conversations:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="没有可用的历史记录，请先进行一些对话分析"
                )
            
            # 随机选择一个对话
            selected_conversation = random.choice(conversations)
            
            # 获取该对话的用户消息
            messages = db.query(Message).filter(
                Message.conversation_id == selected_conversation.id,
                Message.role == "user"
            ).order_by(Message.created_at.desc()).limit(1).all()
            
            if messages:
                chat_content = messages[0].content
                conversation_time = messages[0].created_at
        
        if not chat_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="无法获取对话内容"
            )
        
        # 使用AI分析对话内容
        analysis_result = await ai_service.analyze_chat_content(
            chat_content=chat_content,
            context_mode="general"
        )
        
        # 生成回复建议
        suggestions = await ai_service.generate_response_suggestions(
            chat_content=chat_content,
            analysis_result=analysis_result,
            context_mode="general"
        )
        
        # 生成卡片标题
        intent = analysis_result.intent.get('primary', '未知意图') if isinstance(analysis_result.intent, dict) else '未知意图'
        title = f"{intent}分析"
        
        # 创建分析卡片
        db_card = AnalysisCard(
            title=title,
            description="卡片模式生成的分析卡片",
            original_content=chat_content,
            analysis_data=analysis_result.model_dump(),
            response_suggestions=[suggestion.model_dump() for suggestion in suggestions],
            context_mode="card_mode",
            user_id=current_user.id if current_user else None,
            conversation_id=None,
            conversation_time=conversation_time,
            session_token=session_token if not current_user else None
        )
        
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        
        logger.info(f"卡片模式生成卡片: {db_card.id}")
        
        return GenerateCardResponse(
            card_id=db_card.id,
            message="卡片生成成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成卡片失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成卡片失败"
        )

