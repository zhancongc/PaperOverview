"""
调试并彻底修复序列问题
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# 数据库配置
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "security")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "paper")

database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

print(f"连接数据库: {db_host}:{db_port}/{db_name}")

engine = create_engine(database_url)

with engine.connect() as conn:
    # 1. 检查当前最大ID
    result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM review_records"))
    max_id = result.scalar()
    print(f"当前最大ID: {max_id}")
    
    # 2. 检查序列当前值
    result = conn.execute(text("SELECT last_value FROM review_records_id_seq"))
    last_value = result.scalar()
    print(f"序列last_value: {last_value}")
    
    # 3. 测试下一个值
    result = conn.execute(text("SELECT nextval('review_records_id_seq')"))
    next_val = result.scalar()
    print(f"序列nextval: {next_val}")
    
    # 4. 检查是否有is_called标志
    result = conn.execute(text("SELECT is_called FROM review_records_id_seq"))
    is_called = result.scalar()
    print(f"序列is_called: {is_called}")
    
    # 5. 彻底修复：设置序列值
    # 使用 setval 将序列设置为 max_id，is_called=false 表示这个值还没被使用
    # 下次 nextval 会返回 max_id + 1
    print(f"\n修复序列...")
    conn.execute(text(f"SELECT setval('review_records_id_seq', {max_id}, false)"))
    conn.commit()
    
    # 6. 验证修复
    result = conn.execute(text("SELECT nextval('review_records_id_seq')"))
    next_val_after = result.scalar()
    print(f"修复后nextval: {next_val_after}")
    
    expected = max_id + 1
    if next_val_after == expected:
        print(f"✅ 序列已正确设置为: {expected}")
    else:
        print(f"❌ 序列设置异常! 期望: {expected}, 实际: {next_val_after}")

