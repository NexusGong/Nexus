"""
聊天相关API路由
处理聊天对话、消息管理和分析功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user_optional
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationListResponse
from app.schemas.message import ChatRequest, ChatResponse, MessageResponse
from app.schemas.analysis import OCRRequest, OCRResponse
from app.services.ocr_service import ocr_service
from app.services.ai_service import ai_service
from loguru import logger

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    创建新的对话会话
    
    Args:
        conversation: 对话创建数据
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ConversationResponse: 创建的对话会话
    """
    try:
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
        
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建对话失败"
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取对话会话列表
    
    Args:
        page: 页码
        size: 每页大小
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ConversationListResponse: 对话列表
    """
    try:
        # 构建查询
        query = db.query(Conversation).filter(Conversation.is_active == "active")
        
        # 如果用户已登录，只返回该用户的对话
        if current_user:
            query = query.filter(Conversation.user_id == current_user.id)
        else:
            # 未登录用户只返回公开对话或临时对话
            query = query.filter(Conversation.user_id.is_(None))
        
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取特定对话会话详情
    
    Args:
        conversation_id: 对话ID
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        ConversationResponse: 对话详情
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
                detail="无权限访问此对话"
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    分析聊天内容并生成回复建议
    
    Args:
        request: 聊天分析请求
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


@router.post("/ocr", response_model=OCRResponse)
async def extract_text_from_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
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
        
        # 调用OCR服务
        ocr_result = await ocr_service.extract_text_from_image(image_data, file_extension)
        
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
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    批量OCR识别多张图片
    
    Args:
        files: 图片文件列表
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
        logger.info(f"批量OCR: 预处理用时 {(t1-t0):.3f}s, 共 {len(images_data)} 张")
        # 批量OCR识别
        ocr_result = await ocr_service.extract_text_from_images(images_data, image_formats)
        t2 = time.monotonic()
        logger.info(f"批量OCR: 模型用时 {(t2-t1):.3f}s, 总用时 {(t2-t0):.3f}s")
        logger.info(f"批量OCR识别完成: {len(files)} 张图片")
        
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
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取对话中的消息列表
    
    Args:
        conversation_id: 对话ID
        page: 页码
        size: 每页大小
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        List[MessageResponse]: 消息列表
    """
    try:
        # 验证对话是否存在
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
