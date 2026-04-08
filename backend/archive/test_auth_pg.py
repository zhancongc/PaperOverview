"""
测试 Auth Kit 在 PostgreSQL 中的表创建
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_auth_postgresql():
    """测试 auth-kit 在 PostgreSQL 中创建表"""
    print("=" * 60)
    print("测试 Auth Kit PostgreSQL 表创建")
    print("=" * 60)

    # PostgreSQL 连接信息
    db_url = "postgresql://postgres:security@localhost/paper"
    print(f"\n数据库: {db_url}")

    try:
        from authkit.database import init_database
        from authkit.models import User
        from sqlalchemy import inspect

        # 初始化数据库（创建表）
        print("\n正在创建 users 表...")
        init_database(db_url)
        print("✓ 数据库初始化成功")

        # 检查表是否创建
        from authkit.database import engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"\n当前数据库中的表 ({len(tables)} 个):")
        for table in sorted(tables):
            print(f"  - {table}")

        if "users" in tables:
            print("\n✓ users 表已创建")

            # 显示表结构
            columns = inspector.get_columns("users")
            print("\nusers 表结构:")
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                default = f"DEFAULT {col['default']}" if col['default'] else ""
                print(f"  - {col['name']:20} {str(col['type']):20} {nullable} {default}")

            # 检查索引
            indexes = inspector.get_indexes("users")
            if indexes:
                print("\nusers 表索引:")
                for idx in indexes:
                    columns_str = ", ".join(idx['column_names'])
                    unique = "UNIQUE" if idx['unique'] else ""
                    print(f"  - {idx['name']}: ({columns_str}) {unique}")

            return True
        else:
            print("\n✗ users 表未找到")
            print("请检查数据库权限或表名冲突")
            return False

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n提示: 请确保 PostgreSQL 服务正在运行")
    print("启动命令: brew services start postgresql\n")

    success = test_auth_postgresql()

    print("\n" + "=" * 60)
    if success:
        print("✓ 用户表创建成功！现在可以使用登录功能了")
        print("\n下一步:")
        print("  1. 配置 .env.auth 文件（邮件服务）")
        print("  2. 启动后端: python main.py")
        print("  3. 访问: http://localhost:3000/login")
    else:
        print("✗ 请检查错误信息并重试")
    print("=" * 60)
