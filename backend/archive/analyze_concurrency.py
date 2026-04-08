"""
分析服务端并发支持情况
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("服务端并发支持分析")
print("=" * 70)

# 1. 检查配置
print("\n1️⃣  配置检查")
print("-" * 70)

config_checks = {
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", "未设置"),
    "AMINER_API_TOKEN": os.getenv("AMINER_API_TOKEN", "未设置"),
    "DB_TYPE": os.getenv("DB_TYPE", "未设置"),
    "DB_HOST": os.getenv("DB_HOST", "未设置"),
    "DB_PORT": os.getenv("DB_PORT", "未设置"),
}

for key, value in config_checks.items():
    status = "✅" if value != "未设置" else "❌"
    print(f"{status} {key}: {'✓ 已配置' if value != '未设置' else '✗ 未配置'}")

# 2. 分析代码架构
print("\n2️⃣  并发架构分析")
print("-" * 70)

concurrency_issues = []

print("✅ 支持并发的部分:")
print("  - 任务提交: 使用 asyncio.create_task() 异步执行")
print("  - 任务存储: 内存字典 (TaskManager._tasks)")
print("  - 数据库: 连接池模式 (QueuePool)")

print("\n⚠️  可能的并发问题:")
print("  1. 任务存储在内存中，服务重启会丢失所有任务")
print("  2. 没有并发数量限制")
print("  3. 数据库连接池可能耗尽")
print("  4. 外部API速率限制可能被触发")

# 3. 检查数据库连接池配置
print("\n3️⃣  数据库连接池配置")
print("-" * 70)

db_type = os.getenv("DB_TYPE", "postgresql").lower()
if db_type == "postgresql":
    pool_size = 10
    max_overflow = 20
    print(f"  连接池大小: {pool_size}")
    print(f"  最大溢出连接: {max_overflow}")
    print(f"  最大并发连接: {pool_size + max_overflow}")
    print(f"  ⚠️  当前配置支持 {pool_size + max_overflow} 个并发数据库连接")
else:
    pool_size = 5
    max_overflow = 10
    print(f"  连接池大小: {pool_size}")
    print(f"  最大溢出连接: {max_overflow}")
    print(f"  最大并发连接: {pool_size + max_overflow}")

# 4. 检查外部API限制
print("\n4️⃣  外部API限制")
print("-" * 70)

api_limits = {
    "AMiner": f"{os.getenv('AMINER_RATE_LIMIT', '1.0')} req/s",
    "OpenAlex": f"{os.getenv('OPENALEX_RATE_LIMIT', '5.0')} req/s",
    "Semantic Scholar": f"{os.getenv('SEMANTIC_SCHOLAR_RATE_LIMIT', '1.0')} req/s",
}

for api, limit in api_limits.items():
    print(f"  {api}: {limit}")

print("\n  ⚠️  多任务并发时可能触发速率限制")

# 5. 建议改进
print("\n5️⃣  并发改进建议")
print("-" * 70)

print("✅ 当前实现:")
print("  - 使用 asyncio.create_task() 支持异步执行")
print("  - 数据库连接池自动管理连接")
print("  - 每个任务独立的数据库会话")

print("\n📋 建议添加:")
print("  1. 并发任务数量限制（信号量或队列）")
print("  2. 任务队列持久化（Redis或数据库）")
print("  3. API速率限制协调器（全局）")
print("  4. 任务重试机制")
print("  5. 资源监控（数据库连接、内存使用）")

# 6. 并发测试建议
print("\n6️⃣  并发测试建议")
print("-" * 70)

print("可以通过以下方式测试并发支持:")
print("  1. 同时提交3-5个综述生成任务")
print("  2. 观察任务是否并行执行（检查日志时间戳）")
print("  3. 检查是否有数据库连接错误")
print("  4. 检查是否有API速率限制错误")
print("  5. 验证所有任务都能正常完成")

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)

