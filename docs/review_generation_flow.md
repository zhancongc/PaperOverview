# 综述生成流程文档

## 概述

本文档描述了论文综述生成器API的智能生成综述流程（`/api/smart-generate`）。该流程采用混合分类器、多数据源搜索、语言区分搜索、质量过滤、LLM生成和质量验证反馈循环，确保生成的综述质量。

## 架构组件

### Service 类职责

| Service 类 | 文件 | 职责 |
|-----------|------|------|
| `FrameworkGenerator` | `services/hybrid_classifier.py` | 题目分析、关键词提取、搜索查询生成 |
| `ScholarFlux` | `services/scholarflux_wrapper.py` | 统一文献搜索API（多数据源聚合、语言区分） |
| `PaperQualityFilter` | `services/paper_quality_filter.py` | 文献质量过滤（过滤低质量文献） |
| `PaperFilterService` | `services/paper_filter.py` | 文献筛选、相关性评分、统计计算 |
| `ReviewGeneratorService` | `services/review_generator.py` | 综述生成、引用处理、编号管理 |
| `AMinerPaperDetailService` | `services/aminer_paper_detail.py` | 论文详情补充（获取作者、DOI） |
| `ReferenceValidator` | `services/reference_validator.py` | 参考文献质量验证 |
| `ReviewRecordService` | `services/review_record_service.py` | 综述记录数据库操作 |

## 数据源配置

| 数据源 | 用途 | 语言 | API |
|--------|------|------|-----|
| AMiner | 中文文献搜索 | 中文/混合 | https://datacenter.aminer.cn |
| OpenAlex | 英文文献搜索 | 英文 | https://api.openalex.org |
| Semantic Scholar | 补充搜索 | 全部 | https://api.semanticscholar.org |

## 完整流程

```
┌─────────────────────────────────────────────────────────────────────┐
│  0. 用户请求                                                         │
│     POST /api/smart-generate                                        │
│     { topic, target_count, recent_years_ratio, english_ratio,       │
│       search_years, max_search_queries }                            │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. 智能分析题目（FrameworkGenerator）                              │
│     - 混合分类器：规则提取 + LLM验证优化                            │
│     - 识别题目类型：应用型/评价型/理论型/实证型                     │
│     - 生成搜索查询（search_queries）                                │
│       • 每个查询包含：query, section, lang, keywords, search_mode   │
│       • lang: 'zh'（中文）、'en'（英文）或 None（自动）             │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. 多数据源文献搜索（ScholarFlux）【语言区分】                     │
│                                                                     │
│   对每个搜索查询（最多 max_search_queries 个）：                    │
│     • 中文查询（lang='zh'）→ 仅使用 AMiner                         │
│     • 英文查询（lang='en'）→ 使用 OpenAlex + Semantic Scholar      │
│     • 未指定语言 → 使用所有数据源                                  │
│                                                                     │
│   AMiner 特殊处理：                                                 │
│     • 支持 title + keywords 双关键词组合搜索                       │
│     • 使用 pro_search 接口提升相关度                               │
│                                                                     │
│   每个查询：years_ago=search_years, limit=50                       │
│   补充搜索：如果总数 < 20，扩大年份范围继续搜索                    │
│                                                                     │
│   → 去重（基于 paper.id）                                          │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. 质量过滤（PaperQualityFilter）【新增】                         │
│     - 过滤低质量文献：                                             │
│       • 会议通知、会议记录、工作会议等                             │
│       • 内部资料、工作简报、年度报告等                             │
│       • 新闻、通知、公告等                                         │
│       • 机构仓储无被引文献                                         │
│       • 作者为"佚名"、"匿名"的文献（部分过滤）                     │
│     - 计算质量得分（0-100）                                        │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. 提取主题关键词（FrameworkGenerator.extract_relevance_keywords）│
│     - 从 key_elements 中提取                                        │
│     - 从 variables 中提取（实证型）                                 │
│     - 处理缩写（QFD、FMEA、DMAIC、AHP）                             │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. 筛选文献（PaperFilterService.filter_and_sort）                  │
│     - 按相关性评分排序（关键词匹配度）                               │
│     - 按时间分布筛选（近5年占比）                                    │
│     - 按语言筛选（英文文献占比）                                     │
│     → 输出：候选池（100+篇）                                        │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  6-8. 生成综述 + 验证被引用文献（带重试循环）【核心】              │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │  Loop (最多2次):                                         │      │
│   │                                                          │      │
│   │  6. 生成综述 (ReviewGeneratorService)                   │      │
│   │     ┌────────────────────────────────────────────────┐  │      │
│   │     │ 6.1 LLM从候选池中选择文献引用                   │  │      │
│   │     │ 6.2 按首次出现顺序重新编号                      │  │      │
│   │     │ 6.3 补充论文详情（AMiner API）【新增】          │  │      │
│   │     │     • 获取缺失的作者信息                         │  │      │
│   │     │     • 获取缺失的 DOI                             │  │      │
│   │     │ 6.4 过滤佚名论文【新增】                         │  │      │
│   │     │     • 过滤作者为"佚名"、"匿名"、"未知作者"的论文 │  │      │
│   │     │     • 重新编号引用                               │  │      │
│   │     │ 6.5 限制每篇文献引用次数（最多2次）              │  │      │
│   │     │ 6.6 排序并合并连续引用【新增】                   │  │      │
│   │     │     • [35][34][36][47] → [34-36][47]            │  │      │
│   │     │ 6.7 格式化参考文献列表                           │  │      │
│   │     └────────────────────────────────────────────────┘  │      │
│   │                                                          │      │
│   │  7. 验证被引用文献质量                                  │      │
│   │     - validate_citation_count(): 引用数量 >= target?    │      │
│   │     - validate_recent_ratio(): 近5年占比 >= 用户要求?    │      │
│   │     - validate_english_ratio(): 英文占比 >= 用户要求?    │      │
│   │                                                          │      │
│   │  8. 决策：                                                │      │
│   │     - 全部通过 → 退出循环                                 │      │
│   │     - 不通过 + 未达最大重试 → 扩大候选池重新生成        │      │
│   │     - 不通过 + 达到最大重试 → 标记 validation_failed     │      │
│   │                                                          │      │
│   └─────────────────────────────────────────────────────────┘      │
│                                                                     │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  9. 计算统计信息（PaperFilterService.get_statistics）               │
│     - 基于最终被引用的文献计算（不是候选池）                         │
│     - 总数、近5年占比、英文占比、平均被引量                         │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  10. 最终验证 + 保存记录                                            │
│      - validate_review(): 完整验证                                  │
│      - ReviewRecordService.update_success(): 保存到数据库          │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  返回结果                                                            │
│  {                                                                   │
│    id, topic, review, papers (候选池),                              │
│    statistics, analysis, search_queries_results,                    │
│    cited_papers_count, validation_passed, validation                │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心设计决策

### 1. 语言区分搜索

**问题**：OpenAlex 对中文文献的支持质量较差

**解决方案**：
- 中文查询（`lang='zh'`）→ 仅使用 AMiner
- 英文查询（`lang='en'`）→ 使用 OpenAlex + Semantic Scholar
- 未指定语言 → 使用所有数据源

**实现**：`ScholarFlux.search()` 方法根据 `lang` 参数选择数据源

### 2. AMiner 双关键词组合搜索

**问题**：单关键词搜索相关度不够

**解决方案**：
- 使用 `title` + `keywords` 双关键词组合
- 通过 AMiner Pro API 实现：`/paper/search/pro`

**效果**：大幅提升搜索结果相关度

### 3. 质量过滤

**问题**：搜索结果中包含大量低质量文献

**解决方案**：
- 过滤会议通知、内部资料、新闻通知等
- 过滤机构仓储中无被引的文献
- 过滤作者为"佚名"的文献

**实现**：`PaperQualityFilter` 类

### 4. 论文详情补充

**问题**：部分文献缺少作者或DOI信息

**解决方案**：
- 使用 AMiner API 获取完整论文信息
- 并发请求，限制速率避免超限

**实现**：`AMinerPaperDetailService.enrich_papers()`

### 5. 引用排序和合并

**问题**：LLM生成的引用顺序混乱，如 `[35][34][36][47]`

**解决方案**：
- 按首次出现顺序重新编号
- 过滤佚名论文后重新编号
- 排序并合并连续引用

**实现**：`_sort_and_merge_citations()` 方法

**效果**：`[35][34][36][47]` → `[34-36][47]`

### 6. 验证时机：生成后验证

**问题**：为什么不在筛选后验证候选池？

**答案**：
- 候选池（100+篇）只是供LLM选择的范围
- LLM最终可能只引用其中50篇
- 验证候选池无法保证LLM选择的文献达标

**解决方案**：在LLM生成综述后，验证其**实际引用**的文献质量。

## 引用处理流程详解

```
原始AI生成内容
    ↓
[5][3][4][6]... （顺序混乱）
    ↓
┌─────────────────────────────────────────┐
│ 按首次出现重新编号                        │
│ [5][3][4][6] → [1][2][3][4]              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 补充论文详情（AMiner API）               │
│ 获取缺失的作者和DOI                      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 过滤佚名论文                              │
│ 移除作者为"佚名"的论文                    │
│ 重新编号：[1][2][3][4] → [1][2][4]       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 限制引用次数（每篇最多2次）               │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 排序并合并连续引用                        │
│ [1][2][4] → [1-2][4]                     │
└─────────────────────────────────────────┘
    ↓
最终格式化内容
```

## API 请求/响应

### 请求

```json
POST /api/smart-generate
{
  "topic": "基于QFD和PFMEA的螺纹钢质量管理研究",
  "target_count": 50,
  "recent_years_ratio": 0.5,
  "english_ratio": 0.3,
  "search_years": 10,
  "max_search_queries": 8
}
```

### 响应

```json
{
  "success": true,
  "message": "文献综述生成成功",
  "data": {
    "id": 1,
    "topic": "基于QFD和PFMEA的螺纹钢质量管理研究",
    "review": "综述内容...",
    "papers": [...],
    "statistics": {
      "total": 52,
      "recent_count": 30,
      "recent_ratio": 0.58,
      "english_count": 18,
      "english_ratio": 0.35
    },
    "analysis": {
      "type": "application",
      "key_elements": {...},
      "search_queries": [...]
    },
    "search_queries_results": [...],
    "cited_papers_count": 52,
    "validation_passed": true,
    "validation": {
      "passed": true,
      "warnings": [],
      "details": {...}
    },
    "created_at": "2026-04-01T10:30:00"
  }
}
```

## 验证标准

| 验证项 | 默认要求 | 说明 |
|--------|----------|------|
| 引用数量 | >= 50 | 可通过 `target_count` 参数调整 |
| 近5年占比 | >= 50% | 可通过 `recent_years_ratio` 参数调整 |
| 英文文献占比 | >= 30% | 可通过 `english_ratio` 参数调整 |

## 环境变量配置

```bash
# DeepSeek API（用于LLM生成）
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# AMiner API（用于中文文献搜索和详情补充）
AMINER_API_TOKEN=eyJxxx

# MySQL 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=xxx
DB_NAME=paper
```

## 文件位置

| 组件 | 文件路径 |
|------|----------|
| API接口 | `backend/main.py` - `/api/smart-generate` |
| 题目分析 | `backend/services/hybrid_classifier.py` |
| 文献搜索 | `backend/services/scholarflux_wrapper.py` |
| AMiner搜索 | `backend/services/aminer_search.py` |
| 质量过滤 | `backend/services/paper_quality_filter.py` |
| 论文筛选 | `backend/services/paper_filter.py` |
| 综述生成 | `backend/services/review_generator.py` |
| 详情补充 | `backend/services/aminer_paper_detail.py` |
| 引用验证 | `backend/services/reference_validator.py` |
| 数据记录 | `backend/services/review_record_service.py` |

## 更新历史

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-04-01 | 3.0 | 语言区分搜索、质量过滤、论文详情补充、引用排序合并、佚名论文过滤 |
| 2026-03-31 | 2.1 | 增加初始文献搜索数量：每个查询50篇，补充搜索确保至少150篇 |
| 2026-03-31 | 2.0 | 重构验证流程：验证被引用文献而非候选池 |
| 2026-03-30 | 1.0 | 初始版本 |
