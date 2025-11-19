"""
修复 ai_characters 表结构
删除旧表并重新创建
"""

from app.database import engine, create_tables
from sqlalchemy import text, inspect
from loguru import logger

if __name__ == "__main__":
    logger.info("开始修复 ai_characters 表...")
    try:
        # 检查表是否存在
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'ai_characters' in tables:
            logger.info("删除旧的 ai_characters 表...")
            with engine.connect() as conn:
                conn.execute(text('DROP TABLE IF EXISTS ai_characters'))
                conn.execute(text('DROP TABLE IF EXISTS character_conversations'))
                conn.execute(text('DROP TABLE IF EXISTS character_messages'))
                conn.commit()
            logger.info("旧表已删除")
        
        # 重新创建所有表
        logger.info("重新创建表...")
        create_tables()
        
        # 验证表结构
        inspector = inspect(engine)
        if 'ai_characters' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('ai_characters')]
            logger.info(f"✅ ai_characters 表已创建，包含列: {sorted(columns)}")
            
            # 检查必需的列
            required_columns = ['id', 'name', 'avatar_url', 'personality', 'speaking_style', 'system_prompt', 'category', 'rarity', 'is_active']
            missing = [col for col in required_columns if col not in columns]
            if missing:
                logger.error(f"❌ 缺少必需的列: {missing}")
            else:
                logger.info("✅ 所有必需的列都存在")
        else:
            logger.error("❌ 表创建失败")
            
    except Exception as e:
        logger.error(f"❌ 修复失败: {e}")
        raise

