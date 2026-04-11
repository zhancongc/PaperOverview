# AutoOverview v1.0 中文版（归档分支）

> **⚠️ 此分支已停止开发，仅供维护使用**
>
> 最新开发请移至 [`main`](https://github.com/zhancongc/PaperOverview/tree/main) 分支

---

## 📌 分支信息

- **版本**：v1.0
- **标签**：[v1.0 Release](https://github.com/zhancongc/PaperOverview/releases/tag/v1.0)
- **状态**：🔒 锁定 - 仅接受关键 Bug 修复
- **语言**：中文
- **发布日期**：2026-04-11

---

## ✨ 核心功能

- **📚 真实文献数据库**：深度检索 2亿+ 真实论文（Semantic Scholar、IEEE 等权威数据库）
- **⚡ 5分钟生成综述**：AI 驱动的智能综述生成
- **📝 规范引用格式**：支持 IEEE、APA、MLA、GB/T 7714 等多种引用格式
- **🌍 中英文双语**：支持中英文综述生成
- **✅ 拒绝 AI 幻觉**：所有引用文献真实可溯源

---

## 🚀 部署方式

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

### 后端部署

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 配置环境变量
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端部署

```bash
cd frontend
npm install
npm run build
npm run preview
```

---

## 🔧 维护说明

### 适用场景

此分支仅适用于以下情况：
- 🔴 生产环境紧急 Bug 修复
- 🔴 安全漏洞修复
- 🔴 关键问题补丁

### 不适用场景

- ❌ 新功能开发（请使用 `main` 分支）
- ❌ 优化改进（请使用 `main` 分支）
- ❌ 实验性功能（请使用 `main` 分支）

### 提交流程

如需修复关键 Bug：

1. 基于此分支创建修复分支：`git checkout -b fix/v1.0-critical-bug`
2. 完成修复并测试
3. 提交 Pull Request 到此分支
4. 审核通过后合并
5. 创建新的补丁标签（如 `v1.0.1`）

---

## 📦 技术栈

- **后端**：FastAPI (Python)
- **前端**：React + TypeScript + Vite
- **数据库**：PostgreSQL + Redis
- **AI 模型**：DeepSeek LLM

---

## 📚 文档

- [项目文档索引](../docs/INDEX.md)
- [API 文档](../docs/API.md)
- [部署指南](../docs/DEPLOYMENT.md)

---

## 🙏 致谢

感谢所有早期用户和贡献者的支持！

---

## 📮 联系方式

- 问题反馈：[GitHub Issues](https://github.com/zhancongc/PaperOverview/issues)
- 项目主页：[AutoOverview](https://github.com/zhancongc/PaperOverview)
