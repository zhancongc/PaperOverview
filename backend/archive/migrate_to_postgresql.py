#!/usr/bin/env python3
"""
MySQL 到 PostgreSQL 迁移脚本

功能：
1. 从 MySQL 读取所有数据
2. 在 PostgreSQL 中创建表结构
3. 转换并插入数据
4. 数据验证和错误处理
5. 进度显示和统计信息

使用方法：
    python migrate_to_postgresql.py

环境变量（可在 .env 文件中配置）：
    # MySQL 源数据库
    MYSQL_DB_USER=root
    MYSQL_DB_PASSWORD=security
    MYSQL_DB_HOST=localhost
    MYSQL_DB_PORT=3306
    MYSQL_DB_NAME=paper

    # PostgreSQL 目标数据库
    DB_TYPE=postgresql
    DB_USER=postgres
    DB_PASSWORD=security
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=paper
"""
import sys
import os
from datetime import datetime
from typing import Dict, List
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()


class MigrationTool:
    """数据库迁移工具"""

    def __init__(self):
        """初始化源数据库(MySQL)和目标数据库(PostgreSQL)连接"""
        # MySQL 源数据库配置
        self.mysql_user = os.getenv("MYSQL_DB_USER", "root")
        self.mysql_password = os.getenv("MYSQL_DB_PASSWORD", "security")
        self.mysql_host = os.getenv("MYSQL_DB_HOST", "localhost")
        self.mysql_port = os.getenv("MYSQL_DB_PORT", "3306")
        self.mysql_db_name = os.getenv("MYSQL_DB_NAME", "paper")

        self.mysql_url = (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db_name}"
            f"?charset=utf8mb4"
        )

        # PostgreSQL 目标数据库配置
        self.pg_user = os.getenv("DB_USER", "postgres")
        self.pg_password = os.getenv("DB_PASSWORD", "security")
        self.pg_host = os.getenv("DB_HOST", "localhost")
        self.pg_port = os.getenv("DB_PORT", "5432")
        self.pg_db_name = os.getenv("DB_NAME", "paper")

        self.pg_url = (
            f"postgresql://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db_name}"
        )

        self.mysql_engine = None
        self.pg_engine = None
        self.mysql_session = None
        self.pg_session = None

        # 统计信息
        self.stats = {
            "paper_metadata": {"source": 0, "migrated": 0, "failed": 0},
            "review_records": {"source": 0, "migrated": 0, "failed": 0},
            "academic_terms": {"source": 0, "migrated": 0, "failed": 0},
        }

    def connect_mysql(self):
        """连接 MySQL 数据库"""
        print(f"\n[MySQL] 连接中: {self.mysql_host}:{self.mysql_port}/{self.mysql_db_name}")
        try:
            self.mysql_engine = create_engine(
                self.mysql_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.mysql_engine
            )
            self.mysql_session = SessionLocal()

            # 测试连接
            result = self.mysql_session.execute(text("SELECT 1")).scalar()
            print(f"[MySQL] ✓ 连接成功")
            return True
        except Exception as e:
            print(f"[MySQL] ✗ 连接失败: {e}")
            return False

    def connect_postgresql(self):
        """连接 PostgreSQL 数据库"""
        print(f"\n[PostgreSQL] 连接中: {self.pg_host}:{self.pg_port}/{self.pg_db_name}")
        try:
            self.pg_engine = create_engine(
                self.pg_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.pg_engine
            )
            self.pg_session = SessionLocal()

            # 测试连接
            result = self.pg_session.execute(text("SELECT 1")).scalar()
            print(f"[PostgreSQL] ✓ 连接成功")
            return True
        except Exception as e:
            print(f"[PostgreSQL] ✗ 连接失败: {e}")
            return False

    def create_postgresql_tables(self):
        """在 PostgreSQL 中创建表结构"""
        print("\n[PostgreSQL] 创建表结构...")
        try:
            from models import Base, PaperMetadata, ReviewRecord, AcademicTerm
            Base.metadata.create_all(bind=self.pg_engine)
            self.PaperMetadata = PaperMetadata
            self.ReviewRecord = ReviewRecord
            self.AcademicTerm = AcademicTerm
            print("[PostgreSQL] ✓ 表结构创建完成")
            return True
        except Exception as e:
            print(f"[PostgreSQL] ✗ 表结构创建失败: {e}")
            return False

    def get_table_count(self, session: Session, table_name: str) -> int:
        """获取表的记录数"""
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            return result or 0
        except:
            return 0

    def convert_json_for_pg(self, value):
        """
        转换 MySQL JSON 数据为 Python 对象

        MySQL JSON 字段返回的是字符串，需要正确处理
        """
        if value is None:
            return []

        # 如果已经是字符串，尝试解析
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                # 解析失败，返回空数组
                return []

        # 如果是列表或字典，直接返回
        if isinstance(value, (list, dict)):
            return value

        return []

    def convert_bool_for_pg(self, value) -> bool:
        """
        转换 MySQL 整数布尔值为 Python 布尔类型

        MySQL 使用 1/0 表示布尔，Python 使用 True/False
        """
        if value is None:
            return True
        if isinstance(value, bool):
            return value
        return bool(value)

    def migrate_paper_metadata(self, batch_size: int = 100):
        """迁移论文元数据表"""
        print("\n[迁移] paper_metadata 表...")

        # 获取源数据总数
        try:
            self.stats["paper_metadata"]["source"] = self.get_table_count(
                self.mysql_session, "paper_metadata"
            )
            print(f"[迁移] 源数据记录: {self.stats['paper_metadata']['source']} 条")
        except Exception as e:
            print(f"[迁移] ✗ 获取源数据失败: {e}")
            return

        if self.stats["paper_metadata"]["source"] == 0:
            print("[迁移] 跳过（无数据）")
            return

        # 分批迁移
        offset = 0
        migrated = 0
        failed = 0

        while offset < self.stats["paper_metadata"]["source"]:
            try:
                # 从 MySQL 读取数据
                query = text("""
                    SELECT id, title, authors, year, abstract, cited_by_count,
                           is_english, type, doi, concepts, venue_name, issue,
                           source, url, created_at, updated_at
                    FROM paper_metadata
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                """)
                result = self.mysql_session.execute(
                    query,
                    {"limit": batch_size, "offset": offset}
                )

                rows = result.fetchall()
                if not rows:
                    break

                # 插入到 PostgreSQL（使用 ORM）
                for row in rows:
                    try:
                        record = self.PaperMetadata(
                            id=row[0],
                            title=row[1],
                            authors=self.convert_json_for_pg(row[2]),
                            year=row[3],
                            abstract=row[4],
                            cited_by_count=row[5],
                            is_english=self.convert_bool_for_pg(row[6]),
                            type=row[7],
                            doi=row[8],
                            concepts=self.convert_json_for_pg(row[9]),
                            venue_name=row[10],
                            issue=row[11],
                            source=row[12],
                            url=row[13],
                            created_at=row[14],
                            updated_at=row[15]
                        )
                        self.pg_session.merge(record)
                        migrated += 1
                    except Exception as e:
                        self.pg_session.rollback()
                        print(f"[迁移] ✗ 记录失败 {row[0]}: {e}")
                        failed += 1

                # 提交当前批次
                self.pg_session.commit()
                offset += len(rows)
                print(f"[迁移] 进度: {offset}/{self.stats['paper_metadata']['source']} "
                      f"({offset * 100 // self.stats['paper_metadata']['source']}%)")

            except Exception as e:
                print(f"[迁移] ✗ 批次失败: {e}")
                self.pg_session.rollback()
                break

        self.stats["paper_metadata"]["migrated"] = migrated
        self.stats["paper_metadata"]["failed"] = failed
        print(f"[迁移] ✓ 完成: 成功 {migrated}, 失败 {failed}")

    def migrate_review_records(self, batch_size: int = 100):
        """迁移综述记录表"""
        print("\n[迁移] review_records 表...")

        # 获取源数据总数
        try:
            self.stats["review_records"]["source"] = self.get_table_count(
                self.mysql_session, "review_records"
            )
            print(f"[迁移] 源数据记录: {self.stats['review_records']['source']} 条")
        except Exception as e:
            print(f"[迁移] ✗ 获取源数据失败: {e}")
            return

        if self.stats["review_records"]["source"] == 0:
            print("[迁移] 跳过（无数据）")
            return

        # 分批迁移
        offset = 0
        migrated = 0
        failed = 0

        while offset < self.stats["review_records"]["source"]:
            try:
                # 从 MySQL 读取数据
                query = text("""
                    SELECT id, topic, review, papers, statistics,
                           target_count, recent_years_ratio, english_ratio,
                           status, error_message, created_at, updated_at
                    FROM review_records
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                """)
                result = self.mysql_session.execute(
                    query,
                    {"limit": batch_size, "offset": offset}
                )

                rows = result.fetchall()
                if not rows:
                    break

                # 插入到 PostgreSQL（使用 ORM）
                for row in rows:
                    try:
                        record = self.ReviewRecord(
                            id=row[0],
                            topic=row[1],
                            review=row[2],
                            papers=self.convert_json_for_pg(row[3]),
                            statistics=self.convert_json_for_pg(row[4]),
                            target_count=row[5],
                            recent_years_ratio=float(row[6]) if row[6] else 0.5,
                            english_ratio=float(row[7]) if row[7] else 0.3,
                            status=row[8],
                            error_message=row[9],
                            created_at=row[10],
                            updated_at=row[11]
                        )
                        self.pg_session.merge(record)
                        migrated += 1
                    except Exception as e:
                        self.pg_session.rollback()
                        print(f"[迁移] ✗ 记录失败 ID={row[0]}: {e}")
                        failed += 1

                # 提交当前批次
                self.pg_session.commit()
                offset += len(rows)
                print(f"[迁移] 进度: {offset}/{self.stats['review_records']['source']} "
                      f"({offset * 100 // self.stats['review_records']['source']}%)")

            except Exception as e:
                print(f"[迁移] ✗ 批次失败: {e}")
                self.pg_session.rollback()
                break

        self.stats["review_records"]["migrated"] = migrated
        self.stats["review_records"]["failed"] = failed
        print(f"[迁移] ✓ 完成: 成功 {migrated}, 失败 {failed}")

    def migrate_academic_terms(self, batch_size: int = 100):
        """迁移学术术语表"""
        print("\n[迁移] academic_terms 表...")

        # 获取源数据总数
        try:
            self.stats["academic_terms"]["source"] = self.get_table_count(
                self.mysql_session, "academic_terms"
            )
            print(f"[迁移] 源数据记录: {self.stats['academic_terms']['source']} 条")
        except Exception as e:
            print(f"[迁移] ✗ 获取源数据失败: {e}")
            return

        if self.stats["academic_terms"]["source"] == 0:
            print("[迁移] 跳过（无数据）")
            return

        # 分批迁移
        offset = 0
        migrated = 0
        failed = 0

        while offset < self.stats["academic_terms"]["source"]:
            try:
                # 从 MySQL 读取数据
                query = text("""
                    SELECT id, chinese_term, english_terms, category, subcategory,
                           aliases, description, usage_examples, is_active,
                           priority, created_at, updated_at
                    FROM academic_terms
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                """)
                result = self.mysql_session.execute(
                    query,
                    {"limit": batch_size, "offset": offset}
                )

                rows = result.fetchall()
                if not rows:
                    break

                # 插入到 PostgreSQL（使用 ORM）
                for row in rows:
                    try:
                        record = self.AcademicTerm(
                            id=row[0],
                            chinese_term=row[1],
                            english_terms=self.convert_json_for_pg(row[2]),
                            category=row[3],
                            subcategory=row[4],
                            aliases=self.convert_json_for_pg(row[5]),
                            description=row[6],
                            usage_examples=self.convert_json_for_pg(row[7]),
                            is_active=self.convert_bool_for_pg(row[8]),
                            priority=row[9],
                            created_at=row[10],
                            updated_at=row[11]
                        )
                        self.pg_session.merge(record)
                        migrated += 1
                    except Exception as e:
                        self.pg_session.rollback()
                        print(f"[迁移] ✗ 记录失败 ID={row[0]}: {e}")
                        failed += 1

                # 提交当前批次
                self.pg_session.commit()
                offset += len(rows)
                print(f"[迁移] 进度: {offset}/{self.stats['academic_terms']['source']} "
                      f"({offset * 100 // self.stats['academic_terms']['source']}%)")

            except Exception as e:
                print(f"[迁移] ✗ 批次失败: {e}")
                self.pg_session.rollback()
                break

        self.stats["academic_terms"]["migrated"] = migrated
        self.stats["academic_terms"]["failed"] = failed
        print(f"[迁移] ✓ 完成: 成功 {migrated}, 失败 {failed}")

    def verify_migration(self):
        """验证迁移结果"""
        print("\n[验证] 检查迁移结果...")

        tables = ["paper_metadata", "review_records", "academic_terms"]

        for table in tables:
            try:
                pg_count = self.get_table_count(self.pg_session, table)
                source_count = self.stats[table]["source"]
                migrated_count = self.stats[table]["migrated"]

                print(f"\n[验证] {table}:")
                print(f"  - 源数据: {source_count}")
                print(f"  - 迁移成功: {migrated_count}")
                print(f"  - PostgreSQL 实际: {pg_count}")

                if pg_count == migrated_count:
                    print(f"  - ✓ 验证通过")
                else:
                    print(f"  - ⚠ 数量不匹配 (差异: {pg_count - migrated_count})")
            except Exception as e:
                print(f"[验证] ✗ {table} 验证失败: {e}")

    def print_summary(self):
        """打印迁移摘要"""
        print("\n" + "=" * 80)
        print("迁移摘要")
        print("=" * 80)

        total_source = sum(s["source"] for s in self.stats.values())
        total_migrated = sum(s["migrated"] for s in self.stats.values())
        total_failed = sum(s["failed"] for s in self.stats.values())

        for table, stat in self.stats.items():
            print(f"\n{table}:")
            print(f"  源数据: {stat['source']}")
            print(f"  迁移成功: {stat['migrated']}")
            print(f"  迁移失败: {stat['failed']}")

        print(f"\n总计:")
        print(f"  源数据: {total_source}")
        print(f"  迁移成功: {total_migrated}")
        print(f"  迁移失败: {total_failed}")
        print(f"  成功率: {total_migrated * 100 // total_source if total_source > 0 else 0}%")

    def close(self):
        """关闭数据库连接"""
        if self.mysql_session:
            self.mysql_session.close()
        if self.pg_session:
            self.pg_session.close()
        if self.mysql_engine:
            self.mysql_engine.dispose()
        if self.pg_engine:
            self.pg_engine.dispose()
        print("\n[关闭] 数据库连接已关闭")

    def run(self):
        """执行迁移"""
        print("=" * 80)
        print("MySQL 到 PostgreSQL 数据库迁移工具")
        print("=" * 80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. 连接源数据库
        if not self.connect_mysql():
            print("\n[错误] 无法连接到 MySQL 数据库，迁移中止")
            return False

        # 2. 连接目标数据库
        if not self.connect_postgresql():
            print("\n[错误] 无法连接到 PostgreSQL 数据库，迁移中止")
            self.close()
            return False

        # 3. 创建表结构
        if not self.create_postgresql_tables():
            print("\n[错误] 无法创建 PostgreSQL 表结构，迁移中止")
            self.close()
            return False

        # 4. 迁移数据
        print("\n" + "=" * 80)
        print("开始数据迁移")
        print("=" * 80)

        self.migrate_paper_metadata()
        self.migrate_review_records()
        self.migrate_academic_terms()

        # 5. 验证迁移
        self.verify_migration()

        # 6. 打印摘要
        self.print_summary()

        print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 7. 关闭连接
        self.close()

        return True


def main():
    """主函数"""
    tool = MigrationTool()

    try:
        success = tool.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[中断] 用户中断迁移")
        tool.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 迁移过程发生异常: {e}")
        import traceback
        traceback.print_exc()
        tool.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
