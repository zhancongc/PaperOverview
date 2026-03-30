# 论文综述生成器

输入论文主题，自动生成带50篇参考文献的文献综述。

## 功能特点

- 自动检索相关文献（基于 OpenAlex API）
- 智能筛选：近5年占比 ≥50%，英文文献占比 ≥30%
- 按被引量排序，选取高质量文献
- 使用 DeepSeek API 生成学术综述
- 输出 Markdown 格式，含参考文献列表

## 技术栈

- **后端**: FastAPI (Python)
- **前端**: React + TypeScript + Vite
- **文献检索**: OpenAlex API（免费，无需申请）
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
│   │   ├── paper_search.py    # 文献检索
│   │   ├── paper_filter.py    # 文献筛选
│   │   └── review_generator.py # 综述生成
│   ├── main.py           # FastAPI 应用
│   └── requirements.txt   # Python 依赖
└── frontend/             # 前端应用
    ├── src/
    │   ├── App.tsx       # 主组件
    │   ├── api.ts        # API 调用
    │   └── types.ts      # 类型定义
    └── package.json      # Node 依赖
```

## API 文档

启动后端后，访问 `http://localhost:8000/docs` 查看完整 API 文档。

### 主要接口

- `POST /api/generate` - 生成文献综述
- `GET /api/search` - 搜索论文
- `GET /api/health` - 健康检查

## 开源协议

MIT License
