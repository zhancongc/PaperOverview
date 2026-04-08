# 关键词翻译功能 Bug 分析

## 问题

阶段2搜索时，**中文关键词没有被翻译成英文**，导致：
- 使用中文关键词搜索英文数据库
- 搜索结果与主题完全不相关

## 根本原因

文件：`services/review_task_executor.py` 第 2280 行

```python
async def _optimize_search_queries_basic(
    self,
    search_queries: list,
    topic: str,
    research_direction: str = ""  # ← 只有这3个参数
) -> list:
    ...
    translations = await translate_keywords_contextual(
        keywords=zh_keywords,
        topic=topic,
        target_lang='en',
        research_direction_id=params.get('research_direction_id', '')  # ← Bug! params 未定义
    )
```

### 错误分析

1. **函数参数中没有 `params`**
   - 函数只有 `search_queries`, `topic`, `research_direction` 三个参数
   - 但代码中使用了 `params.get('research_direction_id', '')`
   - 这会抛出 `NameError: name 'params' is not defined`

2. **异常被静默捕获**
   ```python
   except Exception as e:
       print(f"[阶段2] 上下文翻译失败: {e}")
       print(f"[阶段2] 回退到原文查询")
   ```
   - 异常被捕获后，翻译失败但程序继续运行
   - 回退到原文查询（中文）
   - 没有明显的错误提示

## 影响

### 任务 70eed2c7 实际情况

| 预期 | 实际 |
|------|------|
| 使用 "Computer Algebra System" 搜索 | 使用 "计算机代数系统算法实现" 搜索 |
| 使用 "symbolic computation" 搜索 | 使用 "符号计算算法设计" 搜索 |
| 使用英文关键词搜索 Semantic Scholar | 使用中文关键词搜索 Semantic Scholar |

### 结果
- Semantic Scholar 收到中文查询，无法匹配英文论文
- 返回的论文与 CAS 完全无关
- 相关性 = 0%

## 修复方案

### 方案1：修正函数参数（推荐）

```python
async def _optimize_search_queries_basic(
    self,
    search_queries: list,
    topic: str,
    research_direction: str = "",
    params: dict = None  # ← 添加 params 参数
) -> list:
    if params is None:
        params = {}
    
    # ... 后续代码可以使用 params.get('research_direction_id', '')
```

### 方案2：使用已有参数

```python
# 使用 research_direction 参数替代 params.get('research_direction_id')
translations = await translate_keywords_contextual(
    keywords=zh_keywords,
    topic=topic,
    target_lang='en',
    research_direction_id=research_direction  # ← 使用已有参数
)
```

## 测试验证

修复后运行测试：
```bash
cd backend
python3 -c "
import asyncio
from services.review_task_executor import ReviewTaskExecutor

async def test():
    executor = ReviewTaskExecutor()
    queries = [{'query': '计算机代数系统算法实现'}]
    result = await executor._optimize_search_queries_basic(
        search_queries=queries,
        topic='computer algebra system的算法实现及应用',
        research_direction=''
    )
    print(f'优化后查询数: {len(result)}')
    for q in result:
        print(f'  [{q.get(\"lang\")}] {q.get(\"query\")}')

asyncio.run(test())
"
```

预期输出应该包含英文翻译：
```
  [zh] 计算机代数系统算法实现
  [en] Computer Algebra System algorithm implementation
```

## 相关任务

- ❌ 任务 70eed2c7 - 受此 Bug 影响，相关性 0%
- ❌ 任务 f8dcc110 - 可能受此 Bug 影响

## 总结

这是一个**参数缺失 Bug**，导致关键词翻译功能完全失效。虽然代码有翻译逻辑，但由于 `params` 参数未定义，翻译功能在运行时抛出异常并被静默捕获，最终使用中文关键词搜索英文数据库。
