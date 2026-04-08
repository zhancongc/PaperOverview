# 综述生成流程调用链分析

## 阶段方法调用链

```
用户请求 (POST /api/submit-review-task)
    ↓
execute_task() [ReviewTaskExecutor]
    ↓
阶段1: _generate_review_outline()
    ├─ 输入: topic (str)
    └─ 输出: dict {outline: {...}}
    ↓
阶段2: _optimize_search_queries_basic()
    ├─ 输入: search_queries (list), topic (str)
    └─ 输出: list [optimized_queries]
    ↓
阶段3: _search_literature_by_sections()
    ├─ 输入: topic, optimized_queries, params, framework, task_id
    └─ 输出: dict {sections: {...}, all_papers: [...], stats: {...}}
    ↓
阶段4: _filter_papers_by_quality() ✅ 当前使用
    ├─ 输入: search_result, topic, framework, params, task_id
    └─ 输出: dict {all_papers: [...], total_count: int}
    ↓
阶段5: ReviewGeneratorFCUnified.generate_review()
    ├─ 输入: topic, papers, framework, target_citation_count
    ├─ 调用: _build_system_prompt()
    ├─ 调用: _build_user_message()
    ├─ 调用: _get_tools_definition()
    ├─ 调用: _get_paper_details() (工具函数)
    ├─ 调用: _search_papers_by_keyword() (工具函数)
    └─ 输出: (review_content, cited_papers)
```

## 方法签名检查

### 阶段1: _generate_review_outline

```python
async def _generate_review_outline(self, topic: str) -> dict:
    """
    输入: topic (str)
    输出: dict {
        'outline': {
            'introduction': {...},
            'body_sections': [...],
            'conclusion': {...}
        }
    }
    """
```

### 阶段2: _optimize_search_queries_basic

```python
def _optimize_search_queries_basic(
    self,
    search_queries: list,
    topic: str
) -> list:
    """
    输入: 
        - search_queries (list): [{'query': str, 'lang': 'mixed'}]
        - topic (str)
    输出:
        - list: [{'query': str, 'lang': str, 'source': str, 'original_query': str}]
    """
```

### 阶段3: _search_literature_by_sections

```python
async def _search_literature_by_sections(
    self,
    topic: str,
    optimized_queries: list,
    params: dict,
    framework: dict,
    task_id: str
) -> dict:
    """
    输入:
        - topic (str)
        - optimized_queries (list)
        - params (dict): {target_count, recent_years_ratio, english_ratio, search_years, max_search_queries}
        - framework (dict)
        - task_id (str)
    输出:
        - dict: {sections: {...}, all_papers: [...], stats: {...}}
    """
```

### 阶段4: _filter_papers_by_quality (当前使用)

```python
async def _filter_papers_by_quality(
    self,
    search_result: dict,
    topic: str,
    framework: dict,
    params: dict,
    task_id: str
) -> dict:
    """
    输入:
        - search_result (dict): {sections: {...}, all_papers: [...], stats: {...}}
        - topic (str)
        - framework (dict)
        - params (dict)
        - task_id (str)
    输出:
        - dict: {all_papers: [...], total_count: int}
    """
```

### 阶段4: _filter_papers_to_target (旧方法，已废弃)

```python
async def _filter_papers_to_target(
    self,
    search_result: dict,
    topic: str,
    framework: dict,
    params: dict,
    task_id: str
) -> dict:
    """
    输入:
        - search_result (dict)
        - topic (str)
        - framework (dict)
        - params (dict)
        - task_id (str)
    输出:
        - dict: {sections: {...}, all_papers: [...], total_count: int}
    """
```

### 阶段5: ReviewGeneratorFCUnified.generate_review()

```python
async def generate_review(
    self,
    topic: str,
    papers: List[Dict],
    framework: dict,
    model: str = "deepseek-chat",
    specificity_guidance: dict = None,
    target_citation_count: int = 50
) -> Tuple[str, List[Dict]]:
    """
    输入:
        - topic (str)
        - papers (List[Dict])
        - framework (dict)
        - model (str)
        - specificity_guidance (dict)
        - target_citation_count (int)
    输出:
        - Tuple[str, List[Dict]]: (review_content, cited_papers)
    """
```

## 外部服务类方法签名

### PaperQualityFilter

```python
# ✅ 正确的方法
get_paper_quality_score(paper: Dict) -> float

# ❌ 错误的方法（不存在）
calculate_quality_score(paper: Dict) -> float

# 其他方法
is_low_quality_paper(paper: Dict) -> Tuple[bool, str]
filter_papers(papers: List[Dict]) -> List[Dict]
```

### EnhancedPaperFilterService (paper_field_classifier.py)

```python
# ✅ 正确的方法
_calculate_enhanced_relevance_score(paper: Dict, topic_keywords: List[str]) -> float

filter_and_sort_with_fields(
    papers: List[Dict],
    section_name: str = None,
    target_count: int = 50,
    recent_years_ratio: float = 0.5,
    english_ratio: float = 0.3,
    topic_keywords: List[str] = None,
    enable_field_filter: bool = True,
    use_llm_classification: bool = False
) -> Tuple[List[Dict], Dict]
```

### PaperFilterService (paper_filter.py)

```python
filter_and_sort(
    papers: List[Dict],
    target_count: int = 50,
    recent_years_ratio: float = 0.5,
    english_ratio: float = 0.3,
    topic_keywords: List[str] | None = None
) -> List[Dict]

get_statistics(papers: List[Dict]) -> Dict
```

## 潜在问题和解决方案

### 问题1: 方法名不一致

**问题**: `calculate_quality_score` vs `get_paper_quality_score`

**解决**: 已修复，统一使用 `get_paper_quality_score`

### 问题2: 阶段4有两个方法

**问题**: 
- `_filter_papers_to_target` (旧)
- `_filter_papers_by_quality` (新)

**解决**: 
- 当前使用 `_filter_papers_by_quality`
- 旧的 `_filter_papers_to_target` 可以标记为废弃

### 问题3: 参数传递不一致

**问题**: 
- `_filter_papers_to_target` 返回 `{sections: {...}, all_papers: [...]}`
- `_filter_papers_by_quality` 返回 `{all_papers: [...], total_count: int}`

**解决**: 
- 在 `execute_task` 中已正确处理，不再使用 `papers_by_section`

### 问题4: target_citation_count 参数

**问题**: 
- 新增的 `target_citation_count` 参数需要正确传递

**解决**: 
- 在 `execute_task` 中正确传递给 `generate_review`

## 建议的改进

### 1. 统一返回格式

建议所有阶段方法返回统一的格式：

```python
{
    'success': bool,
    'data': {...},
    'errors': []
}
```

### 2. 添加类型提示

为所有方法添加完整的类型提示，减少调用错误。

### 3. 添加参数验证

在每个方法开始时验证输入参数：

```python
def _filter_papers_by_quality(..., search_result: dict, ...):
    # 验证输入
    if 'all_papers' not in search_result:
        raise ValueError("search_result 必须包含 'all_papers' 字段")
    ...
```

### 4. 废弃旧方法

将 `_filter_papers_to_target` 标记为废弃：

```python
async def _filter_papers_to_target(...) -> dict:
    """
    ⚠️ 已废弃，请使用 _filter_papers_by_quality
    
    此方法不再被调用，保留仅为向后兼容。
    """
    warnings.warn("_filter_papers_to_target 已废弃，请使用 _filter_papers_by_quality", 
                  DeprecationWarning)
    ...
```

### 5. 创建统一的接口层

创建一个 `StageExecutor` 类来统一管理各阶段的调用：

```python
class StageExecutor:
    """阶段执行器 - 统一管理各阶段调用"""
    
    def __init__(self, task_executor: ReviewTaskExecutor):
        self.executor = task_executor
    
    async def execute_stage1(self, topic: str) -> dict:
        return await self.executor._generate_review_outline(topic)
    
    async def execute_stage2(self, queries: list, topic: str) -> list:
        return self.executor._optimize_search_queries_basic(queries, topic)
    
    async def execute_stage3(self, ...) -> dict:
        ...
    
    async def execute_all_stages(self, ...) -> dict:
        """执行所有阶段"""
        ...
```

## 当前正确的调用链

```
execute_task()
    ↓
├─ _generate_review_outline(topic)
├─ _optimize_search_queries_basic(search_queries, topic)
├─ _search_literature_by_sections(topic, optimized_queries, params, framework, task_id)
├─ _filter_papers_by_quality(search_result, topic, framework, params, task_id)
└─ ReviewGeneratorFCUnified.generate_review(topic, papers, framework, target_citation_count)
    ├─ _build_system_prompt(specificity_guidance, target_citation_count)
    ├─ _build_user_message(topic, paper_titles, framework, target_citation_count)
    ├─ _get_tools_definition()
    ├─ _get_paper_details(paper_index, papers) [工具调用]
    └─ _search_papers_by_keyword(keyword, papers) [工具调用]
```

## 快速检查清单

使用此清单验证代码是否正确：

- [ ] 阶段4调用的是 `_filter_papers_by_quality` 而不是 `_filter_papers_to_target` ⚠️ 已废弃
- [ ] 搜索词优化使用 `_optimize_search_queries_basic` 而不是 `_optimize_search_queries` ⚠️ 已废弃
- [ ] 质量评分使用 `get_paper_quality_score` 而不是 `calculate_quality_score`
- [ ] `target_citation_count` 参数正确传递到 `generate_review`
- [ ] `generate_review` 的所有参数都有正确的默认值
- [ ] 工具函数 `_get_paper_details` 和 `_search_papers_by_keyword` 正确定义
- [ ] 所有异步方法都使用 `async def` 声明
- [ ] 所有字典参数都有正确的默认值处理

## 废弃方法汇总

### ReviewTaskExecutor 废弃方法
- `_filter_papers_to_target()` → 使用 `_filter_papers_by_quality()`
- `_optimize_search_queries()` → 使用 `_optimize_search_queries_basic()`

### 废弃的综述生成器
- `review_generator.py` → 使用 `review_generator_fc_unified.py`
- `review_generator_v2_enhanced.py` → 使用 `review_generator_fc_unified.py`
- `review_generator_function_calling.py` → 使用 `review_generator_fc_unified.py`
