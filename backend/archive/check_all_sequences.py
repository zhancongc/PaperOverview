"""
检查并修复所有表的序列
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

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
    # 获取所有表名
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n数据库中的表 ({len(tables)} 个):")
    for table in tables:
        print(f"  - {table}")
    
    # 获取所有序列
    result = conn.execute(text("""
        SELECT sequence_name 
        FROM information_schema.sequences 
        WHERE sequence_schema = 'public'
    """))
    sequences = [row[0] for row in result.fetchall()]
    
    print(f"\n找到 {len(sequences)} 个序列:")
    for seq in sequences:
        print(f"  - {seq}")
    
    # 检查每个表的ID序列
    tables_to_check = [
        ('review_records', 'review_records_id_seq', 'id'),
        ('academic_terms', 'academic_terms_id_seq', 'id'),
    ]
    
    print("\n" + "="*70)
    print("详细检查")
    print("="*70)
    
    needs_fix = []
    
    for table_name, seq_name, id_column in tables_to_check:
        if table_name not in tables:
            print(f"\n⚠️  表 {table_name} 不存在，跳过")
            continue
        
        if seq_name not in sequences:
            print(f"\n⚠️  序列 {seq_name} 不存在，跳过")
            continue
        
        print(f"\n📋 表: {table_name}")
        print(f"   序列: {seq_name}")
        print(f"   ID列: {id_column}")
        
        # 获取当前最大ID
        result = conn.execute(text(f"SELECT COALESCE(MAX({id_column}), 0) FROM {table_name}"))
        max_id = result.scalar()
        print(f"   最大ID: {max_id}")
        
        # 获取序列当前值
        try:
            result = conn.execute(text(f"SELECT last_value FROM {seq_name}"))
            seq_value = result.scalar()
            print(f"   序列值: {seq_value}")
        except Exception as e:
            print(f"   ⚠️  无法获取序列值: {e}")
            continue
        
        # 检查是否需要修复
        # PostgreSQL序列：如果last_value < max_id，需要修复
        if seq_value < max_id:
            print(f"   ⚠️  序列不同步！")
            print(f"      期望最小值: {max_id + 1}")
            print(f"      实际序列值: {seq_value}")
            needs_fix.append((table_name, seq_name, max_id))
        else:
            print(f"   ✅ 序列正常")
            
        # 显示记录数量
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
        print(f"   记录数: {count}")
    
    # 修复需要修复的序列
    if needs_fix:
        print("\n" + "="*70)
        print("修复不同步的序列")
        print("="*70)
        
        for table_name, seq_name, max_id in needs_fix:
            new_value = max_id + 1
            print(f"\n修复 {table_name}.{seq_name}:")
            print(f"  设置序列从 {new_value} 开始")
            conn.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH {new_value}"))
            conn.commit()
            print(f"  ✅ 已修复")
    else:
        print("\n" + "="*70)
        print("✅ 所有表的序列都正常")
        print("="*70)

