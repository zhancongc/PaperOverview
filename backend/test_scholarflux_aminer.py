"""
测试 ScholarFlux 与 AMiner 集成
"""
import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, 'services')
sys.path.insert(0, '.')

from services.scholarflux_wrapper import ScholarFlux


async def test_chinese_search():
    """测试中文文献搜索"""
    # 设置 AMiner Token
    new_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4NjEzNzQ0ODgsInRpbWVzdGFtcCI6MTc3NDk3NDQ4OSwidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.2wBc5EhnXeaYqioYWH4orOkCSw_-duAMudVYEhwTWlg"
    os.environ['AMINER_API_TOKEN'] = new_token

    print("=" * 80)
    print("测试 ScholarFlux 中文文献搜索（使用新 Token）")
    print("=" * 80)

    # 检查环境变量
    if not os.getenv('AMINER_API_TOKEN'):
        print("\n⚠️  未设置 AMINER_API_TOKEN 环境变量")
        print("中文文献搜索需要 AMiner API Token")
        print("\n获取方式:")
        print("1. 访问 https://www.aminer.cn/")
        print("2. 注册并获取 API Token")
        print("3. 设置环境变量: export AMINER_API_TOKEN='your_token_here'")
        print("\n将使用英文文献搜索进行测试...")
    else:
        print("\n✓ AMiner API Token 已配置")

    print()

    # 初始化 ScholarFlux
    flux = ScholarFlux()

    # 显示数据源状态
    status = flux.get_status()
    print("\n数据源状态:")
    for name, info in status.items():
        status_str = "✓" if info['available'] else "✗"
        print(f"  {status_str} {name}: {info['rate_limit']} req/s")

    # 测试1: 中文查询
    print("\n" + "=" * 60)
    print("测试1: 中文关键词搜索")
    print("=" * 60)

    chinese_papers = await flux.search(
        query="投资者情绪 分析师预测",
        years_ago=5,
        limit=20
    )

    print(f"\n找到 {len(chinese_papers)} 篇中文文献:")
    for i, paper in enumerate(chinese_papers[:3], 1):
        title = paper.get('title', 'N/A')
        year = paper.get('year', 'N/A')
        source = paper.get('source', 'N/A')
        print(f"\n{i}. [{year}] {title}")
        print(f"   来源: {source}")

    # 测试2: 英文查询
    print("\n" + "=" * 60)
    print("测试2: 英文关键词搜索")
    print("=" * 60)

    english_papers = await flux.search(
        query="machine learning deep learning",
        years_ago=5,
        limit=20
    )

    print(f"\n找到 {len(english_papers)} 篇英文文献:")
    for i, paper in enumerate(english_papers[:3], 1):
        title = paper.get('title', 'N/A')
        year = paper.get('year', 'N/A')
        source = paper.get('source', 'N/A')
        print(f"\n{i}. [{year}] {title}")
        print(f"   来源: {source}")

    # 统计
    all_papers = chinese_papers + english_papers
    seen = set()
    unique = []
    for p in all_papers:
        t = p.get('title', '')
        if t and t not in seen:
            seen.add(t)
            unique.append(p)

    # 按数据源统计
    by_source = {}
    for p in all_papers:
        s = p.get('source', 'unknown')
        by_source[s] = by_source.get(s, 0) + 1

    print("\n" + "=" * 80)
    print(f"总计: {len(unique)} 篇不重复文献")
    print(f"按数据源分布: {by_source}")
    print("=" * 80)

    await flux.close()


if __name__ == "__main__":
    asyncio.run(test_chinese_search())
