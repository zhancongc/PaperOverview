"""
数据库迁移：删除 users 表中未使用的 is_staff 字段
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from database import db

def migrate():
    """执行迁移"""
    print("开始数据库迁移：删除 is_staff 字段...")

    # 确保数据库已连接
    if db.engine is None:
        db.connect()

    with db.engine.connect() as conn:
        # 检查字段是否存在
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND column_name = 'is_staff'
        """))
        exists = result.fetchone()

        if not exists:
            print("字段 is_staff 不存在，跳过")
            return

        # 删除字段
        print("删除字段 is_staff...")
        conn.execute(text("""
            ALTER TABLE users
            DROP COLUMN IF EXISTS is_staff
        """))
        conn.commit()

        print("迁移完成！")

if __name__ == "__main__":
    migrate()
