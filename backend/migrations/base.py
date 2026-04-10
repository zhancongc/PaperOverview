#!/usr/bin/env python3
"""
数据库迁移基类和工具函数

提供迁移脚本的基础设施，包括版本控制、执行记录等。
"""
import os
import sys
from datetime import datetime
from typing import Optional

# 添加 backend 目录到 Python 路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import db
from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.orm import declarative_base

MigrationBase = declarative_base()


class SchemaVersion(MigrationBase):
    """数据库迁移版本表"""
    __tablename__ = "schema_versions"

    version = Column(String(20), primary_key=True, comment="迁移版本号")
    name = Column(String(200), nullable=False, comment="迁移名称")
    applied_at = Column(DateTime, default=datetime.now, comment="执行时间")

    def to_dict(self):
        return {
            "version": self.version,
            "name": self.name,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None
        }


def get_session():
    """获取数据库会话"""
    return next(db.get_session())


def ensure_version_table():
    """确保版本表存在"""
    session = get_session()
    try:
        # 检查表是否存在
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'schema_versions'
            )
        """)).scalar()

        if not result:
            # 创建版本表
            session.execute(text("""
                CREATE TABLE schema_versions (
                    version VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            session.commit()
            print("✓ 创建 schema_versions 表")
        else:
            print("✓ schema_versions 表已存在")
    finally:
        session.close()


def is_applied(version: str) -> bool:
    """检查迁移是否已执行"""
    # 先确保版本表存在
    ensure_version_table()

    session = get_session()
    try:
        result = session.query(SchemaVersion).filter_by(version=version).first()
        return result is not None
    finally:
        session.close()


def record_migration(version: str, name: str):
    """记录已执行的迁移"""
    session = get_session()
    try:
        migration_record = SchemaVersion(version=version, name=name)
        session.add(migration_record)
        session.commit()
        print(f"✓ 记录迁移版本: {version}")
    finally:
        session.close()


def get_applied_migrations():
    """获取已执行的迁移列表"""
    # 先确保版本表存在
    ensure_version_table()

    session = get_session()
    try:
        migrations = session.query(SchemaVersion).order_by(SchemaVersion.applied_at).all()
        return [m.version for m in migrations]
    finally:
        session.close()


def get_pending_migrations(migrations_dir: str):
    """获取待执行的迁移脚本"""
    applied = get_applied_migrations()
    applied_set = set(applied)

    # 扫描迁移目录
    if not os.path.exists(migrations_dir):
        return []

    pending = []
    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            # 提取版本号（文件名格式：XXX_name.py）
            parts = filename.split('_', 1)
            if len(parts) == 2 and parts[0].isdigit():
                version = parts[0]
                if version not in applied_set:
                    pending.append((version, filename))

    # 按版本号排序
    pending.sort(key=lambda x: int(x[0]))
    return pending


class Migration:
    """迁移基类"""

    def __init__(self, version: str, name: str):
        self.version = version
        self.name = name

    def up(self):
        """执行迁移（子类必须实现）"""
        raise NotImplementedError("子类必须实现 up() 方法")

    def down(self):
        """回滚迁移（可选实现）"""
        raise NotImplementedError("此迁移不支持回滚")

    def run(self):
        """运行迁移"""
        print(f"[{self.version}] {self.name}")
        print("-" * 50)

        # 检查是否已执行
        if is_applied(self.version):
            print(f"⊙ 迁移已执行，跳过")
            return

        # 执行迁移
        print("↑ 执行迁移...")
        self.up()

        # 记录版本
        record_migration(self.version, self.name)
        print(f"✓ 迁移完成")


def run_migration(migrations_dir: str, version: Optional[str] = None):
    """
    运行迁移脚本

    Args:
        migrations_dir: 迁移脚本目录
        version: 指定版本号（可选），不指定则执行所有待执行的迁移
    """
    print("=" * 60)
    print("数据库迁移系统")
    print("=" * 60)
    print()

    # 确保版本表存在
    print("[1/4] 检查版本表...")
    ensure_version_table()
    print()

    # 获取待执行的迁移
    if version:
        # 执行指定版本的迁移
        filename = f"{version}_*.py"
        files = list(os.listdir(migrations_dir))
        matching = [f for f in files if f.startswith(version + '_')]
        if not matching:
            print(f"❌ 未找到版本 {version} 的迁移脚本")
            return False

        filename = matching[0]
        print(f"[2/4] 执行迁移: {filename}")
    else:
        # 执行所有待执行的迁移
        print("[2/4] 检查待执行的迁移...")
        pending = get_pending_migrations(migrations_dir)

        if not pending:
            print("✓ 所有迁移都已执行，无需迁移")
            return True

        print(f"发现 {len(pending)} 个待执行的迁移:")
        for v, f in pending:
            print(f"  - {v}: {f}")
        print()

        version, filename = pending[0]
        print(f"[3/4] 执行迁移: {filename}")

    print()

    # 执行迁移脚本
    script_path = os.path.join(migrations_dir, filename)
    try:
        # 动态导入迁移模块
        import importlib.util
        import sys

        # 将 migrations 目录添加到 sys.path
        if migrations_dir not in sys.path:
            sys.path.insert(0, migrations_dir)

        spec = importlib.util.spec_from_file_location("migration_module", script_path)
        migration_module = importlib.util.module_from_spec(spec)

        # 设置模块的 __file__ 属性
        migration_module.__file__ = script_path

        # 在当前上下文中执行模块
        spec.loader.exec_module(migration_module)

        # 查找 migration 对象并运行
        if hasattr(migration_module, 'migration'):
            migration_module.migration.run()
        elif hasattr(migration_module, 'main'):
            # 兼容旧式迁移脚本
            print("⚠ 警告: 使用旧式迁移脚本，建议迁移到新格式")
            migration_module.main()
        else:
            print(f"❌ 迁移脚本格式错误: {filename}")
            return False

        print()
        print("=" * 60)
        print("✓ 迁移成功完成")
        print("=" * 60)
        return True

    except Exception as e:
        print()
        print(f"❌ 迁移执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def show_status(migrations_dir: str):
    """显示迁移状态"""
    print("=" * 60)
    print("迁移状态")
    print("=" * 60)
    print()

    # 获取所有迁移文件
    all_migrations = []
    if os.path.exists(migrations_dir):
        for filename in os.listdir(migrations_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                # 提取版本号（文件名格式：XXX_name.py）
                parts = filename.split('_', 1)
                if len(parts) == 2 and parts[0].isdigit():
                    version = parts[0]
                    name = parts[1].replace('.py', '').replace('_', ' ')
                    all_migrations.append((version, name, filename))

    all_migrations.sort(key=lambda x: int(x[0]))

    # 获取已执行的迁移
    applied = get_applied_migrations()
    applied_set = set(applied)

    print(f"总迁移数: {len(all_migrations)}")
    print(f"已执行: {len(applied)}")
    print(f"待执行: {len(all_migrations) - len(applied)}")
    print()

    if all_migrations:
        print("迁移列表:")
        print("-" * 60)
        for version, name, filename in all_migrations:
            status = "✓" if version in applied_set else "⊙"
            print(f"{status} {version} - {name}")
        print()
    else:
        print("未找到迁移脚本")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("action", choices=["migrate", "status"], help="操作类型")
    parser.add_argument("--version", help="指定迁移版本号")
    parser.add_argument("--dir", default="migrations", help="迁移脚本目录")

    args = parser.parse_args()

    migrations_dir = args.dir
    if not os.path.isabs(migrations_dir):
        # 相对路径转换为绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        migrations_dir = os.path.join(script_dir, migrations_dir)
        # 如果拼接后的目录不存在，尝试直接使用相对路径
        if not os.path.exists(migrations_dir):
            migrations_dir = args.dir
            if not os.path.isabs(migrations_dir):
                migrations_dir = os.path.abspath(args.dir)

    if args.action == "migrate":
        success = run_migration(migrations_dir, args.version)
        sys.exit(0 if success else 1)
    elif args.action == "status":
        show_status(migrations_dir)
