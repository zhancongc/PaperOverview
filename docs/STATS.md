# 统计功能文档

> 最后更新: 2026-04-11

## 功能概述

AutoOverview 提供完整的用户数据统计功能，包括访问量、注册量、生成数、付费数等核心指标。

---

## 统计类型

### 1. 网站统计（公开）

**API 端点：** `/api/stats/overview`

统计数据：
- 总访问量
- 总注册量
- 今日访问量
- 今日注册量

**API 端点：** `/api/stats/daily?start_date=&end_date=`

获取指定日期范围的每日统计数据。

### 2. 管理员统计（需授权）

**API 端点：** `/api/admin/stats/overview`

完整统计概览：
- **访问统计**：总访问量、今日访问量
- **注册统计**：总注册量、今日注册量
- **生成统计**：总生成数（免费/付费）
- **付费统计**：总订单数、总收入、各套餐分组
- **今日数据**：今日所有指标汇总

**API 端点：** `/api/admin/stats/daily?days=30`

获取每日趋势数据（支持 7/30/90 天）。

---

## DDoS 防护

统计功能采用 Redis 缓存 + 批量写入架构，有效防止 DDoS 攻击：

| 措施 | 说明 |
|------|------|
| **Redis 缓存** | 每个请求只写 Redis，不直接写数据库 |
| **批量写入** | 每 5 分钟同步一次到数据库 |
| **IP 限流** | 每 IP 每分钟最多 100 次请求 |
| **降级机制** | Redis 不可用时自动降级到数据库模式 |

---

## 数据库表

### site_stats（每日统计表）

```sql
CREATE TABLE site_stats (
    id SERIAL PRIMARY KEY,
    stat_date VARCHAR(10) UNIQUE NOT NULL,  -- 统计日期 (YYYY-MM-DD)
    visit_count BIGINT DEFAULT 0,            -- 访问量
    register_count INTEGER DEFAULT 0,        -- 注册用户数
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### visit_logs（访问日志表，可选）

详细访问日志，默认不启用以避免磁盘爆炸。

---

## 环境变量配置

### Redis 配置

```bash
# Redis 配置（用于统计缓存）
AUTH_REDIS_HOST=localhost
AUTH_REDIS_PORT=6379
AUTH_REDIS_DB=0
AUTH_REDIS_PASSWORD=
```

### 白名单配置

```bash
# /david 页面访问白名单
DAVID_WHITELIST=zhancongc@icloud.com
```

---

## /david 数据统计页面

**访问地址：** `https://autooverview.snappicker.com/david`

**权限：** 仅白名单用户可访问

### 展示内容

1. **数据概览**
   - 总访问量（今日新增）
   - 总注册量（今日新增）
   - 总生成数（免费/付费）
   - 总收入（订单数）

2. **今日数据**
   - 访问量、注册量、生成数、付费数、收入

3. **套餐统计**
   - 体验包、标准包、进阶包、单次解锁
   - 各套餐订单数和收入

4. **每日趋势**
   - 可切换 7/30/90 天
   - 访问量、注册量、生成数、付费数、收入趋势图

---

## 自动统计

### 访问量统计

通过 `StatsMiddleware` 中间件自动记录所有 HTTP 请求：

- 排除路径：`/api/health`, `/api/stats`, `/docs`
- 排除静态资源：`.css`, `.js`, `.png`, `.jpg` 等
- 使用 Redis 计数，定期同步到数据库

### 注册量统计

用户注册时自动增加注册量：

- 密码注册：`auth_service.register_by_password()`
- 验证码登录（自动注册）：`auth_service.login_by_code()`

---

## API 使用示例

### 获取统计概览

```bash
curl https://autooverview.snappicker.com/api/stats/overview
```

响应：
```json
{
  "success": true,
  "data": {
    "total_visits": 12345,
    "total_registers": 123,
    "today_visits": 100,
    "today_registers": 5
  }
}
```

### 获取管理员统计

```bash
curl -H "Authorization: Bearer <token>" \
  https://autooverview.snappicker.com/api/admin/stats/overview
```

响应：
```json
{
  "success": true,
  "data": {
    "visits": { "total": 12345, "today": 100 },
    "registers": { "total": 123, "today": 5 },
    "generations": { "total": 200, "free": 150, "paid": 50 },
    "payments": {
      "total_orders": 50,
      "total_revenue": 5000.00,
      "by_plan": { ... }
    }
  }
}
```

---

## 开发说明

### 添加新的统计指标

1. 在 `AdminStatsService` 中添加统计方法
2. 在 `admin_stats.py` 路由中添加 API 端点
3. 在 `DavidPage.tsx` 中添加展示组件

### 调试统计功能

```bash
# 查看统计日志
tail -f /var/log/paperoverview/backend.log | grep Stats

# 查看 Redis 统计数据
redis-cli
> KEYS stats:*
> GET stats:visits:2026-04-11
```

---

## 故障排查

### 统计数据不准确

1. 检查 Redis 是否正常运行
2. 检查批量写入任务是否启动
3. 查看数据库 `site_stats` 表数据

### /david 页面无法访问

1. 检查用户是否在 `DAVID_WHITELIST` 中
2. 检查用户是否已登录
3. 查看浏览器控制台错误信息
