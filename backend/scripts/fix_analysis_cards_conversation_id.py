"""
修复 analysis_cards 表的 conversation_id 字段
将 conversation_id 从 NOT NULL 改为允许 NULL
"""

import sqlite3
import os
from pathlib import Path
from loguru import logger

def fix_analysis_cards_conversation_id():
    """修复 analysis_cards 表的 conversation_id 字段约束"""
    
    # 获取数据库路径
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "nexus.db"
    
    if not db_path.exists():
        logger.warning(f"数据库文件不存在: {db_path}")
        return
    
    logger.info(f"开始修复数据库: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # SQLite 不支持直接修改列约束，需要重建表
        # 1. 创建新表（conversation_id 允许 NULL）
        logger.info("创建新表...")
        cursor.execute("""
            CREATE TABLE analysis_cards_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                conversation_id INTEGER,
                session_token VARCHAR(255),
                title VARCHAR(200) NOT NULL,
                description TEXT,
                original_content TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                response_suggestions TEXT,
                context_mode VARCHAR(50),
                analysis_focus TEXT,
                card_template VARCHAR(50) DEFAULT 'default',
                is_favorite BOOLEAN DEFAULT 0,
                is_public BOOLEAN DEFAULT 0,
                tags TEXT,
                export_count INTEGER DEFAULT 0,
                last_exported_at DATETIME,
                conversation_time DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # 2. 复制数据
        logger.info("复制数据...")
        cursor.execute("""
            INSERT INTO analysis_cards_new 
            SELECT * FROM analysis_cards
        """)
        
        # 3. 删除旧表
        logger.info("删除旧表...")
        cursor.execute("DROP TABLE analysis_cards")
        
        # 4. 重命名新表
        logger.info("重命名新表...")
        cursor.execute("ALTER TABLE analysis_cards_new RENAME TO analysis_cards")
        
        # 5. 重新创建索引
        logger.info("重新创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_analysis_cards_id ON analysis_cards(id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_analysis_cards_session_token ON analysis_cards(session_token)")
        
        conn.commit()
        logger.info("✅ 数据库修复完成！")
        
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            logger.info("analysis_cards 表不存在，跳过修复（将在首次使用时自动创建）")
        else:
            logger.error(f"修复失败: {e}")
            conn.rollback()
            raise
    except Exception as e:
        logger.error(f"修复失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_analysis_cards_conversation_id()

