"""
次数限制服务模块
负责检查和使用次数限制
"""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from loguru import logger

from app.models.user import User
from app.models.conversation import Conversation
from app.models.usage_record import UsageRecord
from app.core.config import settings


def get_ocr_limit(user: Optional[User], mode: str) -> int:
    """获取OCR次数限制"""
    if user:
        if mode == "fast":
            return settings.user_ocr_fast_limit
        else:
            return settings.user_ocr_quality_limit
    else:
        if mode == "fast":
            return settings.guest_ocr_fast_limit
        else:
            return settings.guest_ocr_quality_limit


def get_ocr_usage_count(user: Optional[User], mode: str, ip: str, session_token: str, db: Session) -> int:
    """获取OCR已使用次数"""
    usage_type = "ocr_fast" if mode == "fast" else "ocr_quality"
    
    # 计算今天开始的时间
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(func.count(UsageRecord.id)).filter(
        UsageRecord.usage_type == usage_type,
        UsageRecord.created_at >= today_start
    )
    
    if user:
        query = query.filter(UsageRecord.user_id == user.id)
    else:
        # 非登录用户：按IP和session_token统计
        query = query.filter(
            and_(
                UsageRecord.user_id.is_(None),
                UsageRecord.ip_address == ip,
                UsageRecord.session_token == session_token
            )
        )
    
    return query.scalar() or 0


def check_ocr_limit(user: Optional[User], mode: str, ip: str, session_token: str, db: Session) -> tuple[bool, int, int]:
    """
    检查OCR使用次数限制
    
    Args:
        user: 用户对象（可选）
        mode: OCR模式（fast/quality）
        ip: IP地址
        session_token: 会话token
        db: 数据库会话
        
    Returns:
        tuple[bool, int, int]: (是否可用, 已使用次数, 总限制次数)
    """
    limit = get_ocr_limit(user, mode)
    used = get_ocr_usage_count(user, mode, ip, session_token, db)
    
    return used < limit, used, limit


def record_ocr_usage(user: Optional[User], mode: str, ip: str, session_token: str, db: Session) -> bool:
    """
    记录OCR使用
    
    Args:
        user: 用户对象（可选）
        mode: OCR模式
        ip: IP地址
        session_token: 会话token
        db: 数据库会话
        
    Returns:
        bool: 是否记录成功
    """
    try:
        usage_type = "ocr_fast" if mode == "fast" else "ocr_quality"
        
        usage_record = UsageRecord(
            user_id=user.id if user else None,
            session_token=session_token if not user else None,
            ip_address=ip,
            usage_type=usage_type
        )
        
        db.add(usage_record)
        db.commit()
        
        return True
    except Exception as e:
        logger.error(f"记录OCR使用失败: {e}")
        db.rollback()
        return False


def get_conversation_count(user: Optional[User], ip: str, session_token: str, db: Session) -> int:
    """获取会话数量"""
    query = db.query(func.count(Conversation.id)).filter(
        Conversation.is_active == "active"
    )
    
    if user:
        query = query.filter(Conversation.user_id == user.id)
    else:
        # 非登录用户：按 session_token 统计
        # 如果 session_token 为空，则只统计 session_token 为 NULL 的会话（历史数据）
        if session_token:
            query = query.filter(
                Conversation.user_id.is_(None),
                Conversation.session_token == session_token
            )
        else:
            # session_token 为空时，只统计 session_token 为 NULL 的会话
            query = query.filter(
                Conversation.user_id.is_(None),
                Conversation.session_token.is_(None)
            )
    
    return query.scalar() or 0


def check_conversation_limit(user: Optional[User], ip: str, session_token: str, db: Session) -> tuple[bool, int, int]:
    """
    检查会话创建限制
    
    Args:
        user: 用户对象（可选）
        ip: IP地址
        session_token: 会话token
        db: 数据库会话
        
    Returns:
        tuple[bool, int, int]: (是否可用, 已创建会话数, 总限制数)
    """
    if user:
        # 登录用户无限制
        return True, 0, 0
    
    # 非登录用户限制
    limit = settings.guest_conversation_limit
    count = get_conversation_count(user, ip, session_token, db)
    
    return count < limit, count, limit


def get_chat_analysis_count(user: Optional[User], conversation_id: int, ip: str, session_token: str, db: Session) -> int:
    """获取聊天分析已使用次数"""
    # 计算今天开始的时间
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(func.count(UsageRecord.id)).filter(
        UsageRecord.usage_type == "chat_analysis",
        UsageRecord.conversation_id == conversation_id,
        UsageRecord.created_at >= today_start
    )
    
    if user:
        query = query.filter(UsageRecord.user_id == user.id)
    else:
        query = query.filter(
            and_(
                UsageRecord.user_id.is_(None),
                UsageRecord.ip_address == ip,
                UsageRecord.session_token == session_token
            )
        )
    
    return query.scalar() or 0


def get_chat_analysis_limit(user: Optional[User]) -> int:
    """获取聊天分析次数限制"""
    if user:
        return settings.user_chat_analysis_limit
    else:
        return settings.guest_chat_analysis_limit


def check_chat_analysis_limit(user: Optional[User], conversation_id: int, ip: str, session_token: str, db: Session) -> tuple[bool, int, int]:
    """
    检查聊天分析次数限制
    
    Args:
        user: 用户对象（可选）
        conversation_id: 会话ID
        ip: IP地址
        session_token: 会话token
        db: 数据库会话
        
    Returns:
        tuple[bool, int, int]: (是否可用, 已使用次数, 总限制次数)
    """
    limit = get_chat_analysis_limit(user)
    used = get_chat_analysis_count(user, conversation_id, ip, session_token, db)
    
    return used < limit, used, limit


def record_chat_analysis_usage(user: Optional[User], conversation_id: int, ip: str, session_token: str, db: Session) -> bool:
    """
    记录聊天分析使用
    
    Args:
        user: 用户对象（可选）
        conversation_id: 会话ID
        ip: IP地址
        session_token: 会话token
        db: 数据库会话
        
    Returns:
        bool: 是否记录成功
    """
    try:
        usage_record = UsageRecord(
            user_id=user.id if user else None,
            session_token=session_token if not user else None,
            ip_address=ip,
            usage_type="chat_analysis",
            conversation_id=conversation_id
        )
        
        db.add(usage_record)
        db.commit()
        
        return True
    except Exception as e:
        logger.error(f"记录聊天分析使用失败: {e}")
        db.rollback()
        return False


def get_chat_analysis_total_count(user: Optional[User], ip: str, session_token: str, db: Session) -> int:
    """获取聊天分析总使用次数（所有会话）"""
    # 计算今天开始的时间
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(func.count(UsageRecord.id)).filter(
        UsageRecord.usage_type == "chat_analysis",
        UsageRecord.created_at >= today_start
    )
    
    if user:
        query = query.filter(UsageRecord.user_id == user.id)
    else:
        query = query.filter(
            and_(
                UsageRecord.user_id.is_(None),
                UsageRecord.ip_address == ip,
                UsageRecord.session_token == session_token
            )
        )
    
    return query.scalar() or 0


def get_usage_stats(user: Optional[User], ip: str, session_token: str, db: Session) -> dict:
    """
    获取使用统计
    
    Args:
        user: 用户对象（可选）
        ip: IP地址
        session_token: 会话token
        db: 数据库会话
        
    Returns:
        dict: 使用统计信息
    """
    # 计算今天开始的时间
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # OCR统计
    ocr_fast_used, ocr_fast_limit = get_ocr_usage_count(user, "fast", ip, session_token, db), get_ocr_limit(user, "fast")
    ocr_quality_used, ocr_quality_limit = get_ocr_usage_count(user, "quality", ip, session_token, db), get_ocr_limit(user, "quality")
    
    # 会话统计
    conversation_count, conversation_limit = get_conversation_count(user, ip, session_token, db), (
        0 if user else settings.guest_conversation_limit
    )
    
    # 聊天分析统计（所有会话的总和）
    chat_analysis_used = get_chat_analysis_total_count(user, ip, session_token, db)
    chat_analysis_limit = get_chat_analysis_limit(user)
    
    return {
        "ocr_fast": {
            "used": ocr_fast_used,
            "limit": ocr_fast_limit,
            "remaining": max(0, ocr_fast_limit - ocr_fast_used)
        },
        "ocr_quality": {
            "used": ocr_quality_used,
            "limit": ocr_quality_limit,
            "remaining": max(0, ocr_quality_limit - ocr_quality_used)
        },
        "conversation": {
            "count": conversation_count,
            "limit": conversation_limit,
            "remaining": max(0, conversation_limit - conversation_count) if conversation_limit > 0 else -1
        },
        "chat_analysis": {
            "used": chat_analysis_used,
            "limit": chat_analysis_limit,
            "remaining": max(0, chat_analysis_limit - chat_analysis_used)
        }
    }

