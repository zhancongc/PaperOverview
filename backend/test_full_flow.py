"""
测试完整的综述生成流程（使用用户提供的题目）
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.hybrid_classifier import FrameworkGenerator
from services.scholarflux_wrapper import ScholarFlux


async def test_full_flow():
    """测试完整流程"""
    topic = "基于QFD的铝合金轮毂质量管理研究"

    print("=" * 80)
    print(f"测试题目: {topic}")
    print("=" * 80)

    # Step 1: 题目分类
    print("\nStep 1: 题目分类")
    print("-" * 60)

    gen = FrameworkGenerator()
    framework = await gen.generate_framework(topic, enable_llm_validation=True)

    print(f"题目类型: {framework['type']}")
    print(f"搜索查询数量: {len(framework.get('search_queries', []))}")

    # Step 2: 显示搜索查询
    search_queries = framework.get('search_queries', [])
    print("\nStep 2: 搜索查询")
    print("-" * 60)

    for i, query_info in enumerate(search_queries, 1):
        print(f"\n查询 {i}:")
        print(f"  查询: {query_info.get('query', 'N/A')}")
        print(f"  章节: {query_info.get('section', 'N/A')}")
        print(f"  语言: {query_info.get('lang', 'N/A')}")
        print(f"  搜索模式: {query_info.get('search_mode', 'N/A')}")
        print(f"  关键词: {query_info.get('keywords', 'N/A')}")

    # Step 3: 执行搜索
    print("\nStep 3: 执行搜索")
    print("-" * 60)

    search_service = ScholarFlux()
    all_papers = []

    for query_info in search_queries[:5]:  # 只测试前5个查询
        query = query_info.get('query', topic)
        section = query_info.get('section', '通用')
        lang = query_info.get('lang', None)
        keywords = query_info.get('keywords', None)
        search_mode = query_info.get('search_mode', None)

        print(f"\n搜索: {query}")
        print(f"  语言: {lang}, 模式: {search_mode}, 关键词: {keywords}")

        papers = await search_service.search(
            query=query,
            years_ago=10,
            limit=20,
            lang=lang,
            keywords=keywords,
            search_mode=search_mode
        )

        print(f"  找到: {len(papers)} 篇")

        # 显示前2篇
        for paper in papers[:2]:
            title = paper.get('title', 'N/A')[:50]
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            print(f"    - [{year}] {cited}c | {title}...")

        all_papers.extend(papers)

    # 去重
    seen_ids = set()
    unique_papers = []
    for paper in all_papers:
        paper_id = paper.get('id')
        if paper_id not in seen_ids:
            seen_ids.add(paper_id)
            unique_papers.append(paper)

    print(f"\n总去重后: {len(unique_papers)} 篇")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_full_flow())
