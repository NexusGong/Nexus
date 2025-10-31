"""
应用配置管理模块（适配层）
保留历史导入路径 `app.config`，实际实现迁移到 `app.core.config`。
"""

from app.core.config import Settings, settings  # 兼容旧导入路径
