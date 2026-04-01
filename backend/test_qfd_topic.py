"""
测试题目：基于QFD的铝合金轮毂质量管理研究
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# 设置环境变量
os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.hybrid_classifier import FrameworkGenerator
from services.scholarflux_wrapper import ScholarFlux


async def test_qfd_topic():
    """测试 QFD 题目搜索"""
    print("=" * 80)
    print("测试题目：基于QFD的铝合金轮毂质量管理研究")
    print("=" * 80)

    topic = "基于QFD的铝合金轮毂质量管理研究"

    # 步骤1: 智能分析
    print("\n步骤1: 智能分析")
    print("-" * 60)

    gen = FrameworkGenerator()
    framework = await gen.generate_framework(topic)

    print(f"题目类型: {framework['type_name']}")
    print(f"判定理由: {framework['classification_reason']}")

    key_elements = framework.get('key_elements', {})
    print(f"研究对象: {key_elements.get('research_object', 'N/A')}")
    print(f"优化目标: {key_elements.get('optimization_goal', 'N/A')}")
    print(f"方法论: {key_elements.get('methodology', 'N/A')}")

    # 显示搜索查询
    search_queries = framework.get('search_queries', [])
    print(f"\n生成搜索查询: {len(search_queries)} 个")
    for i, q in enumerate(search_queries, 1):
        print(f"  {i}. {q['query']} (章节: {q['section']})")

    # 步骤2: 测试搜索
    print("\n步骤2: 测试搜索")
    print("-" * 60)

    flux = ScholarFlux()

    try:
        all_papers = []
        search_queries_results = []

        # 测试每个查询
        for i, query_info in enumerate(search_queries, 1):
            query = query_info['query']
            lang = query_info.get('lang', None)

            print(f"\n[{i}/{len(search_queries)}] 搜索: {query}")
            print(f"  语言标识: {lang}")

            papers = await flux.search(
                query=query,
                years_ago=10,
                limit=50,
                lang=lang
            )

            print(f"  结果: {len(papers)} 篇")

            search_queries_results.append({
                'query': query,
                'papers': papers,
                'count': len(papers)
            })
            all_papers.extend(papers)

            # 显示前2篇
            if papers:
                for j, paper in enumerate(papers[:2], 1):
                    title = paper.get('title', 'N/A')
                    year = paper.get('year', 'N/A')
                    cited = paper.get('cited_by_count', 0)
                    print(f"    {j}. [{year}] {cited}c | {title[:50]}...")

        # 统计
        print("\n步骤3: 统计结果")
        print("-" * 60)

        # 去重
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            pid = paper.get('id')
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_papers.append(paper)

        print(f"原始结果: {len(all_papers)} 篇")
        print(f"去重后: {len(unique_papers)} 篇")

        if not unique_papers:
            print("\n❌ 没有找到任何文献！")
            print("\n可能的原因:")
            print("  1. AMiner 对英文缩写（QFD）的中文文献覆盖有限")
            print("  2. 铝合金轮毂这个细分领域的中文学术文献较少")
            print("  3. 质量过滤可能过滤掉了一些文献")

            # 建议
            print("\n建议:")
            print("  - 尝试使用英文关键词搜索 OpenAlex")
            print("  - 简化关键词（如只搜索'铝合金 质量管理'）")
            print("  - 扩大年份范围")
        else:
            # 按被引量排序
            unique_papers.sort(key=lambda x: x.get('cited_by_count', 0), reverse=True)

            print(f"\nTop 10 文献:")
            for i, paper in enumerate(unique_papers[:10], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                cited = paper.get('cited_by_count', 0)
                venue = paper.get('journal', 'N/A')[:30]
                is_en = paper.get('is_english', False)
                lang_mark = "🇬🇧" if is_en else "🇨🇳"
                print(f"  {i}. [{year}] {lang_mark} {cited:3d}c | {title[:55]}...")

    finally:
        await flux.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_qfd_topic())
