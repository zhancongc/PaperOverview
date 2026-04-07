# CLAUDE.md — AutoOverview 项目指引

> 给 Claude Code 的上下文文件，帮助理解项目结构和约定。

## 项目简介

AutoOverview 是一个 AI 驱动的文献综述生成平台。用户输入研究主题，系统自动搜索文献并生成高质量的中文学术综述。

**技术栈**: FastAPI (Python) + React (TypeScript/Vite) + PostgreSQL

## 核心流程

1. **阶段1**: PaperSearchAgent - LLM + Function Calling 驱动的文献检索（Semantic Scholar）
2. **阶段2**: SmartReviewGeneratorFinal - 生成综述（预处理 → 初始生成 → 5条引用规范应用 → IEEE 格式）
3. **阶段3**: CitationValidatorV2 - 额外引用校验和修复

## 关键约定

### 后端
- **主入口**: `backend/main.py` — 所有 API 路由、中间件、额度检查
- **综述生成核心**: `backend/services/smart_review_generator_final.py`
- **异步任务**: `backend/services/review_task_executor.py`，通过 TaskManager 管理轮询
- **认证模块**: `backend/authkit/` — 独立可复用的认证 & 支付模块
- **JWT**: token 中用户 ID 存储在 `sub` 字段，不是 `user_id`
- **额度体系**: 注册送 1 篇，按次扣费（体验包/基础包/进阶包），字段 `review_credits`
- **环境变量**: `backend/.env` 配置 DeepSeek API Key、数据库等

### 前端
- **主页**: `SimpleApp.tsx`（输入框 + 定价卡片 + 功能介绍）
- **综述页**: `ReviewPage.tsx`（正文/参考文献分 Tab，URL: `/review?task_id=xxx`）
- **渲染器**: `ReviewViewer.tsx`（Markdown + TOC 侧边栏，标题级别会自动标准化）
- **认证**: `LoginPage.tsx` + `authApi.ts`（验证码登录，无密码登录）
- **支付**: `PaymentModal.tsx`（支付宝扫码，开发环境走 mock）
- **PDF 导出**: `frontend/src/utils/pdfExport.ts`（html2canvas + jsPDF，纯前端）
- **路由**: hash 路由（`/#/login`, `/#pricing`, `/#profile`）

### 额度与导出逻辑
- 免费额度：注册送 1 篇，可导出带水印 PDF
- 付费额度：可导出无水印 Word（服务端 python-docx）
- 生成时立即扣额度（`check_and_deduct_credit`），任务失败不退回
- 导出 Word 时检查 `has_purchased`，未购买弹支付弹窗

### API 路径
- 前端代理: `localhost:3000` → `localhost:8000`（vite.config.ts 配置）
- API 前缀: `/api/...`
- 认证头: `Authorization: Bearer <token>`

## 文档

- **[docs/INDEX.md](docs/INDEX.md)** — 文档首页，渐进式披露文档（推荐从这里开始）
- **[docs/MAP.md](docs/MAP.md)** — 完整文档目录，包含所有文档的列表
