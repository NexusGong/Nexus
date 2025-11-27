"""
聊天相关API路由
处理聊天对话、消息管理和分析功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user_optional, get_client_info
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationListResponse
from app.schemas.message import ChatRequest, ChatResponse, MessageResponse, CardModeAnalyzeRequest
from app.schemas.analysis import OCRRequest, OCRResponse
from app.services.ocr_service import volc_ocr_service, doubao_ocr_service
from app.services.usage_limit_service import (
    check_ocr_limit, record_ocr_usage,
    check_conversation_limit,
    check_chat_analysis_limit, record_chat_analysis_usage
)
from fastapi import Request
from app.services.ai_service import ai_service
from loguru import logger

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    创建新的对话会话
    
    Args:
        conversation: 对话创建数据
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ConversationResponse: 创建的对话会话
    """
    try:
        # 检查会话创建限制（仅非登录用户）
        if not current_user:
            ip_address, session_token = get_client_info(request)
            can_create, count, limit = check_conversation_limit(current_user, ip_address, session_token, db)
            if not can_create:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"非登录用户最多只能创建{limit}个会话，当前已有{count}个。请登录后继续使用。"
                )
        
        # 创建新对话
        db_conversation = Conversation(
            title=conversation.title,
            description=conversation.description,
            context_mode=conversation.context_mode,
            analysis_focus=conversation.analysis_focus,
            user_id=current_user.id if current_user else None
        )
        
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        logger.info(f"创建新对话: {db_conversation.id}")
        
        return ConversationResponse.model_validate(db_conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建对话失败"
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    request: Request,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取对话会话列表
    
    Args:
        request: FastAPI请求对象
        page: 页码
        size: 每页大小
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ConversationListResponse: 对话列表
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        # 构建查询
        query = db.query(Conversation).filter(Conversation.is_active == "active")
        
        # 如果用户已登录，只返回该用户的对话
        if current_user:
            query = query.filter(Conversation.user_id == current_user.id)
        else:
            # 未登录用户只返回该 session_token 的对话
            # 如果 session_token 为空，则只返回 session_token 为 NULL 的对话（历史数据）
            # 如果 session_token 不为空，返回该 session_token 的对话或 session_token 为 NULL 的对话（历史数据）
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
                # session_token 为空时，只返回 session_token 为 NULL 的对话
                query = query.filter(
                    Conversation.user_id.is_(None),
                    Conversation.session_token.is_(None)
                )
        
        # 分页查询
        total = query.count()
        conversations = query.order_by(Conversation.updated_at.desc()).offset((page - 1) * size).limit(size).all()
        
        return ConversationListResponse(
            conversations=[ConversationResponse.model_validate(conv) for conv in conversations],
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话列表失败"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取特定对话会话详情
    
    Args:
        conversation_id: 对话ID
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ConversationResponse: 对话详情
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        # 调试日志：检查认证状态
        if current_user:
            logger.debug(f"获取对话 {conversation_id}: 当前用户已登录，用户ID={current_user.id}")
        else:
            logger.debug(f"获取对话 {conversation_id}: 当前用户未登录，session_token={session_token[:20] if session_token else 'None'}...")
            # 检查是否有Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header:
                logger.warning(f"获取对话 {conversation_id}: 有Authorization header但用户未认证，header={auth_header[:30]}...")
            else:
                logger.debug(f"获取对话 {conversation_id}: 没有Authorization header")
        
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查权限（添加详细日志用于调试）
        if current_user:
            # 登录用户只能访问自己的对话
            if conversation.user_id != current_user.id:
                logger.warning(
                    f"权限检查失败: 用户 {current_user.id} 尝试访问对话 {conversation_id}, "
                    f"但对话属于用户 {conversation.user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话"
                )
            logger.debug(f"权限检查通过: 用户 {current_user.id} 访问自己的对话 {conversation_id}")
        else:
            # 未登录用户只能访问自己的 session_token 的对话
            # 如果对话的 session_token 为 NULL（历史数据），允许所有未登录用户访问
            if conversation.user_id is not None:
                logger.warning(
                    f"权限检查失败: 未登录用户尝试访问对话 {conversation_id}, "
                    f"但对话属于已登录用户 {conversation.user_id}, session_token={session_token[:20] if session_token else 'None'}..."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话（该对话属于已登录用户，请先登录）"
                )
            # 如果对话的 session_token 为 NULL（历史数据），允许访问
            # 如果对话的 session_token 不为 NULL，必须匹配
            if conversation.session_token is not None and conversation.session_token != session_token:
                logger.warning(
                    f"权限检查失败: 未登录用户尝试访问对话 {conversation_id}, "
                    f"session_token不匹配. 对话token={conversation.session_token[:20] if conversation.session_token else 'None'}..., "
                    f"请求token={session_token[:20] if session_token else 'None'}..."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话（session token不匹配）"
                )
            logger.debug(
                f"权限检查通过: 未登录用户访问对话 {conversation_id}, "
                f"session_token匹配或为历史数据"
            )
        
        return ConversationResponse.model_validate(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话详情失败"
        )


@router.post("/analyze", response_model=ChatResponse)
async def analyze_chat(
    request: ChatRequest,
    request_obj: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    分析聊天内容并生成回复建议
    
    Args:
        request: 聊天分析请求
        request_obj: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ChatResponse: 分析结果和回复建议
    """
    try:
        # 验证对话是否存在
        conversation = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查聊天分析次数限制
        ip_address, session_token = get_client_info(request_obj)
        can_analyze, used, limit = check_chat_analysis_limit(
            current_user, request.conversation_id, ip_address, session_token, db
        )
        if not can_analyze:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"该会话今日分析次数已达上限（{limit}次），已使用{used}次。请登录后获得更多次数。"
            )
        
        # 保存用户消息
        user_message = Message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message,
            message_type="text",
            source="manual"
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 使用AI分析聊天内容
        analysis_result = await ai_service.analyze_chat_content(
            chat_content=request.message,
            context_mode=request.context_mode or conversation.context_mode,
            analysis_focus=request.analysis_focus or conversation.analysis_focus
        )
        
        # 生成回复建议
        suggestions = await ai_service.generate_response_suggestions(
            chat_content=request.message,
            analysis_result=analysis_result,
            context_mode=request.context_mode or conversation.context_mode
        )
        
        # 生成AI分析摘要
        analysis_summary = f"""📊 **分析结果摘要**

🎯 **主要意图**: {analysis_result.intent['primary']}
💭 **情感状态**: {analysis_result.sentiment['overall']} (强度: {int(analysis_result.sentiment['intensity'] * 100)}%)
🗣️ **语气风格**: {analysis_result.tone['style']} / {analysis_result.tone['politeness']}
👥 **关系分析**: {analysis_result.relationship['closeness']} / {analysis_result.relationship['power_dynamic']}
🔍 **关键信息**: {', '.join(analysis_result.key_points[:3])}

💡 **已生成 {len(suggestions)} 条回复建议，点击下方展开查看详细分析**"""

        # 保存AI分析结果
        ai_message = Message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=analysis_summary,
            message_type="analysis",
            source="ai_generated",
            analysis_result=analysis_result.model_dump(),
            analysis_metadata={
                "context_mode": request.context_mode or conversation.context_mode,
                "analysis_focus": request.analysis_focus or conversation.analysis_focus,
                "suggestions": [suggestion.model_dump() for suggestion in suggestions],
                "suggestions_count": len(suggestions)
            },
            is_processed=True
        )
        db.add(ai_message)
        
        # 更新对话统计
        conversation.message_count += 1
        conversation.analysis_count += 1
        conversation.last_message_at = user_message.created_at
        
        db.commit()
        db.refresh(ai_message)
        
        # 记录聊天分析使用
        record_chat_analysis_usage(
            current_user, request.conversation_id, ip_address, session_token, db
        )
        
        logger.info(f"聊天分析完成: 对话{request.conversation_id}")
        
        return ChatResponse(
            message=MessageResponse.model_validate(ai_message),
            analysis=analysis_result.model_dump(),
            suggestions=[suggestion.model_dump() for suggestion in suggestions]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="聊天分析失败"
        )


@router.post("/analyze-card-mode", response_model=ChatResponse)
async def analyze_chat_card_mode(
    request_data: CardModeAnalyzeRequest,
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    卡片模式：分析聊天内容并生成回复建议（不保存对话）
    
    Args:
        request_data: 卡片模式分析请求
        request_obj: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ChatResponse: 分析结果和回复建议（不包含message字段，因为不保存对话）
    """
    try:
        # 确保context_mode默认为card_mode（如果没有提供或为空）
        context_mode = request_data.context_mode or "card_mode"
        
        # 使用AI分析聊天内容（不保存对话）
        analysis_result = await ai_service.analyze_chat_content(
            chat_content=request_data.message,
            context_mode=context_mode
        )
        
        # 生成回复建议
        suggestions = await ai_service.generate_response_suggestions(
            chat_content=request_data.message,
            analysis_result=analysis_result,
            context_mode=context_mode
        )
        
        # 创建一个临时的MessageResponse用于返回（不保存到数据库）
        from app.schemas.message import MessageResponse
        from datetime import datetime
        temp_message = MessageResponse(
            id=0,  # 临时ID
            conversation_id=0,  # 临时ID
            role="assistant",
            content="卡片模式分析结果",  # 占位符内容，满足schema验证要求
            message_type="analysis",
            source="card_mode",
            analysis_result=analysis_result.model_dump(),
            analysis_metadata={
                "context_mode": context_mode,
                "suggestions": [suggestion.model_dump() for suggestion in suggestions],
                "suggestions_count": len(suggestions)
            },
            is_processed=True,
            is_archived=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        logger.info(f"卡片模式分析完成（不保存对话）")
        
        return ChatResponse(
            message=temp_message,
            analysis=analysis_result.model_dump(),
            suggestions=[suggestion.model_dump() for suggestion in suggestions]
        )
        
    except Exception as e:
        logger.error(f"卡片模式分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="卡片模式分析失败"
        )


@router.post("/ocr", response_model=OCRResponse)
async def extract_text_from_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    request: Request = None
):
    """
    从上传的图片中提取文字内容
    
    Args:
        file: 上传的图片文件
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        OCRResponse: OCR识别结果
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只支持图片文件"
            )
        
        # 读取文件内容
        image_data = await file.read()
        
        # 获取文件扩展名
        file_extension = file.filename.split('.')[-1].lower() if file.filename else 'png'
        
        # 构造取消事件，监听客户端断开
        import asyncio
        cancel_event = asyncio.Event()
        async def _watch_disconnect():
            try:
                if request is None:
                    return
                while True:
                    if await request.is_disconnected():
                        cancel_event.set()
                        break
                    await asyncio.sleep(0.2)
            except Exception:
                pass
        asyncio.create_task(_watch_disconnect())
        # 调用OCR服务（单张默认走火山）
        ocr_result = await volc_ocr_service.extract_text_from_image(image_data, file_extension, cancel_event=cancel_event)
        
        logger.info(f"OCR识别完成: {file.filename}")
        
        return ocr_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR识别失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="图片识别失败"
        )


@router.post("/ocr/batch", response_model=OCRResponse)
async def extract_text_from_images_batch(
    files: List[UploadFile] = File(...),
    mode: str = Form("fast"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    request: Request = None
):
    """
    批量OCR识别多张图片
    
    Args:
        files: 图片文件列表
        mode: 识别模式，'fast'为极速模式（火山引擎OCR），'quality'为性能模式（豆包OCR）
        current_user: 当前用户（可选）
        
    Returns:
        OCRResponse: OCR识别结果
    """
    try:
        import time
        t0 = time.monotonic()
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请至少上传一张图片"
            )
        
        if len(files) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最多支持10张图片批量识别"
            )
        
        # 验证文件类型和大小
        images_data = []
        image_formats = []
        
        for file in files:
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件 {file.filename} 不是有效的图片格式"
                )
            
            # 检查文件大小 (10MB)
            file_size = 0
            read_start = time.monotonic()
            content = await file.read()
            read_end = time.monotonic()
            logger.info(f"批量OCR: 读取文件 {file.filename} 用时 {(read_end-read_start):.3f}s, 大小 {len(content)} bytes")
            file_size = len(content)
            
            if file_size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件 {file.filename} 大小超过10MB限制"
                )
            
            # 获取文件扩展名
            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else 'png'
            if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                file_extension = 'png'
            
            images_data.append(content)
            image_formats.append(file_extension)
        
        t1 = time.monotonic()
        logger.info(f"批量OCR: 预处理用时 {(t1-t0):.3f}s, 共 {len(images_data)} 张, 模式={mode}")
        
        # 检查OCR使用次数限制
        ip_address, session_token = get_client_info(request)
        can_use, used, limit = check_ocr_limit(current_user, mode, ip_address, session_token, db)
        if not can_use:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"今日{mode == 'fast' and '极速模式' or '性能模式'}OCR使用次数已达上限（{limit}次），已使用{used}次。请登录后获得更多次数。"
            )
        
        # 批量OCR识别：按mode选择服务
        # 构造取消事件，监听客户端断开
        import asyncio
        cancel_event = asyncio.Event()
        async def _watch_disconnect():
            try:
                if request is None:
                    return
                while True:
                    if await request.is_disconnected():
                        cancel_event.set()
                        break
                    await asyncio.sleep(0.2)
            except Exception:
                pass
        asyncio.create_task(_watch_disconnect())
        if mode == "quality":
            ocr_result = await doubao_ocr_service._extract_with_doubao_ocr(images_data, image_formats, cancel_event=cancel_event)
        else:
            ocr_result = await volc_ocr_service.extract_text_from_images(images_data, image_formats, cancel_event=cancel_event)
        t2 = time.monotonic()
        logger.info(f"批量OCR: 模型用时 {(t2-t1):.3f}s, 总用时 {(t2-t0):.3f}s")
        logger.info(f"批量OCR识别完成: {len(files)} 张图片")
        
        # 记录OCR使用
        record_ocr_usage(current_user, mode, ip_address, session_token, db)
        
        return ocr_result
        
    except HTTPException:
        raise
    except Exception as e:
        # 将具体原因透传给前端，便于排查（仅调试模式下详细）
        logger.error(f"批量OCR识别失败: {e}")
        from app.config import settings as app_settings
        detail = str(e) if app_settings.debug else "图片识别失败"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail
        )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    request: Request,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取对话中的消息列表
    
    Args:
        conversation_id: 对话ID
        request: FastAPI请求对象
        page: 页码
        size: 每页大小
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        List[MessageResponse]: 消息列表
    """
    try:
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        # 验证对话是否存在
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查权限
        if current_user:
            # 登录用户只能访问自己的对话
            if conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话"
                )
        else:
            # 未登录用户只能访问自己的 session_token 的对话
            # 如果对话的 session_token 为 NULL（历史数据），允许所有未登录用户访问
            if conversation.user_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话"
                )
            # 如果对话的 session_token 为 NULL（历史数据），允许访问
            # 如果对话的 session_token 不为 NULL，必须匹配
            if conversation.session_token is not None and conversation.session_token != session_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话"
                )
        
        # 查询消息
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.is_archived == False
        ).order_by(Message.created_at.asc()).offset((page - 1) * size).limit(size).all()
        
        return [MessageResponse.model_validate(msg) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息列表失败"
        )


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    更新对话会话
    
    Args:
        conversation_id: 对话ID
        conversation_update: 对话更新数据
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ConversationResponse: 更新后的对话
    """
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查权限
        if current_user and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限修改此对话"
            )
        
        # 更新字段
        update_data = conversation_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conversation, field, value)
        
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"更新对话: {conversation_id}")
        
        return ConversationResponse.model_validate(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新对话失败"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    删除对话会话
    
    Args:
        conversation_id: 对话ID
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        dict: 删除结果
    """
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查权限
        if current_user and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此对话"
            )
        
        # 软删除：将对话标记为非活跃状态
        conversation.is_active = "deleted"
        db.commit()
        
        logger.info(f"删除对话: {conversation_id}")
        
        return {"message": "对话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除对话失败"
        )
