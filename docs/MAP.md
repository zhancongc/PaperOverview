# 项目文件目录

> 最后更新: 2026-04-08
>
> 本文档展示项目整体结构，目录深度不超过三级。
> 如需文档导航，请查看 [INDEX.md](INDEX.md)。

---

## 项目结构

```
PaperOverview/
├── 📄 CLAUDE.md                    # Claude Code 项目指引
├── 📄 README.md                    # 项目说明与快速开始
├── 📄 AUTH_INTEGRATION.md          # AuthKit 集成指南
├── 📄 docker-compose.yml           # PostgreSQL 容器配置
├── 📄 server-install.sh            # 服务器初始化安装脚本
├── 📄 server-update.sh             # 服务器自动更新脚本
├── 📄 change_model.sh              # Claude 模型切换脚本
├── 📁 docs/                        # 项目文档目录
├── 📁 backend/                     # FastAPI 后端
└── 📁 frontend/                    # React 前端
```

---

## 📁 docs/ — 项目文档

```
docs/
├── 📄 INDEX.md           # 文档首页（渐进式导航）
├── 📄 MAP.md             # 本文档（项目文件目录）
├── 📄 SCRIPTS.md         # 辅助脚本使用说明（新增）
├── 📄 CREDIT_SYSTEM.md  # 额度体系设计
├── 📄 async_api.md       # 异步 API 设计
├── 📄 review_generation_flow.md  # 综述生成流程
├── 📄 smart_review_generator.md  # 综述生成器文档
├── 📄 function_calling_unified.md # Function Calling 实现
├── 📄 advanced_features.md         # 高级功能说明
└── 📁 archive/           # 归档文档（历史参考）
```

---

## 📁 backend/ — 后端服务

```
backend/
├── 📄 main.py                  # FastAPI 主入口（路由 + 中间件）
├── 📄 database.py              # 数据库初始化
├── 📄 requirements.txt         # Python 依赖
├── 📄 .env.example             # 环境变量示例
├── 📁 authkit/                 # 认证 & 支付模块
│   ├── 📄 README.md            # AuthKit 文档
│   ├── 📁 models/              # 数据模型
│   ├── 📁 routers/             # API 路由
│   └── 📁 services/            # 业务逻辑
├── 📁 services/                # 核心业务服务
│   ├── 📄 smart_review_generator_final.py  # 综述生成核心
│   ├── 📄 review_task_executor.py          # 异步任务执行
│   ├── 📄 task_manager.py                  # 任务管理
│   ├── 📄 credit_service.py                # 额度服务
│   ├── 📄 docx_generator.py                # Word 导出
│   ├── 📄 paper_filter.py                  # 论文过滤
│   └── 📄 *_search.py                      # 多源文献搜索
├── 📁 models/                  # SQLAlchemy 数据模型
├── 📁 routers/                 # API 路由
├── 📁 config/                  # 配置文件
└── 📁 tests/                   # 测试用例
```

### 关键文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | FastAPI 应用入口，所有 API 路由注册、额度检查中间件 |
| `services/smart_review_generator_final.py` | 综述生成核心逻辑 |
| `services/review_task_executor.py` | 异步任务执行器 |
| `authkit/` | 独立可复用的认证支付模块 |

---

## 📁 frontend/ — 前端应用

```
frontend/
├── 📄 package.json           # Node 依赖
├── 📄 tsconfig.json          # TypeScript 配置
├── 📄 vite.config.ts         # Vite 配置
├── 📄 index.html             # HTML 入口
└── 📁 src/
    ├── 📄 api.ts             # 后端 API 客户端
    ├── 📄 authApi.ts         # 认证 API 客户端
    ├── 📄 types.ts           # TypeScript 类型定义
    ├── 📄 App.tsx            # 主应用组件
    ├── 📄 main.tsx           # 应用入口
    ├── 📁 components/        # React 组件
    │   ├── 📄 SimpleApp.tsx  # 主页（输入 + 定价）
    │   ├── 📄 ReviewPage.tsx # 综述详情页
    │   ├── 📄 ReviewViewer.tsx # Markdown 渲染器
    │   ├── 📄 LoginPage.tsx  # 登录页
    │   ├── 📄 ProfilePage.tsx # 个人中心
    │   ├── 📄 PaymentModal.tsx # 支付弹窗
    │   └── ...
    └── 📁 utils/             # 工具函数
        └── 📄 pdfExport.ts   # PDF 导出
```

### 关键组件说明

| 组件 | 说明 |
|------|------|
| `SimpleApp.tsx` | 主页，包含输入框、定价卡片、功能介绍 |
| `ReviewPage.tsx` | 综述展示页，正文/参考文献分 Tab |
| `ReviewViewer.tsx` | Markdown 渲染器，带 TOC 侧边栏 |
| `PaymentModal.tsx` | 支付弹窗，支付宝扫码支付 |

---

## 技术栈速览

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | FastAPI + Python |
| 前端框架 | React + TypeScript + Vite |
| 数据库 | PostgreSQL |
| LLM | DeepSeek API |
| 数据源 | Semantic Scholar, Crossref, DataCite, AMiner, OpenAlex |
