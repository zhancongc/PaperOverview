"""
测试文献质量过滤功能
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# 设置环境变量
os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.scholarflux_wrapper import ScholarFlux
from services.paper_quality_filter import PaperQualityFilter


async def test_quality_filter():
    """测试质量过滤功能"""
    print("=" * 80)
    print("测试文献质量过滤")
    print("=" * 80)

    # 测试数据
    test_papers = [
        {
            'title': '心理所召开2019年度工作会议',
            'year': 2019,
            'authors': ['综合办公室'],
            'journal': 'Institutional Repository of Institute of Psychology',
            'cited_by_count': 0,
            'id': '1'
        },
        {
            'title': '上市公司ESG表现与企业绩效关系研究',
            'year': 2021,
            'authors': ['张三', '李四', '王五'],
            'journal': '管理世界',
            'cited_by_count': 30,
            'id': '2'
        },
        {
            'title': '关于召开2024年学术研讨会的通知',
            'year': 2024,
            'authors': ['编辑部'],
            'journal': '内部资料',
            'cited_by_count': 0,
            'id': '3'
        },
        {
            'title': '投资者情绪与股票市场波动研究',
            'year': 2020,
            'authors': ['赵六', '钱七'],
            'journal': '金融研究',
            'cited_by_count': 15,
            'id': '4'
        },
        {
            'title': '工作简报：2023年工作总结',
            'year': 2023,
            'authors': ['委员会'],
            'journal': '工作简报',
            'cited_by_count': 0,
            'id': '5'
        },
    ]

    # 测试质量过滤器
    print("\n步骤1: 测试质量过滤器")
    print("=" * 60)

    quality_filter = PaperQualityFilter()

    print(f"\n原始文献: {len(test_papers)} 篇")
    for i, paper in enumerate(test_papers, 1):
        title = paper['title']
        is_low, reason = quality_filter.is_low_quality_paper(paper)
        status = "❌ 低质量" if is_low else "✅ 合格"
        reason_str = f" ({reason})" if reason else ""
        print(f"  {i}. {status}{reason_str}")
        print(f"     {title}")

    # 过滤
    filtered = quality_filter.filter_papers(test_papers)

    print(f"\n过滤后: {len(filtered)} 篇")
    for i, paper in enumerate(filtered, 1):
        title = paper['title']
        cited = paper['cited_by_count']
        print(f"  {i}. [{cited}c] {title}")

    # 测试实际搜索
    print("\n" + "=" * 60)
    print("步骤2: 测试实际搜索（中文查询）")
    print("=" * 60)

    flux = ScholarFlux()

    try:
        # 中文查询应该只使用 AMiner
        print("\n查询: 投资者情绪")

        papers = await flux.search(
            query='投资者情绪',
            years_ago=10,
            limit=50,
            lang='zh'  # 明确指定中文
        )

        print(f"\n找到 {len(papers)} 篇高质量文献")

        # 显示前10篇
        print("\nTop 10 文献:")
        for i, paper in enumerate(papers[:10], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            venue = paper.get('journal', 'N/A')[:30]
            print(f"  {i}. [{year}] {cited:3d}c | {title[:50]}...")

        # 测试英文查询
        print("\n" + "=" * 60)
        print("步骤3: 测试实际搜索（英文查询）")
        print("=" * 60)

        print("\n查询: investor sentiment")

        papers_en = await flux.search(
            query='investor sentiment',
            years_ago=10,
            limit=30,
            lang='en'  # 明确指定英文
        )

        print(f"\n找到 {len(papers_en)} 篇高质量文献")

        print("\nTop 10 文献:")
        for i, paper in enumerate(papers_en[:10], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            venue = paper.get('journal', 'N/A')[:30]
            is_en = paper.get('is_english', True)
            lang_mark = "🇬🇧" if is_en else "🇨🇳"
            print(f"  {i}. [{year}] {lang_mark} {cited:3d}c | {title[:45]}...")

    finally:
        await flux.close()

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_quality_filter())
