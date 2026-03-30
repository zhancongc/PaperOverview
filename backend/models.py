"""
数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ReviewRecord(Base):
    """综述生成记录"""
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    topic = Column(String(500), nullable=False, comment="论文主题")
    review = Column(Text, nullable=False, comment="综述内容（Markdown）")
    papers = Column(JSON, nullable=False, comment="文献列表JSON")
    statistics = Column(JSON, nullable=False, comment="统计信息JSON")

    # 生成参数
    target_count = Column(Integer, default=50, comment="目标文献数量")
    recent_years_ratio = Column(Float, default=0.5, comment="近5年占比")
    english_ratio = Column(Float, default=0.3, comment="英文文献占比")

    # 状态
    status = Column(String(20), default="success", comment="状态: success/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "review": self.review,
            "papers": self.papers,
            "statistics": self.statistics,
            "target_count": self.target_count,
            "recent_years_ratio": self.recent_years_ratio,
            "english_ratio": self.english_ratio,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
