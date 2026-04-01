# 论文综述生成器

输入论文主题，自动生成带50篇参考文献的文献综述。

## 功能特点

- **智能文献检索**
  - 多数据源聚合：AMiner（中文）、OpenAlex（英文）、Semantic Scholar（补充）
  - 语言区分搜索：自动识别中英文，使用对应数据源
  - 论文数据库：自动保存所有搜索到的论文，避免重复搜索
- **智能筛选**
  - 近5年占比 ≥50%，英文文献占比 30%-70%
  - 按被引量排序，选取高质量文献
  - 质量过滤：自动过滤低质量文献（会议通知、内部资料等）
- **AI 综述生成**
  - 使用 DeepSeek API 生成学术综述
  - 自动引用处理：排序、合并、去重
  - 输出 Markdown 格式，含参考文献列表

## 技术栈

- **后端**: FastAPI (Python) + MySQL
- **前端**: React + TypeScript + Vite
- **文献检索**: AMiner API（中文）、OpenAlex API（英文）、Semantic Scholar（补充）
- **AI 生成**: DeepSeek API

## 快速开始

### 1. 后端设置

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

后端将在 `http://localhost:8000` 启动

### 2. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:3000` 启动

### 3. 使用

1. 在前端页面输入论文主题
2. 点击"生成综述"
3. 等待生成完成，查看综述和参考文献列表

## 项目结构

```
.
├── backend/               # 后端服务
│   ├── services/         # 业务逻辑
│   │   ├── scholarflux_wrapper.py    # 统一文献搜索API
│   │   ├── smart_paper_search.py     # 智能搜索（数据库+外部API）
│   │   ├── aminer_search.py          # AMiner搜索服务
│   │   ├── paper_search.py           # OpenAlex搜索服务
│   │   ├── paper_filter.py           # 文献筛选
│   │   ├── paper_quality_filter.py   # 质量过滤
│   │   ├── paper_metadata_dao.py     # 论文元数据DAO
│   │   ├── review_generator.py       # 综述生成
│   │   ├── hybrid_classifier.py      # 题目分析
│   │   └── reference_validator.py    # 引用验证
│   ├── models.py          # 数据库模型
│   ├── database.py        # 数据库配置
│   ├── main.py            # FastAPI 应用
│   └── requirements.txt   # Python 依赖
└── frontend/             # 前端应用
    ├── src/
    │   ├── components/   # React组件
    │   ├── App.tsx       # 主组件
    │   ├── api.ts        # API 调用
    │   └── types.ts      # 类型定义
    └── package.json      # Node 依赖
```

## API 文档

启动后端后，访问 `http://localhost:8000/docs` 查看完整 API 文档。

### 主要接口

#### 综述生成
- `POST /api/smart-generate` - 智能生成文献综述（推荐）
- `POST /api/generate` - 生成文献综述（基础版）

#### 文献搜索
- `GET /api/search` - 搜索论文
- `GET /api/papers/statistics` - 论文库统计信息
- `GET /api/papers/recent` - 最近入库的论文
- `GET /api/papers/top-cited` - 高被引论文

#### 记录管理
- `GET /api/records` - 获取生成记录列表
- `GET /api/records/{record_id}` - 获取单条记录详情
- `DELETE /api/records/{record_id}` - 删除记录

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

# MySQL 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=xxx
DB_NAME=paper
```

## 数据库表

| 表名 | 说明 |
|------|------|
| `review_records` | 综述生成记录 |
| `paper_metadata` | 论文元数据（所有搜索到的论文） |

## 开源协议

MIT License
