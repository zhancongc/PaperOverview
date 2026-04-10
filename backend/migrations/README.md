# 数据库迁移脚本

此目录包含数据库迁移脚本，用于在生产环境中更新数据库结构。

## 迁移脚本命名规范

使用描述性的文件名，例如：
- `init_plans.py` - 初始化套餐价格表
- `add_user_fields.py` - 添加用户字段
- `create_index_table.py` - 创建索引表

## 迁移脚本要求

每个迁移脚本应该：
1. **可重复执行**：多次运行不会产生错误或重复数据
2. **幂等性**：执行结果与执行次数无关
3. **提供清晰输出**：显示执行进度和结果
4. **包含错误处理**：出错时提供有用的错误信息

## 迁移脚本模板

```python
#!/usr/bin/env python3
"""
数据库迁移脚本：[描述迁移内容]

用途：
  - [具体用途1]
  - [具体用途2]

执行方式：
  python backend/migrations/[script_name].py

注意事项：
  - [重要注意事项]
"""
import os
import sys

# 添加 backend 目录到 Python 路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import db


def main():
    print("=" * 50)
    print("[迁移名称]")
    print("=" * 50)
    print()

    # 连接数据库
    print("[1/2] 连接数据库...")
    db.connect()
    print("✓ 数据库连接成功")
    print()

    # 执行迁移
    print("[2/2] 执行迁移...")
    with next(db.get_session()) as session:
        # 检查是否已迁移
        # ... 检查逻辑 ...

        # 执行迁移
        # ... 迁移逻辑 ...

        print("✓ 迁移完成")
    print()

    print("=" * 50)
    print("迁移成功！")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print()
        print(f"错误：迁移失败 - {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

## 自动执行

迁移脚本会在 `server-update.sh` 部署脚本中自动执行。

手动执行：
```bash
cd backend
python migrations/init_plans.py
```

## 已完成的迁移

- ✅ `init_plans.py` - 初始化套餐价格表
