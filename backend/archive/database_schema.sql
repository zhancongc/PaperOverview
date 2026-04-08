-- ============================================================================
-- AutoOverview Database Schema
-- PostgreSQL DDL
-- Generated from backend/models.py
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: paper_metadata
-- Description: 论文元数据表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_metadata (
    id VARCHAR(100) PRIMARY KEY COMMENT '论文ID（来自AMiner/OpenAlex等）',
    title VARCHAR(1000) NOT NULL COMMENT '论文标题',
    authors JSONB NOT NULL COMMENT '作者列表JSON',
    year INTEGER COMMENT '发表年份',
    abstract TEXT COMMENT '摘要',
    cited_by_count INTEGER DEFAULT 0 COMMENT '被引次数',
    is_english BOOLEAN DEFAULT TRUE COMMENT '是否英文文献',
    type VARCHAR(50) COMMENT '文献类型',
    doi VARCHAR(200) COMMENT 'DOI',
    concepts JSONB COMMENT '概念标签JSON',
    venue_name VARCHAR(500) COMMENT '期刊/会议名称',
    issue VARCHAR(50) COMMENT '卷号',
    source JSONB NOT NULL COMMENT '数据源列表，如 ["openalex", "semantic_scholar"]',
    url VARCHAR(1000) COMMENT '论文链接',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '首次入库时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
);

-- Indexes
CREATE INDEX idx_paper_metadata_year ON paper_metadata(year);
CREATE INDEX idx_paper_metadata_source ON paper_metadata(source);
CREATE INDEX idx_paper_metadata_created_at ON paper_metadata(created_at);
CREATE INDEX idx_paper_metadata_is_english ON paper_metadata(is_english);

-- ----------------------------------------------------------------------------
-- Table: review_records
-- Description: 综述生成记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_records (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(500) NOT NULL COMMENT '论文主题',
    review TEXT NOT NULL COMMENT '综述内容（Markdown）',
    papers JSONB NOT NULL COMMENT '文献列表JSON',
    statistics JSONB NOT NULL COMMENT '统计信息JSON',
    target_count INTEGER DEFAULT 50 COMMENT '目标文献数量',
    recent_years_ratio FLOAT DEFAULT 0.5 COMMENT '近5年占比',
    english_ratio FLOAT DEFAULT 0.3 COMMENT '英文文献占比',
    status VARCHAR(20) DEFAULT 'success' COMMENT '状态: success/failed',
    error_message TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
);

-- ----------------------------------------------------------------------------
-- Table: academic_terms
-- Description: 学术术语表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS academic_terms (
    id SERIAL PRIMARY KEY,
    chinese_term VARCHAR(200) NOT NULL UNIQUE COMMENT '中文术语',
    english_terms JSONB NOT NULL COMMENT '英文术语列表，如 ["lstm", "long short-term memory"]',
    category VARCHAR(50) NOT NULL COMMENT '分类：dl/nlp/bio/medical/general等',
    subcategory VARCHAR(50) COMMENT '子分类：如dl下的cnn/rnn等',
    aliases JSONB COMMENT '别名列表，包括中英文同义词',
    description TEXT COMMENT '术语描述',
    usage_examples JSONB COMMENT '使用示例',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    priority INTEGER DEFAULT 0 COMMENT '优先级（用于排序）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
);

-- Indexes
CREATE INDEX idx_category ON academic_terms(category);
CREATE INDEX idx_is_active ON academic_terms(is_active);
CREATE INDEX idx_chinese_term ON academic_terms(chinese_term);

-- ----------------------------------------------------------------------------
-- Table: review_tasks
-- Description: 综述生成任务表 - 记录整个任务生命周期
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_tasks (
    id VARCHAR(50) PRIMARY KEY COMMENT '任务ID',
    topic VARCHAR(500) NOT NULL COMMENT '论文主题',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/processing/completed/failed',
    current_stage VARCHAR(50) COMMENT '当前阶段',
    params JSONB NOT NULL COMMENT '生成参数JSON',
    error_message TEXT COMMENT '错误信息',
    review_record_id INTEGER COMMENT '关联的综述记录ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at TIMESTAMP COMMENT '开始时间',
    completed_at TIMESTAMP COMMENT '完成时间',
    FOREIGN KEY (review_record_id) REFERENCES review_records(id)
);

-- Indexes
CREATE INDEX idx_review_tasks_status ON review_tasks(status);
CREATE INDEX idx_review_tasks_created_at ON review_tasks(created_at);

-- ----------------------------------------------------------------------------
-- Table: outline_generation_stages
-- Description: 生成大纲阶段记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outline_generation_stages (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL COMMENT '任务ID',
    topic VARCHAR(500) NOT NULL COMMENT '论文主题',
    outline JSONB NOT NULL COMMENT '大纲结果JSON',
    framework_type VARCHAR(100) COMMENT '框架类型',
    classification JSONB COMMENT '分类结果JSON',
    status VARCHAR(20) DEFAULT 'completed' COMMENT '状态: completed/failed',
    error_message TEXT COMMENT '错误信息',
    duration_ms INTEGER COMMENT '耗时（毫秒）',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    completed_at TIMESTAMP COMMENT '完成时间',
    FOREIGN KEY (task_id) REFERENCES review_tasks(id)
);

-- Indexes
CREATE INDEX idx_outline_gen_stage_task_id ON outline_generation_stages(task_id);
CREATE INDEX idx_outline_gen_stage_started_at ON outline_generation_stages(started_at);

-- ----------------------------------------------------------------------------
-- Table: paper_search_stages
-- Description: 文献搜索阶段记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_search_stages (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL COMMENT '任务ID',
    outline JSONB NOT NULL COMMENT '大纲信息（包含搜索查询）',
    search_queries_count INTEGER DEFAULT 0 COMMENT '搜索查询数量',
    papers_count INTEGER DEFAULT 0 COMMENT '搜索到的文献总数',
    papers_summary JSONB COMMENT '文献摘要统计JSON',
    papers_sample JSONB COMMENT '文献样本（前20篇）',
    status VARCHAR(20) DEFAULT 'completed' COMMENT '状态: completed/failed',
    error_message TEXT COMMENT '错误信息',
    duration_ms INTEGER COMMENT '耗时（毫秒）',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    completed_at TIMESTAMP COMMENT '完成时间',
    FOREIGN KEY (task_id) REFERENCES review_tasks(id)
);

-- Indexes
CREATE INDEX idx_paper_search_stage_task_id ON paper_search_stages(task_id);
CREATE INDEX idx_paper_search_stage_started_at ON paper_search_stages(started_at);

-- ----------------------------------------------------------------------------
-- Table: paper_filter_stages
-- Description: 文献筛选阶段记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_filter_stages (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL COMMENT '任务ID',
    input_papers_count INTEGER DEFAULT 0 COMMENT '输入文献数',
    quality_filtered_count INTEGER DEFAULT 0 COMMENT '质量过滤移除数',
    quality_filtered_details JSONB COMMENT '质量过滤移除详情',
    topic_irrelevant_count INTEGER DEFAULT 0 COMMENT '主题不相关移除数',
    topic_irrelevant_details JSONB COMMENT '主题不相关移除详情',
    output_papers_count INTEGER DEFAULT 0 COMMENT '筛选后文献数',
    output_papers_summary JSONB COMMENT '筛选后文献统计JSON',
    status VARCHAR(20) DEFAULT 'completed' COMMENT '状态: completed/failed',
    error_message TEXT COMMENT '错误信息',
    duration_ms INTEGER COMMENT '耗时（毫秒）',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    completed_at TIMESTAMP COMMENT '完成时间',
    FOREIGN KEY (task_id) REFERENCES review_tasks(id)
);

-- Indexes
CREATE INDEX idx_paper_filter_stage_task_id ON paper_filter_stages(task_id);
CREATE INDEX idx_paper_filter_stage_started_at ON paper_filter_stages(started_at);

-- ----------------------------------------------------------------------------
-- Table: review_generation_stages
-- Description: 生成综述阶段记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_generation_stages (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL COMMENT '任务ID',
    papers_count INTEGER DEFAULT 0 COMMENT '输入文献数',
    review_length INTEGER DEFAULT 0 COMMENT '综述内容长度',
    citation_count INTEGER DEFAULT 0 COMMENT '引用文献数',
    cited_papers_count INTEGER DEFAULT 0 COMMENT '被引用文献数',
    review TEXT COMMENT '综述内容（Markdown格式，用于版本对比）',
    papers_summary JSONB COMMENT '引用文献摘要（包含id、title、authors等核心字段）',
    candidate_pool_summary JSONB COMMENT '候选文献池摘要（筛选前的所有论文）',
    validation_result JSONB COMMENT '验证结果JSON',
    status VARCHAR(20) DEFAULT 'completed' COMMENT '状态: completed/failed',
    error_message TEXT COMMENT '错误信息',
    duration_ms INTEGER COMMENT '耗时（毫秒）',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    completed_at TIMESTAMP COMMENT '完成时间',
    FOREIGN KEY (task_id) REFERENCES review_tasks(id)
);

-- Indexes
CREATE INDEX idx_review_gen_stage_task_id ON review_generation_stages(task_id);
CREATE INDEX idx_review_gen_stage_started_at ON review_generation_stages(started_at);

-- ----------------------------------------------------------------------------
-- Table: paper_search_sources
-- Description: 文献搜索来源记录（记录每篇文献对应的搜索关键词）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_search_sources (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL COMMENT '任务ID',
    paper_id VARCHAR(100) NOT NULL COMMENT '文献ID',
    search_keyword VARCHAR(500) NOT NULL COMMENT '匹配的搜索关键词',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (task_id) REFERENCES review_tasks(id),
    FOREIGN KEY (paper_id) REFERENCES paper_metadata(id),
    UNIQUE (task_id, paper_id, search_keyword)
);

-- Indexes
CREATE INDEX idx_paper_search_source_task_id ON paper_search_sources(task_id);
CREATE INDEX idx_paper_search_source_paper_id ON paper_search_sources(paper_id);
CREATE INDEX idx_paper_search_source_keyword ON paper_search_sources(search_keyword);

-- ============================================================================
-- Entity Relationship Diagram
-- ============================================================================
--
-- review_tasks (主任务表)
--     ├─── review_records (关联综述记录，1:1)
--     ├─── outline_generation_stages (大纲生成阶段，1:1)
--     ├─── paper_search_stages (文献搜索阶段，1:1)
--     ├─── paper_filter_stages (文献筛选阶段，1:1)
--     ├─── review_generation_stages (综述生成阶段，1:1)
--     └─── paper_search_sources (搜索来源记录，1:N)
--              └─── paper_metadata (文献元数据，N:1)
--
-- paper_metadata (独立文献库)
--
-- academic_terms (学术术语库，独立)
--
-- ============================================================================
