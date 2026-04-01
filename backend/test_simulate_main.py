"""
模拟 main.py smart_generate_review 的完整流程
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
from services.paper_filter import PaperFilterService


async def simulate_main_flow():
    """模拟 main.py 的 smart_generate_review 流程"""
    print("=" * 80)
    print("模拟 smart_generate_review 流程")
    print("=" * 80)

    # 模拟请求参数
    topic = "基于QFD的铝合金轮毂质量管理研究"
    target_count = 50
    recent_years_ratio = 0.5
    english_ratio = 0.3

    print(f"\n题目: {topic}")
    print(f"目标文献数: {target_count}")

    # 初始化服务
    gen = FrameworkGenerator()
    search_service = ScholarFlux()
    filter_service = PaperFilterService()

    try:
        # ========== 步骤1: 智能分析 ==========
        print("\n" + "=" * 60)
        print("步骤1: 智能分析")
        print("=" * 60)

        framework = await gen.generate_framework(topic)

        print(f"题目类型: {framework['type_name']}")
        search_queries = framework.get('search_queries', [])
        print(f"搜索查询: {len(search_queries)} 个")

        # ========== 步骤2: 初始文献搜索 ==========
        print("\n" + "=" * 60)
        print("步骤2: 初始文献搜索")
        print("=" * 60)

        all_papers = []
        search_queries_results = []

        for i, query_info in enumerate(search_queries[:8], 1):
            query = query_info.get('query', topic)
            section = query_info.get('section', '通用')
            lang = query_info.get('lang', None)

            print(f"\n[{i}] 搜索: {query[:40]}...")
            print(f"    章节: {section} | lang: {lang}")

            # 使用 search 方法（和 main.py 一致）
            papers = await search_service.search(
                query=query,
                years_ago=10,
                limit=50,
                lang=lang
            )

            print(f"    结果: {len(papers)} 篇")

            search_queries_results.append({
                'query': query,
                'section': section,
                'papers': papers,
                'citedCount': 0
            })
            all_papers.extend(papers)

        # ========== 补充搜索 ==========
        print(f"\n补充搜索（如果 < 150 篇）")
        if len(all_papers) < 150:
            print(f"当前文献数: {len(all_papers)} < 150，执行补充搜索")

            additional_papers = await search_service.search_papers(
                query=topic,
                years_ago=10,
                limit=200
            )

            print(f"补充搜索结果: {len(additional_papers)} 篇")
            all_papers.extend(additional_papers)

        # ========== 去重 ==========
        print("\n去重...")
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            paper_id = paper.get("id")
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                unique_papers.append(paper)

        all_papers = unique_papers
        print(f"去重后: {len(all_papers)} 篇")

        # ========== 检查是否有文献 ==========
        if not all_papers:
            print("\n❌ 未找到相关文献！")
            return

        # ========== 步骤3: 提取关键词 ==========
        print("\n" + "=" * 60)
        print("步骤3: 提取关键词")
        print("=" * 60)

        topic_keywords = gen.extract_relevance_keywords(framework)
        print(f"主题关键词: {topic_keywords[:5]}")

        # ========== 步骤4: 筛选文献 ==========
        print("\n" + "=" * 60)
        print("步骤4: 筛选文献")
        print("=" * 60)

        search_count = max(target_count * 2, 100)
        filtered_papers = filter_service.filter_and_sort(
            papers=all_papers,
            target_count=search_count,
            recent_years_ratio=recent_years_ratio,
            english_ratio=english_ratio,
            topic_keywords=topic_keywords
        )

        print(f"筛选后候选池: {len(filtered_papers)} 篇")

        # 显示 Top 10
        print("\nTop 10 筛选后的文献:")
        for i, paper in enumerate(filtered_papers[:10], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            is_en = paper.get('is_english', False)
            lang_mark = "🇬🇧" if is_en else "🇨🇳"
            print(f"  {i}. [{year}] {lang_mark} {cited:3d}c | {title[:55]}...")

    finally:
        await search_service.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(simulate_main_flow())
