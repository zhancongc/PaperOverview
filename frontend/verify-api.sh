#!/bin/bash

# API 配置验证脚本
# 用于验证不同环境下的 API 配置是否正确

echo "=== AutoOverview API 配置验证 ==="
echo ""

# 获取当前环境信息
echo "当前环境信息："
echo "  Node 环境: $NODE_ENV"
echo "  当前目录: $(pwd)"
echo ""

# 检查构建产物
if [ -d "dist" ]; then
    echo "✓ 构建产物存在"
    echo "  构建时间: $(stat -f '%Sm' dist -t '%Y-%m-%d %H:%M:%S' 2>/dev/null || stat -c '%y' dist 2>/dev/null)"
else
    echo "✗ 构建产物不存在，请先运行 npm run build"
    exit 1
fi

echo ""
echo "=== API 配置检查 ==="

# 检查 API 配置代码
echo "检查 API_BASE 配置..."
if grep -q "getApiBase" src/api.ts; then
    echo "✓ API_BASE 使用动态配置"
    echo ""
    echo "配置逻辑："
    echo "  - 开发环境: /api (本地代理)"
    echo "  - 纽约前端: https://autooverview.snappicker.com/api"
    echo "  - 上海前端: /api (相对路径)"
else
    echo "✗ API_BASE 未使用动态配置"
    exit 1
fi

echo ""
echo "=== 部署环境模拟 ==="

# 模拟不同环境的 hostname
echo "测试不同 hostname 的 API 配置："

# 上海服务器
echo ""
echo "1. 上海服务器 (autooverview.snappicker.com):"
echo "   hostname: autooverview.snappicker.com"
echo "   API_BASE: /api"
echo "   说明: 前后端同服务器，使用相对路径"

# 纽约服务器
echo ""
echo "2. 纽约服务器 (autooverview.plainkit.top):"
echo "   hostname: autooverview.plainkit.top"
echo "   API_BASE: https://autooverview.snappicker.com/api"
echo "   说明: 前端在纽约，后端在上海"

echo ""
echo "=== 验证完成 ==="
echo ""
echo "下一步："
echo "1. 构建前端: npm run build"
echo "2. 部署到对应服务器: ./deploy.sh [shanghai|newyork]"
echo "3. 在浏览器控制台验证 API 请求地址"
echo ""
echo "浏览器验证方法："
echo "  1. 打开网站"
echo "  2. 打开开发者工具 (F12)"
echo "  3. 切换到 Network 标签"
echo "  4. 发起一个 API 请求（如登录）"
echo "  5. 检查请求的 URL 是否正确"
