"""
数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, Index, UniqueConstraint
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
    source = Column(JSON, nullable=False, comment="数据源列表，如 ['openalex', 'semantic_scholar']")
    url = Column(String(1000), nullable=True, comment="论文链接")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="首次入库时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 索引（移除title索引以避免长度限制问题，title搜索使用LIKE查询）
    __table_args__ = (
        Index('idx_paper_metadata_year', 'year'),
        Index('idx_paper_metadata_source', 'source'),
        Index('idx_paper_metadata_created_at', 'created_at'),
        Index('idx_paper_metadata_is_english', 'is_english'),
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
            "source": self.source if isinstance(self.source, list) else [self.source],
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
            "source": self.source if isinstance(self.source, list) else [self.source],
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


class AcademicTerm(Base):
    """学术术语表"""
    __tablename__ = "academic_terms"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="术语ID")

    # 中文术语（主要标识）
    chinese_term = Column(String(200), nullable=False, unique=True, comment="中文术语")

    # 英文术语（多个，用JSON存储）
    english_terms = Column(JSON, nullable=False, comment="英文术语列表，如 ['lstm', 'long short-term memory']")

    # 分类信息
    category = Column(String(50), nullable=False, comment="分类：dl/nlp/bio/medical/general等")
    subcategory = Column(String(50), nullable=True, comment="子分类：如dl下的cnn/rnn等")

    # 别名（同义词）
    aliases = Column(JSON, nullable=True, comment="别名列表，包括中英文同义词")

    # 描述和用法
    description = Column(Text, nullable=True, comment="术语描述")
    usage_examples = Column(JSON, nullable=True, comment="使用示例")

    # 元数据
    is_active = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级（用于排序）")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 索引
    __table_args__ = (
        Index('idx_category', 'category'),
        Index('idx_is_active', 'is_active'),
        Index('idx_chinese_term', 'chinese_term'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "chinese_term": self.chinese_term,
            "english_terms": self.english_terms,
            "category": self.category,
            "subcategory": self.subcategory,
            "aliases": self.aliases or [],
            "description": self.description,
            "usage_examples": self.usage_examples or [],
            "is_active": self.is_active,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ReviewTask(Base):
    """综述生成任务表 - 记录整个任务生命周期"""
    __tablename__ = "review_tasks"

    id = Column(String(50), primary_key=True, comment="任务ID")
    topic = Column(String(500), nullable=False, comment="论文主题")

    # 任务状态
    status = Column(String(20), default="pending", comment="状态: pending/processing/completed/failed")
    current_stage = Column(String(50), nullable=True, comment="当前阶段")

    # 输入参数
    params = Column(JSON, nullable=False, comment="生成参数JSON")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 关联的综述记录ID（生成完成后填充）
    review_record_id = Column(Integer, nullable=True, comment="关联的综述记录ID")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 索引
    __table_args__ = (
        Index('idx_review_tasks_status', 'status'),
        Index('idx_review_tasks_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "status": self.status,
            "current_stage": self.current_stage,
            "params": self.params,
            "error_message": self.error_message,
            "review_record_id": self.review_record_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class OutlineGenerationStage(Base):
    """生成大纲阶段记录"""
    __tablename__ = "outline_generation_stages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    task_id = Column(String(50), nullable=False, comment="任务ID")

    # 输入
    topic = Column(String(500), nullable=False, comment="论文主题")

    # 输出
    outline = Column(JSON, nullable=False, comment="大纲结果JSON")
    framework_type = Column(String(100), nullable=True, comment="框架类型")
    classification = Column(JSON, nullable=True, comment="分类结果JSON")

    # 状态
    status = Column(String(20), default="completed", comment="状态: completed/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    duration_ms = Column(Integer, nullable=True, comment="耗时（毫秒）")

    # 时间戳
    started_at = Column(DateTime, default=datetime.now, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 索引
    __table_args__ = (
        Index('idx_outline_gen_stage_task_id', 'task_id'),
        Index('idx_outline_gen_stage_started_at', 'started_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "topic": self.topic,
            "outline": self.outline,
            "framework_type": self.framework_type,
            "classification": self.classification,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PaperSearchStage(Base):
    """文献搜索阶段记录"""
    __tablename__ = "paper_search_stages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    task_id = Column(String(50), nullable=False, comment="任务ID")

    # 输入
    outline = Column(JSON, nullable=False, comment="大纲信息（包含搜索查询）")
    search_queries_count = Column(Integer, default=0, comment="搜索查询数量")

    # 输出
    papers_count = Column(Integer, default=0, comment="搜索到的文献总数")
    papers_summary = Column(JSON, nullable=True, comment="文献摘要统计JSON")
    papers_sample = Column(JSON, nullable=True, comment="文献样本（前20篇）")

    # 状态
    status = Column(String(20), default="completed", comment="状态: completed/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    duration_ms = Column(Integer, nullable=True, comment="耗时（毫秒）")

    # 时间戳
    started_at = Column(DateTime, default=datetime.now, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 索引
    __table_args__ = (
        Index('idx_paper_search_stage_task_id', 'task_id'),
        Index('idx_paper_search_stage_started_at', 'started_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "outline": self.outline,
            "search_queries_count": self.search_queries_count,
            "papers_count": self.papers_count,
            "papers_summary": self.papers_summary,
            "papers_sample": self.papers_sample,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PaperFilterStage(Base):
    """文献筛选阶段记录"""
    __tablename__ = "paper_filter_stages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    task_id = Column(String(50), nullable=False, comment="任务ID")

    # 输入
    input_papers_count = Column(Integer, default=0, comment="输入文献数")

    # 质量过滤结果
    quality_filtered_count = Column(Integer, default=0, comment="质量过滤移除数")
    quality_filtered_details = Column(JSON, nullable=True, comment="质量过滤移除详情")

    # 主题相关性检查结果
    topic_irrelevant_count = Column(Integer, default=0, comment="主题不相关移除数")
    topic_irrelevant_details = Column(JSON, nullable=True, comment="主题不相关移除详情")

    # 输出
    output_papers_count = Column(Integer, default=0, comment="筛选后文献数")
    output_papers_summary = Column(JSON, nullable=True, comment="筛选后文献统计JSON")

    # 状态
    status = Column(String(20), default="completed", comment="状态: completed/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    duration_ms = Column(Integer, nullable=True, comment="耗时（毫秒）")

    # 时间戳
    started_at = Column(DateTime, default=datetime.now, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 索引
    __table_args__ = (
        Index('idx_paper_filter_stage_task_id', 'task_id'),
        Index('idx_paper_filter_stage_started_at', 'started_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "input_papers_count": self.input_papers_count,
            "quality_filtered_count": self.quality_filtered_count,
            "quality_filtered_details": self.quality_filtered_details,
            "topic_irrelevant_count": self.topic_irrelevant_count,
            "topic_irrelevant_details": self.topic_irrelevant_details,
            "output_papers_count": self.output_papers_count,
            "output_papers_summary": self.output_papers_summary,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class ReviewGenerationStage(Base):
    """生成综述阶段记录"""
    __tablename__ = "review_generation_stages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    task_id = Column(String(50), nullable=False, comment="任务ID")

    # 输入
    papers_count = Column(Integer, default=0, comment="输入文献数")

    # 输出
    review_length = Column(Integer, default=0, comment="综述内容长度")
    citation_count = Column(Integer, default=0, comment="引用文献数")
    cited_papers_count = Column(Integer, default=0, comment="被引用文献数")

    # 综述内容和文献摘要（用于版本对比和恢复）
    review = Column(Text, nullable=True, comment="综述内容（Markdown格式，用于版本对比）")
    papers_summary = Column(JSON, nullable=True, comment="引用文献摘要（包含id、title、authors等核心字段）")
    candidate_pool_summary = Column(JSON, nullable=True, comment="候选文献池摘要（筛选前的所有论文）")

    # 验证结果
    validation_result = Column(JSON, nullable=True, comment="验证结果JSON")

    # 状态
    status = Column(String(20), default="completed", comment="状态: completed/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    duration_ms = Column(Integer, nullable=True, comment="耗时（毫秒）")

    # 时间戳
    started_at = Column(DateTime, default=datetime.now, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 索引
    __table_args__ = (
        Index('idx_review_gen_stage_task_id', 'task_id'),
        Index('idx_review_gen_stage_started_at', 'started_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "papers_count": self.papers_count,
            "review_length": self.review_length,
            "citation_count": self.citation_count,
            "cited_papers_count": self.cited_papers_count,
            "review": self.review,
            "papers_summary": self.papers_summary,
            "candidate_pool_summary": self.candidate_pool_summary,
            "validation_result": self.validation_result,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PaperSearchSource(Base):
    """文献搜索来源记录（记录每篇文献对应的搜索关键词）"""
    __tablename__ = "paper_search_sources"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    task_id = Column(String(50), nullable=False, comment="任务ID")
    paper_id = Column(String(100), nullable=False, comment="文献ID")
    search_keyword = Column(String(500), nullable=False, comment="匹配的搜索关键词")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 索引
    __table_args__ = (
        Index('idx_paper_search_source_task_id', 'task_id'),
        Index('idx_paper_search_source_paper_id', 'paper_id'),
        Index('idx_paper_search_source_keyword', 'search_keyword'),
        # 唯一约束：同一任务、同一文献、同一关键词只记录一次
        UniqueConstraint('task_id', 'paper_id', 'search_keyword',
                      name='uq_paper_search_source_unique'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "paper_id": self.paper_id,
            "search_keyword": self.search_keyword,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

