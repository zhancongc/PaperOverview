# AMiner 论文搜索服务

## 简介

AMiner (https://www.aminer.cn/) 是一个专业的学术搜索平台，支持中英文文献搜索。

## 获取 API Token

1. 访问 [AMiner 开放平台](https://www.aminer.cn/)
2. 注册并登录账号
3. 进入开发者中心获取 API Token

## 使用方法

### 1. 基本使用

```python
import asyncio
from services.aminer_search import AMinerSearchService

async def search():
    # 使用你的 API Token
    api_token = "your_token_here"

    async with AMinerSearchService(api_token=api_token) as service:
        # 验证 Token
        if await service.verify_token():
            # 搜索论文
            papers = await service.search_papers(
                keywords=['投资者情绪', '分析师预测'],
                year_start=2020,
                year_end=2024,
                max_results=50
            )

            for paper in papers:
                print(f"{paper['title']} ({paper['year']})")
```

### 2. 设置环境变量

```bash
export AMINER_API_TOKEN="your_token_here"
```

### 3. 测试 Token

```bash
python3 test_aminer.py
```

## API 参数说明

**请求地址**: `https://datacenter.aminer.cn/gateway/open_platform/api/paper/search`

**请求方法**: GET

**请求头**:
- `Authorization`: Bearer {your_token}

**URL 参数**:
- `title`: 论文标题（空格用 + 代替）
- `page`: 页码（从 1 开始）
- `size`: 每页数量（最大 20）

**返回字段**:
- `id`: 论文 ID
- `title`: 论文标题
- `title_zh`: 中文标题
- `authors`: 作者列表
- `year`: 年份
- `venue_name`: 期刊/会议名称
- `n_citation_bucket`: 被引档位
- `doi`: DOI

## 使用场景

1. **中文文献搜索**: AMiner 对中文文献支持较好
2. **补充 Semantic Scholar**: 可以作为英文文献搜索的补充
3. **标题精确搜索**: 支持按论文标题精确查找

## 注意事项

1. API Token 有有效期，过期后需重新获取
2. 每次请求最多返回 20 条结果
3. 建议添加请求间隔，避免频率限制
4. Token 需要保密，不要提交到代码仓库

## 与现有系统集成

可以将 AMiner 服务集成到 `scholarflux_wrapper.py` 中：

```python
class ScholarFlux:
    def __init__(self):
        # 现有服务
        self.semantic_service = SemanticScholarService()
        # 添加 AMiner
        self.aminer_service = AMinerSearchService(api_token=os.getenv('AMINER_API_TOKEN'))

    async def search_papers(self, query, ...):
        # 优先使用 AMiner 搜索中文文献
        if self._is_chinese_query(query):
            return await self.aminer_service.search_papers(...)
        else:
            return await self.semantic_service.search_papers(...)
```

## 当前状态

- ✅ 服务已创建
- ⚠️ 需要有效的 API Token 才能使用
- 📝 测试 Token 已过期，需要更新

## 更新 Token

更新 `test_aminer.py` 中的 `API_TOKEN` 变量为你获取的新 Token。
