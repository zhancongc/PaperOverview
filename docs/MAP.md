# 项目文件目录

> 最后更新: 2026-04-11
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
├── 📄 SCRIPTS.md         # 辅助脚本使用说明
├── 📄 CREDIT_SYSTEM.md  # 额度体系设计
├── 📄 STATS.md          # 统计功能文档（新增）
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
│   │   ├── __init__.py         # User 模型
│   │   ├── schemas.py          # Pydantic 模型
│   │   ├── payment.py          # 支付模型（Subscription, PaymentLog）
│   │   └── stats.py            # 统计模型（SiteStats, VisitLog）
│   ├── 📁 routers/             # API 路由
│   │   ├── auth.py             # 认证路由
│   │   ├── stats.py            # 统计路由（公开）
│   │   ├── admin_stats.py      # 管理员统计路由（需授权）
│   │   ├── subscription.py     # 支付订阅路由
│   │   ├── webhook.py          # 支付回调路由
│   │   └── payment_callback.py # 支付结果路由
│   ├── 📁 services/            # 业务逻辑
│   │   ├── auth_service.py     # 认证服务（含注册统计）
│   │   ├── admin_stats_service.py # 管理员统计服务
│   │   ├── stats_service.py    # 统计服务
│   │   ├── email_service.py    # 邮件服务
│   │   └── cache_service.py    # 缓存服务
│   ├── 📁 middleware/          # 中间件
│   │   └── stats_middleware.py # 访问量统计中间件（DDoS 防护）
│   ├── 📁 core/                # 核心功能
│   │   ├── security.py         # JWT、密码加密
│   │   ├── validator.py        # 数据验证
│   │   └── config.py           # 配置管理
│   └── 📁 templates/           # 邮件模板
├── 📁 services/                # 核心业务服务
│   ├── 📄 smart_review_generator_final.py  # 综述生成核心
│   ├── 📄 review_task_executor.py          # 异步任务执行
│   ├── 📄 task_manager.py                  # 任务管理
│   ├── 📄 credit_service.py                # 额度服务
│   ├── 📄 docx_generator.py                # Word 导出
│   ├── 📄 paper_filter.py                  # 论文过滤
│   └── 📄 *_search.py                      # 多源文献搜索
├── 📁 models/                  # SQLAlchemy 数据模型
│   ├── __init__.py             # 所有数据模型定义
│   ├── review_records.py       # 综述记录
│   ├── review_tasks.py         # 综述任务
│   └── ...                     # 其他模型
├── 📁 routers/                 # API 路由
├── 📁 config/                  # 配置文件
└── 📁 tests/                   # 测试用例
```

### 关键文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | FastAPI 应用入口，所有 API 路由注册、额度检查中间件、统计中间件 |
| `authkit/middleware/stats_middleware.py` | 访问量统计中间件，支持 DDoS 防护 |
| `authkit/services/stats_service.py` | 统计服务，支持 Redis 缓存 |
| `authkit/services/admin_stats_service.py` | 管理员统计服务，汇总所有数据 |
| `services/smart_review_generator_final.py` | 综述生成核心逻辑 |
| `services/review_task_executor.py` | 异步任务执行器 |

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
    ├── 📄 main.tsx           # 应用入口（路由配置）
    └── 📁 components/        # React 组件
        ├── 📄 SimpleApp.tsx  # 主页（输入 + 定价）
        ├── 📄 ReviewPage.tsx # 综述详情页
        ├── 📄 ReviewViewer.tsx # Markdown 渲染器
        ├── 📄 LoginPage.tsx  # 登录页
        ├── 📄 ProfilePage.tsx # 个人中心
        ├── 📄 DavidPage.tsx  # 数据统计页（新增）
        └── 📄 PaymentModal.tsx # 支付弹窗
```

### 关键组件说明

| 组件 | 说明 |
|------|------|
| `SimpleApp.tsx` | 主页，包含输入框、定价卡片、功能介绍 |
| `ReviewPage.tsx` | 综述展示页，正文/参考文献分 Tab |
| `ReviewViewer.tsx` | Markdown 渲染器，带 TOC 侧边栏 |
| `DavidPage.tsx` | 数据统计页面，仅白名单用户可访问 |
| `PaymentModal.tsx` | 支付弹窗，支付宝扫码支付 |

---

## 技术栈速览

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | FastAPI + Python |
| 前端框架 | React + TypeScript + Vite |
| 数据库 | PostgreSQL |
| 缓存 | Redis（统计缓存、验证码存储） |
| LLM | DeepSeek API |
| 数据源 | Semantic Scholar, Crossref, DataCite, AMiner, OpenAlex |

---

## 核心功能模块

### 1. 认证与支付（AuthKit）

**文档：** [AUTH_INTEGRATION.md](../AUTH_INTEGRATION.md) | [authkit/README.md](../backend/authkit/README.md)

- 用户注册/登录（密码 + 验证码）
- JWT 认证
- 支付宝扫码支付
- 额度管理

### 2. 综述生成

**文档：** [review_generation_flow.md](review_generation_flow.md) | [smart_review_generator.md](smart_review_generator.md)

- 异步任务队列
- 6 阶段生成流程
- IEEE 引用格式
- Word/PDF 导出

### 3. 统计分析

**文档：** [STATS.md](STATS.md)

- 访问量统计（Redis 缓存 + 批量写入）
- 注册量统计
- 生成数统计
- 付费数据统计
- /david 数据统计页面（白名单访问）

---

## 环境变量配置

### 数据库配置

```bash
DATABASE_URL=postgresql://user:password@localhost/dbname
```

### Redis 配置

```bash
AUTH_REDIS_HOST=localhost
AUTH_REDIS_PORT=6379
AUTH_REDIS_DB=0
AUTH_REDIS_PASSWORD=
```

### 白名单配置

```bash
# 案例展示白名单（/review 页面免登录访问）
DEMO_TASK_IDS=81fac90d,59c01cc4,2a90e24d

# /david 页面访问白名单
DAVID_WHITELIST=zhancongc@icloud.com

# /jade 页面访问白名单
JADE_WHITELIST=
```

### LLM 配置

```bash
DEEPSEEK_API_KEY=your_api_key_here
```

---

## API 端点速览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/login-with-code` | POST | 验证码登录 |
| `/api/tasks` | POST | 创建综述任务 |
| `/api/tasks/{task_id}` | GET | 获取任务状态 |
| `/api/tasks/{task_id}/review` | GET | 获取综述内容 |
| `/api/stats/overview` | GET | 获取统计概览（公开）|
| `/api/stats/daily` | GET | 获取每日统计（公开）|
| `/api/admin/stats/overview` | GET | 获取管理员统计（需授权）|
| `/api/admin/stats/daily` | GET | 获取管理员每日统计（需授权）|
| `/api/david/access` | GET | 检查 /david 页面访问权限 |
