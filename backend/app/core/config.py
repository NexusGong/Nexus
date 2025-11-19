"""
核心配置模块
集中管理环境变量与应用配置。
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """应用配置类（集中于 core 层）"""

    # 应用基础配置
    app_name: str = Field(default="聊天内容智能分析平台", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=True, description="调试模式")

    # 数据库配置
    database_url: str = Field(default="sqlite:///./nexus.db", description="数据库连接URL")
    sql_echo: bool = Field(default=False, description="是否打印SQL语句以便调试")

    # 安全配置
    secret_key: str = Field(description="JWT密钥")
    algorithm: str = Field(default="HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(default=10080, description="访问令牌过期时间(分钟)，默认7天")

    # DeepSeek API配置
    deepseek_api_key: str = Field(description="DeepSeek API密钥")
    deepseek_api_base: str = Field(default="https://api.deepseek.com", description="DeepSeek API基础URL")

    # 火山引擎OCR配置（通用文字识别服务）
    volc_access_key_id: str = Field(default="", description="火山引擎AccessKeyId")
    volc_secret_access_key: str = Field(default="", description="火山引擎SecretAccessKey")
    volc_region: str = Field(default="cn-north-1", description="火山引擎区域")
    volc_service: str = Field(default="cv", description="火山引擎服务名称")

    # 豆包API配置（用于OCR后处理，判断发言人位置）
    doubao_api_key: str = Field(description="豆包API密钥")
    doubao_api_url: str = Field(description="豆包API URL")
    doubao_model: str = Field(default="doubao-seed-1-6-vision-250815", description="豆包模型名称")

    # 文件上传配置
    max_file_size: int = Field(default=10485760, description="最大文件大小(字节)")  # 10MB
    allowed_extensions: str = Field(default="jpg,jpeg,png,gif,webp", description="允许的文件扩展名")

    # CORS配置
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173", description="CORS允许的源")

    # 次数限制配置 - 非登录用户
    guest_ocr_fast_limit: int = Field(default=5, description="非登录用户极速模式OCR次数限制")
    guest_ocr_quality_limit: int = Field(default=2, description="非登录用户性能模式OCR次数限制")
    guest_conversation_limit: int = Field(default=5, description="非登录用户最多会话数")
    guest_chat_analysis_limit: int = Field(default=10, description="非登录用户每个会话最多分析次数")

    # 次数限制配置 - 登录用户
    user_ocr_fast_limit: int = Field(default=10, description="登录用户极速模式OCR次数限制")
    user_ocr_quality_limit: int = Field(default=5, description="登录用户性能模式OCR次数限制")
    user_chat_analysis_limit: int = Field(default=50, description="登录用户每个会话最多分析次数")

    # 验证码配置
    verification_code_length: int = Field(default=6, description="验证码长度")
    verification_code_expire_minutes: int = Field(default=5, description="验证码过期时间(分钟)")
    verification_code_resend_interval: int = Field(default=60, description="验证码重发间隔(秒)")

    # 邮件配置（用于发送验证码）
    smtp_host: str = Field(default="", description="SMTP服务器地址")
    smtp_port: int = Field(default=587, description="SMTP服务器端口")
    smtp_user: str = Field(default="", description="SMTP用户名")
    smtp_password: str = Field(default="", description="SMTP密码")
    smtp_from_email: str = Field(default="", description="发送验证码的邮箱地址")

    def get_allowed_extensions(self) -> List[str]:
        """获取允许的文件扩展名列表"""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的源列表"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # pydantic-settings v2使用model_config
    # 确定.env文件的路径：优先使用backend目录下的.env，其次尝试项目根目录
    _env_file_path = None
    # 获取当前文件所在目录（app/core/），然后找backend目录
    _config_dir = Path(__file__).parent.parent.parent  # 从app/core/config.py -> app -> backend
    _backend_env = _config_dir / ".env"
    _root_env = _config_dir.parent / ".env"
    
    # 按优先级检查.env文件
    if _backend_env.exists():
        _env_file_path = str(_backend_env)
    elif _root_env.exists():
        _env_file_path = str(_root_env)
    else:
        _env_file_path = ".env"  # 回退到相对路径
    
    model_config = {
        "env_file": _env_file_path,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    @field_validator("doubao_api_key", mode="before")
    @classmethod
    def prefer_ark_api_key(cls, v: str) -> str:
        # 允许通过 ARK_API_KEY 注入（文档示例名称）
        return os.getenv("ARK_API_KEY") or v or ""
    
    @field_validator("volc_access_key_id", mode="before")
    @classmethod
    def load_volc_access_key_id(cls, v: str) -> str:
        # pydantic-settings会从.env文件读取，如果读取成功v会有值
        # 如果v为空，则尝试从环境变量读取（兼容直接从环境变量注入的情况）
        if v and v.strip():
            return v.strip()
        # 如果.env文件中没有，尝试从环境变量读取
        env_value = os.getenv("VOLC_ACCESS_KEY_ID") or os.getenv("VOLC_ACCESSKEY")
        return env_value.strip() if env_value else ""
    
    @field_validator("volc_secret_access_key", mode="before")
    @classmethod
    def load_volc_secret_access_key(cls, v: str) -> str:
        # pydantic-settings会从.env文件读取，如果读取成功v会有值
        if v and v.strip():
            return v.strip()
        # 如果.env文件中没有，尝试从环境变量读取
        env_value = os.getenv("VOLC_SECRET_ACCESS_KEY") or os.getenv("VOLC_SECRETKEY")
        return env_value.strip() if env_value else ""


# 全局配置实例（导出给外部使用）
settings = Settings()




