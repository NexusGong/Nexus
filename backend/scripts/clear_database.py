"""
清空数据库中的所有记录
保留表结构，只删除数据
"""

import sys
from pathlib import Path

# 添加backend目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import (
    User,
    Conversation,
    Message,
    AnalysisCard,
    UsageRecord,
    VerificationCode,
    AICharacter,
    CharacterConversation,
    CharacterMessage
)
from app.utils.init_characters import init_characters
from loguru import logger

def clear_all_data():
    """清空所有表的数据"""
    db = SessionLocal()
    try:
        logger.info("开始清空数据库...")
        
        # 按依赖关系顺序删除（先删除子表，再删除父表）
        # 1. 删除消息相关
        deleted_messages = db.query(Message).delete()
        logger.info(f"删除了 {deleted_messages} 条消息记录")
        
        deleted_character_messages = db.query(CharacterMessage).delete()
        logger.info(f"删除了 {deleted_character_messages} 条角色消息记录")
        
        # 2. 删除对话相关
        deleted_conversations = db.query(Conversation).delete()
        logger.info(f"删除了 {deleted_conversations} 条对话记录")
        
        deleted_character_conversations = db.query(CharacterConversation).delete()
        logger.info(f"删除了 {deleted_character_conversations} 条角色对话记录")
        
        # 3. 删除卡片
        deleted_cards = db.query(AnalysisCard).delete()
        logger.info(f"删除了 {deleted_cards} 条分析卡片记录")
        
        # 4. 删除使用记录
        deleted_usage = db.query(UsageRecord).delete()
        logger.info(f"删除了 {deleted_usage} 条使用记录")
        
        # 5. 删除验证码
        deleted_codes = db.query(VerificationCode).delete()
        logger.info(f"删除了 {deleted_codes} 条验证码记录")
        
        # 6. 删除AI角色（会重新初始化）
        deleted_characters = db.query(AICharacter).delete()
        logger.info(f"删除了 {deleted_characters} 个AI角色")
        
        # 7. 删除用户（最后删除）
        deleted_users = db.query(User).delete()
        logger.info(f"删除了 {deleted_users} 个用户")
        
        # 提交更改
        db.commit()
        logger.info("✅ 数据库清空完成")
        
        # 重新初始化AI角色
        logger.info("重新初始化AI角色...")
        init_characters()
        logger.info("✅ AI角色初始化完成")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 清空数据库失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_data()

