#!/usr/bin/env python3
"""
数据库迁移脚本：初始化套餐价格表

用途：
  - 创建 plans 表（如果不存在）
  - 初始化默认套餐数据（如果表为空）

执行方式：
  python backend/migrations/init_plans.py

注意事项：
  - 此脚本可重复执行，不会重复插入数据
  - 适合在 server-update.sh 中自动执行
"""
import os
import sys

# 添加 backend 目录到 Python 路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import db
from authkit.models.payment import Plan, PaymentBase, init_plans_in_db


def main():
    print("=" * 50)
    print("套餐价格表迁移脚本")
    print("=" * 50)
    print()

    # 连接数据库
    print("[1/3] 连接数据库...")
    db.connect()
    print("✓ 数据库连接成功")
    print()

    # 创建表
    print("[2/3] 创建 plans 表...")
    PaymentBase.metadata.create_all(bind=db.engine)
    print("✓ plans 表已创建（如已存在则跳过）")
    print()

    # 初始化数据
    print("[3/3] 初始化套餐数据...")
    with next(db.get_session()) as session:
        # 检查是否已有数据
        existing_count = session.query(Plan).count()
        if existing_count > 0:
            print(f"✓ 数据库中已有 {existing_count} 条套餐记录，跳过初始化")
            print()
            print("当前套餐列表：")
            plans = session.query(Plan).order_by(Plan.sort_order).all()
            for plan in plans:
                status = "推荐" if plan.recommended else "  "
                print(f"  [{status}] {plan.name} ({plan.type})")
                print(f"      价格: ¥{plan.price}")
                print(f"      额度: {plan.credits} 篇")
                print(f"      状态: {'启用' if plan.is_active else '禁用'}")
                print()
        else:
            init_plans_in_db(session)
            print("✓ 套餐数据初始化完成")
            print()
            print("已初始化的套餐：")
            plans = session.query(Plan).order_by(Plan.sort_order).all()
            for plan in plans:
                status = "推荐" if plan.recommended else "  "
                print(f"  [{status}] {plan.name} ({plan.type})")
                print(f"      价格: ¥{plan.price}")
                print(f"      额度: {plan.credits} 篇")
                print()

    print("=" * 50)
    print("迁移完成！")
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
