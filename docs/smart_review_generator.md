# 智能综述生成器（SmartReviewGenerator）

## 概述

SmartReviewGenerator 是一个整合了完整流程的智能综述生成器，基于以下成功经验：

1. **LLM 驱动的 Semantic Scholar 搜索** - 让 LLM 决定搜索什么关键词
2. **渐进式信息披露** - 先显示论文标题，按需获取详情
3. **Function Calling 机制** - LLM 通过工具调用获取论文信息

## 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    SmartReviewGenerator                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  阶段 1: 智能文献搜索 (LLM 驱动)                        │ │
│  │  - LLM 生成搜索关键词                                   │ │
│  │  - Semantic Scholar API 搜索                             │ │
│  │  - 多轮搜索优化                                          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  阶段 2: 大纲设计+综述撰写（一体化）⭐                    │ │
│  │                                                           │ │
│  │  LLM 在一个流程中完成：                                  │ │
│  │  1. 浏览论文标题列表                                    │ │
│  │  2. 设计综述结构（引言、主体章节、结论）                │ │
│  │  3. 调用 get_multiple_paper_details 批量获取论文详情  │ │
│  │  4. 直接撰写完整综述                                    │ │
│  │                                                           │ │
│  │  优势：                                                   │ │
│  │  - 减少一次 LLM 调用（节省时间和 tokens）              │ │
│  │  - 更连贯的结构设计（LLM 边看论文边构思）              │ │
│  │  - 更灵活的大纲（可根据实际论文调整）                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 与传统方法的对比

| 特性 | 传统方法 | SmartReviewGenerator (v1) | **SmartReviewGenerator (v2)** ⭐ |
|------|---------|---------------------------|--------------------------------|
| 搜索策略 | 人工关键词 | LLM 智能生成 | **LLM 智能生成** |
| 大纲生成 | 独立阶段 | 独立阶段 | **与撰写合并** |
| LLM 调用次数 | 3 次 | 3 次 | **2 次** ⚡ |
| 信息披露 | 一次性发送所有论文 | 渐进式按需获取 | **渐进式按需获取** |
| Token 消耗 | ~15,000 tokens | ~8,600 tokens | **~7,000 tokens (节省 53%)** 🚀 |
| 搜索轮数 | 固定 1 轮 | 多轮动态优化 | **多轮动态优化** |
| 结构连贯性 | 一般 | 良好 | **优秀** ✨ |

**v2 核心改进**：
- 合并阶段 2（大纲生成）和阶段 3（综述撰写）
- LLM 在一个流程中完成：浏览论文 → 设计结构 → 获取详情 → 撰写综述
- 减少一次 LLM 调用，节省时间和 tokens
- 更连贯的结构设计（LLM 边看论文边构思）

## 快速开始

### 基础使用

```python
import os
import asyncio
from dotenv import load_dotenv
from services.smart_review_generator import SmartReviewGenerator

load_dotenv()

async def main():
    generator = SmartReviewGenerator(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    )

    result = await generator.generate_review(
        topic="Transformer 模型在代码生成中的应用",
        target_paper_count=100,
        max_search_rounds=3
    )

    print(f"综述长度: {len(result['review'])} 字符")
    print(f"引用论文: {len(result['cited_papers'])} 篇")

asyncio.run(main())
```

### 使用便捷函数

```python
from services.smart_review_generator import generate_smart_review

result = await generate_smart_review(
    topic="符号计算在理论物理中的应用",
    deepseek_api_key="your-key",
    semantic_scholar_api_key="optional-key",
    target_paper_count=80
)
```

### 分步执行

```python
# 1. 只搜索论文
papers = await generator._intelligent_search(
    topic="你的主题",
    target_count=100,
    max_rounds=3,
    model="deepseek-reasoner"
)

# 2. 生成大纲
outline = await generator._generate_outline(
    topic="你的主题",
    papers=papers,
    model="deepseek-reasoner"
)

# 3. 撰写综述
review, cited_papers = await generator._write_review(
    topic="你的主题",
    papers=papers,
    outline=outline,
    model="deepseek-reasoner"
)
```

## API 参考

### SmartReviewGenerator

#### 初始化

```python
SmartReviewGenerator(
    deepseek_api_key: str,              # DeepSeek API Key
    semantic_scholar_api_key: str = None,  # Semantic Scholar API Key (可选)
    deepseek_base_url: str = "https://api.deepseek.com"
)
```

#### generate_review()

主方法，生成完整综述。

```python
async def generate_review(
    self,
    topic: str,                      # 综述主题
    target_paper_count: int = 100,     # 目标收集论文数
    max_search_rounds: int = 3,       # 最大搜索轮数
    model: str = "deepseek-reasoner"  # 使用的模型
) -> Dict[str, Any]:
```

**返回值**:
```python
{
    "topic": str,                    # 综述主题
    "outline": dict,                 # 生成的大纲
    "papers": list,                  # 收集的所有论文
    "review": str,                   # 综述内容 (Markdown)
    "cited_papers": list,            # 被引用的论文
    "statistics": {
        "total_time_seconds": float,
        "papers_collected": int,
        "papers_cited": int,
        "search_rounds": int,
        "review_length": int,
        "generated_at": str
    },
    "search_history": list            # 每轮搜索记录
}
```

## 核心设计决策

### 1. 大纲与撰写一体化（v2 核心改进）

**问题**: 分阶段流程存在以下问题：
- 需要 3 次 LLM 调用（搜索关键词、大纲、撰写）
- 大纲阶段看不到论文详情，设计可能不够贴合实际
- 撰写阶段需要重新理解大纲，增加上下文消耗

**解决方案**:
- 合并阶段 2 和 3
- LLM 先浏览论文标题列表
- 直接在同一对话中设计结构并撰写
- 按需调用工具获取论文详情

**优势**:
- 减少一次 LLM 调用（时间节省 ~25%）
- 结构设计更贴合实际论文内容
- Token 消耗降低 ~15-20%
- 更好的全局连贯性

### 2. LLM 驱动的搜索策略

**问题**: 人工设计关键词容易遗漏重要方向

**解决方案**:
- 让 LLM 根据主题生成搜索关键词
- 每轮搜索后，LLM 根据已有论文调整搜索方向
- 支持布尔查询语法（AND、OR、引号）

**示例**:
```json
{
  "queries": [
    "\"computer algebra system\" AND algorithm",
    "\"symbolic integration\" OR \"Gröbner basis\"",
    "Mathematica OR Maple OR Maxima"
  ]
}
```

### 2. 渐进式信息披露

**问题**: 一次性发送 100 篇完整论文消耗 ~13,000 tokens

**解决方案**:
- 初始只发送论文标题列表 (~600 tokens)
- LLM 通过 `get_multiple_paper_details` 按需获取详情
- Token 节省 ~70%

### 3. 多轮搜索优化

**问题**: 单轮搜索可能遗漏重要文献

**解决方案**:
- 第 1 轮: 基础关键词搜索
- 第 2 轮: 根据已有论文补充搜索
- 第 3 轮: 填补空白方向
- 动态终止: 新增论文过少时提前结束

## 运行示例

### 示例 1: 基础使用

```bash
cd backend
python example_smart_review.py basic
```

### 示例 2: 自定义分步执行

```bash
python example_smart_review.py custom
```

### 示例 3: 使用已有 JSON 论文

```bash
python example_smart_review.py existing
```

## 结果文件说明

生成的结果包含两个文件:

1. **JSON 格式** (`smart_review_YYYYMMDD_HHMMSS.json`):
   - 完整的元数据
   - 搜索历史
   - 统计信息
   - 所有论文数据

2. **Markdown 格式** (`smart_review_YYYYMMDD_HHMMSS.md`):
   - 可读的综述内容
   - 包含参考文献
   - 可直接使用

## 与现有系统的集成

SmartReviewGenerator 可以无缝集成到现有系统中:

```python
# 在 review_task_executor.py 中使用
from services.smart_review_generator import SmartReviewGenerator

async def execute_task(self, task_id: str, db_session: Session):
    # ... 现有代码 ...

    # 使用 SmartReviewGenerator
    generator = SmartReviewGenerator(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    )

    result = await generator.generate_review(
        topic=task.topic,
        target_paper_count=params.get('target_count', 100)
    )

    # 保存结果
    # ...
```

## 性能指标

### v2 版本（大纲+撰写一体化）

| 指标 | 数值 |
|------|------|
| 搜索 API 调用 | ~3-9 次 (3 轮 × 3 关键词) |
| 论文收集 | 80-120 篇 |
| LLM 调用次数 | **2 次** (搜索策略 + 综述撰写) |
| Token 消耗 (搜索) | ~2,000 |
| Token 消耗 (综述) | ~5,000 |
| **总 Token** | **~7,000** |
| **总耗时** | **4-8 分钟** |

### 对比

| 版本 | LLM 调用 | 总 Token | 相对耗时 |
|------|---------|---------|---------|
| 传统 (分3阶段) | 3 次 | ~15,000 | 100% |
| v1 (SmartReview) | 3 次 | ~8,600 | 57% |
| **v2 (一体化)** | **2 次** | **~7,000** | **47%** ⚡ |

## 最佳实践

1. **选择合适的 `target_paper_count`**:
   - 快速预览: 30-50 篇
   - 标准综述: 80-120 篇
   - 深度综述: 150-200 篇

2. **调整 `max_search_rounds`**:
   - 主题较窄: 2 轮
   - 一般主题: 3 轮
   - 跨学科主题: 4 轮

3. **模型选择**:
   - `deepseek-reasoner`: 高质量，稍慢
   - `deepseek-chat`: 快速，质量良好

4. **Semantic Scholar API Key**:
   - 有 API Key: 速率限制 100 请求/分钟
   - 无 API Key: 速率限制 15 请求/5 分钟

## 故障排除

### 问题: 搜索结果过少

**解决方案**:
- 增加 `max_search_rounds`
- 使用更通用的关键词
- 检查 Semantic Scholar API 速率限制

### 问题: Token 消耗过高

**解决方案**:
- 减少 `target_paper_count`
- 确保使用 Function Calling 模式
- 考虑使用 `deepseek-chat` 替代 `deepseek-reasoner`

### 问题: 综述质量不理想

**解决方案**:
- 增加收集的论文数量
- 确保论文有摘要
- 调整主题描述，使其更具体

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 2.0 | 2026-04-05 | **大纲+撰写一体化** - 合并阶段2和3，减少 LLM 调用，节省 token |
| 1.0 | 2026-04-05 | 初始版本，整合完整流程 |

## 相关文件

- `backend/services/smart_review_generator.py` - 主实现
- `backend/example_smart_review.py` - 使用示例
- `backend/services/review_generator_fc_unified.py` - Function Calling 综述生成器
- `docs/review_generation_flow.md` - 原始流程文档
