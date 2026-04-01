"""
测试 AMiner 中文文献搜索
"""
import asyncio
import os
from services.aminer_search import AMinerSearchService

async def test_chinese_search():
    """测试中文文献搜索"""
    # 新 Token
    API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

    print("=" * 80)
    print("测试 AMiner 中文文献搜索")
    print("=" * 80)

    async with AMinerSearchService(api_token=API_TOKEN) as service:
        # 测试1: 验证 Token
        print("\n正在验证 Token...")
        if not await service.verify_token():
            print("✗ Token 无效")
            return
        print("✓ Token 有效\n")

        # 测试2: 搜索中文文献
        print("=" * 60)
        print("测试: 投资者情绪 + 分析师预测")
        print("=" * 60)

        papers = await service.search_papers(
            keywords=['投资者情绪', '分析师预测'],
            year_start=2016,  # 扩大年份范围
            year_end=2026,
            max_results=30
        )

        print(f"\n找到 {len(papers)} 篇论文:")
        for i, paper in enumerate(papers[:10], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            authors = paper.get('authors', [])[:3]
            author_str = ', '.join(authors) if authors else 'N/A'
            venue = paper.get('journal', 'N/A')
            cited = paper.get('cited_by_count', 0)

            print(f"\n{i}. [{year}] {title}")
            if author_str != 'N/A':
                print(f"   作者: {author_str}")
            if venue != 'N/A':
                print(f"   期刊: {venue}")
            print(f"   被引: {cited}")

        # 统计
        chinese_count = len([p for p in papers if not p['is_english']])
        english_count = len([p for p in papers if p['is_english']])

        print("\n" + "=" * 80)
        print(f"总计: {len(papers)} 篇 (中文: {chinese_count}, 英文: {english_count})")
        print("=" * 80)

        # 测试3: 更多中文关键词
        print("\n" + "=" * 60)
        print("测试: 大数据 + 并行计算")
        print("=" * 60)

        await asyncio.sleep(2)  # 避免请求过快

        papers2 = await service.search_papers(
            keywords=['大数据', '并行计算'],
            year_start=2020,
            year_end=2024,
            max_results=20
        )

        print(f"\n找到 {len(papers2)} 篇论文:")
        for i, paper in enumerate(papers2[:5], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            print(f"{i}. [{year}] {title}")


if __name__ == "__main__":
    asyncio.run(test_chinese_search())
