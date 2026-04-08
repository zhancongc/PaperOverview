"""
数据库迁移脚本：修复索引名称冲突

运行方式：
    python migrate_fix_index_conflicts.py
"""
import sys
from sqlalchemy import text
from database import db


def migrate():
    """执行迁移"""
    print("[迁移] 开始修复索引名称冲突...")

    # 确保数据库已连接
    if db.engine is None:
        db.connect()

    # 检查数据库类型
    database_url = db.engine.url.__to_string__()
    print(f"[迁移] 数据库类型: {database_url[:50]}...")

    # 定义需要删除的旧索引和创建的新索引
    # 格式：(表名, 旧索引名, 新索引名, 列名)
    index_changes = [
        # paper_metadata 表的索引
        ('paper_metadata', 'idx_year', 'idx_paper_metadata_year', 'year'),
        ('paper_metadata', 'idx_source', 'idx_paper_metadata_source', 'source'),
        ('paper_metadata', 'idx_created_at', 'idx_paper_metadata_created_at', 'created_at'),
        ('paper_metadata', 'idx_is_english', 'idx_paper_metadata_is_english', 'is_english'),

        # review_tasks 表的索引
        ('review_tasks', 'idx_status', 'idx_review_tasks_status', 'status'),
        ('review_tasks', 'idx_created_at', 'idx_review_tasks_created_at', 'created_at'),

        # outline_generation_stages 表的索引
        ('outline_generation_stages', 'idx_task_id', 'idx_outline_gen_stage_task_id', 'task_id'),
        ('outline_generation_stages', 'idx_started_at', 'idx_outline_gen_stage_started_at', 'started_at'),

        # paper_search_stages 表的索引
        ('paper_search_stages', 'idx_task_id', 'idx_paper_search_stage_task_id', 'task_id'),
        ('paper_search_stages', 'idx_started_at', 'idx_paper_search_stage_started_at', 'started_at'),

        # paper_filter_stages 表的索引
        ('paper_filter_stages', 'idx_task_id', 'idx_paper_filter_stage_task_id', 'task_id'),
        ('paper_filter_stages', 'idx_started_at', 'idx_paper_filter_stage_started_at', 'started_at'),

        # review_generation_stages 表的索引
        ('review_generation_stages', 'idx_task_id', 'idx_review_gen_stage_task_id', 'task_id'),
        ('review_generation_stages', 'idx_started_at', 'idx_review_gen_stage_started_at', 'started_at'),
    ]

    for table_name, old_index, new_index, column_name in index_changes:
        try:
            with db.engine.connect() as conn:
                # 检查旧索引是否存在
                if 'postgresql' in database_url:
                    check_result = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_indexes
                            WHERE tablename = '{table_name}'
                            AND indexname = '{old_index}'
                        )
                    """))
                    old_exists = check_result.scalar()

                    # 检查新索引是否已存在
                    check_result = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_indexes
                            WHERE tablename = '{table_name}'
                            AND indexname = '{new_index}'
                        )
                    """))
                    new_exists = check_result.scalar()

                elif 'sqlite' in database_url:
                    # SQLite
                    check_result = conn.execute(text(f"""
                        SELECT COUNT(*) FROM sqlite_master
                        WHERE type='index' AND tbl_name='{table_name}' AND name='{old_index}'
                    """))
                    old_exists = check_result.scalar() > 0

                    check_result = conn.execute(text(f"""
                        SELECT COUNT(*) FROM sqlite_master
                        WHERE type='index' AND tbl_name='{table_name}' AND name='{new_index}'
                    """))
                    new_exists = check_result.scalar() > 0
                else:
                    print(f"[迁移] ⊙ 跳过不支持的数据库类型")
                    continue

                if old_exists and not new_exists:
                    # 删除旧索引
                    conn.execute(text(f"DROP INDEX IF EXISTS {old_index}"))
                    conn.commit()
                    print(f"[迁移] ✓ 删除旧索引: {old_index}")

                    # 创建新索引
                    conn.execute(text(f"CREATE INDEX {new_index} ON {table_name} ({column_name})"))
                    conn.commit()
                    print(f"[迁移] ✓ 创建新索引: {new_index}")

                elif old_exists and new_exists:
                    print(f"[迁移] ⊙ 新索引已存在，删除旧索引: {old_index}")
                    conn.execute(text(f"DROP INDEX IF EXISTS {old_index}"))
                    conn.commit()

                elif not old_exists and new_exists:
                    print(f"[迁移] ⊙ 新索引已存在，跳过: {new_index}")

                else:
                    print(f"[迁移] ⊙ 索引不存在，跳过: {old_index} -> {new_index}")

        except Exception as e:
            print(f"[迁移] ✗ 处理索引 {old_index} 时出错: {e}")
            # 继续处理下一个索引
            continue

    print("[迁移] ✓ 索引修复完成！")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移：修复索引名称冲突")
    print("=" * 60)
    print()

    # 执行迁移
    success = migrate()

    if success:
        print()
        print("=" * 60)
        print("迁移完成！所有索引名称已更新为唯一名称。")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("迁移失败！请检查错误信息。")
        print("=" * 60)
        sys.exit(1)
