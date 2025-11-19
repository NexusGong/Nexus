"""
数据库更新脚本
用于更新数据库表结构（删除旧表并重新创建）
"""

from app.database import drop_tables, create_tables
from loguru import logger

if __name__ == "__main__":
    logger.info("开始更新数据库...")
    try:
        # 删除所有表
        logger.info("删除现有表...")
        drop_tables()
        
        # 重新创建所有表
        logger.info("创建新表...")
        create_tables()
        
        logger.info("✅ 数据库更新完成！")
        logger.info("现在可以重新启动后端服务，AI角色将自动初始化")
    except Exception as e:
        logger.error(f"❌ 数据库更新失败: {e}")
        raise

