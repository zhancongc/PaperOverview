# 引用序号检查器使用说明

## 功能

检查文献综述正文中的引用序号是否按顺序出现，**不使用大模型**，纯正则表达式实现。

## 检测项目

1. **顺序错误**：序号是否按递增顺序出现（如 [1][3][2] 会被标记）
2. **缺失序号**：是否有跳过的序号（如 [1][2][4] 会提示缺失 [3]）
3. **重复序号**：序号被多次使用的情况
4. **格式支持**：支持 `[1]`, `(1)`, `（1）` 等多种格式

## 使用方法

### 1. API 接口

```bash
curl -X POST http://localhost:8000/api/check-citation-order \
  -H "Content-Type: application/json" \
  -d '{"text": "这是测试[1]，然后是[2]"}'
```

响应示例：
```json
{
  "success": true,
  "data": {
    "valid": true,
    "message": "✓ 引用序号顺序正确，共 2 个引用，最大序号 2",
    "total_citations": 2,
    "unique_numbers": [1, 2],
    "missing_numbers": [],
    "duplicate_numbers": [],
    "out_of_order": [],
    "issues": []
  }
}
```

### 2. 命令行工具

```bash
# 直接检查文本
python3 check_citation_order.py "这是测试[1]，然后是[2]"

# 检查文件
python3 check_citation_order.py review.txt
```

### 3. Python 代码

```python
from services.citation_order_checker import CitationOrderChecker

checker = CitationOrderChecker()
result = checker.check_order("你的文献综述内容")

if result['valid']:
    print("✓ 引用序号正确")
else:
    print("✗ 发现问题:")
    for issue in result['issues']:
        print(f"  - {issue['message']}")
```

## 检测规则

### 正确的引用顺序

- ✓ `[1][2][3][4]` - 连续递增
- ✓ `[1][2][2][3]` - 允许相邻重复引用
- ✓ `[1][1][2][2]` - 允许连续重复引用

### 错误的引用顺序

- ✗ `[1][3][2]` - 序号倒退
- ✗ `[1][4][2]` - 跳过序号后倒退
- ✗ `[2][1]` - 开头就倒退

## 输出说明

| 字段 | 说明 |
|------|------|
| `valid` | 是否有效（true=无顺序错误） |
| `total_citations` | 总引用次数 |
| `unique_numbers` | 唯一序号列表 |
| `missing_numbers` | 缺失的序号（如 [1][3] 缺失 [2]） |
| `duplicate_numbers` | 重复使用的序号 |
| `out_of_order` | 顺序错误的引用详情 |
| `issues` | 问题汇总列表 |

## 注意事项

1. 同一篇文献多次引用时，序号相同是正常的
2. 序号倒退会被标记为错误（如 [1][3][2]）
3. 缺失序号会被警告（如 [1][3] 缺失 [2]）
4. 检查器不验证序号是否超出参考文献列表范围
