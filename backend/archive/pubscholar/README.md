# PubScholar 文献搜索服务 - 归档

## 归档原因

经过多次测试，PubScholar 的搜索服务存在以下问题：

1. **API 限制**: 直接调用 API 返回 403 错误："第三方应用独立请求时，无此操作权限"
2. **频率限制**: 即使在浏览器内发起请求，也会遇到 "Exceeding the access frequency limit"
3. **页面结构变化**: 页面抓取方法不稳定，难以可靠地获取搜索结果

## 文件列表

| 文件 | 说明 |
|------|------|
| `pubscholar_search.py` | 原始搜索服务 |
| `pubscholar_browser.py` | 基于 Playwright 的浏览器服务 |
| `pubscholar_search_v2.py` | 页面抓取服务 v2 |
| `pubscholar_search_v3.py` | 页面抓取服务 v3 |
| `pubscholar_advanced.py` | 高级筛选服务 |
| `pubscholar_professional.py` | 专业检索服务 |
| `pubscholar_api.py` | 直接 API 调用服务 |
| `pubscholar_api_v2.py` | API 服务 v2 |
| `pubscholar_api_v3.py` | API 服务 v3（浏览器内） |
| `pubscholar_request.py` | HTTP 请求服务 |
| `pubscholar_browser_request.py` | 浏览器内 XMLHttpRequest |
| `pubscholar_page_search.py` | 页面搜索服务 |
| `pubscholar_page_simple.py` | 简化页面搜索 |
| `pubscholar_stable.py` | 稳定版服务 |

## 测试结论

- ✅ 可以打开高级检索弹窗
- ✅ 可以切换到专业检索 tab
- ✅ 可以输入检索式
- ✅ 可以点击检索按钮
- ✅ API 返回 200 状态码
- ❌ 但响应内容为错误："Exceeding the access frequency limit"
- ❌ 页面抓取结果不稳定

## 替代方案

建议使用以下服务获取中文文献：

1. **Semantic Scholar** - 英文文献（已集成）
2. **手动补充** - 从 CNKI 等数据库手动搜索中文文献
3. **其他 API** - 寻找更稳定的中文文献 API

## 归档日期

2026-03-31
