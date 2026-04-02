# 论文综述生成器

输入论文主题，自动生成带50篇参考文献的文献综述。

## 功能特点

- **智能文献检索**
  - ScholarFlux 多数据源聚合：AMiner（中文）、OpenAlex（英文）、Semantic Scholar、Crossref、DataCite
  - 论文元数据数据库：自动保存所有搜索到的论文，避免重复搜索
  - 可配置数据源开关，灵活控制搜索策略

- **AI 综述生成**
  - DeepSeek 大模型驱动，自动生成学术综述
  - 混合分类器：规则引擎 + LLM 验证，准确识别题目类型
  - 场景特异性综述框架：应用型、评价型、理论型、实证型
  - 异步任务模式，支持长时间生成任务

- **质量控制**
  - 低质量文献过滤：自动过滤会议通知、内部资料等
  - 引用数量和年份分布验证
  - 引用顺序检查：确保正文引用连续无遗漏
  - 按被引量排序，优先选择高质量文献

- **高级功能**
  - 自然数据嵌入：统计数据自然融入叙述，避免 AI 痕迹
  - 深度对比分析：不仅列出对立观点，还分析分歧原因
  - 综述润色：自动消除 AI 腔，让语言更干练
  - 观点碰撞分析：结构化分析学术争议
  - Word 文档导出：一键生成格式规范的 Word 文档

## 技术栈

- **后端**: FastAPI (Python) + PostgreSQL
- **前端**: React + TypeScript + Vite
- **文献检索**: ScholarFlux（多数据源聚合：AMiner、OpenAlex、Semantic Scholar、Crossref、DataCite）
- **AI 生成**: DeepSeek API
- **容器化**: Docker Compose

## 快速开始

### 使用 Docker（推荐）

```bash
# 1. 启动 PostgreSQL 数据库
docker-compose up -d

# 2. 后端设置
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
python main.py

# 3. 前端设置
cd frontend
npm install
npm run dev
```

### 手动安装

#### 1. 数据库设置

```bash
# 安装 PostgreSQL 16
# macOS
brew install postgresql@16
brew services start postgresql@16

# 创建数据库
createdb -U postgres paper
```

#### 2. 后端设置

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY

# 启动服务
python main.py
```

#### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 4. 使用系统

1. 打开浏览器访问 `http://localhost:3000`
2. 输入论文主题
3. 点击"生成综述"
4. 等待生成完成，查看综述和参考文献列表

## 项目结构

```
.
├── backend/               # 后端服务
│   ├── services/         # 业务逻辑
│   │   ├── scholarflux_wrapper.py    # ScholarFlux统一接口
│   │   ├── smart_paper_search.py     # 智能搜索（数据库+API）
│   │   ├── review_generator.py       # 综述生成
│   │   ├── hybrid_classifier.py      # 混合分类器
│   │   ├── paper_filter.py           # 文献筛选
│   │   ├── reference_validator.py    # 引用验证
│   │   ├── docx_generator.py         # Word文档生成
│   │   └── ...                      # 其他服务模块
│   ├── models.py          # 数据库模型
│   ├── database.py        # 数据库管理（支持PostgreSQL/MySQL）
│   ├── main.py            # FastAPI 应用
│   └── requirements.txt   # Python 依赖
├── frontend/             # 前端应用
│   ├── src/
│   │   ├── components/   # React组件
│   │   ├── App.tsx       # 主组件
│   │   ├── api.ts        # API 调用
│   │   └── types.ts      # 类型定义
│   └── package.json      # Node 依赖
├── docs/                 # 项目文档
├── docker-compose.yml    # Docker Compose 配置
└── README.md            # 项目说明
```

## API 文档

启动后端后，访问 `http://localhost:8000/docs` 查看完整 API 文档。

### 主要接口

#### 综述生成
- `POST /api/smart-generate` - 智能生成文献综述（异步任务）
- `GET /api/tasks/{task_id}` - 查询任务状态

#### 题目分析
- `POST /api/classify-topic` - 题目分类
- `POST /api/smart-analyze` - 智能分析

#### 文献搜索
- `GET /api/search` - 搜索论文
- `GET /api/papers/statistics` - 论文库统计信息
- `GET /api/papers/recent` - 最近入库的论文
- `GET /api/papers/top-cited` - 高被引论文

#### 记录管理
- `GET /api/records` - 获取生成记录列表
- `GET /api/records/{record_id}` - 获取单条记录详情
- `DELETE /api/records/{record_id}` - 删除记录
- `POST /api/records/export` - 导出 Word 文档

#### 验证工具
- `POST /api/validate-review` - 验证综述质量
- `POST /api/check-citation-order` - 检查引用顺序

#### 其他
- `GET /api/health` - 健康检查
- `GET /api/config/schema` - 获取配置Schema
- `GET /api/config/server` - 获取服务端配置

## 环境变量配置

```bash
# DeepSeek API（用于LLM生成）
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# AMiner API（用于中文文献搜索和详情补充）
AMINER_API_TOKEN=eyJxxx

# Semantic Scholar API Key（可选，提高速率限制）
SEMANTIC_SCHOLAR_API_KEY=your_key_here

# 数据库配置
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=security
DB_NAME=paper
```

### Docker 部署（推荐）

```bash
# 启动 PostgreSQL 数据库
docker-compose up -d

# 后续步骤...
```

## 数据库表

| 表名 | 说明 |
|------|------|
| `review_records` | 综述生成记录 |
| `paper_metadata` | 论文元数据（所有搜索到的论文） |

## 开源协议

MIT License
