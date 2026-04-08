# 辅助脚本使用说明

> 最后更新: 2026-04-08
>
> 本文档介绍项目中的各种辅助脚本的使用方法。

---

## 目录

- [Python 脚本](#python-脚本)
  - [manage_user.py - 用户管理工具](#manage_userpy---用户管理工具)
  - [init_db.py - 数据库初始化](#init_dbpy---数据库初始化)
- [Shell 脚本](#shell-脚本)
  - [server-install.sh - 服务器初始化安装](#server-installsh---服务器初始化安装)
  - [server-update.sh - 服务器自动更新](#server-updatesh---服务器自动更新)
  - [change_model.sh - Claude 模型切换](#change_modelsh---claude-模型切换)

---

## Python 脚本

### manage_user.py - 用户管理工具

**位置**: `backend/manage_user.py`

**功能**:
- 查看用户信息（额度、综述记录）
- 设置综述的付费/免费状态
- 增减用户免费额度和付费额度

**前置要求**:
- 在 `backend/` 目录下运行
- 确保 `.env.auth` 文件存在且配置正确

---

#### 命令列表

| 命令 | 说明 |
|------|------|
| `show-user` | 显示用户详细信息 |
| `set-record-status` | 设置综述的付费状态 |
| `update-credits` | 更新用户额度 |

---

#### 1. show-user - 显示用户信息

**用法**:
```bash
python manage_user.py show-user --email <用户邮箱>
```

**示例**:
```bash
python manage_user.py show-user --email user@example.com
```

**输出内容**:
- 用户 ID 和邮箱
- 免费额度 (`free_credits`)
- 付费额度 (`review_credits`)
- 已购买状态 (`has_purchased`)
- 该用户的所有综述记录列表

---

#### 2. set-record-status - 设置综述状态

**用法**:
```bash
python manage_user.py set-record-status --email <邮箱> [--topic <主题> | --record-id <ID>] [--paid | --unpaid]
```

**参数**:
| 参数 | 必需 | 说明 |
|------|------|------|
| `--email` | 是 | 用户邮箱 |
| `--topic` | 否 | 综述主题（与 `--record-id` 二选一） |
| `--record-id` | 否 | 综述 ID（与 `--topic` 二选一） |
| `--paid` | 是 | 设置为已付费状态（二选一） |
| `--unpaid` | 是 | 设置为待付费状态（二选一） |

**示例**:

```bash
# 通过主题设置为已付费
python manage_user.py set-record-status --email user@example.com --topic "深度学习" --paid

# 通过 ID 设置为待付费
python manage_user.py set-record-status --email user@example.com --record-id 123 --unpaid
```

---

#### 3. update-credits - 更新用户额度

**用法**:
```bash
python manage_user.py update-credits --email <邮箱> [--free-credits <值>] [--paid-credits <值>]
```

**参数**:
| 参数 | 说明 |
|------|------|
| `--email` | 用户邮箱（必需） |
| `--free-credits` | 免费额度变更（可选） |
| `--paid-credits` | 付费额度变更（可选） |

**额度值格式**:
- `+N` - 增加 N 个额度
- `-N` - 减少 N 个额度
- `N` - 直接设置为 N 个额度

**示例**:

```bash
# 增加 1 个免费额度
python manage_user.py update-credits --email user@example.com --free-credits +1

# 增加 3 个付费额度
python manage_user.py update-credits --email user@example.com --paid-credits +3

# 同时增加免费和付费额度
python manage_user.py update-credits --email user@example.com --free-credits +2 --paid-credits +3

# 设置免费额度为 5（直接赋值，不是增减）
python manage_user.py update-credits --email user@example.com --free-credits 5

# 减少 1 个付费额度
python manage_user.py update-credits --email user@example.com --paid-credits -1
```

---

### init_db.py - 数据库初始化

**位置**: `backend/init_db.py`

**功能**:
- 创建 MySQL 数据库
- 创建所有数据表

**前置要求**:
- MySQL 服务已启动
- `backend/.env` 文件已配置数据库连接信息

**环境变量配置** (`.env`):
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=paper
```

**用法**:
```bash
cd backend
python init_db.py
```

**执行步骤**:
1. 连接到 MySQL 服务器
2. 创建 `paper` 数据库（如果不存在）
3. 使用 SQLAlchemy 创建所有数据表

---

## Shell 脚本

### server-install.sh - 服务器初始化安装

**位置**: `server-install.sh`

**功能**:
在 Ubuntu 服务器上一键安装和配置 AutoOverview 项目的完整环境。

**包含内容**:
1. 系统更新 + 基础依赖安装
2. 安装 Node.js 20.x
3. 安装和配置 PostgreSQL
4. 创建项目目录和 Python 虚拟环境
5. 安装 Python 依赖
6. 构建 React 前端
7. 配置环境文件
8. 配置 systemd 服务
9. 安装和配置 Nginx
10. 数据库初始化

**前置要求**:
- Ubuntu 服务器
- root 权限或 sudo
- 项目文件已上传到 `/app/AutoOverview`

**用法**:
```bash
sudo ./server-install.sh
```

**配置变量** (脚本开头可修改):
```bash
PROJECT_DIR="/app/AutoOverview"    # 项目目录
PROJECT_USER="root"                  # 运行用户
DB_USER="postgres"                    # 数据库用户
DB_PASSWORD="security"                # 数据库密码（建议修改）
DB_NAME="paper"                       # 数据库名
DB_HOST="localhost"
DB_PORT="5432"
```

**安装完成后的后续步骤**:
1. 修改 `backend/.env` - 设置 API Key 等
2. 修改 `backend/.env.auth` - 设置 JWT 密钥、SMTP、支付宝等
3. 配置 SSL 证书: `certbot --nginx -d your-domain.com`
4. 修改 Nginx 配置中的域名
5. 启动服务: `systemctl start autooverview`

**服务管理命令**:
```bash
# 启动服务
sudo systemctl start autooverview

# 停止服务
sudo systemctl stop autooverview

# 重启服务
sudo systemctl restart autooverview

# 查看状态
sudo systemctl status autooverview

# 查看日志
sudo journalctl -u autooverview -f
```

---

### server-update.sh - 服务器自动更新

**位置**: `server-update.sh`

**功能**:
在已部署的服务器上自动拉取最新代码并更新部署。

**包含内容**:
1. 进入项目目录
2. 重置 frontend 目录更改
3. Git 拉取最新代码
4. 重新构建前端
5. 更新 Python 依赖
6. 检查数据库迁移
7. 更新 systemd 服务和 Nginx 配置
8. 重启服务
9. 验证服务状态

**前置要求**:
- 已通过 `server-install.sh` 安装的服务器
- root 权限或 sudo
- 项目在 `/app/AutoOverview` 目录

**用法**:
```bash
sudo ./server-update.sh
```

**执行步骤说明**:

| 步骤 | 说明 |
|------|------|
| 1/10 | 进入项目目录，创建必要的 cache/logs 目录 |
| 2/10 | 重置 frontend 目录的本地更改 |
| 3/10 | Git pull 拉取 main 分支最新代码 |
| 4/10 | npm install + npm run build 重新构建前端 |
| 5/10 | 更新 Python 依赖包 |
| 6/10 | 检查是否有数据库迁移脚本 |
| 7/10 | 更新 systemd 服务文件和 Nginx 配置 |
| 8/10 | 重新加载 systemd 配置 |
| 9/10 | 重启 autooverview 服务 |
| 10/10 | 验证服务状态和 HTTP 健康检查 |

**健康检查**:
脚本最后会执行以下检查：
- systemd 服务状态
- `/api/health` 端点 HTTP 状态
- 服务端口监听情况

---

### change_model.sh - Claude 模型切换

**位置**: `change_model.sh`

**功能**:
快速切换 Claude Code 使用的模型配置。

**前置要求**:
- Claude Code 已安装
- 模型配置文件存在于 `~/.claude/models/settings.json.<模型名>`

**支持的模型**:
- `aliyun` - 阿里云模型
- `glm` - 智谱 AI 模型
- `doubao` - 豆包模型

**用法**:
```bash
./change_model.sh <模型名>
```

**示例**:
```bash
# 切换到豆包模型
./change_model.sh doubao

# 切换到智谱模型
./change_model.sh glm

# 切换到阿里云模型
./change_model.sh aliyun
```

**执行流程**:
1. 检查模型配置文件是否存在
2. 备份当前的 `settings.json`（如果存在）
3. 复制选中的模型配置到目标位置
4. 自动启动 Claude

**配置文件位置**:
- 源配置: `~/.claude/models/settings.json.<模型名>`
- 目标配置: `~/.claude/settings.json`
- Claude 二进制: `~/.local/bin/claude`

---

## 附录

### 脚本位置总览

```
PaperOverview/
├── 📄 server-install.sh       # 服务器初始化安装
├── 📄 server-update.sh        # 服务器自动更新
├── 📄 change_model.sh         # Claude 模型切换
└── backend/
    ├── 📄 manage_user.py      # 用户管理工具
    ├── 📄 init_db.py          # 数据库初始化
    └── MANAGE_USER_README.md  # manage_user 详细说明
```

### 相关文档

- [INDEX.md](INDEX.md) - 文档首页
- [MAP.md](MAP.md) - 项目文件目录
- [CREDIT_SYSTEM.md](CREDIT_SYSTEM.md) - 额度体系设计
- [AUTH_INTEGRATION.md](../AUTH_INTEGRATION.md) - AuthKit 集成指南
