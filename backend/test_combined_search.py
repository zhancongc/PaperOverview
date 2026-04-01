"""
测试 AMiner Pro 组合搜索功能（title + keyword）
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.aminer_search import AMinerSearchService


async def test_combined_search():
    """测试组合搜索功能"""
    print("=" * 80)
    print("测试 AMiner Pro 组合搜索（title + keyword）")
    print("=" * 80)

    async with AMinerSearchService(api_token=os.environ['AMINER_API_TOKEN']) as service:
        # 测试1: 单独使用 keyword
        print("\n测试1: 仅使用 keyword='QFD'")
        print("-" * 60)

        result1 = await service.search_by_keyword(
            keyword='QFD',
            page=0,
            size=10
        )

        print(f"结果数: {result1.get('total', 0)}")
        if result1.get('items'):
            print("\n前3篇:")
            for i, item in enumerate(result1.get('items', [])[:3], 1):
                title = item.get('title', 'N/A')[:60]
                venue = item.get('venue_name', 'N/A')[:40]
                print(f"  {i}. {title}")
                print(f"     期刊: {venue}")

        await asyncio.sleep(2)

        # 测试2: 单独使用 title
        print("\n测试2: 仅使用 title='铝合金轮毂'")
        print("-" * 60)

        result2 = await service.search_by_keyword(
            keyword='铝合金轮毂',
            page=0,
            size=10
        )

        print(f"结果数: {result2.get('total', 0)}")
        if result2.get('items'):
            print("\n前3篇:")
            for i, item in enumerate(result2.get('items', [])[:3], 1):
                title = item.get('title', 'N/A')[:60]
                venue = item.get('venue_name', 'N/A')[:40]
                print(f"  {i}. {title}")
                print(f"     期刊: {venue}")

        await asyncio.sleep(2)

        # 测试3: 组合使用 title + keyword
        print("\n测试3: 组合搜索 title='铝合金轮毂' + keyword='QFD'")
        print("-" * 60)

        result3 = await service.search_by_keyword_and_title(
            keyword='QFD',
            title='铝合金轮毂',
            page=0,
            size=10
        )

        print(f"结果数: {result3.get('total', 0)}")
        if result3.get('items'):
            print("\n前3篇:")
            for i, item in enumerate(result3.get('items', [])[:3], 1):
                title = item.get('title', 'N/A')[:60]
                venue = item.get('venue_name', 'N/A')[:40]
                year = item.get('year', 'N/A')
                print(f"  {i}. [{year}] {title}")
                print(f"     期刊: {venue}")

        await asyncio.sleep(2)

        # 测试4: 使用 search_papers 方法（两个关键词）
        print("\n测试4: 使用 search_papers 方法（两个关键词）")
        print("-" * 60)

        papers = await service.search_papers(
            keywords=['铝合金轮毂', 'QFD'],
            year_start=2016,
            year_end=2026,
            max_results=20
        )

        print(f"结果数: {len(papers)}")

        # 显示每篇论文的年份以便调试
        if papers:
            print(f"所有 {len(papers)} 篇论文:")
            for i, paper in enumerate(papers, 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                cited = paper.get('cited_by_count', 0)
                venue = paper.get('journal', 'N/A')[:40]
                print(f"  {i}. [{year}] {cited:3d}c | {title[:55]}...")
                print(f"     期刊: {venue}")
        else:
            print("未找到论文")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_combined_search())
