# 综述生成流程文档

## 概述

本文档描述了论文综述生成器的完整生成流程。该流程采用**Function Calling渐进式信息披露**、**按小节文献管理**、**增强相关性评分**、**跨学科过滤**、**多数据源聚合**、**阶段记录追踪**等技术，确保生成的综述质量。

## 版本信息

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| 5.1 | 2026-04-03 | **阶段记录追踪**、代码复用重构、Temperature优化、查找文献功能 |
| 5.0 | 2026-04-03 | Function Calling统一版本、增强相关性评分、跨学科过滤、渐进式搜索 |
| 4.0 | 2026-04-01 | 自然统计数据嵌入、深度对比分析、综述润色 |

## 核心架构

### Service 类职责

| Service 类 | 文件 | 职责 |
|-----------|------|------|
| `ReviewTaskExecutor` | `services/review_task_executor.py` | **综述生成任务执行器（主流程）** |
| `ReviewGeneratorFCUnified` | `services/review_generator_fc_unified.py` | Function Calling统一版本生成器 |
| `StageRecorderService` | `services/stage_recorder.py` | **阶段记录服务（数据库追踪）** |
| `EnhancedPaperFilterService` | `services/paper_field_classifier.py` | 增强筛选服务（相关性评分+跨学科过滤） |
| `FrameworkGenerator` | `services/hybrid_classifier.py` | 题目分析、大纲生成、关键词提取 |
| `SmartPaperSearchService` | `services/smart_paper_search.py` | 智能搜索（数据库优先+API补充） |
| `ScholarFlux` | `services/scholarflux_wrapper.py` | 多数据源聚合搜索 |
| `AcademicTermService` | `services/academic_term_service.py` | 学术术语服务 |
| `ReferenceValidator` | `services/reference_validator.py` | 参考文献质量验证 |
| `ReviewRecordService` | `services/review_record_service.py` | 综述记录数据库操作 |

### 数据库表（阶段记录）

| 表名 | 用途 |
|------|------|
| `outline_generation_stages` | 大纲生成阶段记录 |
| `paper_search_stages` | 文献搜索阶段记录 |
| `paper_filter_stages` | 质量过滤阶段记录 |
| `review_generation_stages` | 综述生成阶段记录 |

## 完整流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户点击"生成综述"                                  │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ReviewTaskExecutor.execute_task()                   │
│                                                                             │
│  1. 创建任务记录 → ReviewRecord(status=running)                              │
│  2. 获取执行槽位 (最多3个并发任务)                                               │
│  3. 执行 _search_and_filter_papers() ─────────────────────────┐              │
│  4. 生成综述                                                     │              │
│  5. 验证和保存                                                   │              │
└───────────────────────────────────────┬─────────────────────────────────────────┘      │
                                        │                                         │
                                        ▼                                         │
┌─────────────────────────────────────────────────────────────────────────────┐ │
│                      _search_and_filter_papers() 【共享方法】                   │ │
│                                                                             │ │
│  ╔═════════════════════════════════════════════════════════════════════════╗ │ │
│  ║ 【阶段1】生成综述大纲和搜索关键词                                         ║ │ │
│  ║  • 调用: _generate_review_outline()                                      ║ │ │
│  ║  • 模型: deepseek-reasoner (temperature=0.3)                             ║ │ │
│  ║  • 输出: {outline, search_queries}                                       ║ │ │
│  ║  • 记录到: OutlineGenerationStage                                         ║ │ │
│  ╚═════════════════════════════════════════════════════════════════════════╝ │ │
│                                    │                                         │ │
│                                    ▼                                         │ │
│  ╔═════════════════════════════════════════════════════════════════════════╗ │ │
│  ║ 【阶段2】搜索词优化 (基本语言优化)                                       ║ │ │
│  ║  • 调用: _optimize_search_queries_basic()                               ║ │ │
│  ║  • 输出: 按数据源使用不同语言的搜索词                                       ║ │ │
│  ╚═════════════════════════════════════════════════════════════════════════╝ │ │
│                                    │                                         │ │
│                                    ▼                                         │ │
│  ╔═════════════════════════════════════════════════════════════════════════╗ │ │
│  ║ 【阶段3】按小节搜索文献                                                  ║ │ │
│  ║  • 调用: _search_literature_by_sections()                                ║ │ │
│  ║  • 数据源: arXiv, CrossRef, Google Scholar, Semantic Scholar             ║ │ │
│  ║  • 输出: all_papers (按小节分组的文献)                                     ║ │ │
│  ║  • 记录到: PaperSearchStage                                              ║ │ │
│  ╚═════════════════════════════════════════════════════════════════════════╝ │ │
│                                    │                                         │ │
│                                    ▼                                         │ │
│  ╔═════════════════════════════════════════════════════════════════════════╗ │ │
│  ║ 【阶段4】质量过滤                                                       ║ │ │
│  ║  • 调用: _filter_papers_by_quality()                                     ║ │ │
│  ║  • 规则: 去重 + 引用数阈值 + 年份过滤                                      ║ │ │
│  ║  • 输出: filtered_papers (高质量文献)                                      ║ │ │
│  ║  • 记录到: PaperFilterStage                                              ║ │ │
│  ╚═════════════════════════════════════════════════════════════════════════╝ │ │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼ 返回 {outline, all_papers, filtered_papers}
┌─────────────────────────────────────────────────────────────────────────────┐
│  ╔═════════════════════════════════════════════════════════════════════════╗ │
│  ║ 【阶段5】生成综述                                                        ║ │
│  ║  • 调用: ReviewGeneratorFCUnified.generate_review()                      ║ │
│  ║  • 模型: deepseek-reasoner (temperature=0.4)                             ║ │
│  ║  • 工具: Function Calling 按需获取文献详情                                  ║ │
│  ║  • 输出: review, cited_papers                                            ║ │
│  ║  • 记录到: ReviewGenerationStage (含review+papers_summary)                ║ │
│  ╚═════════════════════════════════════════════════════════════════════════╝ │
│                                    │                                         │
│                                    ▼                                         │
│  ╔═════════════════════════════════════════════════════════════════════════╗ │
│  ║ 【阶段6】验证和保存                                                      ║ │
│  ║  • 引用验证                                                             ║ │
│  ║  • 统计信息计算                                                         ║ │
│  ║  • 保存到 ReviewRecord                                                  ║ │
│  ║  • 更新状态: running → completed                                        ║ │
│  ╚═════════════════════════════════════════════════════════════════════════╝ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 功能复用关系

### 代码复用设计

| 功能 | 复用的阶段 | 入口方法 | 说明 |
|------|-----------|----------|------|
| **生成综述** | 阶段1-6 | `execute_task()` | 完整流程 |
| **查找文献** | 阶段1-4 | `search_papers_only()` | 复用 `_search_and_filter_papers()` |
| **智能分析** | 阶段1 | `/api/smart-analyze` | 复用 `_generate_review_outline()` |

### 共同方法 `_search_and_filter_papers()`

```python
async def _search_and_filter_papers(
    self,
    topic: str,
    target_count: int,
    recent_years_ratio: float,
    english_ratio: float,
    search_years: int,
    max_search_queries: int
) -> dict:
    """
    共同方法：执行阶段1-4

    返回:
        {
            "outline": {...},
            "all_papers": {...},
            "filtered_papers": [...]
        }
    """
```

## Temperature 设置汇总

针对学术综述生成的特点，对不同阶段的 DeepSeek temperature 进行了优化：

| 阶段 | 文件 | 原值 | 新值 | 理由 |
|------|------|------|------|------|
| 大纲生成 | review_task_executor.py | 0.5 | **0.3** | 结构化输出需要稳定性 |
| 搜索词优化 | hybrid_classifier.py | 0.5 | **0.3** | 关键词提取需要准确性 |
| 综述生成 | review_generator_fc_unified.py | 0.7 | **0.4** | 平衡创造性与准确性 |
| 引用拆分 | citation_splitter.py | 0.5 | **0.3** | 需准确理解原文 |
| 争议分析 | controversy_analyzer.py | 0.7 | **0.3** | 需精确识别观点 |
| 深度对比 | deep_comparison.py | 0.5 | **0.3** | 批判性分析需要严谨 |
| 统计提取 | statistics_extractor.py | 0.7 | **0.3** | 数据提取需要准确 |
| 综述润色 | review_polisher.py | 0.5 | **0.4** | 适度优化保持原意 |

## 数据源配置

| 数据源 | 用途 | 语言 | API |
|--------|------|------|-----|
| OpenAlex | 英文文献搜索（主要） | 英文 | https://api.openalex.org |
| Crossref | 期刊/会议论文 | 英文 | https://api.crossref.org |
| DataCite | 研究数据集 | 英文 | https://api.datacite.org |
| Semantic Scholar | 补充搜索 | 全部 | https://api.semanticscholar.org |
| AMiner | 中文文献搜索 | 中文 | https://datacenter.aminer.cn |
| arXiv | 预印本论文 | 英文 | https://export.arxiv.org |
| Google Scholar | 补充搜索 | 全部 | ScholarFlux 聚合 |

## 核心设计决策

### 1. 阶段记录追踪

**问题**：无法追踪每个阶段的执行结果，难以进行版本对比和问题排查

**解决方案**：
- 创建4个阶段记录表
- 每个阶段完成后记录到数据库
- 支持历史版本对比
- 便于问题排查和质量分析

**实现**：`StageRecorderService` 类

**记录内容**：
```python
# OutlineGenerationStage
{
    "task_id": "xxx",
    "outline": {...},           # 大纲结构
    "search_queries": [...],    # 搜索关键词
    "execution_time": 1.2       # 执行时间
}

# PaperSearchStage
{
    "task_id": "xxx",
    "total_found": 150,
    "papers_by_section": {...}, # 按小节分组的文献
    "sources": ["openalex", "aminer"]
}

# PaperFilterStage
{
    "task_id": "xxx",
    "input_count": 150,
    "output_count": 60,
    "filtered_papers": [...]
}

# ReviewGenerationStage
{
    "task_id": "xxx",
    "review": "...",            # 综述内容（用于版本对比）
    "papers_summary": [...],    # 引用文献摘要
    "cited_papers_count": 52
}
```

### 2. Function Calling 渐进式信息披露

**问题**：一次性发送60篇完整论文（标题+摘要+作者）消耗大量token

**解决方案**：
- 初始只发送论文标题列表（~600 tokens）
- LLM按需调用 `get_paper_details` 获取论文详情
- Token节省：~70%

**优势**：
- Token节省70%
- 注意力更集中（只处理需要的论文）
- 全局连贯性好（一次性生成）

### 3. 增强相关性评分

```python
评分构成（0-100分）：
├─ 被引量：0-25分（归一化）
├─ 标题关键词：20分/词
├─ 摘要关键词：8分/词（可累计）
├─ 概念标签：5分
├─ 领域匹配：0-15分
├─ 期刊质量：10分
├─ 新近论文：0-10分
└─ 英文论文：5分
```

### 4. 渐进式搜索策略

```
第1轮：原始关键词
  ↓ 数量不足？
第2轮：同义词扩展（从术语库获取）
  ↓ 数量仍不足？
第3轮：简化查询（去掉修饰词）
```

## API 接口

### 1. 生成综述

**接口**: `POST /api/smart-generate`

**请求参数**:
```json
{
  "topic": "基于FMEA法的Agent开发项目风险管理研究",
  "target_count": 50,
  "recent_years_ratio": 0.5,
  "english_ratio": 0.3,
  "search_years": 10,
  "max_search_queries": 8
}
```

**响应**:
```json
{
  "success": true,
  "message": "任务已提交",
  "data": {
    "task_id": "751bdaa7",
    "status": "pending",
    "poll_url": "/api/tasks/751bdaa7"
  }
}
```

### 2. 查找文献（仅搜索）

**接口**: `POST /api/search-papers`

**请求参数**: 同上

**响应**:
```json
{
  "success": true,
  "data": {
    "outline": {...},
    "papers": [...],
    "statistics": {...}
  }
}
```

### 3. 智能分析

**接口**: `POST /api/smart-analyze`

**请求参数**:
```json
{
  "topic": "基于FMEA法的Agent开发项目风险管理研究"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "classification": {...},
    "outline": {...},
    "search_keywords": [...]
  }
}
```

### 4. 查询任务状态

**接口**: `GET /api/tasks/{task_id}`

**进度步骤**:
- `analyzing`: 正在分析题目
- `searching`: 正在搜索文献
- `filtering`: 正在筛选文献
- `generating`: 正在生成综述
- `validating`: 正在验证和修复引用

## 数据库表设计

### 阶段记录表

#### outline_generation_stages

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| task_id | String(50) | 任务ID |
| outline | JSON | 大纲结构 |
| search_queries | JSON | 搜索关键词 |
| execution_time | Float | 执行时间 |
| created_at | DateTime | 创建时间 |

#### paper_search_stages

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| task_id | String(50) | 任务ID |
| total_found | Integer | 找到的文献总数 |
| papers_by_section | JSON | 按小节分组的文献 |
| sources | JSON | 数据源列表 |
| created_at | DateTime | 创建时间 |

#### paper_filter_stages

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| task_id | String(50) | 任务ID |
| input_count | Integer | 输入文献数 |
| output_count | Integer | 输出文献数 |
| filtered_papers | JSON | 过滤后的文献 |
| created_at | DateTime | 创建时间 |

#### review_generation_stages

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| task_id | String(50) | 任务ID |
| review | Text | 综述内容（用于版本对比） |
| papers_summary | JSON | 引用文献摘要 |
| cited_papers_count | Integer | 引用文献数量 |
| created_at | DateTime | 创建时间 |

## 性能指标

```
Token 效率：
├─ 传统方式：~13,000 tokens
└─ Function Calling：~6,600 tokens（节省49%）

时间效率：
├─ 数据库优先：减少API调用
├─ 并发控制：最多3个任务同时执行
└─ 渐进式搜索：避免浪费API资源

质量保证：
├─ 相关性评分：确保高相关性论文优先
├─ 跨学科过滤：防止不相关引用
└─ 引用验证：确保引用格式正确
```

## 文件位置

| 组件 | 文件路径 |
|------|----------|
| 主流程 | `backend/services/review_task_executor.py` |
| 统一版本生成器 | `backend/services/review_generator_fc_unified.py` |
| 阶段记录服务 | `backend/services/stage_recorder.py` |
| 增强筛选服务 | `backend/services/paper_field_classifier.py` |
| 多数据源搜索 | `backend/services/scholarflux_wrapper.py` |
| 学术术语服务 | `backend/services/academic_term_service.py` |
| 引用验证 | `backend/services/reference_validator.py` |

## 更新历史

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-04-03 | 5.1 | **阶段记录追踪**、代码复用重构、Temperature优化、查找文献功能 |
| 2026-04-03 | 5.0 | Function Calling统一版本、增强相关性评分、跨学科过滤、渐进式搜索 |
| 2026-04-01 | 4.0 | 自然统计数据嵌入、深度对比分析、综述润色 |
| 2026-04-01 | 3.2 | 论文元数据数据库、智能搜索 |
| 2026-04-01 | 3.0 | 语言区分搜索、质量过滤 |

---

## 附录：阶段记录示例

```python
# 查询某个任务的所有阶段记录
async def get_task_stages(task_id: str):
    return {
        "outline": await db.get_outline_generation_stage(task_id),
        "search": await db.get_paper_search_stage(task_id),
        "filter": await db.get_paper_filter_stage(task_id),
        "review": await db.get_review_generation_stage(task_id)
    }

# 版本对比
async def compare_review_versions(task_id_1: str, task_id_2: str):
    stage_1 = await db.get_review_generation_stage(task_id_1)
    stage_2 = await db.get_review_generation_stage(task_id_2)
    
    return {
        "review_1": stage_1.review,
        "review_2": stage_2.review,
        "cited_count_diff": stage_2.cited_papers_count - stage_1.cited_papers_count
    }
```
