"""
测试认证数据库初始化
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_auth_init():
    """测试 auth-kit 数据库初始化"""
    print("=" * 50)
    print("测试 Auth Kit 数据库初始化")
    print("=" * 50)

    # 导入 auth-kit
    try:
        from authkit.database import init_database
        from authkit.models import User, Base
        print("✓ 导入 auth-kit 成功")
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

    # 初始化数据库
    auth_db_path = "./auth.db"
    auth_db_url = f"sqlite:///{auth_db_path}"

    try:
        print(f"\n正在初始化数据库: {auth_db_url}")
        init_database(auth_db_url)
        print("✓ 数据库初始化成功")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 检查文件是否创建
    if os.path.exists(auth_db_path):
        print(f"✓ 数据库文件已创建: {auth_db_path}")
        file_size = os.path.getsize(auth_db_path)
        print(f"  文件大小: {file_size} bytes")
    else:
        print(f"✗ 数据库文件未创建: {auth_db_path}")
        return False

    # 验证表结构
    try:
        from sqlalchemy import inspect
        from authkit.database import engine

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"\n数据库中的表:")
        for table in tables:
            print(f"  - {table}")

        if "users" in tables:
            print("\n✓ users 表已创建")

            # 显示表结构
            columns = inspector.get_columns("users")
            print("\nusers 表结构:")
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                default = f"DEFAULT {col['default']}" if col['default'] else ""
                print(f"  - {col['name']}: {col['type']} {nullable} {default}")

            return True
        else:
            print("\n✗ users 表未找到")
            return False

    except Exception as e:
        print(f"\n✗ 检查表结构失败: {e}")
        return False


if __name__ == "__main__":
    success = test_auth_init()

    print("\n" + "=" * 50)
    if success:
        print("✓ 所有测试通过！用户表已创建")
    else:
        print("✗ 测试失败，请检查错误信息")
    print("=" * 50)
