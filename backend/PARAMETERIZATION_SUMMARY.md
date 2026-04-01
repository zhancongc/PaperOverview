# 配置参数化完成总结

## 完成的工作

### 1. 创建配置文件

| 文件 | 说明 |
|------|------|
| `.env.example` | 环境变量模板文件 |
| `config.py` | 配置管理模块 |
| `CONFIG_DOCUMENTATION.md` | 配置说明文档 |

### 2. 新增 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/config/schema` | GET | 获取用户配置 Schema（前端表单配置） |
| `/api/config/server` | GET | 获取服务端配置（只读，用于调试） |

### 3. 配置分类

#### 服务端配置 (.env) - 9项

**API 配置 (3项)**
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `AMINER_API_TOKEN`

**搜索配置 (4项)**
- `MAX_RETRIES` - 重试次数（默认: 1）
- `MIN_PAPERS_THRESHOLD` - 补充搜索阈值（默认: 20）
- `CANDIDATE_POOL_MULTIPLIER` - 候选池倍数（默认: 2）
- `PAPERS_PER_PAGE` - 每页论文数（默认: 100）

**API 速率限制 (3项)**
- `AMINER_RATE_LIMIT` - AMiner 速率限制（默认: 1.0）
- `OPENALEX_RATE_LIMIT` - OpenAlex 速率限制（默认: 5.0）
- `SEMANTIC_SCHOLAR_RATE_LIMIT` - Semantic Scholar 速率限制（默认: 0.1）

**质量评分权重 (3项)**
- `CITATION_WEIGHT` - 被引量权重（默认: 0.4）
- `RECENCY_WEIGHT` - 新近度权重（默认: 0.3）
- `RELEVANCE_WEIGHT` - 相关性权重（默认: 0.3）

#### 用户配置（前端页面）- 5项

**基本配置 (3项)**
- `target_count` - 目标文献数量（默认: 50，范围: 10-100）
- `recent_years_ratio` - 近5年文献占比（默认: 0.5，范围: 0.1-1.0）
- `english_ratio` - 英文文献占比（默认: 0.3，范围: 0.1-1.0）

**高级配置 (2项)**
- `search_years` - 搜索年份范围（默认: 10，范围: 5-30）
- `max_search_queries` - 最多搜索查询数（默认: 8，范围: 1-20）

## 使用方法

### 更新服务端配置

1. 编辑 `.env` 文件
2. 重启服务

```bash
# 编辑 .env
vim .env

# 重启服务
pkill -f "uvicorn.*main:app"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端使用用户配置

前端调用 `/api/config/schema` 获取配置 Schema，动态生成表单：

```javascript
// 获取配置 Schema
const response = await fetch('/api/config/schema');
const schema = await response.json();

// schema.data.fields 包含所有字段配置
// 可以动态生成表单
```

## 配置验证

服务启动时自动验证：
- ✅ 检查必需的 API Key
- ✅ 验证权重总和是否为 1.0
- ✅ 验证数值范围

## API 响应示例

### GET /api/config/schema

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
      }
    ]
  }
}
```

### GET /api/config/server

```json
{
  "success": true,
  "data": {
    "max_retries": 1,
    "min_papers_threshold": 20,
    "candidate_pool_multiplier": 2,
    "papers_per_page": 100
  }
}
```

## 下一步建议

1. **前端集成**
   - 在前端页面添加配置面板
   - 使用 `/api/config/schema` 动态生成表单
   - 将用户配置传递给 `/api/smart-generate` 接口

2. **代码更新**
   - 将 `main.py` 中硬编码的值替换为 `Config` 类中的值
   - 例如：`max_retries = 1` → `max_retries = Config.MAX_RETRIES`

3. **文档完善**
   - 在前端添加配置说明
   - 为每个配置项添加帮助提示
