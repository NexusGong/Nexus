"""
API依赖注入模块
提供FastAPI路由中常用的依赖项
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.database import get_db
from app.config import settings
from app.models.user import User

# HTTP Bearer认证
security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    获取当前用户依赖
    从JWT token中解析用户信息
    
    Args:
        db: 数据库会话
        credentials: HTTP认证凭据
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 认证失败时抛出异常
    """
    from loguru import logger
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 检查是否有认证凭据
    if not credentials:
        logger.warning("未提供认证凭据")
        raise credentials_exception
    
    try:
        # 解码JWT token
        payload = jwt.decode(
            credentials.credentials, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        user_id_str = payload.get("sub")
        if user_id_str is None:
            logger.warning("JWT token中缺少用户ID")
            raise credentials_exception
        # JWT的sub字段是字符串，需要转换为整数
        try:
            user_id: int = int(user_id_str)
        except (ValueError, TypeError):
            logger.warning(f"JWT token中的用户ID格式无效: {user_id_str}")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT token验证失败: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"JWT token解码异常: {e}")
        raise credentials_exception
    
    # 从数据库获取用户
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning(f"用户不存在: {user_id}")
        raise credentials_exception
    
    return user


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    获取当前用户依赖（可选）
    如果token无效或不存在，返回None而不是抛出异常
    
    Args:
        db: 数据库会话
        credentials: HTTP认证凭据（可选）
        
    Returns:
        Optional[User]: 当前用户对象或None
    """
    from loguru import logger
    
    if not credentials:
        logger.debug("未提供认证凭据（可选认证）")
        return None
    
    try:
        # 解码JWT token
        token_str = credentials.credentials
        logger.debug(f"尝试验证JWT token: {token_str[:20]}...（可选认证）")
        
        payload = jwt.decode(
            token_str, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        user_id_str = payload.get("sub")
        if user_id_str is None:
            logger.warning("JWT token中缺少用户ID（可选认证）")
            return None
        
        # JWT的sub字段是字符串，需要转换为整数
        try:
            user_id: int = int(user_id_str)
        except (ValueError, TypeError):
            logger.warning(f"JWT token中的用户ID格式无效: {user_id_str}（可选认证）")
            return None
        
        # 从数据库获取用户
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            logger.warning(f"用户不存在: {user_id}（可选认证）")
            return None
        
        logger.debug(f"JWT token验证成功，用户ID: {user_id}（可选认证）")
        return user
    except JWTError as e:
        # token过期或无效是可选认证的预期情况
        # 对于token过期，记录info级别日志
        # 对于其他JWT错误，记录warning级别日志用于调试
        error_msg = str(e).lower()
        if "expired" in error_msg:
            logger.info(f"JWT token已过期（可选认证）: {e}")
        else:
            logger.warning(f"JWT token验证失败（可选认证）: {e}")
        return None
    except Exception as e:
        # 其他异常使用warning级别，因为可能是意外的错误
        logger.warning(f"JWT token解码异常（可选认证）: {e}")
        return None


def get_client_info(request: Request) -> tuple[str, str]:
    """
    获取客户端信息（IP地址和session token）
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        tuple[str, str]: (IP地址, session_token)
    """
    # 获取IP地址
    ip_address = request.client.host if request.client else "unknown"
    
    # 尝试从请求头获取真实IP（如果经过代理）
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    
    # 从请求头获取session token（前端通过X-Session-Token传递）
    session_token = request.headers.get("X-Session-Token", "")
    
    return ip_address, session_token
