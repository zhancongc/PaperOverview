"""
数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class PaperMetadata(Base):
    """论文元数据表"""
    __tablename__ = "paper_metadata"

    id = Column(String(100), primary_key=True, comment="论文ID（来自AMiner/OpenAlex等）")
    title = Column(String(1000), nullable=False, comment="论文标题")
    authors = Column(JSON, nullable=False, comment="作者列表JSON")
    year = Column(Integer, nullable=True, comment="发表年份")
    abstract = Column(Text, nullable=True, comment="摘要")
    cited_by_count = Column(Integer, default=0, comment="被引次数")
    is_english = Column(Boolean, default=True, comment="是否英文文献")
    type = Column(String(50), nullable=True, comment="文献类型")
    doi = Column(String(200), nullable=True, comment="DOI")
    concepts = Column(JSON, nullable=True, comment="概念标签JSON")
    venue_name = Column(String(500), nullable=True, comment="期刊/会议名称")
    issue = Column(String(50), nullable=True, comment="卷号")
    source = Column(String(50), nullable=False, comment="数据源（aminer/openalex/semantic_scholar）")
    url = Column(String(1000), nullable=True, comment="论文链接")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="首次入库时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 索引
    __table_args__ = (
        Index('idx_title', 'title'),
        Index('idx_year', 'year'),
        Index('idx_source', 'source'),
        Index('idx_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "cited_by_count": self.cited_by_count,
            "is_english": self.is_english,
            "type": self.type,
            "doi": self.doi,
            "concepts": self.concepts,
            "venue_name": self.venue_name,
            "issue": self.issue,
            "source": self.source,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def to_paper_dict(self):
        """转换为前端使用的Paper格式"""
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors if isinstance(self.authors, list) else [],
            "year": self.year,
            "abstract": self.abstract or "",
            "cited_by_count": self.cited_by_count or 0,
            "is_english": self.is_english if self.is_english is not None else True,
            "type": self.type or "",
            "doi": self.doi or "",
            "concepts": self.concepts if isinstance(self.concepts, list) else [],
            "venue_name": self.venue_name,
            "issue": self.issue,
            "source": self.source,
            "url": self.url
        }


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
