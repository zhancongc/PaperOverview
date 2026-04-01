"""
扩展搜索：获取更多中文文献
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from services.aminer_search import AMinerSearchService

async def test_extended_search():
    """扩展搜索中文文献"""
    API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

    print("=" * 80)
    print("扩展搜索：媒体关注度 投资者情绪 分析师预测")
    print("=" * 80)

    async with AMinerSearchService(api_token=API_TOKEN) as service:
        # 扩展的关键词搜索
        search_queries = [
            (["投资者情绪"], 50, "投资者情绪 (50篇)"),
            (["分析师", "盈利预测"], 50, "分析师盈利预测 (50篇)"),
            (["媒体", "关注"], 30, "媒体关注 (30篇)"),
            (["行为金融学"], 30, "行为金融学 (30篇)"),
        ]

        all_papers = []
        seen_ids = set()

        for keywords, max_results, desc in search_queries:
            print("\n" + "=" * 60)
            print(f"搜索: {desc}")
            print("=" * 60)

            papers = await service.search_papers(
                keywords=keywords,
                year_start=2016,
                year_end=2026,
                max_results=max_results
            )

            # 去重
            new_papers = []
            for paper in papers:
                paper_id = paper.get('id')
                if paper_id and paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    new_papers.append(paper)

            print(f"本批找到 {len(papers)} 篇 (新增 {len(new_papers)} 篇)")

            # 显示部分结果
            for i, paper in enumerate(new_papers[:8], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                venue = paper.get('journal', 'N/A')
                cited = paper.get('cited_by_count', 0)

                print(f"  {i}. [{year}] {title[:60]}..." if len(title) > 60 else f"  {i}. [{year}] {title}")
                print(f"     被引: {cited} | {venue}")

            all_papers.extend(new_papers)

        # 按被引量排序并显示 top 20
        all_papers.sort(key=lambda x: x.get('cited_by_count', 0), reverse=True)

        print("\n" + "=" * 80)
        print("TOP 20 高被引论文")
        print("=" * 80)

        for i, paper in enumerate(all_papers[:20], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            venue = paper.get('journal', 'N/A')
            cited = paper.get('cited_by_count', 0)
            authors = paper.get('authors', [])[:2]
            author_str = ', '.join(authors) if authors else ''

            print(f"\n{i}. [{year}] {title}")
            if author_str:
                print(f"   作者: {author_str}")
            print(f"   期刊: {venue} | 被引: {cited}")

        print("\n" + "=" * 80)
        print(f"总计: {len(all_papers)} 篇不重复论文")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_extended_search())
