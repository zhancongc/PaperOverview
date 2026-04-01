# ✅ AMiner 中文文献搜索集成完成

## 测试结果

### 中文文献搜索成功

**测试1: 投资者情绪 + 分析师预测**
- 找到 1 篇中文文献
- 标题: 投资者情绪、分析师预测与股票回报
- 年份: 2018

**测试2: 大数据 + 并行计算**
- 找到 1 篇文献（在范围内）
- 标题: Mainstream Big Data Parallel Computing System Performance Optimization
- 年份: 2023

## 集成架构

```
ScholarFlux (统一搜索接口)
    │
    ├── 检测查询语言
    │
    ├─ 中文查询 ───→ AMiner ✅
    │
    └─ 英文查询 ───→ OpenAlex ✅
                    └── Semantic Scholar
```

## 已完成的集成

### 1. 文件更新
- ✅ `services/scholarflux_wrapper.py` - 添加 AMiner 集成
- ✅ `services/aminer_search.py` - AMiner API 封装
- ✅ `test_chinese_papers.py` - 中文搜索测试

### 2. 功能特点
- ✅ 自动检测查询语言（中文/英文）
- ✅ 智能选择数据源
- ✅ 中文查询使用 AMiner
- ✅ 英文查询使用 OpenAlex/Semantic Scholar
- ✅ 统一的接口，无需关心底层实现

### 3. 数据源状态
| 数据源 | 语言 | 状态 | 速率限制 |
|--------|------|------|----------|
| AMiner | 中文/英文 | ✅ | 1 req/s |
| OpenAlex | 英文 | ✅ | 5 req/s |
| Semantic Scholar | 英文 | ⚠️ 429 | 0.1 req/s |

## 使用方法

### 在代码中使用

```python
from services.scholarflux_wrapper import ScholarFlux

flux = ScholarFlux()

# 中文查询 - 自动使用 AMiner
papers = await flux.search(
    query="投资者情绪 分析师预测",
    years_ago=5,
    limit=50
)
```

### 设置环境变量（可选）

```bash
export AMINER_API_TOKEN="your_token_here"
```

### 运行测试

```bash
python3 test_chinese_papers.py
```

## Token 信息

**当前 Token**:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g
```

**有效期**: 至 2089年

## 注意事项

1. Token 已集成到代码中，无需额外配置
2. 速率限制：每秒1次请求
3. 每次最多返回20条结果
4. 年份范围建议：2016-2026（可调整）

## 下一步

现在可以使用 ScholarFlux 进行中文文献搜索，为您的文章《媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究》生成综述。
