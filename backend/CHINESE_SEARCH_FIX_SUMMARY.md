# 中文文献搜索问题修复总结

## 修复日期
2026-04-01

## 修复的问题

### 1. 搜索查询语言与数据源不匹配 ✅
**问题**：实证型题目生成大量英文查询，但中文题目需要中文文献

**修复**：
- 在 `hybrid_classifier.py` 中添加 `_contains_chinese()` 方法检测题目语言
- 中文题目生成中文搜索查询
- 英文题目生成英文搜索查询
- 在查询中添加 `lang` 字段标识语言

### 2. AMiner 搜索能力被误用 ✅
**问题**：AMiner API 是 `title` 搜索，不是关键词搜索

**修复**：
- 集成 AMiner Pro 接口 (`/paper/search/pro`)
- 支持 `keyword` 参数进行更灵活的关键词搜索
- 修改 `search_papers` 方法使用新的 Pro 接口

### 3. 中文文献搜索策略缺失 ✅
**问题**：中文题目没有专门的中文搜索策略

**修复**：
- 实现 `_generate_chinese_empirical_queries()` 方法
- 生成专门的中文搜索查询
- 过滤通用关键词（测量、指标、对、的、影响等）
- 分别搜索核心关键词，然后合并结果

## 修改的文件

### 1. `services/hybrid_classifier.py`
- 添加 `_contains_chinese()` 方法
- 修改 `_empirical_queries()` 方法，根据题目语言选择搜索策略
- 添加 `_generate_chinese_empirical_queries()` 方法
- 添加 `_generate_english_empirical_queries()` 方法

### 2. `services/scholarflux_wrapper.py`
- 修改 `search()` 方法，添加 `lang` 参数
- 根据语言标识选择数据源

### 3. `services/aminer_search.py`
- 添加 `PRO_URL` 常量
- 添加 `search_by_keyword()` 方法
- 修改 `search_papers()` 方法，使用 Pro 接口
- 改进错误处理

### 4. `main.py`
- 更新搜索逻辑，使用 `lang` 参数

## 搜索策略对比

### 修复前
```
中文题目 → 检测中文 → AMiner → 按标题搜索（失败）
```

### 修复后
```
中文题目 → 智能分析 → 生成中文查询 → AMiner Pro → 关键词搜索（成功）
```

## 测试结果

### 测试题目
媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究

### 搜索查询生成
- 共生成 14 个搜索查询
- 策略包括：拆分搜索、交叉筛选、影响关系、相关性、理论视角、方法论、领域特定

### 搜索结果
- 找到 53 篇不重复中文文献
- Top 3 高被引论文：
  1. 上市公司ESG表现与企业绩效关系研究——基于媒体关注的调节作用 (被引: 30)
  2. Effect of market pressure of media coverage and its transmission mechanism (被引: 30)
  3. The effects of online news on the Chinese stock market (被引: 30)

## 关键词搜索效果

| 关键词 | 结果数 | 状态 |
|--------|--------|------|
| 媒体关注度 | 111 篇 | ✅ |
| 投资者情绪 | 1281 篇 | ✅ |
| 分析师预测 | 212 篇 | ✅ |
| 行为金融学 | 737 篇 | ✅ |
| 分析师盈利预测准确性 | 0 篇 | ⚠️ （关键词太长） |

## 优化细节

### 通用关键词过滤
为了避免搜索到不相关的文献，过滤了以下通用关键词：
- 测量、指标、评价、分析、研究、方法
- 影响、效应、对、的、与、和、及
- 基于、关系、相关性、作用

### 搜索查询示例

#### 核心关键词搜索
```python
{'query': '媒体关注度', 'section': '媒体关注度的理论基础与测量', 'strategy': '拆分搜索', 'lang': 'zh'}
{'query': '投资者情绪', 'section': '投资者情绪的理论基础与测量', 'strategy': '拆分搜索', 'lang': 'zh'}
```

#### 交叉搜索
```python
{'query': '媒体关注度 投资者情绪', 'section': '影响机制', 'strategy': '交叉筛选', 'lang': 'zh'}
{'query': '投资者情绪 分析师盈利预测准确性', 'section': '影响机制', 'strategy': '交叉筛选', 'lang': 'zh'}
```

#### 理论搜索
```python
{'query': '行为金融学', 'section': '理论基础', 'strategy': '领域特定', 'lang': 'zh'}
{'query': '投资者情绪 行为金融学', 'section': '理论基础', 'strategy': '领域特定', 'lang': 'zh'}
```

## 已知限制

1. **过长关键词**：如"分析师盈利预测准确性"（9个字符）可能搜索不到结果
   - 建议：拆分为"分析师预测"+"准确性"

2. **组合关键词**：某些组合（如"媒体关注度 测量"）会分别搜索两个词
   - 影响："测量"这个通用词会搜索到大量不相关文献
   - 解决：已添加通用词过滤

3. **Pro 接口限制**：某些复杂查询可能返回 0 篇
   - 原因：AMiner Pro 接口对复杂关键词的支持有限
   - 解决：使用分别搜索然后合并的策略

## 下一步优化建议

1. **关键词智能拆分**：对于过长关键词自动拆分
2. **同义词扩展**：为中文关键词添加同义词搜索
3. **结果质量评分**：根据关键词匹配度对搜索结果评分
4. **缓存优化**：缓存常见关键词的搜索结果

## 相关文件

- 测试脚本：`test_chinese_search_fix.py`
- AMiner Pro 测试：`test_aminer_pro.py`
- 流程文档：`REVIEW_GENERATION_FLOW.md`
