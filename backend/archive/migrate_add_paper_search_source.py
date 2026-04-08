"""
添加 paper_search_sources 表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect, DDL
from database import db
from models import PaperSearchSource

def migrate():
    """执行数据库迁移"""
    db.connect()
    engine = db.engine
    inspector = inspect(engine)

    # 检查表是否存在
    if 'paper_search_sources' in inspector.get_table_names():
        print("[迁移] 表 paper_search_sources 已存在，跳过")
        return

    print("[迁移] 开始创建 paper_search_sources 表...")

    # 创建表
    PaperSearchSource.metadata.create_all(bind=engine)

    print("[迁移] ✓ 完成")

if __name__ == '__main__':
    migrate()
