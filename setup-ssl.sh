#!/bin/bash
# =====================================================
# AutoOverview - SSL 证书配置脚本
# =====================================================
# 功能：使用 Let's Encrypt 为 autooverview.snappicker.com 申请 SSL 证书
# =====================================================

set -e

DOMAIN="autooverview.snappicker.com"
NGINX_CONF="/etc/nginx/sites-available/autooverview"
CERTBOT_EMAIL="service@snappicker.com"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 root
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 用户运行此脚本"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AutoOverview SSL 证书配置${NC}"
echo -e "${BLUE}域名: ${DOMAIN}${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 1. 检查 nginx 配置是否存在
if [ ! -f "$NGINX_CONF" ]; then
    log_error "Nginx 配置不存在: $NGINX_CONF"
    log_error "请先运行 server-install.sh"
    exit 1
fi

# 2. 安装 certbot
log_info "检查 certbot..."
if ! command -v certbot &> /dev/null; then
    log_info "安装 certbot..."
    apt-get update -y
    apt-get install -y certbot python3-certbot-nginx
    log_success "certbot 安装完成"
else
    log_success "certbot 已安装: $(certbot --version 2>&1)"
fi

# 3. 创建 certbot challenge 目录
mkdir -p /var/www/certbot
log_success "certbot challenge 目录就绪"

# 4. 确保 nginx 配置中的域名正确
if grep -q "server_name ${DOMAIN};" "$NGINX_CONF"; then
    log_success "nginx 配置域名正确: ${DOMAIN}"
else
    log_error "nginx 配置中未找到域名 ${DOMAIN}"
    log_error "请检查 ${NGINX_CONF}"
    exit 1
fi

# 5. 测试 nginx 配置
log_info "测试 nginx 配置..."
if nginx -t; then
    log_success "nginx 配置语法正确"
else
    log_error "nginx 配置有误，请先修复"
    exit 1
fi

# 6. 确保 nginx 正在运行
systemctl reload nginx
log_success "nginx 已重载"

# 7. 申请证书
echo ""
log_info "开始申请 SSL 证书..."
echo ""

CERTBOT_CMD="certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos"
if [ -n "$CERTBOT_EMAIL" ]; then
    CERTBOT_CMD="$CERTBOT_CMD --email $CERTBOT_EMAIL"
fi

if eval "$CERTBOT_CMD"; then
    log_success "SSL 证书申请成功!"
else
    log_error "SSL 证书申请失败"
    log_error "请确认："
    log_error "  1. 域名 ${DOMAIN} 已解析到本服务器 IP"
    log_error "  2. 80 端口可从外网访问"
    exit 1
fi

# 8. 验证自动续期
echo ""
log_info "验证证书自动续期..."
if certbot renew --dry-run &> /dev/null; then
    log_success "证书自动续期配置正常"
else
    log_warning "自动续期验证未通过，可手动测试: certbot renew --dry-run"
fi

# 9. 重载 nginx
systemctl reload nginx
log_success "nginx 已重载（启用 HTTPS）"

# 10. 显示证书信息
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SSL 配置完成！${NC}"
echo -e "${GREEN}========================================${NC}\n"

certbot certificates 2>/dev/null | head -10

echo ""
echo -e "访问地址: ${YELLOW}https://${DOMAIN}${NC}"
echo -e ""
echo -e "证书管理命令："
echo -e "  ${YELLOW}查看证书:${NC}   certbot certificates"
echo -e "  ${YELLOW}手动续期:${NC}   certbot renew"
echo -e "  ${YELLOW}撤销证书:${NC}   certbot revoke --cert-name ${DOMAIN}"
echo ""
echo -e "证书会在到期前自动续期（certbot timer）"
echo -e "检查 timer: ${YELLOW}systemctl list-timers | grep certbot${NC}"
