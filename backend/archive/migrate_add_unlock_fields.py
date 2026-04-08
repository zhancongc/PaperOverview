"""
数据库迁移：添加解锁相关字段到 subscriptions 表
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from database import db

def migrate():
    """执行迁移"""
    print("开始数据库迁移：添加解锁相关字段...")

    # 确保数据库已连接
    if db.engine is None:
        db.connect()

    with db.engine.connect() as conn:
        # 需要添加的字段列表
        fields_to_add = [
            ('record_id', 'INTEGER'),
            ('extra_data', 'TEXT'),
        ]

        for column_name, column_def in fields_to_add:
            # 检查字段是否已存在
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'subscriptions'
                AND column_name = :column_name
            """), {"column_name": column_name})
            exists = result.fetchone()

            if exists:
                print(f"字段 {column_name} 已存在，跳过")
                continue

            # 添加字段
            print(f"添加字段 {column_name}...")
            conn.execute(text(f"""
                ALTER TABLE subscriptions
                ADD COLUMN {column_name} {column_def}
            """))
            conn.commit()

        # 添加索引
        index_name = 'idx_subscriptions_record_id'
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'subscriptions'
            AND indexname = :index_name
        """), {"index_name": index_name})
        exists = result.fetchone()

        if not exists:
            print(f"添加索引 {index_name}...")
            conn.execute(text(f"""
                CREATE INDEX {index_name} ON subscriptions (record_id)
            """))
            conn.commit()
        else:
            print(f"索引 {index_name} 已存在，跳过")

        print("迁移完成！")

if __name__ == "__main__":
    migrate()
