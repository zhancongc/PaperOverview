# 文献生成功能测试结果分析

## 测试题目
Array-Carrying Symbolic Execution for Function Contract Generation

## 测试结果
❌ **失败** - 参考文献数量不足，筛选后只有 3 篇，至少需要 20 篇才能生成综述

## 问题分析

### 1. 核心问题：搜索到的文献与主题完全不相关

**搜索阶段统计：**
- 搜索查询数：72 个
- 搜索到的文献总数：123 篇

**问题文献样本（前10篇）：**
1. STRING v11: protein–protein association networks（蛋白质关联网络）
2. deepTools2: deep-sequencing data analysis（深度测序数据分析）
3. The STRING database in 2023（生物信息学数据库）
4. In situ click chemistry（点击化学）
5. ImageJ2（科学图像处理）
6. DAVID: functional enrichment analysis（功能富集分析）
7. Gut microbiota functions（肠道微生物功能）
8. m6A modification（RNA修饰）
9. DNA nanorobot（DNA纳米机器人）
10. Circular RNA-protein interactions（环状RNA）

**结论：** 所有搜索到的文献都是生物信息学/生命科学领域的，与主题"符号执行"和"函数契约生成"完全无关。

### 2. 大纲生成阶段正常

**大纲内容：**
1. 符号执行技术在函数契约生成中的基础研究
   - 关键词: 符号执行函数契约生成, 动态符号执行契约推导, 混合符号执行软件验证

2. Array-Carrying Symbolic Execution（ACSE）的核心技术与方法
   - 关键词: Array-Carrying Symbolic Execution, 符号执行数组处理, ACSE函数契约推导

3. ACSE在函数契约生成中的实证研究与评估
   - 关键词: ACSE实证评估函数契约, 符号执行契约生成实验, 数组处理契约验证研究

4. ACSE的扩展应用与未来研究方向
   - 关键词: ACSE扩展应用软件分析, 符号执行未来研究方向, 数组处理程序验证进展

**结论：** 大纲生成正确，搜索关键词也正确。

### 3. 过滤阶段工作正常

- 输入论文数：123 篇
- 质量过滤移除数：0 篇
- **主题不相关移除数：120 篇**
- 输出论文数：3 篇

**结论：** 过滤阶段正确识别了不相关的文献，但输入文献本身就是错的。

### 4. 根本原因分析

#### 问题定位：搜索关键词与搜索结果不匹配

虽然大纲阶段生成了正确的搜索关键词（如"符号执行函数契约生成"、"Array-Carrying Symbolic Execution"等），但实际搜索时使用的关键词可能有问题。

**可能的原因：**

1. **搜索关键词翻译问题**
   - 中文关键词可能没有被正确翻译成英文
   - 或者翻译后的关键词与原意偏差较大

2. **数据源选择问题**
   - 代码中对中文和英文使用不同的数据源
   - 中文数据源（aminer、semantic_scholar、chinese_doi）可能更适合生物信息学文献

3. **关键词编码/传输问题**
   - 关键词在传递过程中可能被错误编码或截断

4. **数据库默认搜索行为**
   - 如果数据库中没有相关文献，可能返回了默认的热门文献（生物信息学）

## 解决方案

### 方案1：强制使用英文关键词（推荐）

```python
# 在 _optimize_search_queries_basic 方法中
# 对于技术类主题，强制使用英文搜索

technical_keywords = {
    "符号执行": "symbolic execution",
    "函数契约": "function contract",
    "数组处理": "array handling",
    # ...
}

# 在优化查询时，先检查是否是技术术语
for query_item in search_queries:
    query = query_item.get('query', '')
    # 检查是否需要翻译
    translated = technical_keywords.get(query, query)
    # 使用翻译后的英文关键词
```

### 方案2：添加主题相关性验证

```python
# 在搜索阶段结束后，添加验证
# 检查搜索结果的标题是否与主题相关

def validate_search_relevance(topic, papers):
    """验证搜索结果是否与主题相关"""
    topic_words = set(topic.lower().split())
    relevant_count = 0

    for paper in papers[:20]:  # 检查前20篇
        title_words = set(paper.get('title', '').lower().split())
        # 计算重叠度
        overlap = len(topic_words & title_words)
        if overlap > 0:
            relevant_count += 1

    relevance_ratio = relevant_count / min(20, len(papers))
    if relevance_ratio < 0.3:  # 如果相关度低于30%
        raise Exception(f"搜索结果相关性过低 ({relevance_ratio:.1%})，请检查搜索关键词")
```

### 方案3：优化数据源选择

```python
# 根据主题类型选择合适的数据源
def select_data_sources(topic):
    """根据主题选择数据源"""
    # 检测主题领域
    if is_computer_science_topic(topic):
        # 计算机科学优先使用这些数据源
        return ['openalex', 'semantic_scholar', 'crossref']
    elif is_biology_topic(topic):
        # 生物信息学使用这些
        return ['pubmed', 'semantic_scholar']
    else:
        # 默认全部
        return ['all']
```

### 方案4：改进中文关键词翻译

```python
# 在 services/keyword_translator.py 中
# 添加专业术语翻译表

TECHNICAL_TERM_TRANSLATIONS = {
    "符号执行": "symbolic execution",
    "函数契约": "function contract",
    "契约生成": "contract generation",
    "数组处理": "array processing",
    "软件验证": "software verification",
    # ...
}

async def translate_technical_term(chinese_term):
    """翻译技术术语"""
    if chinese_term in TECHNICAL_TERM_TRANSLATIONS:
        return TECHNICAL_TERM_TRANSLATIONS[chinese_term]
    # 否则使用通用翻译
    return await general_translate(chinese_term)
```

### 方案5：添加调试日志

```python
# 在搜索阶段添加详细日志
print(f"[DEBUG] 使用的关键词: {keywords}")
print(f"[DEBUG] 优化的查询: {optimized_queries}")
print(f"[DEBUG] 使用的API: {api_used}")
print(f"[DEBUG] API返回的前5个结果标题: {[p['title'] for p in results[:5]]}")
```

## 建议

1. **立即修复**：实施方案1（强制使用英文关键词）+ 方案5（添加调试日志）

2. **短期优化**：实施方案2（添加主题相关性验证）

3. **长期改进**：实施方案3（优化数据源选择）+ 方案4（改进中文关键词翻译）

## 测试建议

修复后，建议使用以下题目重新测试：
- 纯英文题目：Symbolic Execution for Software Verification
- 混合题目：深度学习在图像识别中的应用
- 纯中文题目：基于Transformer的机器翻译模型研究

这样可以验证系统对不同类型题目的处理能力。
