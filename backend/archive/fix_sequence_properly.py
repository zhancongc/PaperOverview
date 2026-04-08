"""
正确修复序列问题
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
    # 检查当前最大ID
    result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM review_records"))
    max_id = result.scalar()
    print(f"当前最大ID: {max_id}")
    
    # 正确的修复方法：
    # 使用 setval(seq, max_id, true) 
    # 这会将序列设置为 max_id，并标记为"已调用"
    # 下次 nextval 会自动递增到 max_id + 1
    print(f"修复序列: setval('review_records_id_seq', {max_id}, true)")
    conn.execute(text(f"SELECT setval('review_records_id_seq', {max_id}, true)"))
    conn.commit()
    
    # 验证修复
    result = conn.execute(text("SELECT nextval('review_records_id_seq')"))
    next_val = result.scalar()
    print(f"修复后下一个ID: {next_val}")
    
    if next_val == max_id + 1:
        print(f"✅ 序列已正确设置，下一个新记录将使用 ID={next_val}")
    else:
        print(f"❌ 仍有问题，期望: {max_id + 1}, 实际: {next_val}")
        
        # 如果仍有问题，使用 RESTART
        print(f"使用 RESTART 方法...")
        conn.execute(text(f"ALTER SEQUENCE review_records_id_seq RESTART WITH {max_id + 1}"))
        conn.commit()
        
        result = conn.execute(text("SELECT nextval('review_records_id_seq')"))
        next_val2 = result.scalar()
        print(f"RESTART 后下一个ID: {next_val2}")

