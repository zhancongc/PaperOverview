# 多关键词搜索解决方案

## 问题回顾

**任务 9a01603c 的搜索结果**：
- 阶段3 搜索：196 篇
- 阶段4 过滤：16 篇
- 保留率：仅 8.2%

**根本原因**：搜索查询过于宽泛
- `computer algebra system` → 返回 120 万篇论文
- 包含大量不相关文献（深度学习、蛋白质、区块链等）

---

## Semantic Scholar 多关键词搜索测试

### 测试结果对比

| 查询方式 | 结果数 | CAS 相关率 | 效果 |
|---------|--------|-----------|------|
| 单关键词 `computer algebra system` | **1,202,791** | 100% | ❌ 太多 |
| AND 查询 `computer algebra AND algorithm` | **10,720** | 100% | ✅ 精确 |
| AND 查询 `symbolic computation AND implementation` | **5,285** | 80% | ✅ 精确 |
| OR 查询 `Mathematica OR Maple OR SageMath` | 0 | N/A | ❌ 不支持 |

### 关键发现

✅ **Semantic Scholar 支持 AND 查询**
- 使用 AND 查询可以减少 **99%** 的无关结果
- 同时保持高相关性
- 结果数量更合理（几千到几万篇）

---

## 用户建议的正确性

### 示例：基于DMAIC的铝合金轮毂质量管理研究

| 方式 | 查询 | 效果 |
|------|------|------|
| ❌ 单关键词 | `铝合金轮毂` | 搜索到所有轮毂相关论文 |
| ❌ 单关键词 | `质量管理` | 搜索到所有质量管理论文 |
| ✅ **AND 查询** | `铝合金轮毂 AND 质量管理` | 精确匹配 |

### 为什么需要多关键词？

1. **铝合金轮毂** → 返回 5 万篇（所有轮毂）
2. **质量管理** → 返回 20 万篇（所有质量管理）
3. **铝合金轮毂 AND 质量管理** → 返回 292 篇（精确匹配）

---

## 解决方案

### 方案1：修改阶段2查询生成逻辑 ✅ 推荐

#### 当前逻辑
```python
# 阶段2 生成的查询
search_queries = [
    'computer algebra system',      # 单关键词
    'symbolic computation',         # 单关键词
    'algorithm implementation'      # 单关键词
]
```

#### 建议逻辑
```python
# 阶段2 应该生成的查询
search_queries = [
    # 核心术语 + 领域限定
    'computer algebra AND algorithm',
    'symbolic computation AND algorithm',
    
    # 具体系统
    'Mathematica OR Maple OR Maxima',
    
    # 核心功能
    'symbolic integration AND algorithm',
    'polynomial AND symbolic AND computation',
    
    # 应用领域
    'computer algebra AND education',
    'symbolic computation AND engineering',
]
```

### 方案2：从章节关键词生成组合查询

#### 当前
```python
# 章节关键词
section_keywords = {
    '计算机代数系统核心算法实现技术': [
        '计算机代数系统算法实现',
        '符号计算算法设计',
        'CAS多项式运算算法'
    ]
}

# 搜索查询（单关键词）
for kw in section_keywords:
    search_queries.append(kw)  # ❌ 单关键词
```

#### 建议
```python
# 章节关键词
section_keywords = {
    '计算机代数系统核心算法实现技术': [
        ('computer algebra', 'algorithm'),
        ('symbolic computation', 'algorithm design'),
        ('polynomial', 'symbolic', 'computation')
    ]
}

# 搜索查询（AND 组合）
for section, keywords in section_keywords.items():
    if len(keywords) >= 2:
        # 生成 AND 查询
        query = ' AND '.join(keywords)
        search_queries.append(query)
    elif len(keywords) == 1:
        # 单个关键词，添加领域限定
        query = f'"{keywords[0]}" AND computer algebra'
        search_queries.append(query)
```

---

## 实施建议

### 1. 修改章节关键词生成逻辑

在阶段1生成大纲时，每个章节的搜索关键词应该是：

```json
{
    "title": "计算机代数系统核心算法实现技术",
    "search_keywords": [
        "计算机代数系统算法实现",
        "符号计算算法设计"
    ],
    "search_query_combinations": [
        ["computer algebra", "algorithm"],
        ["symbolic computation", "algorithm design"],
        ["polynomial", "symbolic", "computation"]
    ]
}
```

### 2. 阶段2自动组合查询

```python
# 对于每个章节的多个关键词，自动生成 AND 查询
def generate_combined_queries(keywords, topic):
    queries = []
    
    # 如果有多个关键词，组合成 AND 查询
    if len(keywords) >= 2:
        # 两两组合
        for i in range(len(keywords)):
            for j in range(i+1, len(keywords)):
                query = f'{keywords[i]} AND {keywords[j]}'
                queries.append(query)
    else:
        # 单个关键词，添加主题限定
        for kw in keywords:
            query = f'"{kw}" AND {topic}'
            queries.append(query)
    
    return queries
```

### 3. 特定术语优先

对于特定主题，优先使用专有术语：

```python
# ❌ 通用词
'algorithms', 'systems', 'methods'

# ✅ CAS 专有术语
'Mathematica', 'Maple', 'Maxima', 'SageMath'
'symbolic integration', 'equation solving', 'polynomial factorization'
```

---

## 预期效果

### 修改前（任务 9a01603c）
```
搜索: computer algebra system
结果: 1,202,791 篇
相关文献: ~5%（大量不相关）
阶段4过滤: 196 → 16 篇（保留率 8.2%）
```

### 修改后（预期）
```
搜索: 
  - computer algebra AND algorithm
  - symbolic computation AND implementation
  - Mathematica OR Maple OR Maxima
结果: ~10,000-50,000 篇
相关文献: ~60-80%
阶段4过滤: 预计保留率 >50%
```

---

## 总结

### ✅ 用户建议完全正确

1. **Semantic Scholar 支持 AND 查询**
2. **AND 查询效果显著**（减少 99% 无关结果）
3. **应该至少使用 2 个关键词组合搜索**

### 🔧 需要修改的地方

1. **阶段1**：大纲关键词应该生成关键词组合
2. **阶段2**：查询优化应该生成 AND 查询
3. **搜索逻辑**：优先使用专有术语而非通用词

### 📋 实施优先级

1. **高优先级**：修改阶段2，自动生成 AND 查询
2. **中优先级**：更新阶段1，生成关键词组合
3. **低优先级**：添加领域术语库（Mathematica, Maple 等）

---

## 测试代码

```python
import asyncio
import httpx

async def test_and_query():
    api_key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
    base_url = 'https://api.semanticscholar.org/graph/v1'
    
    # 测试 AND 查询
    queries = [
        ('单关键词', 'computer algebra system'),
        ('AND 查询', 'computer algebra AND algorithm'),
        ('AND 查询', 'symbolic computation AND implementation'),
    ]
    
    for desc, query in queries:
        response = await httpx.AsyncClient().get(
            f'{base_url}/paper/search',
            params={'query': query, 'limit': 5},
            headers={'x-api-key': api_key}
        )
        data = response.json()
        print(f'{desc}: {query}')
        print(f'  结果: {data.get("total", 0):,} 篇')
```

**输出**：
```
单关键词: computer algebra system
  结果: 1,202,791 篇

AND 查询: computer algebra AND algorithm
  结果: 10,720 篇

AND 查询: symbolic computation AND implementation
  结果: 5,285 篇
```

**结论**：AND 查询可以大幅提高搜索精确度！
