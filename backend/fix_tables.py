#!/usr/bin/env python
"""修复数据库表结构"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, create_tables
from app.models import AICharacter, CharacterConversation, CharacterMessage  # 确保模型被导入
from sqlalchemy import text, inspect
from loguru import logger

logger.info("开始修复表结构...")

with engine.begin() as conn:
    # 按顺序删除表（考虑外键关系）
    logger.info("删除旧表...")
    conn.execute(text('DROP TABLE IF EXISTS character_messages'))
    conn.execute(text('DROP TABLE IF EXISTS character_conversations'))
    conn.execute(text('DROP TABLE IF EXISTS ai_characters'))
    logger.info("旧表已删除")

# 重新创建所有表
logger.info("重新创建表...")
create_tables()

# 验证
inspector = inspect(engine)
if 'ai_characters' in inspector.get_table_names():
    columns = [col['name'] for col in inspector.get_columns('ai_characters')]
    logger.info(f"✅ ai_characters 表已创建，包含列: {sorted(columns)}")
    
    required = ['id', 'name', 'avatar_url', 'personality', 'speaking_style', 'system_prompt', 'category', 'rarity', 'is_active']
    missing = [col for col in required if col not in columns]
    if missing:
        logger.error(f"❌ 缺少列: {missing}")
    else:
        logger.info("✅ 所有必需的列都存在")
else:
    logger.error("❌ 表创建失败")

