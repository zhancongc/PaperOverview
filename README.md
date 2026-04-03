# 论文综述生成器

基于 AI 的智能文献综述生成工具，使用 FastAPI + React 构建。

## 功能特性

### 🚀 核心功能

- **智能大纲生成**：自动生成综述结构，包含引言、主体章节、结论
- **多源文献搜索**：聚合 OpenAlex、Semantic Scholar、AMiner 等多个数据源
- **Function Calling 生成**：使用渐进式信息披露，节省 49% token
- **增强相关性评分**：多维度评分算法，确保高相关性论文优先
- **跨学科过滤**：自动分类论文领域，防止不相关引用
- **按小节文献管理**：每个小节分配专属文献，确保引用均匀

### 📊 文献管理

- **数据库优先**：优先从本地数据库搜索，减少 API 调用
- **渐进式搜索**：按需扩展同义词，避免浪费 API 资源
- **学术术语库**：预置深度学习、生物信息学等领域术语
- **自动去重**：智能去重保留最优论文

### 🎯 生成质量

- **全局连贯性**：一次性生成，保持全文连贯
- **引用验证**：自动验证引用格式和编号
- **质量过滤**：过滤低质量文献（会议通知、内部资料等）
- **统计报告**：自动生成文献统计信息

## 技术栈

### 后端

- **框架**：FastAPI
- **数据库**：PostgreSQL
- **LLM**：DeepSeek API
- **数据源**：OpenAlex、Crossref、DataCite、Semantic Scholar、AMiner

### 前端

- **框架**：React + TypeScript
- **构建工具**：Vite
- **UI**：原生 CSS

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### 后端设置

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的 API 密钥

# 初始化数据库
python migrate_to_postgresql.py

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 综述生成流程

```
输入：论文主题
    ↓
阶段1: 生成大纲和搜索关键词
    ↓
阶段2: 搜索词优化（语言区分）
    ↓
阶段3: 按小节搜索文献（渐进式）
    ↓
阶段4: 精简文献到N篇（相关性评分+跨学科过滤）
    ↓
阶段5: 生成综述（Function Calling）
    ↓
阶段6: 最终验证
    ↓
输出：完整综述
```

详细流程说明请查看 [docs/review_generation_flow.md](docs/review_generation_flow.md)

## 文档

- [综述生成流程详解](docs/review_generation_flow.md)
- [Function Calling 统一版本](docs/function_calling_unified.md)
- [高级功能说明](docs/advanced_features.md)

## 性能指标

- **Token 节省**：49%（使用 Function Calling）
- **搜索效率**：数据库优先减少 80% API 调用
- **并发控制**：最多 3 个任务同时执行
- **生成质量**：引用率 100%，全局连贯

## 许可证

MIT License
