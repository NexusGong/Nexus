"""
核心配置模块
集中管理环境变量与应用配置。
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os


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
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间(分钟)")

    # DeepSeek API配置
    deepseek_api_key: str = Field(description="DeepSeek API密钥")
    deepseek_api_base: str = Field(default="https://api.deepseek.com", description="DeepSeek API基础URL")

    # 豆包API配置
    doubao_api_key: str = Field(description="豆包API密钥")
    doubao_api_url: str = Field(description="豆包API URL")
    doubao_model: str = Field(default="doubao-seed-1-6-vision-250815", description="豆包模型名称")

    # 可选的OCR提供方与火山引擎配置（用于兼容 .env 中的额外字段）
    ocr_provider: str | None = Field(default=None, description="OCR提供方标识，可选")
    volc_access_key: str | None = Field(default=None, description="火山引擎AK，可选")
    volc_secret_key: str | None = Field(default=None, description="火山引擎SK，可选")
    volc_region: str | None = Field(default=None, description="火山引擎Region，可选")

    # 文件上传配置
    max_file_size: int = Field(default=10485760, description="最大文件大小(字节)")  # 10MB
    allowed_extensions: str = Field(default="jpg,jpeg,png,gif,webp", description="允许的文件扩展名")

    # CORS配置
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173", description="CORS允许的源")

    def get_allowed_extensions(self) -> List[str]:
        """获取允许的文件扩展名列表"""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的源列表"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("doubao_api_key", mode="before")
    @classmethod
    def prefer_ark_api_key(cls, v: str) -> str:
        # 允许通过 ARK_API_KEY 注入（文档示例名称）
        return os.getenv("ARK_API_KEY") or v


# 全局配置实例（导出给外部使用）
settings = Settings()


