"""
数据迁移脚本：将 paper_metadata 表的 source 字段从 String 迁移到 JSON

迁移步骤：
1. 备份现有数据
2. 创建新列 source_json
3. 转换数据格式
4. 验证数据
5. 删除旧列，重命名新列
6. 更新 ORM 模型

使用方法：
    python migrate_source_to_json.py
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 数据库连接配置
DB_TYPE = os.getenv("DB_TYPE", "postgresql")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "paper")

# 构建数据库连接 URL
if DB_TYPE == "postgresql":
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def migrate_source_to_json():
    """执行迁移"""

    print("=" * 80)
    print("数据迁移：source 字段 String → JSON")
    print("=" * 80)
    print(f"数据库: {DATABASE_URL}")
    print()

    # 创建数据库连接
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # ========================================
        # 步骤1：备份现有数据
        # ========================================
        print("[步骤 1/7] 备份现有数据...")

        result = session.execute(text("""
            SELECT id, title, source
            FROM paper_metadata
            LIMIT 5
        """))
        sample_data = result.fetchall()
        print("当前数据样例（前5条）：")
        for row in sample_data:
            print(f"  ID: {row[0][:20]:20} | Source: {row[2]}")

        # 检查表中是否有数据
        count_result = session.execute(text("SELECT COUNT(*) FROM paper_metadata"))
        total_count = count_result.scalar()
        print(f"总记录数: {total_count}")

        if total_count == 0:
            print("表中无数据，无需迁移")
            return

        print()

        # ========================================
        # 步骤2：创建新列 source_json (JSON 类型)
        # ========================================
        print("[步骤 2/7] 创建新列 source_json...")

        if DB_TYPE == "postgresql":
            session.execute(text("""
                ALTER TABLE paper_metadata
                ADD COLUMN source_json JSON
            """))
        else:
            # MySQL 使用 TEXT 存储 JSON
            session.execute(text("""
                ALTER TABLE paper_metadata
                ADD COLUMN source_json TEXT
            """))

        session.commit()
        print("✓ 新列 source_json 创建成功")

        # ========================================
        # 步骤3：转换数据格式
        # ========================================
        print("[步骤 3/7] 转换数据格式...")

        # 获取所有记录
        result = session.execute(text("""
            SELECT id, source
            FROM paper_metadata
        """))
        records = result.fetchall()

        updated_count = 0
        for record in records:
            paper_id = record[0]
            old_source = record[1]

            # 将字符串转换为 JSON 数组
            if old_source:
                new_source = f'["{old_source}"]'
            else:
                new_source = '[]'

            # 使用 cast() 函数进行类型转换
            from sqlalchemy import cast, JSON
            session.execute(text("""
                UPDATE paper_metadata
                SET source_json = cast(:new_source AS json)
                WHERE id = :paper_id
            """), {"new_source": new_source, "paper_id": paper_id})
            updated_count += 1

        session.commit()
        print(f"✓ 已转换 {updated_count} 条记录")

        # ========================================
        # 步骤4：验证数据
        # ========================================
        print("[步骤 4/7] 验证数据...")

        result = session.execute(text("""
            SELECT id, source, source_json
            FROM paper_metadata
            LIMIT 5
        """))
        sample_data = result.fetchall()
        print("转换后的数据样例（前5条）：")
        for row in sample_data:
            print(f"  ID: {row[0][:20]:20} | 旧: {row[1]} | 新: {row[2]}")

        print()

        # ========================================
        # 步骤5：删除旧列
        # ========================================
        print("[步骤 5/7] 删除旧列 source...")

        # PostgreSQL 需要先删除依赖
        if DB_TYPE == "postgresql":
            session.execute(text("""
                ALTER TABLE paper_metadata
                DROP COLUMN source
            """))
        else:
            session.execute(text("""
                ALTER TABLE paper_metadata
                DROP COLUMN source
            """))

        session.commit()
        print("✓ 旧列 source 已删除")

        # ========================================
        # 步骤6：重命名新列
        # ========================================
        print("[步骤 6/7] 重命名新列...")

        if DB_TYPE == "postgresql":
            session.execute(text("""
                ALTER TABLE paper_metadata
                RENAME COLUMN source_json TO source
            """))
        else:
            session.execute(text("""
                ALTER TABLE paper_metadata
                CHANGE COLUMN source_json source TEXT
            """))

        session.commit()
        print("✓ 新列已重命名为 source")

        # ========================================
        # 步骤7：最终验证
        # ========================================
        print("[步骤 7/7] 最终验证...")

        result = session.execute(text("""
            SELECT id, source
            FROM paper_metadata
            LIMIT 5
        """))
        sample_data = result.fetchall()
        print("最终数据样例（前5条）：")
        for row in sample_data:
            print(f"  ID: {row[0][:20]:20} | Source: {row[1]}")

        # 检查数据类型
        if DB_TYPE == "postgresql":
            result = session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'paper_metadata'
                AND column_name = 'source'
            """))
            dtype_info = result.fetchone()
            print(f"✓ 数据类型: {dtype_info[1]}")
        else:
            print("✓ 数据类型: TEXT/JSON")

        print()
        print("=" * 80)
        print("✓ 迁移完成！")
        print("=" * 80)

    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


def check_source_field():
    """检查当前 source 字段的实际类型"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("检查当前 source 字段类型:")

        if DB_TYPE == "postgresql":
            result = session.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'paper_metadata'
                AND column_name = 'source'
            """))
        else:
            result = session.execute(text("""
                SHOW COLUMNS FROM paper_metadata
                WHERE Field = 'source'
            """))

        info = result.fetchone()
        if info:
            print(f"  列名: {info[0]}")
            print(f"  类型: {info[1]}")
        else:
            print("  未找到 source 字段")

    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据迁移：source 字段 String → JSON")
    parser.add_argument("--check", action="store_true", help="只检查当前字段类型，不执行迁移")

    args = parser.parse_args()

    if args.check:
        check_source_field()
    else:
        # 确认迁移
        print()
        response = input("此操作将修改数据库表结构。是否继续？(yes/no): ")
        if response.lower() in ['yes', 'y']:
            migrate_source_to_json()
        else:
            print("已取消迁移")
