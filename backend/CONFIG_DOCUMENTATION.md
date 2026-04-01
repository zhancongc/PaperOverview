# 配置参数说明文档

本文档说明所有可参数化的配置项，分为服务端配置和用户配置。

## 服务端配置 (.env)

服务端配置保存在 `.env` 文件中，需要重启服务才能生效。

### API 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | *必需* | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API 地址 |
| `AMINER_API_TOKEN` | *可选* | AMiner API Token（用于中文文献搜索） |

### 搜索配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_RETRIES` | `1` | 综述生成验证失败时的最大重试次数（0-5） |
| `MIN_PAPERS_THRESHOLD` | `20` | 触发补充搜索的最小文献数量（10-100） |
| `CANDIDATE_POOL_MULTIPLIER` | `2` | 候选池大小为目标数量的倍数 |
| `PAPERS_PER_PAGE` | `100` | 每次API调用返回的论文数量上限 |

### API 速率限制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `AMINER_RATE_LIMIT` | `1.0` | AMiner API 每秒调用次数限制 |
| `OPENALEX_RATE_LIMIT` | `5.0` | OpenAlex API 每秒调用次数限制 |
| `SEMANTIC_SCHOLAR_RATE_LIMIT` | `0.1` | Semantic Scholar API 每秒调用次数限制 |

### 质量评分权重

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CITATION_WEIGHT` | `0.4` | 被引量在质量评分中的权重（0.0-1.0） |
| `RECENCY_WEIGHT` | `0.3` | 新近度在质量评分中的权重（0.0-1.0） |
| `RELEVANCE_WEIGHT` | `0.3` | 相关性在质量评分中的权重（0.0-1.0） |

> 注意：三个权重之和应该等于 1.0

## 用户配置（前端页面）

用户配置在前端页面显示，用户可以在生成综述时调整。这些配置**不需要重启服务**。

### 基本配置

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `target_count` | `50` | 10-100 | 目标文献数量（综述中引用的文献总数） |
| `recent_years_ratio` | `0.5` | 0.1-1.0 | 近5年文献占比 |
| `english_ratio` | `0.3` | 0.1-1.0 | 英文文献占比 |

### 高级配置

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `search_years` | `10` | 5-30 | 搜索最近N年的文献 |
| `max_search_queries` | `8` | 1-20 | 最多使用多少个搜索查询 |

## 配置示例

### .env 文件示例

```bash
# ==================== API 配置 ====================
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

AMINER_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
AMINER_TOKEN_EXPIRES_AT=2026-07-10

# ==================== 搜索配置 ====================
MAX_RETRIES=2
MIN_PAPERS_THRESHOLD=20
CANDIDATE_POOL_MULTIPLIER=2
PAPERS_PER_PAGE=100

# ==================== API 速率限制 ====================
AMINER_RATE_LIMIT=1.0
OPENALEX_RATE_LIMIT=5.0
SEMANTIC_SCHOLAR_RATE_LIMIT=0.1

# ==================== 质量评分权重 ====================
CITATION_WEIGHT=0.4
RECENCY_WEIGHT=0.3
RELEVANCE_WEIGHT=0.3
```

## API 端点

### 获取用户配置 Schema

```http
GET /api/config/schema
```

返回前端表单配置，用于动态生成配置界面。

**响应示例：**
```json
{
  "success": true,
  "data": {
    "fields": [
      {
        "key": "target_count",
        "label": "目标文献数量",
        "type": "number",
        "default": 50,
        "min": 10,
        "max": 100,
        "description": "综述中引用的文献总数",
        "required": true
      },
      {
        "key": "recent_years_ratio",
        "label": "近5年文献占比",
        "type": "slider",
        "default": 0.5,
        "min": 0.1,
        "max": 1.0,
        "step": 0.1,
        "description": "最近5年发表的文献占比",
        "required": true
      }
    ]
  }
}
```

### 获取服务端配置

```http
GET /api/config/server
```

返回当前服务端配置（只读），便于调试。

**响应示例：**
```json
{
  "success": true,
  "data": {
    "max_retries": 1,
    "min_papers_threshold": 20,
    "candidate_pool_multiplier": 2,
    "papers_per_page": 100,
    "aminer_rate_limit": 1.0,
    "openalex_rate_limit": 5.0,
    "semantic_scholar_rate_limit": 0.1,
    "citation_weight": 0.4,
    "recency_weight": 0.3,
    "relevance_weight": 0.3
  }
}
```

## 配置优先级

1. **环境变量** (.env) - 最高优先级
2. **代码默认值** - 当环境变量未设置时使用

## 配置验证

服务启动时会自动验证配置：

- 检查必需的 API Key
- 验证权重总和是否为 1.0
- 验证数值范围是否合理

如果验证失败，会在控制台输出警告信息。

## 更新配置

### 更新服务端配置

1. 编辑 `.env` 文件
2. 重启服务

### 更新用户配置

用户配置通过前端界面设置，每次生成综述时都可以调整，**无需重启服务**。
