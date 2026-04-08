"""
检查是否有触发器或其他机制影响ID
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "security")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "paper")

database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

engine = create_engine(database_url)

with engine.connect() as conn:
    # 检查 review_records 表的触发器
    result = conn.execute(text("""
        SELECT trigger_name, event_manipulation, action_statement
        FROM information_schema.triggers
        WHERE event_object_table = 'review_records'
    """))
    triggers = result.fetchall()
    
    if triggers:
        print(f"找到 {len(triggers)} 个触发器:")
        for trigger in triggers:
            print(f"  - {trigger[0]}: {trigger[1]} -> {trigger[2]}")
    else:
        print("✅ 没有触发器")
    
    # 检查是否有默认值设置
    result = conn.execute(text("""
        SELECT column_name, column_default
        FROM information_schema.columns
        WHERE table_name = 'review_records' AND column_name = 'id'
    """))
    default_val = result.fetchone()
    
    if default_val:
        print(f"\nID列默认值: {default_val[1]}")
    else:
        print(f"\n✅ ID列没有默认值（使用序列）")
    
    # 检查最近几条记录的ID
    result = conn.execute(text("""
        SELECT id, topic, created_at 
        FROM review_records 
        ORDER BY id DESC 
        LIMIT 5
    """))
    recent = result.fetchall()
    
    print(f"\n最近5条记录:")
    for record in recent:
        print(f"  ID={record[0]}: {record[1][:40]}... ({record[2]})")

