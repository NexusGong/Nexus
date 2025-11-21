"""
重置所有用户的角色购买记录
清除所有用户的角色解锁记录，恢复到初始状态
"""

import sys
from pathlib import Path

# 添加backend目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import UserCharacter
from loguru import logger

def reset_user_characters():
    """清除所有用户的角色购买记录"""
    db = SessionLocal()
    try:
        logger.info("开始清除所有用户的角色购买记录...")
        
        # 删除所有用户角色关联记录（包括已购买和未购买的）
        deleted_count = db.query(UserCharacter).delete()
        logger.info(f"删除了 {deleted_count} 条用户角色关联记录")
        
        # 提交更改
        db.commit()
        logger.info("✅ 所有用户的角色购买记录已清除，已恢复到初始状态")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 清除用户角色记录失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    reset_user_characters()

