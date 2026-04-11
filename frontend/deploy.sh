#!/bin/bash

# AutoOverview 前端部署脚本
# 用于将前端部署到不同的服务器

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AutoOverview 前端部署脚本 ===${NC}"
echo ""

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}用法: ./deploy.sh [环境]${NC}"
    echo ""
    echo "可选环境："
    echo "  shanghai    - 部署到上海服务器（中文站）"
    echo "  newyork     - 部署到纽约服务器（英文站）"
    echo "  local       - 本地构建测试"
    echo ""
    exit 1
fi

ENVIRONMENT=$1

echo -e "${GREEN}步骤 1: 安装依赖${NC}"
npm install

echo -e "${GREEN}步骤 2: 构建前端${NC}"
npm run build

echo -e "${GREEN}步骤 3: 部署到 ${ENVIRONMENT}${NC}"

case $ENVIRONMENT in
    shanghai)
        echo "部署到上海服务器..."
        # 这里添加实际的部署命令
        # 例如: rsync -avz dist/ user@snappicker.com:/var/www/html/
        echo -e "${YELLOW}请配置实际的部署命令${NC}"
        ;;

    newyork)
        echo "部署到纽约服务器..."
        # 这里添加实际的部署命令
        # 例如: rsync -avz dist/ user@plainkit.top:/var/www/html/
        echo -e "${YELLOW}请配置实际的部署命令${NC}"
        ;;

    local)
        echo "本地构建完成，不部署"
        echo "构建产物在 dist/ 目录"
        ;;

    *)
        echo -e "${RED}错误: 未知的环境 '${ENVIRONMENT}'${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}部署完成！${NC}"
echo ""
echo "验证部署："
echo "1. 检查网站是否可以访问"
echo "2. 打开浏览器控制台，检查 API 请求是否正常"
echo "3. 测试登录功能"
echo "4. 测试支付流程"
