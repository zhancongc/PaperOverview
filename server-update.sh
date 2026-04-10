#!/bin/bash
# =====================================================
# AutoOverview - 服务器自动更新脚本
# 用途：
#   1. 拉取最新代码
#   2. 重置 frontend 目录更改
#   3. 重新构建前端
#   4. 更新 Python 依赖
#   5. 执行数据库迁移
#   6. 更新 systemd 服务和 Nginx 配置
#   7. 重启服务并验证
# =====================================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目路径
PROJECT_DIR="/app/AutoOverview"
SERVICE_NAME="autooverview"

# 从 .env 文件读取数据库配置
ENV_FILE="$PROJECT_DIR/backend/.env"
if [ -f "$ENV_FILE" ]; then
    # 读取 .env 文件中的数据库配置
    export $(grep "^DB_HOST=" "$ENV_FILE" | xargs)
    export $(grep "^DB_PORT=" "$ENV_FILE" | xargs)
    export $(grep "^DB_USER=" "$ENV_FILE" | xargs)
    export $(grep "^DB_PASSWORD=" "$ENV_FILE" | xargs)
    export $(grep "^DB_NAME=" "$ENV_FILE" | xargs)
else
    echo -e "${RED}错误：未找到 .env 文件${NC}"
    exit 1
fi

echo -e "${BLUE}=========================================="
echo "AutoOverview 服务器更新"
echo -e "==========================================${NC}"
echo ""

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误：请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 1. 进入项目目录
echo -e "${YELLOW}[1/10] 进入项目目录...${NC}"
cd "$PROJECT_DIR" || {
    echo -e "${RED}错误：无法进入目录 $PROJECT_DIR${NC}"
    exit 1
}
echo -e "${GREEN}✓ 当前目录：$(pwd)${NC}"
echo ""

# 创建必要的目录
mkdir -p backend/cache
mkdir -p backend/logs
chmod 755 backend/cache 2>/dev/null || true
chmod 755 backend/logs 2>/dev/null || true
echo -e "${GREEN}✓ 必要目录已创建${NC}"
echo ""

# 2. 重置 frontend 目录更改
echo -e "${YELLOW}[2/10] 重置 frontend 目录更改...${NC}"
git checkout HEAD -- frontend/ 2>/dev/null || true
echo -e "${GREEN}✓ frontend 目录已重置${NC}"
echo ""

# 3. Git 拉取最新代码
echo -e "${YELLOW}[3/10] 拉取最新代码...${NC}"
git pull origin main || {
    echo -e "${RED}错误：Git pull 失败${NC}"
    exit 1
}
echo -e "${GREEN}✓ 代码更新完成${NC}"
echo ""

# 显示最新提交信息
echo -e "${YELLOW}最新提交信息：${NC}"
git log -1 --oneline
echo ""

# 4. 重新构建前端
echo -e "${YELLOW}[4/10] 重新构建前端...${NC}"
cd "$PROJECT_DIR/frontend"
if [ -f "package.json" ]; then
    npm install
    npm run build
    echo -e "${GREEN}✓ 前端构建完成 → frontend/dist/${NC}"
else
    echo -e "${YELLOW}警告：frontend/package.json 不存在，跳过前端构建${NC}"
fi
cd "$PROJECT_DIR"
echo ""

# 5. 更新 Python 依赖
echo -e "${YELLOW}[5/10] 检查并更新 Python 依赖...${NC}"
if [ -f "$PROJECT_DIR/backend/requirements.txt" ]; then
    # 升级 pip
    "$PROJECT_DIR/backend/.venv/bin/pip" install --upgrade pip --quiet

    # 安装/更新依赖
    "$PROJECT_DIR/backend/.venv/bin/pip" install -r "$PROJECT_DIR/backend/requirements.txt" --quiet
    echo -e "${GREEN}✓ Python 依赖已更新${NC}"
else
    echo -e "${YELLOW}警告：requirements.txt 不存在，跳过依赖更新${NC}"
fi
echo ""

# 6. 检查并执行数据库迁移
echo -e "${YELLOW}[6/10] 检查并执行数据库迁移...${NC}"
echo ""

# 检查是否有迁移脚本
MIGRATION_SCRIPTS=$(find "$PROJECT_DIR/backend" -name "migrate_*.py" -type f | sort)
if [ -n "$MIGRATION_SCRIPTS" ]; then
    echo -e "${BLUE}发现迁移脚本，开始执行...${NC}"
    echo ""

    # 执行每个迁移脚本
    echo "$MIGRATION_SCRIPTS" | while read script; do
        script_name=$(basename "$script")
        echo -e "${YELLOW}执行: $script_name${NC}"

        # 使用项目的 Python 环境执行脚本
        if "$PROJECT_DIR/backend/.venv/bin/python" "$script"; then
            echo -e "${GREEN}✓ $script_name 执行成功${NC}"
        else
            echo -e "${RED}✗ $script_name 执行失败${NC}"
            exit 1
        fi
        echo ""
    done

    echo -e "${GREEN}✓ 所有迁移脚本执行完成${NC}"
else
    echo -e "${GREEN}✓ 未发现待执行的迁移脚本${NC}"
fi
echo ""

# 7. 更新 systemd 服务文件
echo -e "${YELLOW}[7/10] 更新 systemd 服务文件...${NC}"
if [ -f "$PROJECT_DIR/autooverview.service" ]; then
    cp "$PROJECT_DIR/autooverview.service" /etc/systemd/system/
    chmod 644 /etc/systemd/system/autooverview.service
    echo -e "${GREEN}✓ 服务文件已更新${NC}"
else
    echo -e "${YELLOW}警告：autooverview.service 不存在${NC}"
fi

# 更新 Nginx 配置
if [ -f "$PROJECT_DIR/nginx-autooverview.conf" ]; then
    cp "$PROJECT_DIR/nginx-autooverview.conf" "/etc/nginx/sites-available/autooverview"
    if nginx -t &> /dev/null; then
        systemctl reload-or-restart nginx || true
        echo -e "${GREEN}✓ Nginx 配置已更新并重载${NC}"
    else
        echo -e "${YELLOW}警告：Nginx 配置测试失败${NC}"
        nginx -t
    fi
fi
echo ""

# 8. 重新加载 systemd 配置
echo -e "${YELLOW}[8/10] 重新加载 systemd 配置...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ systemd 配置已重新加载${NC}"
echo ""

# 9. 重启服务
echo -e "${YELLOW}[9/10] 重启服务...${NC}"
systemctl restart "$SERVICE_NAME"
sleep 3
echo -e "${GREEN}✓ 服务已重启${NC}"
echo ""

# 10. 验证服务状态
echo -e "${YELLOW}[10/10] 验证服务状态...${NC}"
echo ""

all_services_ok=true

# 检查 systemd 状态
echo "检查服务: $SERVICE_NAME"
echo "----------------------------------------"

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}状态: 运行中 ✓${NC}"

    # 显示运行时间
    uptime=$(systemctl show "$SERVICE_NAME" -p ActiveEnterTimestamp --value)
    echo "启动时间: $uptime"

    # 显示最近几行日志
    echo ""
    echo "最近日志："
    journalctl -u "$SERVICE_NAME" -n 5 --no-pager

    echo ""
    echo -e "${GREEN}✓ $SERVICE_NAME 服务正常${NC}"
else
    echo -e "${RED}状态: 未运行 ✗${NC}"
    echo ""
    echo "错误日志："
    journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    echo ""
    echo -e "${RED}✗ $SERVICE_NAME 服务启动失败${NC}"
    all_services_ok=false
fi

echo ""
echo "=========================================="
echo ""

# HTTP 健康检查
echo "HTTP 健康检查..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8006/api/health 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ /api/health → 200${NC}"
    curl -s http://localhost:8006/api/health 2>/dev/null | "$PROJECT_DIR/backend/.venv/bin/python" -m json.tool 2>/dev/null || true
else
    echo -e "${RED}✗ /api/health → $HEALTH_RESPONSE${NC}"
    all_services_ok=false
fi

echo ""

# 总结
if [ "$all_services_ok" = true ]; then
    echo -e "${GREEN}=========================================="
    echo "所有服务更新成功！"
    echo -e "==========================================${NC}"
    echo ""

    # 显示服务监听端口
    echo "服务端口监听情况："
    echo "----------------------------------------"
    ss -tlnp | grep -E "(8000|80)" 2>/dev/null || netstat -tlnp 2>/dev/null | grep -E "(8000|80)" || true
    echo ""

    exit 0
else
    echo -e "${RED}=========================================="
    echo "部分服务启动失败，请检查上面的日志"
    echo -e "==========================================${NC}"
    echo ""

    echo "手动检查命令："
    echo "  sudo systemctl status autooverview"
    echo "  sudo journalctl -u autooverview -f"
    echo "  curl http://localhost:8006/api/health"
    echo ""

    exit 1
fi

