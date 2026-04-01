"""
测试文献搜索和筛选流程（不调用 DeepSeek）
"""
import asyncio
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# 设置环境变量
os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.hybrid_classifier import FrameworkGenerator
from services.scholarflux_wrapper import ScholarFlux
from services.paper_filter import PaperFilterService


async def test_search_and_filter():
    """测试搜索和筛选流程"""
    print("=" * 80)
    print("文献搜索与筛选流程测试")
    print("=" * 80)

    topic = '媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究'
    target_count = 50

    print(f"\n📝 题目: {topic}")
    print(f"🎯 目标文献数: {target_count}")

    # ========== 步骤1: 智能分析 ==========
    print("\n" + "=" * 60)
    print("步骤1: 智能分析题目")
    print("=" * 60)

    gen = FrameworkGenerator()
    framework = await gen.generate_framework(topic)

    print(f"✓ 题目类型: {framework['type_name']}")
    print(f"✓ 自变量: {framework['key_elements']['variables']['independent']}")
    print(f"✓ 因变量: {framework['key_elements']['variables']['dependent']}")
    print(f"✓ 搜索查询: {len(framework['search_queries'])} 个")

    # ========== 步骤2: 文献搜索 ==========
    print("\n" + "=" * 60)
    print("步骤2: 文献搜索")
    print("=" * 60)

    flux = ScholarFlux()
    all_papers = []

    # 执行搜索（使用更多查询）
    search_queries = framework['search_queries']
    max_queries = min(len(search_queries), 12)

    for i, query_info in enumerate(search_queries[:max_queries], 1):
        query = query_info['query']
        lang = query_info.get('lang', None)

        print(f"[{i}/{max_queries}] {query[:30]}...", end=" ")

        papers = await flux.search(query=query, years_ago=10, limit=25, lang=lang)
        all_papers.extend(papers)
        print(f"→ {len(papers)} 篇")

        await asyncio.sleep(1)

    # 去重
    seen_ids = set()
    unique_papers = []
    for paper in all_papers:
        pid = paper.get('id')
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            unique_papers.append(paper)

    print(f"\n✓ 原始: {len(all_papers)} 篇 | 去重: {len(unique_papers)} 篇")

    # ========== 步骤3: 文献筛选 ==========
    print("\n" + "=" * 60)
    print("步骤3: 文献筛选")
    print("=" * 60)

    filter_service = PaperFilterService()
    topic_keywords = gen.extract_relevance_keywords(framework)

    filtered_papers = filter_service.filter_and_sort(
        papers=unique_papers,
        target_count=target_count * 2,
        recent_years_ratio=0.5,
        english_ratio=0.3,
        topic_keywords=topic_keywords
    )

    print(f"✓ 筛选后候选池: {len(filtered_papers)} 篇")

    # 统计
    current_year = datetime.now().year
    recent = [p for p in filtered_papers if p.get('year', 0) >= current_year - 5]
    english = [p for p in filtered_papers if p.get('is_english', False)]

    print(f"  - 近5年: {len(recent)} 篇 ({len(recent)/len(filtered_papers)*100:.1f}%)")
    print(f"  - 英文: {len(english)} 篇 ({len(english)/len(filtered_papers)*100:.1f}%)")

    # ========== 显示 Top 文献 ==========
    print("\n" + "=" * 60)
    print(f"Top {min(20, len(filtered_papers))} 筛选后的文献")
    print("=" * 60)

    for i, paper in enumerate(filtered_papers[:20], 1):
        title = paper.get('title', 'N/A')
        year = paper.get('year', 'N/A')
        cited = paper.get('cited_by_count', 0)
        venue = paper.get('journal', 'N/A')[:30]
        is_en = paper.get('is_english', False)
        lang_mark = "🇬🇧" if is_en else "🇨🇳"

        print(f"{i:2d}. [{year}] {lang_mark} {cited:3d}c | {title[:55]}...")

    # ========== 保存结果 ==========
    result = {
        'topic': topic,
        'framework': {
            'type': framework['type'],
            'type_name': framework['type_name'],
            'variables': framework['key_elements']['variables']
        },
        'search_results': {
            'total_queries': len(search_queries),
            'executed_queries': max_queries,
            'raw_papers': len(all_papers),
            'unique_papers': len(unique_papers)
        },
        'filtered_results': {
            'candidate_pool_size': len(filtered_papers),
            'recent_years_count': len(recent),
            'recent_years_ratio': len(recent) / len(filtered_papers),
            'english_count': len(english),
            'english_ratio': len(english) / len(filtered_papers)
        },
        'top_papers': [
            {
                'title': p['title'],
                'year': p['year'],
                'cited_by_count': p['cited_by_count'],
                'journal': p.get('journal', ''),
                'is_english': p.get('is_english', False)
            }
            for p in filtered_papers[:20]
        ],
        'timestamp': datetime.now().isoformat()
    }

    with open('test_search_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n📁 结果已保存: test_search_result.json")

    await flux.close()

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_search_and_filter())
