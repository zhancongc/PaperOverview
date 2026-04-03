# 综述生成流程文档

## 概述

本文档描述了论文综述生成器的完整生成流程。该流程采用**Function Calling渐进式信息披露**、**按小节文献管理**、**增强相关性评分**、**跨学科过滤**、**多数据源聚合**等技术，确保生成的综述质量。

## 版本信息

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| 5.0 | 2026-04-03 | Function Calling统一版本、增强相关性评分、跨学科过滤、渐进式搜索 |
| 4.0 | 2026-04-01 | 自然统计数据嵌入、深度对比分析、综述润色 |
| 3.2 | 2026-04-01 | 论文元数据数据库、智能搜索 |
| 3.0 | 2026-04-01 | 语言区分搜索、质量过滤 |

## 核心架构

### Service 类职责

| Service 类 | 文件 | 职责 |
|-----------|------|------|
| `ReviewTaskExecutor` | `services/review_task_executor.py` | 综述生成任务执行器（主流程） |
| `ReviewGeneratorFCUnified` | `services/review_generator_fc_unified.py` | **Function Calling统一版本生成器** |
| `EnhancedPaperFilterService` | `services/paper_field_classifier.py` | **增强筛选服务（相关性评分+跨学科过滤）** |
| `FrameworkGenerator` | `services/hybrid_classifier.py` | 题目分析、大纲生成、关键词提取 |
| `SmartPaperSearchService` | `services/smart_paper_search.py` | 智能搜索（数据库优先+API补充） |
| `ScholarFlux` | `services/scholarflux_wrapper.py` | 多数据源聚合搜索 |
| `AcademicTermService` | `services/academic_term_service.py` | **学术术语服务** |
| `ReferenceValidator` | `services/reference_validator.py` | 参考文献质量验证 |
| `ReviewRecordService` | `services/review_record_service.py` | 综述记录数据库操作 |

## 数据源配置

| 数据源 | 用途 | 语言 | API |
|--------|------|------|-----|
| OpenAlex | 英文文献搜索（主要） | 英文 | https://api.openalex.org |
| Crossref | 期刊/会议论文 | 英文 | https://api.crossref.org |
| DataCite | 研究数据集 | 英文 | https://api.datacite.org |
| Semantic Scholar | 补充搜索 | 全部 | https://api.semanticscholar.org |
| AMiner | 中文文献搜索 | 中文 | https://datacenter.aminer.cn |

## 完整流程

```
┌─────────────────────────────────────────────────────────────────────┐
│  输入：论文主题 + 参数                                              │
│  POST /api/submit-review-task                                     │
│  { topic, target_count, recent_years_ratio, english_ratio,         │
│    search_years, max_search_queries }                              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  阶段1: 生成大纲和搜索关键词                                        │
│  ─────────────────────────────────────────                         │
│  • 生成综述大纲（DeepSeek LLM）                                    │
│    - 引言：focus + key_papers                                     │
│    - 主体章节：2-5个（每个含 title, focus, key_points,             │
│                  comparison_points, search_keywords）             │
│    - 结论：待定（根据文献内容生成）                                │
│  • 提取每个小节的搜索关键词                                        │
│  • 获取场景特异性指导                                              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  阶段2: 搜索词优化（基本语言优化）                                  │
│  ─────────────────────────────────────────                         │
│  • 根据数据源类型使用不同语言                                        │
│    OPENALEX, CROSSREF, DATACITE → 英文                              │
│    AMINER, SEMANTIC_SCHOLAR → 中文/英文                             │
│  • 不扩展同义词/近义词（避免浪费API资源）                           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  阶段3: 按小节搜索文献（渐进式搜索策略）                             │
│  ─────────────────────────────────────────                         │
│  对每个小节：                                                      │
│    1. 优先从PostgreSQL数据库搜索                                   │
│    2. 数据库不足时使用API补充                                       │
│    3. 渐进式搜索（最多3轮）：                                       │
│       第1轮：原始关键词                                            │
│       第2轮：同义词扩展（从术语库获取）                             │
│       第3轮：简化查询                                              │
│    4. 小节内部去重                                                │
│    5. 小节间去重（保留文献少的小节的文献）                          │
│    6. 总数<100篇时补充搜索                                         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  阶段4: 精简文献到N篇（N = 50~60随机）                              │
│  ─────────────────────────────────────────                         │
│  1. 随机确定目标数量 N ∈ [50, 60]                                  │
│  2. 按小节比例分配文献数                                            │
│  3. 对每个小节进行筛选：                                            │
│     • 增强相关性评分（0-100分）                                     │
│       - 标题关键词匹配：20分/词                                    │
│       - 摘要关键词匹配：8分/词（可累计）                            │
│       - 概念标签匹配：5分                                          │
│       - 领域匹配：0-15分                                           │
│       - 期刊质量：10分                                             │
│       - 新近论文：0-10分                                           │
│     • 跨学科过滤                                                   │
│       - 自动分类论文领域                                           │
│       - 小节-领域映射                                              │
│       - 普适性章节检测（允许跨学科）                                │
│       - 兜底机制（不足时补充）                                      │
│  4. 按年份和语言比例筛选                                            │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  阶段5: 生成综述（Function Calling 统一版本）                       │
│  ─────────────────────────────────────────                         │
│  输入：                                                            │
│    • 大纲结构                                                      │
│    • 论文标题列表（轻量级，~600 tokens）                            │
│                                                                   │
│  流程：                                                            │
│    1. 发送大纲 + 标题列表给 LLM                                    │
│    2. 多轮对话循环：                                                │
│       LLM 生成内容                                                │
│       → 需要引用时调用 get_paper_details                           │
│       → 返回论文详细信息（摘要、作者等）                            │
│       → LLM 继续生成                                              │
│    3. 检查引用数量，不足则补充                                     │
│    4. 添加标题和参考文献                                           │
│                                                                   │
│  工具定义：                                                        │
│    • get_paper_details: 获取论文详情                               │
│    • search_papers_by_keyword: 按关键词搜索                         │
│                                                                   │
│  优势：                                                            │
│    • Token 节省 ~70%                                              │
│    • 全局连贯性好                                                 │
│    • 引用编号一次性正确                                            │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  阶段6: 最终验证                                                    │
│  ─────────────────────────────────────────                         │
│  • 验证引用格式和编号                                               │
│  • 检查所有引用是否在论文列表中                                     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  阶段7: 统计和保存                                                  │
│  ─────────────────────────────────────────                         │
│  • 计算统计信息（总数、中英文比例、近5年比例）                        │
│  • 标记文献是否被引用                                               │
│  • 保存到PostgreSQL数据库                                          │
│  • 更新任务状态为 COMPLETED                                        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
                    输出：完整综述（Markdown格式）
```

## 核心设计决策

### 1. Function Calling 渐进式信息披露

**问题**：一次性发送60篇完整论文（标题+摘要+作者）消耗大量token

**解决方案**：
- 初始只发送论文标题列表（~600 tokens）
- LLM按需调用 `get_paper_details` 获取论文详情
- Token节省：~49%（13,000 → 6,600）

**实现**：`ReviewGeneratorFCUnified` 类

**优势**：
- Token节省49%
- 注意力更集中（只处理需要的论文）
- 全局连贯性好（一次性生成）

### 2. 增强相关性评分

**问题**：简单的关键词匹配无法准确评估论文相关性

**解决方案**：
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

**实现**：`EnhancedPaperFilterService._calculate_enhanced_relevance_score()`

### 3. 跨学科过滤

**问题**：材料章节可能引用医学论文（不相关）

**解决方案**：
- 自动分类论文领域（materials, medicine, cs等）
- 小节-领域映射：
  - "材料制备" → [materials, chemistry, engineering]
  - "质量管理" → [management, engineering]
  - "方法普适性研究" → [所有领域]
- 过滤不匹配的论文
- 兜底：不足时补充高相关性跨学科论文

**实现**：`PaperFieldClassifier` + `SectionFieldMatcher`

### 4. 渐进式搜索策略

**问题**：一次性搜索所有同义词组合浪费API资源

**解决方案**：
```
第1轮：原始关键词
  ↓ 数量不足？
第2轮：同义词扩展（从术语库获取）
  ↓ 数量仍不足？
第3轮：简化查询（去掉修饰词）
```

**优势**：
- 避免浪费API资源
- 优先使用原始关键词（最相关）
- 按需扩展

### 5. 按小节文献管理

**问题**：所有论文共享导致引用分配不均

**解决方案**：
- 每个小节搜索专属文献
- 小节间去重（保留文献少的小节的文献）
- 每个小节分配固定数量的论文
- 生成时每个小节引用自己的专属论文

**优势**：
- 引用分配均匀
- 每个小节都有充足的引用
- 避免某些小节引用不足

### 6. 数据库优先搜索

**问题**：每次搜索都调用外部API，效率低

**解决方案**：
- 优先从PostgreSQL数据库搜索
- 不足时再调用外部API
- 自动保存新搜索到的论文

**优势**：
- 避免重复搜索
- 提高搜索速度
- 积累论文资产

## 增强相关性评分详解

### 评分算法

```python
def _calculate_enhanced_relevance_score(paper, topic_keywords):
    score = 0.0

    # 1. 被引量（0-25分）
    citations = paper.get("cited_by_count", 0)
    score += min(citations / 10, 25)

    # 2. 标题关键词匹配（20分/词）
    title_lower = paper.get("title", "").lower()
    for kw in topic_keywords:
        if kw.lower() in title_lower:
            score += 20

    # 3. 摘要关键词匹配（8分/词，可累计）
    abstract_lower = paper.get("abstract", "").lower()
    for kw in topic_keywords:
        if kw.lower() in abstract_lower:
            score += 8

    # 4. 概念标签匹配（5分）
    concepts = paper.get("concepts", [])
    for concept in concepts:
        for kw in topic_keywords:
            if kw.lower() in concept.lower():
                score += 5
                break

    # 5. 领域匹配（0-15分）
    field_confidence = paper.get("field_confidence", 0)
    score += field_confidence * 15

    # 6. 期刊质量（10分）
    high_quality_venues = ["nature", "science", "cell", ...]
    if any(venue in paper.get("venue_name", "").lower() 
           for venue in high_quality_venues):
        score += 10

    # 7. 新近论文（0-10分）
    if paper.get("year", 0) >= current_year - 3:
        score += 10
    elif paper.get("year", 0) >= current_year - 5:
        score += 5

    return min(score, 100)
```

### 跨学科过滤

```python
# 领域分类
FIELD_KEYWORDS = {
    FieldCategory.MATERIALS: {
        "journals": ["nature materials", "advanced materials", ...],
        "keywords": ["材料", "合成", "制备", "表征", ...],
        "concepts": ["materials science", "nanotechnology", ...]
    },
    FieldCategory.MEDICINE: {
        "journals": ["new england journal of medicine", ...],
        "keywords": ["医学", "临床", "病理", ...],
        "concepts": ["medicine", "clinical medicine", ...]
    },
    # ...
}

# 小节-领域映射
SECTION_FIELD_MAPPING = {
    "材料制备": [FieldCategory.MATERIALS, FieldCategory.CHEMISTRY],
    "质量管理": [FieldCategory.MANAGEMENT, FieldCategory.ENGINEERING],
    # ...
}

# 过滤逻辑
def is_paper_allowed_for_section(paper, section_name):
    paper_field = classify_paper(paper)
    allowed_fields = SECTION_FIELD_MAPPING.get(section_name)
    return paper_field in allowed_fields
```

## Function Calling 工作流程

```
用户请求
    ↓
发送：大纲 + 论文标题列表（60篇）
    ↓
┌─────────────────────────────────────┐
│ LLM 开始生成                        │
│ "深度学习在图像识别中..."           │
│ 需要引用 → 调用 get_paper_details(3)│
└─────────────────────────────────────┘
    ↓
返回：论文3的摘要、作者、年份...
    ↓
┌─────────────────────────────────────┐
│ LLM 继续生成                        │
│ "张三等[3]提出了一种新的..."        │
│ 需要引用 → 调用 get_paper_details(7)│
└─────────────────────────────────────┘
    ↓
返回：论文7的摘要、作者、年份...
    ↓
...（重复多次）
    ↓
┌─────────────────────────────────────┐
│ LLM 完成生成                        │
│ 输出完整综述                        │
└─────────────────────────────────────┘
```

## 环境变量配置

```bash
# DeepSeek API（用于LLM生成）
DEEPSEEK_API_KEY=sk-xxx

# AMiner API（用于中文文献搜索）
AMINER_API_TOKEN=eyJxxx

# PostgreSQL 数据库
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=xxx
DB_NAME=paper
DB_TYPE=postgresql
```

## 数据库表

### paper_metadata（论文元数据表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(100) | 论文ID（主键） |
| title | String(1000) | 论文标题 |
| authors | JSON | 作者列表 |
| year | Integer | 发表年份 |
| abstract | Text | 摘要 |
| cited_by_count | Integer | 被引次数 |
| is_english | Boolean | 是否英文文献 |
| type | String(50) | 文献类型 |
| doi | String(200) | DOI |
| concepts | JSON | 概念标签 |
| venue_name | String(500) | 期刊/会议名称 |
| source | JSON | 数据源列表 ['openalex', 'semantic_scholar'] |
| url | String(1000) | 论文链接 |
| created_at | DateTime | 首次入库时间 |
| updated_at | DateTime | 更新时间 |

### review_records（综述记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 记录ID（主键，自增） |
| topic | String(500) | 论文主题 |
| review | Text | 综述内容 |
| papers | JSON | 论文列表 |
| statistics | JSON | 统计信息 |
| status | String(20) | 状态（pending/processing/completed/failed） |
| target_count | Integer | 目标文献数 |
| recent_years_ratio | Float | 近5年占比要求 |
| english_ratio | Float | 英文文献占比要求 |
| error_message | Text | 错误信息 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### academic_terms（学术术语表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 术语ID（主键，自增） |
| chinese_term | String(200) | 中文术语 |
| english_terms | JSON | 英文术语列表 |
| category | String(50) | 分类（dl/bio/ml等） |
| subcategory | String(50) | 子分类 |
| aliases | JSON | 别名列表 |
| description | Text | 描述 |
| priority | Integer | 优先级 |
| is_active | Boolean | 是否活跃 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 验证标准

| 验证项 | 默认要求 | 说明 |
|--------|----------|------|
| 引用数量 | >= 50 | 可通过 `target_count` 参数调整 |
| 近5年占比 | >= 50% | 可通过 `recent_years_ratio` 参数调整 |
| 英文文献占比 | 30%-70% | 可通过 `english_ratio` 参数调整 |

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

## 测试结果

```
测试：8篇论文，3个小节
├─ 迭代次数：9
├─ 工具调用：8次
├─ 访问论文：7篇
├─ 引用率：100%
└─ 内容长度：2,547字符
```

## 文件位置

| 组件 | 文件路径 |
|------|----------|
| 主流程 | `backend/services/review_task_executor.py` |
| 统一版本生成器 | `backend/services/review_generator_fc_unified.py` |
| 增强筛选服务 | `backend/services/paper_field_classifier.py` |
| 多数据源搜索 | `backend/services/scholarflux_wrapper.py` |
| 学术术语服务 | `backend/services/academic_term_service.py` |
| 引用验证 | `backend/services/reference_validator.py` |

## 更新历史

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-04-03 | 5.0 | **Function Calling统一版本**、增强相关性评分、跨学科过滤、渐进式搜索、按小节文献管理、学术术语服务 |
| 2026-04-01 | 4.0 | 自然统计数据嵌入、深度对比分析、综述润色 |
| 2026-04-01 | 3.2 | 论文元数据数据库、智能搜索 |
| 2026-04-01 | 3.0 | 语言区分搜索、质量过滤 |
| 2026-03-31 | 2.0 | 重构验证流程 |
| 2026-03-30 | 1.0 | 初始版本 |

---

## 附录：Function Calling 工具定义

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_paper_details",
            "description": "获取论文的详细信息（摘要、作者、年份等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_index": {
                        "type": "integer",
                        "description": "论文在列表中的索引（1-60）"
                    }
                },
                "required": ["paper_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_papers_by_keyword",
            "description": "根据关键词搜索论文",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["keyword"]
            }
        }
    }
]
```
