# 后端服务

基于 FastAPI 的文献综述生成后端服务，支持多数据源文献搜索和 AI 综述生成。

## 功能特性

- 🔍 **多数据源文献搜索**
  - ScholarFlux 统一接口
  - 支持 AMiner（中文）、OpenAlex（英文）、Semantic Scholar、Crossref、DataCite
  - 论文元数据数据库，避免重复搜索

- 🤖 **AI 综述生成**
  - DeepSeek 大模型驱动
  - 混合分类器：规则引擎 + LLM 验证
  - 场景特异性综述框架

- ✅ **质量控制**
  - 低质量文献过滤
  - 引用数量和年份分布验证
  - 引用顺序检查

- 🎯 **高级功能**
  - 自然数据嵌入（避免 AI 痕迹）
  - 深度对比分析
  - 综述润色
  - 观点碰撞分析

## 技术栈

- **框架**: FastAPI 0.115
- **数据库**: PostgreSQL 16 (支持 MySQL)
- **ORM**: SQLAlchemy 2.0
- **HTTP 客户端**: httpx 0.28
- **AI/LLM**: OpenAI SDK 1.54 (DeepSeek API)
- **文档处理**: python-docx 1.1

## 安装依赖

```bash
# 使用虚拟环境推荐
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 依赖说明

```
# 核心框架
fastapi==0.115.0          # Web 框架
uvicorn[standard]==0.32.0 # ASGI 服务器
pydantic==2.10.0          # 数据验证

# 数据库
sqlalchemy==2.0.36        # ORM
psycopg2-binary==2.9.10   # PostgreSQL 驱动
pymysql==1.1.1            # MySQL 驱动（可选）

# HTTP 客户端
httpx==0.28.0             # 异步 HTTP

# AI/LLM
openai==1.54.0            # OpenAI API SDK

# 文档处理
python-docx==1.1.2        # Word 文档生成

# 配置管理
python-dotenv==1.0.1      # 环境变量

# 测试工具
pytest==8.3.0
pytest-asyncio==0.24.0
```

## 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键参数：

```bash
# ==================== API 配置 ====================
# DeepSeek API（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# AMiner API（推荐，用于中文文献）
AMINER_API_TOKEN=your_aminer_token_here

# Semantic Scholar API（可选）
SEMANTIC_SCHOLAR_API_KEY=your_key_here

# ==================== 数据库配置 ====================
# 数据库类型：postgresql 或 mysql
DB_TYPE=postgresql

# PostgreSQL 配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=security
DB_NAME=paper

# ==================== 数据源开关 ====================
# 启用/禁用各数据源（true/false）
OPENALEX_ENABLED=true
AMINER_ENABLED=true
SEMANTIC_SCHOLAR_ENABLED=true
CROSSREF_ENABLED=true
DATACITE_ENABLED=true
```

## 数据库设置

### 使用 Docker（推荐）

```bash
# 启动 PostgreSQL
docker-compose up -d

# 检查状态
docker-compose ps
```

### 手动安装 PostgreSQL

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql-16
sudo systemctl start postgresql

# 创建数据库
createdb -U postgres paper
```

### 初始化数据库

```bash
# 数据库表会在首次启动时自动创建
python main.py
```

## 运行服务

### 开发模式（热重载）

```bash
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 生产模式

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

服务将在 `http://localhost:8000` 启动

## API 文档

启动后访问以下地址查看 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 项目结构

```
backend/
├── main.py                      # FastAPI 应用入口
├── database.py                  # 数据库管理
├── models.py                    # SQLAlchemy 模型
├── config.py                    # 配置管理
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量示例
│
├── services/                    # 业务逻辑层
│   ├── scholarflux_wrapper.py   # ScholarFlux 统一接口
│   ├── smart_paper_search.py    # 智能搜索（数据库+API）
│   ├── review_generator.py      # 综述生成服务
│   ├── hybrid_classifier.py     # 混合分类器
│   ├── paper_filter.py          # 文献筛选
│   ├── reference_validator.py   # 引用验证
│   ├── docx_generator.py        # Word 文档生成
│   └── ...                      # 其他服务
│
├── tests/                       # 测试
│   ├── conftest.py
│   └── test_cases.py
│
└── init_term_library.py         # 术语库初始化脚本
```

## 主要 API 端点

### 综述生成
- `POST /api/smart-generate` - 智能生成文献综述（异步任务）
- `GET /api/tasks/{task_id}` - 查询任务状态

### 文献搜索
- `GET /api/search` - 搜索论文
- `GET /api/papers/statistics` - 论文库统计
- `GET /api/papers/recent` - 最近入库论文
- `GET /api/papers/top-cited` - 高被引论文

### 记录管理
- `GET /api/records` - 获取记录列表
- `GET /api/records/{id}` - 获取记录详情
- `DELETE /api/records/{id}` - 删除记录
- `POST /api/records/export` - 导出 Word 文档

### 分析工具
- `POST /api/classify-topic` - 题目分类
- `POST /api/smart-analyze` - 智能分析
- `POST /api/validate-review` - 验证综述质量
- `POST /api/check-citation-order` - 检查引用顺序

## 常见问题

### Q: 如何切换数据库类型？

在 `.env` 文件中设置 `DB_TYPE=mysql` 或 `DB_TYPE=postgresql`

### Q: 数据源 API 配置建议

- **AMiner**: 必需，用于中文文献搜索
- **OpenAlex**: 推荐，免费且无限制
- **Semantic Scholar**: 可选，提供更准确的引用数据

### Q: 如何提高搜索质量？

1. 调整 `.env` 中的质量评分权重
2. 启用更多数据源
3. 增加 `search_years` 范围
