"""
创建数据库和表的初始化脚本
"""
import pymysql
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

def create_database():
    """创建 paper 数据库"""
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "security")
    )

    try:
        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DB_NAME', 'paper')} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 '{os.getenv('DB_NAME', 'paper')}' 创建成功或已存在")
    finally:
        connection.close()


def create_tables():
    """创建数据表"""
    from database import db
    from models import Base

    try:
        db.connect()
        Base.metadata.create_all(bind=db.engine)
        print("数据表创建成功")
    except Exception as e:
        print(f"创建数据表失败: {e}")


if __name__ == "__main__":
    print("正在创建数据库...")
    create_database()
    print("\n正在创建数据表...")
    create_tables()
    print("\n初始化完成！")
