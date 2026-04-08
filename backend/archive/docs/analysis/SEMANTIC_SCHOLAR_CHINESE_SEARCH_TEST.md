# Semantic Scholar API 中文关键词搜索测试报告

## 测试目的

验证 Semantic Scholar API 是否能够使用中文关键词搜索到相关文献。

## 测试环境

- **API**: Semantic Scholar Graph API
- **API Key**: 已配置
- **测试日期**: 2026-04-04

---

## 测试用例与结果

### 对比测试：中文 vs 英文关键词

| 中文关键词 | 中文结果数 | 英文关键词 | 英文结果数 | 差异 |
|-----------|-----------|-----------|-----------|------|
| 六西格玛 | 143 篇 | Six Sigma | 3,526,392 篇 | **+3,526,249** |
| 细菌排序算法 | 8 篇 | bacterial sorting algorithm | 74,274 篇 | **+74,266** |
| 中药复方数据挖掘 | 33 篇 | traditional chinese medicine data mining | 19,791 篇 | **+19,758** |

### 关键发现

**英文关键词的搜索结果数量是中文的数百到数万倍！**

---

## 详细分析：六西格玛案例

### 中文搜索 "六西格玛"
- **总结果数**: 143 篇
- **语言分布**: 100% 中文标题
- **相关性**: 仅 10% 包含 "Six Sigma" 术语

### 前 10 篇论文分析

| # | 标题示例 | 语言 | 相关性 |
|---|---------|------|--------|
| 1 | 基于六西格玛在服务业中的应用研究 | 🇨🇳 中文 | ❌ 未包含英文术语 |
| 2 | 面向航空装备研制的六西格玛设计（DFSS）... | 🇨🇳 中文 | ❌ 未包含英文术语 |
| 3-9 | 各种六西格玛应用研究... | 🇨🇳 中文 | ❌ 未包含英文术语 |
| 10 | 基于六西格玛体系的国际钻井投标管理 International... | 🇨🇳 中文 | ✅ 包含英文术语 |

### 结论

**中文关键词搜索结果的问题**：
1. ❌ 结果数量极少（143 篇 vs 352 万篇）
2. ❌ 100% 是中文论文（国际文献覆盖不足）
3. ❌ 仅 10% 包含目标术语 "Six Sigma"
4. ❌ 缺少国际前沿研究文献

---

## 为什么会出现这种情况？

### 1. Semantic Scholar 数据源特点

- **主要收录**: 英文论文为主
- **中文论文覆盖**: 非常有限，主要是：
  - 有英文标题/摘要的中文论文
  - 在国际期刊发表的中文研究
  - 有英文翻译的中文文献

### 2. 搜索引擎索引机制

- 中文关键词主要匹配：
  - 英文标题中包含的中文术语（罕见）
  - 中文论文的英文摘要（有限）
  - 翻译后的标题（很少）

- 英文关键词匹配：
  - 大量英文论文标题
  - 英文摘要
  - 国际研究文献

### 3. 学术出版现实

- **国际主流**: 英文发表
- **中文文献**: 大部分只有中文版本，未被国际索引收录
- **跨语言检索**: Semantic Scholar 没有中文翻译功能

---

## 实际案例对比

### 搜索 "六西格玛" vs "Six Sigma"

**中文搜索返回**：
- 中文管理类期刊论文
- 本土应用案例
- 被引量极低（大部分为 0）

**英文搜索返回**：
- International Journal of Six Sigma... 
- Six Sigma Forum（国际期刊）
- 高被引核心文献
- 跨学科应用研究

---

## 结论与建议

### ❌ 不建议使用中文关键词搜索 Semantic Scholar

**原因**：
1. **结果数量差异巨大**（数百倍）
2. **文献质量差异明显**（中文文献被引量低）
3. **覆盖范围有限**（缺少国际前沿研究）
4. **语言匹配问题**（中文论文英文摘要可能不包含完整关键词）

### ✅ 推荐做法

#### 1. 使用英文关键词搜索 Semantic Scholar

```python
# ❌ 不推荐
semantic_scholar.search('六西格玛')  # 返回 143 篇

# ✅ 推荐  
semantic_scholar.search('Six Sigma')  # 返回 3,526,392 篇
```

#### 2. 中文主题的翻译策略

```python
# 中文主题：基于数据挖掘的治疗抑郁症肝郁气滞型中药复方组方规律研究

# 翻译为英文关键词：
- 'traditional chinese medicine'
- 'herbal formula'
- 'data mining'
- 'depression treatment'
```

#### 3. 中文文献使用专门数据源

- **AMiner**: 中文文献支持最好
- **中文 DOI**: 中文期刊论文
- **CNKI/万方**: 国内数据库（需单独接入）

---

## 数据支持

| 搜索策略 | 数据源 | 推荐度 |
|---------|--------|--------|
| 英文关键词 | Semantic Scholar | ⭐⭐⭐⭐⭐ |
| 中文关键词 | Semantic Scholar | ⭐ |
| 中文关键词 | AMiner | ⭐⭐⭐⭐ |
| 中文关键词 | 中文 DOI | ⭐⭐⭐ |
| 中文关键词 | CNKI | ⭐⭐⭐⭐⭐ |

---

## 总结

**Semantic Scholar API 不是为中文搜索设计的**。

虽然它能够"找到"一些中文文献（通过英文翻译或英文化标题），但：
- 结果数量极少（相差数百倍）
- 质量明显较低（被引量低）
- 无法覆盖主流中文文献

**最佳实践**：
- Semantic Scholar → 只用英文关键词
- 中文文献 → 使用 AMiner 或专门的中文数据库

---

## 测试验证代码

```python
import httpx

async def test_semantic_scholar():
    api_key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
    base_url = 'https://api.semanticscholar.org/graph/v1'
    
    headers = {'x-api-key': api_key} if api_key else {}
    
    # 中文搜索
    response = await httpx.AsyncClient().get(
        f'{base_url}/paper/search',
        params={'query': '六西格玛', 'limit': 10},
        headers=headers
    )
    
    # 英文搜索
    response = await httpx.AsyncClient().get(
        f'{base_url}/paper/search',
        params={'query': 'Six Sigma', 'limit': 10},
        headers=headers
    )
```

**预期结果**：
- 中文: ~143 篇
- 英文: ~3,500,000 篇
