# AutoOverview 文档中心

> 最后更新: 2026-04-11

欢迎使用 AutoOverview 文档中心！本页面为您提供渐进式的文档导航，帮助您快速找到所需信息。

---

## 🚀 快速开始

如果您是第一次接触 AutoOverview，建议从这里开始：

| 文档 | 说明 |
|------|------|
| [../README.md](../README.md) | 项目概述与快速开始指南 |
| [MAP.md](MAP.md) | 完整文档目录（所有文档列表）|

---

## 📚 核心文档（必读）

### 产品与业务
- [CREDIT_SYSTEM.md](CREDIT_SYSTEM.md) - 额度体系设计（定价模型、支付集成）
- [STATS.md](STATS.md) - 统计功能文档（访问量、注册量、付费数据）

### 技术架构
- [async_api.md](async_api.md) - 异步综述生成 API 设计与前端对接
- [review_generation_flow.md](review_generation_flow.md) - 综述生成全流程（6 个阶段详解）

### 开发指南
- [../CLAUDE.md](../CLAUDE.md) - Claude Code 项目指引（关键约定）
- [../AUTH_INTEGRATION.md](../AUTH_INTEGRATION.md) - AuthKit 集成指南
- [../backend/authkit/README.md](../backend/authkit/README.md) - AuthKit 认证模块文档
- [SCRIPTS.md](SCRIPTS.md) - 辅助脚本使用说明（用户管理、服务器部署等）

---

## 🔧 深入技术（选读）

需要了解更多技术细节？请查看：

| 文档 | 说明 |
|------|------|
| [smart_review_generator.md](smart_review_generator.md) | 智能综述生成器实现 |
| [function_calling_unified.md](function_calling_unified.md) | Function Calling 统一版本 |
| [advanced_features.md](advanced_features.md) | 高级功能说明 |

---

## 📂 完整文档目录

如需查看所有文档（包括归档文档），请访问 [MAP.md](MAP.md)。

---

## 项目结构速览

```
PaperOverview/
├── backend/
│   ├── main.py                  # FastAPI 主入口
│   ├── authkit/                 # 认证 & 支付模块
│   │   ├── models/              # 数据模型
│   │   ├── routers/             # API 路由
│   │   ├── services/            # 业务逻辑
│   │   └── middleware/          # 中间件（统计等）
│   └── services/                # 核心业务逻辑
└── frontend/
    └── src/components/          # React 组件
        ├── SimpleApp.tsx        # 主页
        ├── ReviewPage.tsx       # 综述详情页
        └── DavidPage.tsx        # 数据统计页
```

更多详细结构请查看 [MAP.md](MAP.md)。
