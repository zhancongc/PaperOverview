"""
数据库管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()


class Database:
    """数据库管理类"""

    def __init__(self):
        self.db_user = os.getenv("DB_USER", "root")
        self.db_password = os.getenv("DB_PASSWORD", "security")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "3306")
        self.db_name = os.getenv("DB_NAME", "paper")

        self.database_url = (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

        self.engine = None
        self.SessionLocal = None

    def connect(self):
        """创建数据库连接"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        return self.engine

    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话"""
        if self.SessionLocal is None:
            self.connect()
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def create_tables(self):
        """创建所有表"""
        from models import Base
        if self.engine is None:
            self.connect()
        Base.metadata.create_all(bind=self.engine)


# 全局数据库实例
db = Database()


def get_db():
    """依赖注入：获取数据库会话"""
    yield from db.get_session()
