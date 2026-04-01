# 综述生成流程文档

## 概述

本文档描述了论文综述生成器API的智能生成综述流程（`/api/smart-generate`）。该流程采用混合分类器、多数据源搜索、语言区分搜索、质量过滤、LLM生成和质量验证反馈循环，确保生成的综述质量。

## 架构组件

### Service 类职责

| Service 类 | 文件 | 职责 |
|-----------|------|------|
| `FrameworkGenerator` | `services/hybrid_classifier.py` | 题目分析、关键词提取、搜索查询生成 |
| `SmartPaperSearchService` | `services/smart_paper_search.py` | 智能搜索（先查数据库，再查外部API） |
| `ScholarFlux` | `services/scholarflux_wrapper.py` | 统一文献搜索API（多数据源聚合、语言区分） |
| `PaperQualityFilter` | `services/paper_quality_filter.py` | 文献质量过滤（过滤低质量文献） |
| `PaperFilterService` | `services/paper_filter.py` | 文献筛选、相关性评分、统计计算 |
| `ReviewGeneratorService` | `services/review_generator.py` | 综述生成、引用处理、编号管理 |
| `AMinerPaperDetailService` | `services/aminer_paper_detail.py` | 论文详情补充（获取作者、DOI） |
| `PaperMetadataDAO` | `services/paper_metadata_dao.py` | 论文元数据数据库操作 |
| `ReferenceValidator` | `services/reference_validator.py` | 参考文献质量验证 |
| `ReviewRecordService` | `services/review_record_service.py` | 综述记录数据库操作 |
| `NaturalStatisticsIntegrator` | `services/natural_statistics.py` | 自然统计数据嵌入（避免AI痕迹） |
| `DeepComparisonAnalyzer` | `services/deep_comparison.py` | 深度对比分析（追问分歧原因） |
| `AIToneEliminator` | `services/review_polisher.py` | AI腔消除（综述润色） |
| `ControversyAnalyzer` | `services/controversy_analyzer.py` | 争议与对话分析（观点碰撞） |
| `CitationSplitter` | `services/citation_splitter.py` | 连续引用拆分（[1-5]→结构化陈述） |

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
│  2. 智能文献搜索（SmartPaperSearchService）【先数据库后外部】       │
│                                                                     │
│   对每个搜索查询（最多 max_search_queries 个）：                    │
│     • 先从本地数据库搜索（paper_metadata表）                       │
│     • 不足时再调用外部API                                          │
│                                                                     │
│   外部API语言区分：                                                 │
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
│   → 自动保存到数据库（PaperMetadataDAO）【新增】                   │
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

### 1. 论文元数据数据库

**问题**：每次搜索都调用外部API，效率低且消耗配额

**解决方案**：
- 创建 `paper_metadata` 表存储所有搜索到的论文
- 搜索时优先查询本地数据库
- 不足时再调用外部API
- 自动保存新搜索到的论文到数据库

**实现**：
- `SmartPaperSearchService`：智能搜索服务
- `PaperMetadataDAO`：数据库访问层
- `ScholarFlux._save_papers_to_db()`：自动保存

**优势**：
- 避免重复搜索相同论文
- 提高搜索速度
- 减少API调用消耗
- 积累论文资产

### 2. 语言区分搜索

**问题**：OpenAlex 对中文文献的支持质量较差

**解决方案**：
- 中文查询（`lang='zh'`）→ 仅使用 AMiner
- 英文查询（`lang='en'`）→ 使用 OpenAlex + Semantic Scholar
- 未指定语言 → 使用所有数据源

**实现**：`ScholarFlux.search()` 方法根据 `lang` 参数选择数据源

### 3. AMiner 双关键词组合搜索

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
| 引用数量 | >= 50 | 可通过 `target_count` 参数调整（10-100） |
| 近5年占比 | >= 50% | 可通过 `recent_years_ratio` 参数调整（50%-100%） |
| 英文文献占比 | 30%-70% | 可通过 `english_ratio` 参数调整（30%-70%） |

**说明**：
- 近5年文献占比：**不低于50%**（硬性要求）
- 外文文献占比：**30%-70%之间**（上下限限制）
- 如果验证未通过，系统会自动扩大搜索范围重新采集文献

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
| 智能搜索 | `backend/services/smart_paper_search.py` |
| 文献搜索 | `backend/services/scholarflux_wrapper.py` |
| AMiner搜索 | `backend/services/aminer_search.py` |
| 题目分析 | `backend/services/hybrid_classifier.py` |
| 质量过滤 | `backend/services/paper_quality_filter.py` |
| 论文筛选 | `backend/services/paper_filter.py` |
| 论文DAO | `backend/services/paper_metadata_dao.py` |
| 综述生成 | `backend/services/review_generator.py` |
| 详情补充 | `backend/services/aminer_paper_detail.py` |
| 引用验证 | `backend/services/reference_validator.py` |
| 数据记录 | `backend/services/review_record_service.py` |

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
| issue | String(50) | 卷号 |
| source | String(50) | 数据源（aminer/openalex/semantic_scholar） |
| url | String(1000) | 论文链接 |
| created_at | DateTime | 首次入库时间 |
| updated_at | DateTime | 更新时间 |

## 新增API接口

### 论文库管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/papers/statistics` | GET | 获取论文库统计信息 |
| `/api/papers/recent` | GET | 获取最近入库的论文 |
| `/api/papers/top-cited` | GET | 获取高被引论文 |

## 更新历史

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-04-01 | 4.0 | 自然统计数据嵌入、深度对比分析、综述润色、连续引用拆分、观点碰撞分析 |
| 2026-04-01 | 3.2 | 论文元数据数据库、智能搜索、论文库管理API |
| 2026-04-01 | 3.1 | 文献占比限制：外文30%-70%，近5年不低于50%；强化对比分析撰写 |
| 2026-04-01 | 3.0 | 语言区分搜索、质量过滤、论文详情补充、引用排序合并、佚名论文过滤 |
| 2026-03-31 | 2.1 | 增加初始文献搜索数量：每个查询50篇，补充搜索确保至少150篇 |
| 2026-03-31 | 2.0 | 重构验证流程：验证被引用文献而非候选池 |
| 2026-03-30 | 1.0 | 初始版本 |

---

## 高级功能（v4.0）

### 1. 自然统计数据嵌入

**问题**：AI生成的综述常使用 `(OR=0.65, p<0.001)` 风格的引用，AI痕迹明显

**解决方案**：
- 只对重要发现嵌入数据（突破性发现、大样本、高度显著）
- 数据自然融入叙述："Zhang等[1]发现实施QFD后产品缺陷率下降了35%"

**实现**：`NaturalStatisticsIntegrator` 类

**使用判断**：
- 突破性发现（OR<0.5或>2.0, r≥0.7, Cohen's d≥0.8）
- 大样本研究（n≥1000）
- 高度显著（p<0.001）
- 边界条件/负面发现
- 常规发现不使用数据（避免冗余）

### 2. 深度对比分析

**问题**：文献对比只列出对立观点，未分析分歧原因

**解决方案**：
- 不仅列出观点差异，还追问"这种分歧可能源于..."
- 推断分歧原因：样本差异、方法差异、情境差异、理论差异

**实现**：`DeepComparisonAnalyzer` 类

**输出格式**：
```
关于媒体关注的效应，现有研究存在分歧。Zhang等[1]发现显著负相关；
Smith等[2]则发现压力效应；Chen等[3]指出治理水平的调节作用。

> **这种分歧可能源于：**
> - **研究对象差异**：Zhang等[1]基于中国市场，而Smith等[2]研究美国企业
> - **样本情境差异**：Smith等[2]聚焦于业绩压力情境
> - **理论视角差异**：Zhang等[1]强调监督理论，而Smith等[2]关注压力应对理论
```

### 3. 综述润色（消除AI腔）

**问题**：AI生成文本包含大量"AI腔"词汇

**解决方案**：
- 删除："近年来"、"值得注意的是"、"换言之"、"显而易见"等
- 删除："随着...的发展"、"在...背景下"等背景铺垫
- 删除："一方面...另一方面"、"此外"、"另外"等过渡词

**实现**：`AIToneEliminator` 类

**压缩效果**：通常可压缩30%-40%的文本

### 4. 连续引用拆分

**问题**：连续引用 `[1-5]` 难以识别具体文献

**解决方案**：
- 检测连续引用如 `[1-5]`, `[1,2,3,4,5]`
- 拆分为结构化陈述："A等[x]...；B等[y]则..."

**实现**：`CitationSplitter` 类

**示例**：
```
原始：多项研究[1-5]支持QFD的积极作用
拆分：Zhang等[1]发现...；Li等[2]指出...；Wang等[3]证实...
```

### 5. 观点碰撞分析

**问题**：综述缺乏对学术争议的结构化分析

**解决方案**：
- 提取核心观点并分组
- 识别对立观点
- 分析分歧原因

**实现**：`ControversyAnalyzer` 类

**输出格式**：
```markdown
## 争议与对话

### 对立观点A：支持派
- 核心论点：...
- 支持文献：[1-3]

### 对立观点B：反对派
- 核心论点：...
- 支持文献：[4-5]

### 可能的原因
1. 样本差异：...
2. 方法差异：...
```
