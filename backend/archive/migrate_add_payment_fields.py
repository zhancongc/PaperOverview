"""
数据库迁移：添加支付关联字段到 review_records 表
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from database import db

def migrate():
    """执行迁移"""
    print("开始数据库迁移：添加支付关联字段...")

    # 确保数据库已连接
    if db.engine is None:
        db.connect()

    with db.engine.connect() as conn:
        # 需要添加的字段列表
        fields_to_add = [
            ('is_paid', 'BOOLEAN DEFAULT FALSE'),
            ('user_id', 'INTEGER'),
            ('subscription_id', 'INTEGER'),
            ('order_no', 'VARCHAR(64)'),
        ]

        for column_name, column_def in fields_to_add:
            # 检查字段是否已存在
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'review_records'
                AND column_name = :column_name
            """), {"column_name": column_name})
            exists = result.fetchone()

            if exists:
                print(f"字段 {column_name} 已存在，跳过")
                continue

            # 添加字段
            print(f"添加字段 {column_name}...")
            conn.execute(text(f"""
                ALTER TABLE review_records
                ADD COLUMN {column_name} {column_def}
            """))
            conn.commit()

        # 添加索引
        indexes_to_add = [
            ('idx_review_records_user_id', 'user_id'),
            ('idx_review_records_subscription_id', 'subscription_id'),
            ('idx_review_records_order_no', 'order_no'),
        ]

        for index_name, column_name in indexes_to_add:
            # 检查索引是否已存在
            result = conn.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'review_records'
                AND indexname = :index_name
            """), {"index_name": index_name})
            exists = result.fetchone()

            if exists:
                print(f"索引 {index_name} 已存在，跳过")
                continue

            # 添加索引
            print(f"添加索引 {index_name}...")
            conn.execute(text(f"""
                CREATE INDEX {index_name} ON review_records ({column_name})
            """))
            conn.commit()

        print("迁移完成！")

if __name__ == "__main__":
    migrate()
