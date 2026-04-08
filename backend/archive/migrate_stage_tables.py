"""
创建阶段跟踪表的迁移脚本
"""
import sys
from sqlalchemy import create_engine, text

# 直接使用正确的数据库连接
DATABASE_URL = "postgresql://postgres:security@localhost:5432/paper"

def create_tables():
    """创建阶段跟踪表"""
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # 创建 review_tasks 表
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_tasks (
                id VARCHAR(50) PRIMARY KEY,
                topic VARCHAR(500) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                current_stage VARCHAR(50),
                params JSON NOT NULL,
                error_message TEXT,
                review_record_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
            """))
            print("✓ review_tasks 表创建成功")

            # 创建 outline_generation_stages 表
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS outline_generation_stages (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(50) NOT NULL,
                topic VARCHAR(500) NOT NULL,
                outline JSON NOT NULL,
                framework_type VARCHAR(100),
                classification JSON,
                status VARCHAR(20) DEFAULT 'completed',
                error_message TEXT,
                duration_ms INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """))
            print("✓ outline_generation_stages 表创建成功")

            # 创建 paper_search_stages 表
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_search_stages (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(50) NOT NULL,
                outline JSON NOT NULL,
                search_queries_count INTEGER DEFAULT 0,
                papers_count INTEGER DEFAULT 0,
                papers_summary JSON,
                papers_sample JSON,
                status VARCHAR(20) DEFAULT 'completed',
                error_message TEXT,
                duration_ms INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """))
            print("✓ paper_search_stages 表创建成功")

            # 创建 paper_filter_stages 表
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_filter_stages (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(50) NOT NULL,
                input_papers_count INTEGER DEFAULT 0,
                quality_filtered_count INTEGER DEFAULT 0,
                quality_filtered_details JSON,
                topic_irrelevant_count INTEGER DEFAULT 0,
                topic_irrelevant_details JSON,
                output_papers_count INTEGER DEFAULT 0,
                output_papers_summary JSON,
                status VARCHAR(20) DEFAULT 'completed',
                error_message TEXT,
                duration_ms INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """))
            print("✓ paper_filter_stages 表创建成功")

            # 创建 review_generation_stages 表
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_generation_stages (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(50) NOT NULL,
                papers_count INTEGER DEFAULT 0,
                review_length INTEGER DEFAULT 0,
                citation_count INTEGER DEFAULT 0,
                cited_papers_count INTEGER DEFAULT 0,
                validation_result JSON,
                status VARCHAR(20) DEFAULT 'completed',
                error_message TEXT,
                duration_ms INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """))
            print("✓ review_generation_stages 表创建成功")

            # 创建索引
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_tasks_status ON review_tasks(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_tasks_created_at ON review_tasks(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_outline_task_id ON outline_generation_stages(task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_outline_started_at ON outline_generation_stages(started_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_search_task_id ON paper_search_stages(task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_search_started_at ON paper_search_stages(started_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_filter_task_id ON paper_filter_stages(task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_filter_started_at ON paper_filter_stages(started_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_gen_task_id ON review_generation_stages(task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_gen_started_at ON review_generation_stages(started_at)"))
            print("✓ 索引创建成功")

            print("\n✅ 所有阶段跟踪表创建成功！")

    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print(f"连接地址: {DATABASE_URL}")
    print("\n开始创建阶段跟踪表...")
    create_tables()
