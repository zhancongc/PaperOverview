"""
数据库迁移脚本：为 review_generation_stages 表添加 review 和 papers_summary 字段

运行方式：
    python migrate_add_review_to_stage.py
"""
import sys
from sqlalchemy import text
from database import db


def migrate():
    """执行迁移"""
    print("[迁移] 开始为 review_generation_stages 表添加字段...")

    # 确保数据库已连接
    if db.engine is None:
        db.connect()

    # 检查数据库类型
    database_url = db.engine.url.__to_string__()
    print(f"[迁移] 数据库类型: {database_url[:50]}...")

    # 检查表是否存在
    try:
        with db.engine.connect() as conn:
            if 'postgresql' in database_url:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'review_generation_stages'
                    )
                """))
                table_exists = result.scalar()
            else:
                # SQLite
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM sqlite_master
                    WHERE type='table' AND name='review_generation_stages'
                """))
                table_exists = result.scalar() > 0

            if not table_exists:
                print("[迁移] ⊙ 表 review_generation_stages 不存在，将使用模型定义自动创建")
                print("[迁移] 提示：下次启动应用时会自动创建包含新字段的表")
                return True
    except Exception as e:
        print(f"[迁移] ✗ 检查表是否存在时出错: {e}")
        return False

    if 'postgresql' in database_url or 'sqlite' in database_url:
        # PostgreSQL 或 SQLite
        print("[迁移] 检测到 PostgreSQL 或 SQLite 数据库")

        sql_statements = [
            # 添加 review 字段
            "ALTER TABLE review_generation_stages ADD COLUMN IF NOT EXISTS review TEXT;",
            # 添加 papers_summary 字段
            "ALTER TABLE review_generation_stages ADD COLUMN IF NOT EXISTS papers_summary JSON;"
        ]

        for i, sql in enumerate(sql_statements, 1):
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                print(f"[迁移] ✓ 执行成功: 语句 {i}")
            except Exception as e:
                # 如果字段已存在，忽略错误
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"[迁移] ⊙ 字段已存在，跳过: 语句 {i}")
                else:
                    print(f"[迁移] ✗ 执行失败: 语句 {i}")
                    print(f"[迁移] 错误: {e}")
                    return False

    elif 'mysql' in database_url:
        # MySQL
        print("[迁移] 检测到 MySQL 数据库")

        sql_statements = [
            # 添加 review 字段
            """
            ALTER TABLE review_generation_stages
            ADD COLUMN review TEXT NULL COMMENT '综述内容（Markdown格式，用于版本对比）';
            """,
            # 添加 papers_summary 字段
            """
            ALTER TABLE review_generation_stages
            ADD COLUMN papers_summary JSON NULL COMMENT '引用文献摘要（包含id、title、authors等核心字段）';
            """
        ]

        for i, sql in enumerate(sql_statements, 1):
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                print(f"[迁移] ✓ 执行成功: 语句 {i}")
            except Exception as e:
                # 如果字段已存在，忽略错误
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"[迁移] ⊙ 字段已存在，跳过: 语句 {i}")
                else:
                    print(f"[迁移] ✗ 执行失败: 语句 {i}")
                    print(f"[迁移] 错误: {e}")
                    return False
    else:
        print(f"[迁移] ✗ 不支持的数据库类型: {database_url}")
        return False

    print("[迁移] ✓ 迁移完成！")
    return True


def verify():
    """验证迁移结果"""
    print("\n[验证] 检查字段是否添加成功...")

    try:
        with db.engine.connect() as conn:
            # 查询表结构
            if 'postgresql' in db.engine.url.__to_string():
                result = conn.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'review_generation_stages'
                    AND column_name IN ('review', 'papers_summary')
                """)
            elif 'sqlite' in db.engine.url.__to_string():
                result = conn.execute("""
                    PRAGMA table_info(review_generation_stages)
                """)
            else:
                # MySQL
                result = conn.execute("""
                    SHOW COLUMNS FROM review_generation_stages
                    WHERE Field IN ('review', 'papers_summary')
                """)

            rows = result.fetchall()
            if rows:
                print(f"[验证] ✓ 找到 {len(rows)} 个新字段:")
                for row in rows:
                    print(f"  - {row}")
                return True
            else:
                print("[验证] ✗ 未找到新字段")
                return False

    except Exception as e:
        print(f"[验证] ✗ 验证失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移：为 review_generation_stages 添加字段")
    print("=" * 60)
    print()

    # 执行迁移
    success = migrate()

    if success:
        # 验证结果
        verify()
        print()
        print("=" * 60)
        print("迁移完成！现在 review_generation_stages 表包含：")
        print("  - review: 综述内容（用于版本对比）")
        print("  - papers_summary: 引用文献摘要")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("迁移失败！请检查错误信息。")
        print("=" * 60)
        sys.exit(1)
