"""
测试 Semantic Scholar 高级搜索功能
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.semantic_scholar_search import SemanticScholarService
from dotenv import load_dotenv

load_dotenv()


async def test_advanced_search():
    """测试高级搜索功能"""
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    service = SemanticScholarService(api_key=api_key)

    try:
        print("=" * 80)
        print("Semantic Scholar 高级搜索测试")
        print("=" * 80)

        # 测试1: 年份范围 + 排序
        print("\n[测试1] 搜索2021-2024年的LLM论文，按引用量排序")
        papers = await service.search_papers(
            query="large language model",
            year_start=2021,
            year_end=2024,
            limit=10,
            sort="citationCount:desc"
        )
        print(f"✓ 找到 {len(papers)} 篇论文")
        for i, p in enumerate(papers[:3], 1):
            print(f"  {i}. [{p.get('year')}] {p.get('title')[:60]}... (引用: {p.get('cited_by_count')})")

        # 测试2: 期刊过滤
        print("\n[测试2] 在 Nature 中搜索 AI 论文")
        papers = await service.search_by_venue(
            query="artificial intelligence",
            venue="Nature",
            years_ago=5,
            limit=5
        )
        print(f"✓ 找到 {len(papers)} 篇论文")
        for i, p in enumerate(papers[:2], 1):
            print(f"  {i}. {p.get('title')[:60]}...")

        # 测试3: 布尔查询
        print("\n[测试3] 布尔查询: (transformer OR attention)")
        papers = await service.search_papers(
            query="(transformer OR attention) AND neural network",
            years_ago=2,
            limit=5,
            sort="citationCount:desc"
        )
        print(f"✓ 找到 {len(papers)} 篇论文")

        # 测试4: 便捷方法 - 近期高被引
        print("\n[测试4] 近期高被引论文 (2023-2024, 至少10次引用)")
        papers = await service.search_recent_highly_cited(
            query="diffusion model",
            year_start=2023,
            year_end=2024,
            min_citations=10,
            limit=5
        )
        print(f"✓ 找到 {len(papers)} 篇论文")
        for i, p in enumerate(papers[:3], 1):
            print(f"  {i}. [{p.get('year')}] {p.get('title')[:60]}... (引用: {p.get('cited_by_count')})")

        # 测试5: 多期刊搜索
        print("\n[测试5] 在顶级期刊搜索 computer algebra")
        top_venues = [
            "Journal of Symbolic Computation",
            "Journal of the ACM",
            "SIAM Journal on Computing"
        ]
        papers = await service.search_top_venues(
            query="computer algebra OR symbolic computation",
            venues=top_venues,
            years_ago=10,
            limit_per_venue=5
        )
        print(f"✓ 找到 {len(papers)} 篇论文")
        for i, p in enumerate(papers[:3], 1):
            venue = p.get('venue', 'Unknown')
            print(f"  {i}. [{venue}] {p.get('title')[:60]}...")

        print("\n" + "=" * 80)
        print("所有测试通过！")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close()


async def test_cas_advanced_search():
    """测试 CAS 主题的高级搜索"""
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    service = SemanticScholarService(api_key=api_key)

    try:
        print("\n" + "=" * 80)
        print("CAS 主题高级搜索测试")
        print("=" * 80)

        # 使用专业关键词
        professional_keywords = [
            "Gröbner basis",
            "Risch algorithm",
            "polynomial GCD",
            "symbolic integration",
            "computer algebra system"
        ]

        all_papers = []
        for keyword in professional_keywords:
            print(f"\n搜索: {keyword}")
            papers = await service.search_papers(
                query=keyword,
                year_start=2015,
                year_end=2024,
                limit=10,
                sort="citationCount:desc"
            )
            print(f"  找到 {len(papers)} 篇")
            all_papers.extend(papers)

        # 去重
        seen_ids = set()
        unique_papers = []
        for p in all_papers:
            pid = p.get("id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_papers.append(p)

        # 按引用量排序
        unique_papers.sort(key=lambda p: p.get("cited_by_count", 0), reverse=True)

        print(f"\n✓ 总计找到 {len(unique_papers)} 篇唯一论文")
        print("\n高被引论文:")
        for i, p in enumerate(unique_papers[:10], 1):
            year = p.get('year', 'N/A')
            citations = p.get('cited_by_count', 0)
            venue = p.get('venue', 'Unknown')[:20]
            title = p.get('title', '')[:70]
            print(f"  {i}. [{year}] [{venue}] {title}... (引用: {citations})")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(test_advanced_search())
    print("\n")
    asyncio.run(test_cas_advanced_search())
