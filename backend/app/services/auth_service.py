"""
认证服务模块
负责验证码发送、验证、用户注册和登录
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from loguru import logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

from app.models.user import User
from app.models.verification_code import VerificationCode
from app.core.config import settings
from jose import jwt


def is_email(contact: str) -> bool:
    """判断是否为邮箱"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, contact))


def is_phone(contact: str) -> bool:
    """判断是否为手机号"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, contact))


def generate_verification_code(length: int = 6) -> str:
    """生成数字验证码"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


async def send_email_verification_code(contact: str, code: str) -> bool:
    """发送邮箱验证码"""
    try:
        if not settings.smtp_host or not settings.smtp_user:
            logger.warning("SMTP配置未设置，无法发送邮件验证码")
            # 开发模式下直接返回成功
            if settings.debug:
                logger.info(f"[开发模式] 验证码: {code} (发送到: {contact})")
                return True
            return False
        
        msg = MIMEMultipart()
        msg['From'] = settings.smtp_from_email or settings.smtp_user
        msg['To'] = contact
        msg['Subject'] = "验证码"
        
        body = f"""
        您的验证码是：{code}
        
        验证码有效期为 {settings.verification_code_expire_minutes} 分钟。
        请勿将验证码告知他人。
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"验证码已发送到邮箱: {contact}")
        return True
    except Exception as e:
        logger.error(f"发送邮件验证码失败: {e}")
        return False


async def send_phone_verification_code(contact: str, code: str) -> bool:
    """发送手机验证码（需要集成第三方短信服务）"""
    # TODO: 集成第三方短信服务（如阿里云、腾讯云等）
    logger.warning(f"手机验证码发送功能未实现，验证码: {code} (发送到: {contact})")
    # 开发模式下直接返回成功
    if settings.debug:
        logger.info(f"[开发模式] 验证码: {code} (发送到: {contact})")
        return True
    return False


async def send_verification_code(contact: str, code_type: str, db: Session) -> bool:
    """
    发送验证码
    
    Args:
        contact: 联系方式（邮箱或手机号）
        code_type: 验证码类型（register/login）
        db: 数据库会话
        
    Returns:
        bool: 是否发送成功
    """
    try:
        # 验证联系方式格式
        if not is_email(contact) and not is_phone(contact):
            logger.error(f"无效的联系方式: {contact}")
            return False
        
        # 检查是否在重发间隔内
        recent_code = db.query(VerificationCode).filter(
            VerificationCode.contact == contact,
            VerificationCode.code_type == code_type,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.utcnow()
        ).order_by(VerificationCode.created_at.desc()).first()
        
        if recent_code:
            time_diff = (datetime.utcnow() - recent_code.created_at).total_seconds()
            if time_diff < settings.verification_code_resend_interval:
                remaining = int(settings.verification_code_resend_interval - time_diff)
                logger.warning(f"验证码发送过于频繁，请 {remaining} 秒后再试")
                return False
        
        # 生成验证码
        code = generate_verification_code(settings.verification_code_length)
        
        # 计算过期时间
        expires_at = datetime.utcnow() + timedelta(minutes=settings.verification_code_expire_minutes)
        
        # 保存验证码到数据库
        verification_code = VerificationCode(
            contact=contact,
            code=code,
            code_type=code_type,
            expires_at=expires_at
        )
        db.add(verification_code)
        db.commit()
        
        # 发送验证码
        if is_email(contact):
            success = await send_email_verification_code(contact, code)
        else:
            success = await send_phone_verification_code(contact, code)
        
        if not success:
            # 如果发送失败，标记验证码为已使用
            verification_code.is_used = True
            db.commit()
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        db.rollback()
        return False


def verify_code(contact: str, code: str, code_type: str, db: Session) -> bool:
    """
    验证验证码
    
    Args:
        contact: 联系方式
        code: 验证码
        code_type: 验证码类型
        db: 数据库会话
        
    Returns:
        bool: 验证是否成功
    """
    try:
        # 先查询所有匹配的验证码（用于调试）
        all_codes = db.query(VerificationCode).filter(
            VerificationCode.contact == contact,
            VerificationCode.code_type == code_type
        ).order_by(VerificationCode.created_at.desc()).all()
        
        logger.info(f"验证码验证: contact={contact}, code={code}, code_type={code_type}, 找到 {len(all_codes)} 条记录")
        for vc in all_codes[:3]:  # 只显示最近3条
            logger.info(f"  验证码: {vc.code}, is_used={vc.is_used}, expires_at={vc.expires_at}, created_at={vc.created_at}")
        
        verification_code = db.query(VerificationCode).filter(
            VerificationCode.contact == contact,
            VerificationCode.code == code,
            VerificationCode.code_type == code_type,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.utcnow()
        ).order_by(VerificationCode.created_at.desc()).first()
        
        if not verification_code:
            logger.warning(f"验证码验证失败: contact={contact}, code={code}, code_type={code_type}, 未找到有效验证码")
            return False
        
        # 标记验证码为已使用
        verification_code.is_used = True
        db.commit()
        
        logger.info(f"验证码验证成功: contact={contact}, code={code}")
        return True
    except Exception as e:
        logger.error(f"验证验证码失败: {e}")
        db.rollback()
        return False


def get_user_by_contact(contact: str, db: Session) -> Optional[User]:
    """根据邮箱或手机号获取用户"""
    if is_email(contact):
        return db.query(User).filter(User.email == contact).first()
    elif is_phone(contact):
        return db.query(User).filter(User.phone == contact).first()
    return None


def register_user(contact: str, code: str, username: str, db: Session) -> Optional[User]:
    """
    注册用户
    
    Args:
        contact: 联系方式（邮箱或手机号）
        code: 验证码
        username: 用户名
        db: 数据库会话
        
    Returns:
        User: 注册的用户对象，失败返回None
    """
    try:
        # 验证验证码
        if not verify_code(contact, code, "register", db):
            logger.error("验证码验证失败")
            return None
        
        # 检查用户名是否已存在
        if db.query(User).filter(User.username == username).first():
            logger.error(f"用户名已存在: {username}")
            return None
        
        # 检查联系方式是否已注册
        existing_user = get_user_by_contact(contact, db)
        if existing_user:
            logger.error(f"该联系方式已注册: {contact}")
            return None
        
        # 创建新用户
        user_data = {
            "username": username,
            "is_verified": True
        }
        
        if is_email(contact):
            user_data["email"] = contact
        else:
            user_data["phone"] = contact
        
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"用户注册成功: {username} ({contact})")
        return user
        
    except Exception as e:
        logger.error(f"注册用户失败: {e}")
        db.rollback()
        return None


def login_user(contact: str, code: str, db: Session) -> Optional[User]:
    """
    登录用户
    
    Args:
        contact: 联系方式（邮箱或手机号）
        code: 验证码
        db: 数据库会话
        
    Returns:
        User: 登录的用户对象，失败返回None
    """
    try:
        # 验证验证码
        if not verify_code(contact, code, "login", db):
            logger.error("验证码验证失败")
            return None
        
        # 获取用户
        user = get_user_by_contact(contact, db)
        if not user:
            logger.error(f"用户不存在: {contact}")
            return None
        
        if not user.is_active:
            logger.error(f"用户已被禁用: {contact}")
            return None
        
        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        logger.info(f"用户登录成功: {user.username} ({contact})")
        return user
        
    except Exception as e:
        logger.error(f"登录用户失败: {e}")
        return None


def generate_jwt_token(user: User) -> str:
    """
    生成JWT token
    
    Args:
        user: 用户对象
        
    Returns:
        str: JWT token
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),  # JWT的sub字段必须是字符串
        "username": user.username,
        "exp": expire
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token

