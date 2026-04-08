"""
添加候选文献池摘要字段到 review_generation_stages 表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, inspect
from models import Base, ReviewGenerationStage
from database import db

def migrate():
    """执行数据库迁移"""
    # 使用项目的数据库连接
    db.connect()
    engine = db.engine
    inspector = inspect(engine)

    # 检查表是否存在
    if 'review_generation_stages' not in inspector.get_table_names():
        print("[迁移] 表 review_generation_stages 不存在，跳过")
        return

    # 检查列是否存在
    columns = [col['name'] for col in inspector.get_columns('review_generation_stages')]

    if 'candidate_pool_summary' in columns:
        print("[迁移] 字段 candidate_pool_summary 已存在，跳过")
        return

    print("[迁移] 开始添加 candidate_pool_summary 字段...")

    # 添加新列
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE review_generation_stages
            ADD COLUMN candidate_pool_summary JSONB
        """))
        conn.commit()

    print("[迁移] ✓ 完成")

if __name__ == '__main__':
    migrate()
