"""
修复 review_records 表的 ID 序列
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# 数据库配置
db_type = os.getenv("DB_TYPE", "postgresql")
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "security")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "paper")

database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

print(f"连接数据库: {db_host}:{db_port}/{db_name}")

# 创建引擎
engine = create_engine(database_url)

with engine.connect() as conn:
    # 检查当前最大ID
    result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM review_records"))
    max_id = result.scalar()
    print(f"当前 review_records 表最大 ID: {max_id}")
    
    # 检查序列当前值
    result = conn.execute(text("SELECT last_value FROM review_records_id_seq"))
    seq_value = result.scalar()
    print(f"序列当前值: {seq_value}")
    
    # 如果序列值小于最大ID，需要重置序列
    if seq_value <= max_id:
        new_value = max_id + 1
        print(f"重置序列从 {seq_value} 到 {new_value}")
        conn.execute(text(f"ALTER SEQUENCE review_records_id_seq RESTART WITH {new_value}"))
        conn.commit()
        print("✅ 序列已修复")
    else:
        print("✅ 序列正常，无需修复")
    
    # 检查是否有ID冲突的记录
    result = conn.execute(text("SELECT id, topic, created_at FROM review_records ORDER BY id"))
    records = result.fetchall()
    print(f"\n现有记录 ({len(records)} 条):")
    for record in records:
        print(f"  ID={record[0]}: {record[1][:40]}... (创建时间: {record[2]})")

