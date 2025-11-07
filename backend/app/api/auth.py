"""
认证相关API路由
处理用户注册、登录、验证码发送等功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.api.deps import get_current_user_optional, get_current_user, get_client_info
from app.models.user import User
from app.schemas.auth import (
    SendCodeRequest, SendCodeResponse,
    RegisterRequest, LoginRequest,
    AuthResponse, UserResponse, UsageStatsResponse,
    UpdateProfileRequest
)
from app.services.auth_service import (
    send_verification_code, register_user, login_user, generate_jwt_token
)
from app.services.usage_limit_service import get_usage_stats

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(
    request_data: SendCodeRequest,
    db: Session = Depends(get_db)
):
    """
    发送验证码
    
    Args:
        request_data: 发送验证码请求数据
        db: 数据库会话
        
    Returns:
        SendCodeResponse: 发送结果
    """
    try:
        success = await send_verification_code(
            contact=request_data.contact,
            code_type=request_data.code_type,
            db=db
        )
        
        if success:
            return SendCodeResponse(
                success=True,
                message="验证码已发送",
                resend_interval=60
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码发送失败，请检查联系方式是否正确"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证码失败"
        )


@router.post("/register", response_model=AuthResponse)
async def register(
    request_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    Args:
        request_data: 注册请求数据
        db: 数据库会话
        
    Returns:
        AuthResponse: 认证响应（包含token和用户信息）
    """
    try:
        user = register_user(
            contact=request_data.contact,
            code=request_data.code,
            username=request_data.username,
            db=db
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="注册失败，请检查验证码或联系方式是否已注册"
            )
        
        # 生成JWT token
        token = generate_jwt_token(user)
        
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    Args:
        request_data: 登录请求数据
        request: FastAPI请求对象
        db: 数据库会话
        
    Returns:
        AuthResponse: 认证响应（包含token和用户信息）
    """
    try:
        user = login_user(
            contact=request_data.contact,
            code=request_data.code,
            db=db
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="登录失败，请检查验证码或联系方式"
            )
        
        # 获取客户端信息（用于关联未登录时创建的对话和卡片）
        ip_address, session_token = get_client_info(request)
        
        # 将未登录时创建的对话和卡片关联到当前用户
        try:
            from app.models.conversation import Conversation
            from app.models.analysis_card import AnalysisCard
            
            conversations_to_link = []
            cards_to_link = []
            
            # 关联当前 session_token 的对话和卡片，以及历史数据（session_token 为 NULL）
            if session_token:
                # 关联对话：将 user_id 为 NULL 且 session_token 匹配的对话关联到用户
                conversations_to_link = db.query(Conversation).filter(
                    Conversation.user_id.is_(None),
                    Conversation.session_token == session_token
                ).all()
                
                # 关联卡片：将 user_id 为 NULL 且 session_token 匹配的卡片关联到用户
                cards_to_link = db.query(AnalysisCard).filter(
                    AnalysisCard.user_id.is_(None),
                    AnalysisCard.session_token == session_token
                ).all()
            else:
                # 如果没有 session_token，关联历史数据（user_id 为 NULL 且 session_token 为 NULL）
                # 注意：这会将所有历史数据关联到当前用户，但这是合理的，因为无法区分
                conversations_to_link = db.query(Conversation).filter(
                    Conversation.user_id.is_(None),
                    Conversation.session_token.is_(None)
                ).all()
                
                cards_to_link = db.query(AnalysisCard).filter(
                    AnalysisCard.user_id.is_(None),
                    AnalysisCard.session_token.is_(None)
                ).all()
            
            # 更新对话和卡片的 user_id
            for conversation in conversations_to_link:
                conversation.user_id = user.id
                conversation.session_token = None  # 清除 session_token，因为已经关联到用户
            
            for card in cards_to_link:
                card.user_id = user.id
                card.session_token = None  # 清除 session_token，因为已经关联到用户
            
            if conversations_to_link or cards_to_link:
                db.commit()
                logger.info(f"用户登录时关联了 {len(conversations_to_link)} 个对话和 {len(cards_to_link)} 个卡片到用户 {user.id}")
        except Exception as e:
            logger.error(f"关联对话和卡片失败: {e}")
            # 不影响登录流程，继续执行
            db.rollback()
        
        # 生成JWT token
        token = generate_jwt_token(user)
        
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    获取当前用户信息
    
    Args:
        current_user: 当前用户（可选）
        db: 数据库会话
        
    Returns:
        UserResponse: 用户信息
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录"
        )
    
    return UserResponse.model_validate(current_user)


@router.get("/usage-stats", response_model=UsageStatsResponse)
async def get_usage_statistics(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    获取使用统计
    
    Args:
        request: FastAPI请求对象
        current_user: 当前用户（可选）
        db: 数据库会话
        
    Returns:
        UsageStatsResponse: 使用统计信息
    """
    try:
        ip_address, session_token = get_client_info(request)
        
        stats = get_usage_stats(
            user=current_user,
            ip=ip_address,
            session_token=session_token,
            db=db
        )
        
        return UsageStatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取使用统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取使用统计失败"
        )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户资料
    
    Args:
        request_data: 更新资料请求数据
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        UserResponse: 更新后的用户信息
    """
    try:
        # 更新用户名
        if request_data.username is not None:
            # 检查用户名是否已被其他用户使用
            existing_user = db.query(User).filter(
                User.username == request_data.username,
                User.id != current_user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已被使用"
                )
            current_user.username = request_data.username
        
        # 更新头像
        if request_data.avatar_url is not None:
            current_user.avatar_url = request_data.avatar_url
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"用户资料已更新: {current_user.id}")
        
        return UserResponse.model_validate(current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户资料失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户资料失败"
        )

