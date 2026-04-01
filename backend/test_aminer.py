"""
测试 AMiner API
直接使用提供的 Token 进行测试
"""
import asyncio
import sys
sys.path.insert(0, 'services')

from aminer_search import AMinerSearchService


async def test_with_token():
    """使用提供的 Token 测试"""
    # 使用用户提供的 Token
    API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4NjEzNzQ0ODgsInRpbWVzdGFtcCI6MTc3NDk3NDQ4OSwidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.2wBc5EhnXeaYqioYWH4orOkCSw_-duAMudVYEhwTWlg"

    print("=" * 80)
    print("测试 AMiner 中文文献搜索")
    print("=" * 80)

    async with AMinerSearchService(api_token=API_TOKEN) as service:
        # 验证 Token
        print("\n正在验证 Token...")
        if not await service.verify_token():
            print("\n✗ Token 无效或已过期")
            print("请访问 https://www.aminer.cn/ 获取新的 Token")
            return
        print()

        # 测试中文文献搜索
        print("=" * 60)
        print("测试中文关键词搜索")
        print("=" * 60)

        papers = await service.search_papers(
            keywords=['投资者情绪', '分析师预测'],
            year_start=2020,
            year_end=2024,
            max_results=20
        )

        print(f"\n找到 {len(papers)} 篇论文:")
        for i, paper in enumerate(papers[:5], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            authors = paper.get('authors', [])[:3]
            author_str = ', '.join(authors) if authors else 'N/A'
            venue = paper.get('journal', 'N/A')

            print(f"\n{i}. [{year}] {title}")
            if author_str != 'N/A':
                print(f"   作者: {author_str}")
            if venue != 'N/A':
                print(f"   期刊: {venue}")

        # 统计中英文文献
        chinese = [p for p in papers if not p['is_english']]
        english = [p for p in papers if p['is_english']]

        print("\n" + "=" * 80)
        print(f"总计: {len(papers)} 篇 (中文: {len(chinese)}, 英文: {len(english)})")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_with_token())
