# 文献综述生成流程问题分析

## 发现的问题

### 🔴 严重问题

#### 1. AMiner 搜索关键词分割错误 (services/scholarflux_wrapper.py:75)
```python
# 当前代码
keywords = query.split()  # 对中文查询完全错误！
```

**问题**：使用 `split()` 按空格分割中文查询字符串是不正确的。
- 中文查询 "铝合金轮毂质量管理" 会被当作单个关键词
- 中文查询 "铝合金轮毂 质量管理" 会被分割成 2 个关键词
- 分割逻辑不一致，导致搜索结果不稳定

**影响**：搜索结果质量差，可能找不到相关文献

**建议修复**：
```python
# 改进方案
if self.name == "aminer":
    # 对于 AMiner，优先使用组合搜索模式
    # 如果是中文，按空格分割（如果有）
    # 如果是英文，也按空格分割
    keywords = [k for k in query.split() if k.strip()]
    if not keywords:
        keywords = [query]
    papers = await self.service.search_papers(
        keywords=keywords,
        year_start=datetime.now().year - years_ago,
        year_end=datetime.now().year,
        max_results=limit
    )
```

#### 2. 返回数据不一致 (main.py:665)
```python
return GenerateResponse(
    # ...
    data={
        # ...
        "papers": candidate_pool,  # ❌ 应该返回 cited_papers
        # ...
        "cited_papers_count": len(cited_papers),  # ✓ 正确
    }
)
```

**问题**：返回的 `papers` 字段是 `candidate_pool`（候选池），而不是 `cited_papers`（实际被引用的论文）。

**影响**：前端显示的论文列表和实际被引用的论文不一致

**建议修复**：
```python
"papers": cited_papers,  # 返回实际被引用的论文
```

### 🟡 中等问题

#### 3. 最后宽泛搜索后未去重 (main.py:438-446)
```python
if topic_words:
    last_attempt_papers = await search_service.search(...)
    all_papers.extend(last_attempt_papers)  # ❌ 没有去重！
```

**问题**：最后宽泛搜索获取的论文直接添加到 `all_papers`，没有去重

**影响**：可能包含重复论文

**建议修复**：
```python
if topic_words:
    last_attempt_papers = await search_service.search(...)
    # 去重后添加
    for paper in last_attempt_papers:
        paper_id = paper.get("id")
        if paper_id not in seen_ids:
            seen_ids.add(paper_id)
            all_papers.append(paper)
```

#### 4. 重试时使用 search_papers 而非 search (main.py:552)
```python
# 重试时
additional_papers = await search_service.search_papers(
    query=request.topic,
    years_ago=15,
    limit=150
)
```

**问题**：使用 `search_papers` 而不是 `search`，无法利用智能语言检测和组合搜索功能

**影响**：重试时的搜索质量可能不如初始搜索

**建议修复**：
```python
additional_papers = await search_service.search(
    query=request.topic,
    years_ago=15,
    limit=150,
    use_all_sources=True
)
```

### 🟢 轻微问题

#### 5. 搜索查询数量硬编码 (main.py:379)
```python
for query_info in search_queries[:8]:  # 硬编码 8
```

**问题**：搜索查询数量硬编码为 8

**建议**：可以考虑根据题目类型动态调整，或者作为配置项

#### 6. 缺少超时处理
**问题**：长时间运行的 API 调用没有超时机制

**建议**：为所有外部 API 调用添加超时

#### 7. 错误处理不够细致
**问题**：某些异常被捕获但没有区分错误类型

**建议**：区分可重试错误和不可重试错误

## 优先级修复建议

### 立即修复（影响功能正确性）
1. ✅ 修复返回数据不一致（问题2）
2. ✅ 修复最后宽泛搜索后未去重（问题3）
3. ✅ 修复重试时的搜索方法（问题4）

### 尽快修复（影响搜索质量）
4. ⚠️ 修复 AMiner 搜索关键词分割（问题1）

### 可选优化（改进用户体验）
5. 添加搜索查询数量配置
6. 添加超时处理
7. 改进错误处理

## 测试建议

修复后需要测试以下场景：
1. 中文题目的文献搜索
2. 英文题目的文献搜索
3. 搜索结果为空的边缘情况
4. 重试机制是否正常工作
5. 返回的论文列表是否与综述中的引用一致
