# 多前端单后端架构配置指南

## 架构概述

实现两个前端共享一个后端的架构：

- **中文前端**：https://autooverview.snappicker.com（上海服务器）
- **英文前端**：https://autooverview.plainkit.top（纽约服务器）  
- **统一后端**：https://autooverview.snappicker.com（上海服务器）

## 优势

1. **性能优化**：利用上海服务器的强大性能处理所有业务逻辑
2. **统一数据**：用户数据、订单、支付记录都在同一个数据库
3. **简化部署**：纽约服务器只需部署静态前端，无需部署后端服务
4. **维护简单**：只需维护一套后端代码和数据库

## 配置步骤

### 1. 前端配置（纽约服务器）

#### 1.1 更新 API 基础地址

在 `frontend/src/api.ts` 中添加环境检测：

```typescript
const API_BASE = process.env.NODE_ENV === 'production' 
  ? 'https://autooverview.snappicker.com/api'  // 生产环境指向上海后端
  : '/api'  // 开发环境使用本地代理
```

#### 1.2 更新 Vite 配置

`frontend/vite.config.ts` 已经配置了开发环境的代理：

```typescript
server: {
  port: 3006,
  proxy: {
    '/api': {
      target: 'http://localhost:8006',
      changeOrigin: true
    }
  }
}
```

### 2. 后端配置（上海服务器）

#### 2.1 CORS 配置

后端已经配置了允许所有来源的 CORS：

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 2.2 环境变量配置

需要更新 `backend/.env` 中的 FRONTEND_URL，根据请求来源动态处理：

```bash
# 支付回调 URL（可以配置为主域名）
FRONTEND_URL=https://autooverview.snappicker.com

# 或者可以设置为通配符，让后端根据请求头动态返回
FRONTEND_URL=https://autooverview.snappicker.com
```

### 3. 支付回调处理

由于有两个前端域名，需要修改支付回调逻辑：

#### 3.1 支付宝回调（中文版）

支付宝回调需要返回到用户发起支付的页面。可以通过以下方式处理：

```python
# 在支付回调中获取原始请求的 Referer
def get_return_url(referer: str) -> str:
    """根据 referer 返回对应的前端 URL"""
    if 'plainkit.top' in referer:
        return 'https://autooverview.plainkit.top/profile'
    return 'https://autooverview.snappicker.com/profile'
```

#### 3.2 Paddle 回调（英文版）

Paddle 支付成功后的返回 URL 配置：

```python
# 在 paddle_subscription.py 中
success_url = f"{config['frontend_url']}/profile?payment=success"
```

可以配置为支持两个域名：

```python
# 根据用户邮箱或其他标识判断返回哪个域名
# 或者统一返回到主域名，让前端自己处理
```

### 4. 构建和部署

#### 4.1 纽约前端构建

```bash
cd frontend
npm run build
```

#### 4.2 部署到纽约服务器

将 `frontend/dist` 目录的内容部署到纽约服务器的 Web 服务器：

```bash
# 使用 rsync 或 scp 部署
rsync -avz dist/ user@plainkit.top:/var/www/html/
```

#### 4.3 配置纽约服务器的 Nginx

```nginx
server {
    listen 80;
    server_name autooverview.plainkit.top;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name autooverview.plainkit.top;
    
    # SSL 证书配置
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # 前端静态文件
    root /var/www/html;
    index index.html;
    
    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 请求不需要代理，因为前端直接请求上海服务器
    # 但是为了 SEO 和性能，可以添加缓存
}
```

### 5. 验证配置

#### 5.1 测试中文站

```bash
# 访问中文站
curl https://autooverview.snappicker.com

# 测试 API
curl https://autooverview.snappicker.com/api/health
```

#### 5.2 测试英文站

```bash
# 访问英文站
curl https://autooverview.plainkit.top

# 测试 API（应该请求上海服务器）
# 打开浏览器控制台查看网络请求
```

#### 5.3 测试跨域

在英文站（plainkit.top）发起登录请求，检查：
1. 请求是否发送到 snappicker.com
2. CORS 头是否正确
3. 登录是否成功

### 6. 监控和日志

#### 6.1 后端日志

监控来自不同域名的请求：

```python
import logging

logger = logging.getLogger(__name__)

# 在每个请求中记录来源
@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin", "unknown")
    logger.info(f"Request from: {origin}")
    response = await call_next(request)
    return response
```

#### 6.2 分析数据

可以统计不同域名的访问量：

- 中文站访问量：Origin 为 null 或 snappicker.com
- 英文站访问量：Origin 为 plainkit.top

## 注意事项

### 1. SSL 证书

确保两个域名都有有效的 SSL 证书。

### 2. 支付回调

支付回调 URL 需要配置正确：
- 支付宝回调配置为上海服务器
- Paddle webhook 配置为上海服务器

### 3. Session/Cookie

由于跨域，需要注意：
- 使用 JWT token 而不是 session
- token 存储在 localStorage 中
- 每次请求都在 Authorization 头中携带 token

### 4. 静态资源

可以考虑使用 CDN 加速静态资源：
- 图片、CSS、JS 文件上传到 CDN
- 减少 API 请求的延迟

## 故障排查

### 问题 1：CORS 错误

**症状**：浏览器控制台显示 CORS 错误

**解决方案**：
1. 检查后端 CORS 配置是否正确
2. 确认 `allow_origins=["*"]` 或包含具体域名
3. 检查前端是否正确发送 Origin 头

### 问题 2：支付回调失败

**症状**：支付成功后没有正确返回

**解决方案**：
1. 检查 FRONTEND_URL 配置
2. 查看后端日志中的回调 URL
3. 确认支付平台配置的回调地址正确

### 问题 3：性能问题

**症状**：纽约前端访问上海后端延迟高

**解决方案**：
1. 使用 CDN 缓存静态资源
2. 启用 gzip 压缩
3. 考虑在上海服务器前加 CDN
4. 优化 API 响应时间

## 性能优化建议

### 1. 前端优化

- 代码分割和懒加载
- 图片优化和 WebP 格式
- 启用浏览器缓存

### 2. 网络优化

- 使用 HTTP/2
- 启用 Brotli 压缩
- 预加载关键资源

### 3. 后端优化

- 数据库查询优化
- 添加 Redis 缓存
- 使用异步处理

## 总结

这个架构方案实现了：
- ✅ 两个前端共享一个后端
- ✅ 统一的数据管理和业务逻辑
- ✅ 简化了部署和维护
- ✅ 充分利用上海服务器的性能
- ✅ 纽约服务器只需要处理静态文件

通过这种架构，可以降低运营成本，提高开发效率，同时保持良好的用户体验。
