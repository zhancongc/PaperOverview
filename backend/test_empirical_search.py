"""
测试实证型文献搜索流程
题目：媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.hybrid_classifier import FrameworkGenerator
from services.paper_search import PaperSearchService


async def test_empirical_search():
    """测试实证型文献搜索流程"""

    title = "媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究"

    print("=" * 80)
    print(f"测试题目: {title}")
    print("=" * 80)

    # 第一步：生成框架和查询
    print("\n【第一步】生成综述框架和检索查询...")
    generator = FrameworkGenerator()
    framework = await generator.generate_framework(title, enable_llm_validation=False)

    print(f"\n题目类型: {framework['type_name']}")
    print(f"分类原因: {framework['classification_reason']}")

    # 显示关键元素
    key_elements = framework.get('key_elements', {})
    variables = key_elements.get('variables', {})
    if variables:
        print(f"\n提取的变量:")
        print(f"  自变量: {variables.get('independent')}")
        print(f"  因变量: {variables.get('dependent')}")

    # 显示查询
    queries = framework.get('search_queries', [])
    print(f"\n生成的检索查询 (共 {len(queries)} 个):")
    print("-" * 80)

    # 按策略分组显示
    by_strategy = {}
    for q in queries:
        strategy = q.get('strategy', '未知')
        if strategy not in by_strategy:
            by_strategy[strategy] = []
        by_strategy[strategy].append(q)

    for strategy, qs in by_strategy.items():
        print(f"\n【{strategy}】({len(qs)}个查询)")
        for i, q in enumerate(qs, 1):
            print(f"  {i}. {q['query']} -> {q['section']}")

    # 第二步：执行文献搜索
    print("\n" + "=" * 80)
    print("【第二步】执行文献搜索...")
    print("=" * 80)

    search_service = PaperSearchService()
    all_papers = []
    query_results = []

    # 为每个查询执行搜索（限制查询数量以避免过长时间）
    max_queries = 10  # 只测试前10个查询
    print(f"\n将执行前 {max_queries} 个查询的搜索...\n")

    for i, query_info in enumerate(queries[:max_queries], 1):
        query = query_info['query']
        section = query_info['section']
        strategy = query_info.get('strategy', '未知')

        print(f"[{i}/{min(max_queries, len(queries))}] 搜索: {query}")
        print(f"    章节: {section} | 策略: {strategy}")

        try:
            papers = await search_service.search_papers(
                query=query,
                years_ago=10,  # 搜索近10年
                limit=20,       # 每个查询最多20篇
                min_citations=0 # 不过滤被引量
            )

            # 添加策略标记
            for paper in papers:
                paper['query_strategy'] = strategy
                paper['query_section'] = section

            query_results.append({
                'query': query,
                'section': section,
                'strategy': strategy,
                'count': len(papers),
                'papers': papers
            })

            all_papers.extend(papers)
            print(f"    结果: 找到 {len(papers)} 篇文献")

            # 显示前2篇文献
            for j, paper in enumerate(papers[:2], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                citations = paper.get('cited_by_count', 0)
                print(f"      {j}. [{year}] {title[:60]}... (被引: {citations})")
            if len(papers) > 2:
                print(f"      ... 还有 {len(papers) - 2} 篇")

        except Exception as e:
            print(f"    错误: {e}")
            query_results.append({
                'query': query,
                'section': section,
                'strategy': strategy,
                'count': 0,
                'error': str(e)
            })

        print()

    # 关闭搜索服务
    await search_service.close()

    # 第三步：统计结果
    print("=" * 80)
    print("【第三步】搜索结果统计")
    print("=" * 80)

    # 去重（按标题）
    seen_titles = set()
    unique_papers = []
    for paper in all_papers:
        title = paper.get('title', '')
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_papers.append(paper)

    print(f"\n总计搜索: {len(queries[:max_queries])} 个查询")
    print(f"原始结果: {len(all_papers)} 篇文献")
    print(f"去重后: {len(unique_papers)} 篇文献")

    # 按策略统计
    print(f"\n按策略统计:")
    strategy_stats = {}
    for qr in query_results:
        strategy = qr['strategy']
        if strategy not in strategy_stats:
            strategy_stats[strategy] = {'queries': 0, 'papers': 0}
        strategy_stats[strategy]['queries'] += 1
        strategy_stats[strategy]['papers'] += qr.get('count', 0)

    for strategy, stats in strategy_stats.items():
        print(f"  {strategy}: {stats['queries']} 个查询, {stats['papers']} 篇文献")

    # 按被引量排序，显示top 10
    unique_papers.sort(key=lambda x: x.get('cited_by_count', 0), reverse=True)
    print(f"\n被引量最高的 10 篇文献:")
    print("-" * 80)
    for i, paper in enumerate(unique_papers[:10], 1):
        title = paper.get('title', 'N/A')
        year = paper.get('year', 'N/A')
        citations = paper.get('cited_by_count', 0)
        strategy = paper.get('query_strategy', 'N/A')
        print(f"{i:2d}. [{year}] 被引:{citations:4d} | {strategy}")
        print(f"     {title[:70]}")

    # 第四步：检查是否有零结果查询
    print(f"\n零结果查询分析:")
    zero_count = sum(1 for qr in query_results if qr.get('count', 0) == 0)
    if zero_count > 0:
        print(f"  有 {zero_count} 个查询没有找到文献:")
        for qr in query_results:
            if qr.get('count', 0) == 0:
                print(f"    - {qr['query']} ({qr['strategy']})")
    else:
        print(f"  所有查询都找到了文献！")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_empirical_search())
