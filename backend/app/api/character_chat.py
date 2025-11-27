"""
角色对话相关API路由
处理角色对话的创建、消息发送和卡片生成功能
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user_optional, get_client_info
from app.models.user import User
from app.models.ai_character import AICharacter
from app.models.character_conversation import CharacterConversation
from app.models.character_message import CharacterMessage
from app.models.analysis_card import AnalysisCard
from app.schemas.character import (
    CharacterConversationCreate,
    CharacterConversationResponse,
    CharacterConversationListResponse,
    CharacterMessageCreate,
    CharacterMessageResponse,
    CharacterChatResponse,
    GenerateCardFromChatRequest
)
from app.services.ai_service import ai_service
from loguru import logger
import httpx
import json
import asyncio
from app.config import settings

router = APIRouter(prefix="/api/character-chat", tags=["角色对话"])


@router.post("/conversations", response_model=CharacterConversationResponse)
async def create_character_conversation(
    conversation: CharacterConversationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    创建角色对话
    
    Args:
        conversation: 对话创建数据
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        CharacterConversationResponse: 创建的对话
    """
    try:
        # 验证角色是否存在
        character = db.query(AICharacter).filter(
            AICharacter.id == conversation.character_id,
            AICharacter.is_active == True
        ).first()
        
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )
        
        # 获取客户端信息
        ip_address, session_token = get_client_info(request)
        
        # 创建对话
        db_conversation = CharacterConversation(
            title=conversation.title or f"与{character.name}的对话",
            character_id=conversation.character_id,
            user_id=current_user.id if current_user else None,
            session_token=session_token if not current_user else None
        )
        
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        # 加载角色信息
        db.refresh(character)
        
        logger.info(f"创建角色对话: {db_conversation.id}, 角色: {character.name}")
        
        # 获取角色欢迎语
        from app.utils.character_greetings import get_character_greeting, get_default_greeting
        greeting = get_character_greeting(character.name)
        if not greeting:
            greeting = get_default_greeting(
                character.name,
                character.personality,
                character.speaking_style,
                character.description
            )
        
        # 将欢迎语作为第一条消息保存
        greeting_message = CharacterMessage(
            conversation_id=db_conversation.id,
            role="assistant",
            content=greeting
        )
        db.add(greeting_message)
        db_conversation.message_count = 1
        db.commit()
        db.refresh(greeting_message)
        
        response = CharacterConversationResponse.model_validate(db_conversation)
        response.character = character
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建角色对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建角色对话失败"
        )


@router.post("/conversations/stream")
async def create_character_conversation_stream(
    conversation: CharacterConversationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    创建角色对话并流式返回欢迎语
    """
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate_stream():
        try:
            from app.database import SessionLocal
            local_db = SessionLocal()
            try:
                # 验证角色是否存在
                character = local_db.query(AICharacter).filter(
                    AICharacter.id == conversation.character_id,
                    AICharacter.is_active == True
                ).first()
                
                if not character:
                    yield f"data: {json.dumps({'error': '角色不存在'})}\n\n"
                    return
                
                # 获取客户端信息
                ip_address, session_token = get_client_info(request)
                
                # 创建对话
                db_conversation = CharacterConversation(
                    title=conversation.title or f"与{character.name}的对话",
                    character_id=conversation.character_id,
                    user_id=current_user.id if current_user else None,
                    session_token=session_token if not current_user else None
                )
                
                local_db.add(db_conversation)
                local_db.commit()
                local_db.refresh(db_conversation)
                
                logger.info(f"创建角色对话: {db_conversation.id}, 角色: {character.name}")
                
                # 获取角色欢迎语
                from app.utils.character_greetings import get_character_greeting, get_default_greeting
                greeting = get_character_greeting(character.name)
                if not greeting:
                    greeting = get_default_greeting(
                        character.name,
                        character.personality,
                        character.speaking_style,
                        character.description
                    )
                
                # 流式返回欢迎语（模拟打字效果）
                words = list(greeting)
                accumulated = ""
                for i, char in enumerate(words):
                    accumulated += char
                    # 每2-3个字符发送一次，或者遇到标点符号时发送，使输出更流畅
                    if (i + 1) % 3 == 0 or char in ['。', '！', '？', '\n', '，', '、', '：', '；']:
                        yield f"data: {json.dumps({'greeting': accumulated, 'conversation_id': db_conversation.id, 'done': False})}\n\n"
                        await asyncio.sleep(0.03)  # 缩短延迟时间，使输出更流畅
                
                # 如果还有剩余内容未发送，发送完整的欢迎语
                if accumulated != greeting:
                    yield f"data: {json.dumps({'greeting': greeting, 'conversation_id': db_conversation.id, 'done': False})}\n\n"
                    await asyncio.sleep(0.03)
                
                # 发送完成标志
                yield f"data: {json.dumps({'greeting': greeting, 'conversation_id': db_conversation.id, 'done': True})}\n\n"
                
                # 将欢迎语作为第一条消息保存
                greeting_message = CharacterMessage(
                    conversation_id=db_conversation.id,
                    role="assistant",
                    content=greeting
                )
                local_db.add(greeting_message)
                db_conversation.message_count = 1
                local_db.commit()
                
            finally:
                local_db.close()
        except Exception as e:
            logger.error(f"创建角色对话流式返回失败: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    import asyncio
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/conversations", response_model=CharacterConversationListResponse)
async def get_character_conversations(
    request: Request,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取角色对话列表
    
    Args:
        request: FastAPI请求对象
        page: 页码
        size: 每页大小
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        CharacterConversationListResponse: 对话列表
    """
    try:
        ip_address, session_token = get_client_info(request)
        
        query = db.query(CharacterConversation)
        
        if current_user:
            query = query.filter(CharacterConversation.user_id == current_user.id)
        else:
            if session_token:
                from sqlalchemy import or_
                query = query.filter(
                    CharacterConversation.user_id.is_(None),
                    or_(
                        CharacterConversation.session_token == session_token,
                        CharacterConversation.session_token.is_(None)
                    )
                )
            else:
                query = query.filter(
                    CharacterConversation.user_id.is_(None),
                    CharacterConversation.session_token.is_(None)
                )
        
        # 使用子查询过滤掉没有用户消息的对话（只包含欢迎语的对话不应该出现在历史记录中）
        from sqlalchemy import exists
        subquery = db.query(CharacterMessage).filter(
            CharacterMessage.conversation_id == CharacterConversation.id,
            CharacterMessage.role == "user"
        ).exists()
        query = query.filter(subquery)
        
        # 计算总数（过滤后的）
        total = query.count()
        
        # 分页查询
        conversations = query.order_by(CharacterConversation.updated_at.desc()).offset((page - 1) * size).limit(size).all()
        
        # 加载角色信息
        for conv in conversations:
            db.refresh(conv.character)
        
        return CharacterConversationListResponse(
            conversations=[CharacterConversationResponse.model_validate(conv) for conv in conversations],
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"获取角色对话列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色对话列表失败"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_character_conversation(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    删除角色对话
    
    Args:
        conversation_id: 对话ID
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        dict: 删除结果
    """
    try:
        conversation = db.query(CharacterConversation).filter(
            CharacterConversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查权限
        ip_address, session_token = get_client_info(request)
        if current_user:
            if conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限删除此对话"
                )
        else:
            if conversation.user_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限删除此对话"
                )
            if conversation.session_token is not None and conversation.session_token != session_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限删除此对话"
                )
        
        # 删除对话及其所有消息
        db.query(CharacterMessage).filter(
            CharacterMessage.conversation_id == conversation_id
        ).delete()
        db.delete(conversation)
        db.commit()
        
        logger.info(f"删除角色对话: {conversation_id}")
        
        return {"message": "对话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除角色对话失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除对话失败"
        )


@router.post("/messages/stream")
async def send_character_message_stream(
    message_data: CharacterMessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    发送消息给角色（流式输出）
    """
    async def generate_stream():
        try:
            # 在生成器内部重新获取数据库会话，因为生成器可能在依赖注入的会话关闭后执行
            from app.database import SessionLocal
            local_db = SessionLocal()
            try:
                ip_address, session_token = get_client_info(request)
                
                # 如果对话ID为空，创建新对话
                if not message_data.conversation_id:
                    if not message_data.character_id:
                        yield f"data: {json.dumps({'error': '创建新对话需要提供角色ID'})}\n\n"
                        return
                    
                    # 验证角色是否存在
                    character = local_db.query(AICharacter).filter(
                        AICharacter.id == message_data.character_id,
                        AICharacter.is_active == True
                    ).first()
                    
                    if not character:
                        yield f"data: {json.dumps({'error': '角色不存在'})}\n\n"
                        return
                    
                    # 创建对话
                    conversation = CharacterConversation(
                        title=f"与{character.name}的对话",
                        character_id=message_data.character_id,
                        user_id=current_user.id if current_user else None,
                        session_token=session_token if not current_user else None,
                        message_count=0
                    )
                    local_db.add(conversation)
                    local_db.commit()
                    local_db.refresh(conversation)
                    
                    logger.info(f"自动创建角色对话: {conversation.id}, 角色: {character.name}")
                    
                    # 获取角色欢迎语并保存
                    from app.utils.character_greetings import get_character_greeting, get_default_greeting
                    greeting = get_character_greeting(character.name)
                    if not greeting:
                        greeting = get_default_greeting(
                            character.name,
                            character.personality,
                            character.speaking_style,
                            character.description
                        )
                    
                    greeting_message = CharacterMessage(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=greeting
                    )
                    local_db.add(greeting_message)
                    conversation.message_count = 1
                    local_db.commit()
                    
                    # 如果是新创建的对话，先发送欢迎语
                    yield f"data: {json.dumps({'greeting': greeting, 'done': False})}\n\n"
                else:
                    # 验证对话是否存在
                    conversation = local_db.query(CharacterConversation).filter(
                        CharacterConversation.id == message_data.conversation_id
                    ).first()
                    
                    if not conversation:
                        yield f"data: {json.dumps({'error': '对话不存在'})}\n\n"
                        return
                    
                    # 检查权限
                    if current_user:
                        if conversation.user_id != current_user.id:
                            yield f"data: {json.dumps({'error': '无权限访问此对话'})}\n\n"
                            return
                    else:
                        if conversation.user_id is not None:
                            yield f"data: {json.dumps({'error': '无权限访问此对话'})}\n\n"
                            return
                        if conversation.session_token is not None and conversation.session_token != session_token:
                            yield f"data: {json.dumps({'error': '无权限访问此对话'})}\n\n"
                            return
                    
                    # 获取角色信息
                    character = local_db.query(AICharacter).filter(AICharacter.id == conversation.character_id).first()
                
                # 保存用户消息
                user_message = CharacterMessage(
                    conversation_id=conversation.id,
                    role="user",
                    content=message_data.message
                )
                local_db.add(user_message)
                local_db.commit()
                
                # 获取对话历史（最近30条消息，确保多轮对话的上下文记忆）
                recent_messages = local_db.query(CharacterMessage).filter(
                    CharacterMessage.conversation_id == conversation.id
                ).order_by(CharacterMessage.created_at.asc()).all()
                
                # 如果消息太多，只取最近30条（保持上下文但控制token数量）
                if len(recent_messages) > 30:
                    recent_messages = recent_messages[-30:]
                
                # 构建对话上下文
                messages_for_ai = []
                for msg in recent_messages:
                    messages_for_ai.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                
                # 获取角色的增强System Prompt
                from app.utils.character_greetings import build_enhanced_system_prompt
                system_prompt = build_enhanced_system_prompt(character)
                
                # 调用AI服务生成回复（流式）
                from app.config import settings as app_settings
                async with httpx.AsyncClient(timeout=90.0) as client:
                    ai_messages = [
                        {"role": "system", "content": system_prompt}
                    ] + messages_for_ai
                    
                    full_content = ""
                    async with client.stream(
                        "POST",
                        f"{app_settings.deepseek_api_base}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {app_settings.deepseek_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": ai_messages,
                            "max_tokens": 2000,  # 增加token数量，让回复更详细
                            "temperature": 0.8,  # 提高temperature，让回复更有创意和角色特色
                            "stream": True,
                            # 如果启用搜索且API支持，添加搜索参数
                            **({"web_search": True} if app_settings.deepseek_enable_search else {})
                        }
                    ) as response:
                        response.raise_for_status()
                        
                        async for line in response.aiter_lines():
                            if not line.strip():
                                continue
                            
                            if line.startswith("data: "):
                                data_str = line[6:]  # 移除 "data: " 前缀
                                if data_str == "[DONE]":
                                    break
                                
                                try:
                                    data = json.loads(data_str)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            full_content += content
                                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                                except json.JSONDecodeError:
                                    continue
                    
                    # 保存AI回复
                    ai_message = CharacterMessage(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=full_content
                    )
                    local_db.add(ai_message)
                    conversation.message_count += 2
                    local_db.commit()
                    local_db.refresh(ai_message)
                    
                    # 发送完成信号，包含对话ID（如果是新创建的）
                    response_data = {
                        'content': '',
                        'done': True,
                        'message_id': ai_message.id,
                        'conversation_id': conversation.id
                    }
                    yield f"data: {json.dumps(response_data)}\n\n"
            finally:
                local_db.close()
                
        except Exception as e:
            logger.error(f"流式发送消息失败: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/messages", response_model=CharacterChatResponse)
async def send_character_message(
    message_data: CharacterMessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    发送消息给角色
    
    Args:
        message_data: 消息数据
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        CharacterChatResponse: 对话响应
    """
    try:
        ip_address, session_token = get_client_info(request)
        
        # 如果对话ID为空，创建新对话
        if not message_data.conversation_id:
            if not message_data.character_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="创建新对话需要提供角色ID"
                )
            
            # 验证角色是否存在
            character = db.query(AICharacter).filter(
                AICharacter.id == message_data.character_id,
                AICharacter.is_active == True
            ).first()
            
            if not character:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="角色不存在"
                )
            
            # 创建对话
            conversation = CharacterConversation(
                title=f"与{character.name}的对话",
                character_id=message_data.character_id,
                user_id=current_user.id if current_user else None,
                session_token=session_token if not current_user else None,
                message_count=0
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            logger.info(f"自动创建角色对话: {conversation.id}, 角色: {character.name}")
            
            # 获取角色欢迎语并保存
            from app.utils.character_greetings import get_character_greeting, get_default_greeting
            greeting = get_character_greeting(character.name)
            if not greeting:
                greeting = get_default_greeting(
                    character.name,
                    character.personality,
                    character.speaking_style,
                    character.description
                )
            
            greeting_message = CharacterMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=greeting
            )
            db.add(greeting_message)
            conversation.message_count = 1
            db.commit()
        else:
            # 验证对话是否存在
            conversation = db.query(CharacterConversation).filter(
                CharacterConversation.id == message_data.conversation_id
            ).first()
            
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="对话不存在"
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
                if conversation.session_token is not None and conversation.session_token != session_token:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权限访问此对话"
                    )
            
            # 获取角色信息
            character = db.query(AICharacter).filter(AICharacter.id == conversation.character_id).first()
        
        # 保存用户消息
        user_message = CharacterMessage(
            conversation_id=conversation.id,
            role="user",
            content=message_data.message
        )
        db.add(user_message)
        db.commit()
        
        # 获取对话历史（最近30条消息，确保多轮对话的上下文记忆）
        recent_messages = db.query(CharacterMessage).filter(
            CharacterMessage.conversation_id == conversation.id
        ).order_by(CharacterMessage.created_at.asc()).all()
        
        # 如果消息太多，只取最近30条（保持上下文但控制token数量）
        if len(recent_messages) > 30:
            recent_messages = recent_messages[-30:]
        
        # 构建对话上下文
        messages_for_ai = []
        for msg in recent_messages:
            messages_for_ai.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # 获取角色的增强System Prompt
        from app.utils.character_greetings import build_enhanced_system_prompt
        system_prompt = build_enhanced_system_prompt(character)
        
        # 调用AI服务生成回复
        from app.config import settings as app_settings
        async with httpx.AsyncClient(timeout=90.0) as client:
            ai_messages = [
                {"role": "system", "content": system_prompt}
            ] + messages_for_ai
            
            response = await client.post(
                f"{app_settings.deepseek_api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {app_settings.deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": ai_messages,
                    "max_tokens": 2000,  # 增加token数量，让回复更详细
                    "temperature": 0.8,  # 提高temperature，让回复更有创意和角色特色
                    # 如果启用搜索且API支持，添加搜索参数
                    **({"web_search": True} if app_settings.deepseek_enable_search else {})
                }
            )
            response.raise_for_status()
            result = response.json()
            ai_content = result["choices"][0]["message"]["content"]
        
        # 保存AI回复
        ai_message = CharacterMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=ai_content
        )
        db.add(ai_message)
        
        # 更新对话统计
        conversation.message_count += 2
        db.commit()
        db.refresh(ai_message)
        db.refresh(conversation)
        db.refresh(character)
        
        logger.info(f"角色对话消息: 对话{conversation.id}, 角色: {character.name}")
        
        return CharacterChatResponse(
            message=CharacterMessageResponse.model_validate(ai_message),
            conversation=CharacterConversationResponse.model_validate(conversation)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送角色消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送消息失败"
        )


@router.get("/conversations/{conversation_id}/messages", response_model=List[CharacterMessageResponse])
async def get_character_messages(
    conversation_id: int,
    request: Request,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取角色对话消息列表
    
    Args:
        conversation_id: 对话ID
        request: FastAPI请求对象
        page: 页码
        size: 每页大小
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        List[CharacterMessageResponse]: 消息列表
    """
    try:
        conversation = db.query(CharacterConversation).filter(
            CharacterConversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查权限
        ip_address, session_token = get_client_info(request)
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
            if conversation.session_token is not None and conversation.session_token != session_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话"
                )
        
        messages = db.query(CharacterMessage).filter(
            CharacterMessage.conversation_id == conversation_id
        ).order_by(CharacterMessage.created_at.asc()).offset((page - 1) * size).limit(size).all()
        
        return [CharacterMessageResponse.model_validate(msg) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色消息列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息列表失败"
        )


@router.post("/generate-card", response_model=dict)
async def generate_card_from_chat(
    card_request: GenerateCardFromChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    从角色对话生成分析卡片
    
    Args:
        card_request: 生成卡片请求
        request: FastAPI请求对象
        db: 数据库会话
        current_user: 当前用户（可选）
        
    Returns:
        dict: 生成的卡片信息
    """
    try:
        # 验证对话是否存在
        conversation = db.query(CharacterConversation).filter(
            CharacterConversation.id == card_request.conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 检查权限
        ip_address, session_token = get_client_info(request)
        if current_user:
            if conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限访问此对话"
                )
        
        # 获取所有消息
        messages = db.query(CharacterMessage).filter(
            CharacterMessage.conversation_id == conversation.id
        ).order_by(CharacterMessage.created_at.asc()).all()
        
        # 构建对话内容
        chat_content = "\n".join([f"{'用户' if msg.role == 'user' else conversation.character.name}: {msg.content}" for msg in messages])
        
        # 使用AI分析对话内容
        analysis_result = await ai_service.analyze_chat_content(
            chat_content=chat_content
        )
        
        # 生成回复建议
        suggestions = await ai_service.generate_response_suggestions(
            chat_content=chat_content,
            analysis_result=analysis_result
        )
        
        # 创建分析卡片
        from app.models.message import Message
        latest_user_message = messages[-1] if messages else None
        
        db_card = AnalysisCard(
            title=card_request.title or f"与{conversation.character.name}的对话分析",
            description=f"基于与{conversation.character.name}的对话生成的分析卡片",
            original_content=chat_content,
            analysis_data=analysis_result.model_dump(),
            response_suggestions=[suggestion.model_dump() for suggestion in suggestions],
            context_mode=None,
            user_id=current_user.id if current_user else None,
            conversation_id=None,  # 角色对话不关联普通对话
            conversation_time=latest_user_message.created_at if latest_user_message else None,
            session_token=session_token if not current_user else None
        )
        
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        
        logger.info(f"从角色对话生成卡片: {db_card.id}")
        
        # 返回完整的卡片数据
        return {
            "card_id": db_card.id,
            "message": "卡片生成成功",
            "card": {
                "id": db_card.id,
                "title": db_card.title,
                "description": db_card.description,
                "original_content": db_card.original_content,
                "analysis_data": db_card.analysis_data,
                "response_suggestions": db_card.response_suggestions,
                "context_mode": db_card.context_mode,
                "created_at": db_card.created_at.isoformat() if db_card.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成卡片失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成卡片失败"
        )

