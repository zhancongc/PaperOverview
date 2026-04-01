"""
测试中文文献搜索修复
验证实证型中文题目的搜索功能
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from services.hybrid_classifier import FrameworkGenerator
from services.scholarflux_wrapper import ScholarFlux

async def test_chinese_empirical_search():
    """测试中文实证型题目搜索"""
    print("=" * 80)
    print("测试中文实证型题目搜索修复")
    print("=" * 80)

    # 设置环境变量
    os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

    # 测试题目
    test_topic = "媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究"

    print(f"\n测试题目: {test_topic}")
    print()

    # 1. 智能分析
    print("=" * 60)
    print("步骤1: 智能分析题目")
    print("=" * 60)

    gen = FrameworkGenerator()
    framework = await gen.generate_framework(test_topic)

    print(f"题目类型: {framework['type_name']}")
    print(f"判定理由: {framework['classification_reason']}")
    print()

    # 显示关键元素
    key_elements = framework.get('key_elements', {})
    variables = key_elements.get('variables', {})
    if variables:
        print(f"自变量: {variables.get('independent', 'N/A')}")
        print(f"因变量: {variables.get('dependent', 'N/A')}")
    print()

    # 2. 显示搜索查询
    print("=" * 60)
    print("步骤2: 搜索查询生成")
    print("=" * 60)

    search_queries = framework.get('search_queries', [])
    print(f"共生成 {len(search_queries)} 个搜索查询")
    print()

    # 按策略分组显示
    queries_by_strategy = {}
    for q in search_queries:
        strategy = q.get('strategy', '其他')
        if strategy not in queries_by_strategy:
            queries_by_strategy[strategy] = []
        queries_by_strategy[strategy].append(q)

    for strategy, queries in queries_by_strategy.items():
        print(f"\n【{strategy}】({len(queries)}个查询):")
        for i, q in enumerate(queries[:5], 1):  # 只显示前5个
            print(f"  {i}. {q['query']}")
            print(f"     章节: {q['section']} | 语言: {q.get('lang', 'auto')}")
        if len(queries) > 5:
            print(f"  ... 还有 {len(queries) - 5} 个查询")

    # 3. 执行搜索（只测试前几个查询）
    print("\n" + "=" * 60)
    print("步骤3: 执行文献搜索（测试前5个查询）")
    print("=" * 60)

    flux = ScholarFlux()
    all_papers = []

    try:
        for i, query_info in enumerate(search_queries[:5], 1):
            query = query_info['query']
            lang = query_info.get('lang', None)

            print(f"\n查询 {i}: {query}")
            print(f"  语言: {lang if lang else '自动检测'}")

            papers = await flux.search(
                query=query,
                years_ago=10,
                limit=20,
                lang=lang
            )

            print(f"  结果: {len(papers)} 篇")

            # 显示前2篇
            for j, paper in enumerate(papers[:2], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                cited = paper.get('cited_by_count', 0)
                print(f"    {j}. [{year}] {title[:60]}... (被引: {cited})")

            all_papers.extend(papers)
            await asyncio.sleep(1.5)  # 避免请求过快

        # 4. 统计结果
        print("\n" + "=" * 60)
        print("步骤4: 搜索结果统计")
        print("=" * 60)

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

        # 统计中文/英文
        chinese_count = len([p for p in unique_papers if not p.get('is_english', True)])
        english_count = len([p for p in unique_papers if p.get('is_english', False)])

        print(f"中文文献: {chinese_count} 篇")
        print(f"英文文献: {english_count} 篇")

        # 按被引量排序，显示 top 10
        unique_papers.sort(key=lambda x: x.get('cited_by_count', 0), reverse=True)

        print("\nTop 10 高被引论文:")
        for i, paper in enumerate(unique_papers[:10], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            is_en = paper.get('is_english', False)
            lang_mark = "🇬🇧" if is_en else "🇨🇳"
            print(f"  {i}. [{year}] {lang_mark} {title[:70]}... (被引: {cited})")

    finally:
        await flux.close()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_chinese_empirical_search())
