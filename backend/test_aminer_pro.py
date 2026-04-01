"""
测试 AMiner Pro 接口
验证新的关键词搜索功能
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from services.aminer_search import AMinerSearchService

async def test_aminer_pro():
    """测试 AMiner Pro 接口"""
    print("=" * 80)
    print("测试 AMiner Pro 接口")
    print("=" * 80)

    API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

    async with AMinerSearchService(api_token=API_TOKEN) as service:
        # 测试1: 单个关键词
        print("\n" + "=" * 60)
        print("测试1: 单个关键词搜索")
        print("=" * 60)

        papers1 = await service.search_papers(
            keywords=['投资者情绪'],
            year_start=2016,
            year_end=2026,
            max_results=20
        )

        print(f"\n找到 {len(papers1)} 篇论文:")
        for i, paper in enumerate(papers1[:5], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            print(f"  {i}. [{year}] {title[:60]}... (被引: {cited})")

        await asyncio.sleep(2)

        # 测试2: 组合关键词
        print("\n" + "=" * 60)
        print("测试2: 组合关键词搜索")
        print("=" * 60)

        papers2 = await service.search_papers(
            keywords=['投资者情绪', '分析师预测'],
            year_start=2016,
            year_end=2026,
            max_results=20
        )

        print(f"\n找到 {len(papers2)} 篇论文:")
        for i, paper in enumerate(papers2[:5], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            print(f"  {i}. [{year}] {title[:60]}... (被引: {cited})")

        await asyncio.sleep(2)

        # 测试3: 直接使用 Pro 接口
        print("\n" + "=" * 60)
        print("测试3: 直接使用 Pro 接口")
        print("=" * 60)

        result = await service.search_by_keyword(
            keyword='媒体关注度 投资者情绪',
            page=0,
            size=10
        )

        print(f"\n总数: {result.get('total', 0)}")
        print(f"本页返回: {len(result.get('items', []))} 篇")

        for i, item in enumerate(result.get('items', [])[:5], 1):
            title = item.get('title', '') or item.get('title_zh', '')
            print(f"  {i}. {title[:60]}...")

        await asyncio.sleep(2)

        # 测试4: 测试您的题目关键词
        print("\n" + "=" * 60)
        print("测试4: 题目关键词搜索")
        print("=" * 60)

        test_keywords = [
            ['媒体关注度'],
            ['投资者情绪'],
            ['分析师盈利预测准确性'],
            ['媒体关注度', '投资者情绪'],
            ['投资者情绪', '分析师预测'],
            ['行为金融学'],
        ]

        all_papers = []
        seen_ids = set()

        for keywords in test_keywords:
            papers = await service.search_papers(
                keywords=keywords,
                year_start=2016,
                year_end=2026,
                max_results=15
            )

            # 去重
            new_papers = []
            for paper in papers:
                pid = paper.get('id')
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    new_papers.append(paper)

            kw_str = ' '.join(keywords)
            print(f"\n{kw_str}: {len(papers)} 篇 (新增 {len(new_papers)} 篇)")

            for i, paper in enumerate(new_papers[:3], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                cited = paper.get('cited_by_count', 0)
                print(f"  {i}. [{year}] {title[:55]}... (被引: {cited})")

            all_papers.extend(new_papers)
            await asyncio.sleep(1.5)

        # 统计
        print("\n" + "=" * 60)
        print("汇总统计")
        print("=" * 60)
        print(f"总计: {len(all_papers)} 篇不重复论文")

        # 按被引量排序
        all_papers.sort(key=lambda x: x.get('cited_by_count', 0), reverse=True)

        print("\nTop 10 高被引论文:")
        for i, paper in enumerate(all_papers[:10], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            print(f"  {i}. [{year}] {title[:70]}... (被引: {cited})")


if __name__ == "__main__":
    asyncio.run(test_aminer_pro())
