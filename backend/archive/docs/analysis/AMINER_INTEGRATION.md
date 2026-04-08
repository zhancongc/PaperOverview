# ScholarFlux + AMiner 集成完成

## 集成状态

✅ **代码集成完成**
- AMiner 服务已集成到 `scholarflux_wrapper.py`
- 支持智能选择：中文查询使用 AMiner，英文查询使用 OpenAlex/Semantic Scholar
- 自动检测中文关键词并切换数据源

⚠️ **需要有效 Token**
- 提供的 Token 已过期
- 需要获取新的 AMiner API Token

## 集成架构

```
ScholarFlux (统一搜索接口)
    │
    ├── 检测查询语言
    │
    ├─ 中文查询 ───→ AMiner (中文文献)
    │
    └─ 英文查询 ───→ OpenAlex (主要)
                    └── Semantic Scholar (补充)
```

## 文件更新

### 1. `services/scholarflux_wrapper.py`
- 添加 `is_chinese` 标记
- 添加 `_contains_chinese()` 方法
- 添加 `AMinerSearchService` 导入
- 更新 `search()` 方法支持智能选择

### 2. `services/aminer_search.py`
- 完整的 AMiner API 封装
- 支持 Token 验证
- 支持批量搜索

### 3. `test_scholarflux_aminer.py`
- 集成测试脚本
- 自动检测中文/英文查询

## 使用方法

### 设置 Token

```bash
export AMINER_API_TOKEN="your_new_token_here"
```

### 运行测试

```bash
python3 test_scholarflux_aminer.py
```

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

# 英文查询 - 使用 OpenAlex
papers = await flux.search(
    query="machine learning",
    years_ago=5,
    limit=50
)
```

## 获取新 Token

1. 访问 [AMiner 开放平台](https://www.aminer.cn/)
2. 注册/登录账号
3. 进入开发者中心获取 API Token
4. 更新环境变量或代码中的 Token

## 当前状态

| 数据源 | 状态 | 说明 |
|--------|------|------|
| OpenAlex | ✅ 可用 | 英文文献，5 req/s |
| Semantic Scholar | ⚠️ 429 | 英文文献，速率限制 |
| AMiner | ⚠️ Token无效 | 中文文献，需更新 Token |

## 下一步

1. 获取新的 AMiner API Token
2. 更新 `AMINER_API_TOKEN` 环境变量
3. 重新测试中文文献搜索功能
