"""
辅助工具函数
提供各种通用的辅助功能
"""

import hashlib
import secrets
from typing import Any, Dict, Optional
from datetime import datetime, timezone


def generate_random_string(length: int = 32) -> str:
    """
    生成随机字符串
    
    Args:
        length: 字符串长度
        
    Returns:
        str: 随机字符串
    """
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    
    Args:
        password: 原始密码
        
    Returns:
        str: 哈希后的密码
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        password: 原始密码
        hashed_password: 哈希后的密码
        
    Returns:
        bool: 验证结果
    """
    return hash_password(password) == hashed_password


def get_current_timestamp() -> datetime:
    """
    获取当前时间戳
    
    Returns:
        datetime: 当前时间
    """
    return datetime.now(timezone.utc)


def format_timestamp(timestamp: datetime) -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: 时间戳
        
    Returns:
        str: 格式化后的时间字符串
    """
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    安全获取字典值
    
    Args:
        data: 字典数据
        key: 键名
        default: 默认值
        
    Returns:
        Any: 获取到的值或默认值
    """
    return data.get(key, default) if isinstance(data, dict) else default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_file_type(filename: str, allowed_extensions: list) -> bool:
    """
    验证文件类型
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表
        
    Returns:
        bool: 验证结果
    """
    if not filename:
        return False
    
    extension = filename.lower().split('.')[-1]
    return extension in [ext.lower() for ext in allowed_extensions]


def validate_file_size(file_size: int, max_size: int) -> bool:
    """
    验证文件大小
    
    Args:
        file_size: 文件大小（字节）
        max_size: 最大大小（字节）
        
    Returns:
        bool: 验证结果
    """
    return file_size <= max_size


def clean_text(text: str) -> str:
    """
    清理文本内容
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = " ".join(text.split())
    
    # 移除特殊字符（保留中文、英文、数字、基本标点）
    import re
    text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()（）【】""''""''，。！？；：]', '', text)
    
    return text.strip()


def extract_keywords(text: str, max_keywords: int = 5) -> list:
    """
    提取关键词
    
    Args:
        text: 文本内容
        max_keywords: 最大关键词数量
        
    Returns:
        list: 关键词列表
    """
    if not text:
        return []
    
    # 简单的关键词提取（实际项目中可以使用更复杂的NLP算法）
    import re
    
    # 移除标点符号，分割单词
    words = re.findall(r'\b\w+\b', text.lower())
    
    # 过滤停用词
    stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    # 统计词频
    word_count = {}
    for word in words:
        if word not in stop_words and len(word) > 1:
            word_count[word] = word_count.get(word, 0) + 1
    
    # 按频率排序，返回前N个关键词
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]

