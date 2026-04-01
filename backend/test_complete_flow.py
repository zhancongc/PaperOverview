"""
测试完整的文献综述生成流程
使用用户的题目：媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究
"""
import asyncio
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# 设置环境变量
os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"
os.environ['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY', 'sk-6c41033cd1cd4b79ab9969743550cad3')

from services.hybrid_classifier import FrameworkGenerator
from services.scholarflux_wrapper import ScholarFlux
from services.paper_filter import PaperFilterService
from services.review_generator import ReviewGeneratorService


async def test_complete_flow():
    """测试完整的文献综述生成流程"""
    print("=" * 80)
    print("完整流程测试：文献综述生成")
    print("=" * 80)

    # 测试参数（模拟用户请求）
    request = {
        'topic': '媒体关注度、投资者情绪与分析师盈利预测准确性——基于行为金融学的实证研究',
        'target_count': 50,
        'recent_years_ratio': 0.5,
        'english_ratio': 0.3
    }

    print(f"\n📝 题目: {request['topic']}")
    print(f"🎯 目标文献数: {request['target_count']}")
    print(f"📅 近5年占比: {request['recent_years_ratio']}")
    print(f"🌍 英文占比: {request['english_ratio']}")

    try:
        # ========== 步骤1: 智能分析题目 ==========
        print("\n" + "=" * 60)
        print("步骤1: 智能分析题目")
        print("=" * 60)

        gen = FrameworkGenerator()
        framework = await gen.generate_framework(request['topic'])

        print(f"✓ 题目类型: {framework['type_name']}")
        print(f"✓ 判定理由: {framework['classification_reason']}")

        # 显示关键元素
        key_elements = framework.get('key_elements', {})
        variables = key_elements.get('variables', {})
        if variables:
            print(f"✓ 自变量: {variables.get('independent', 'N/A')}")
            print(f"✓ 因变量: {variables.get('dependent', 'N/A')}")

        # 显示搜索查询数量
        search_queries = framework.get('search_queries', [])
        print(f"✓ 生成搜索查询: {len(search_queries)} 个")

        # ========== 步骤2: 文献搜索 ==========
        print("\n" + "=" * 60)
        print("步骤2: 文献搜索")
        print("=" * 60)

        flux = ScholarFlux()
        all_papers = []
        search_queries_results = []

        # 执行搜索（限制查询数量以加快测试）
        max_queries = 10
        for i, query_info in enumerate(search_queries[:max_queries], 1):
            query = query_info.get('query', request['topic'])
            section = query_info.get('section', '通用')
            lang = query_info.get('lang', None)

            print(f"\n[{i}/{max_queries}] {query[:40]}...")

            papers = await flux.search(
                query=query,
                years_ago=10,
                limit=30,
                lang=lang
            )

            print(f"  → 找到 {len(papers)} 篇")

            search_queries_results.append({
                'query': query,
                'section': section,
                'papers': papers,
                'citedCount': 0
            })
            all_papers.extend(papers)

        # 去重
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            pid = paper.get('id')
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_papers.append(paper)

        print(f"\n✓ 原始结果: {len(all_papers)} 篇")
        print(f"✓ 去重后: {len(unique_papers)} 篇")

        # ========== 步骤3: 文献筛选 ==========
        print("\n" + "=" * 60)
        print("步骤3: 文献筛选")
        print("=" * 60)

        filter_service = PaperFilterService()

        # 提取主题关键词
        topic_keywords = gen.extract_relevance_keywords(framework)
        print(f"✓ 主题关键词: {', '.join(topic_keywords[:5])}")

        # 筛选文献
        search_count = max(request['target_count'] * 2, 100)
        filtered_papers = filter_service.filter_and_sort(
            papers=unique_papers,
            target_count=search_count,
            recent_years_ratio=request['recent_years_ratio'],
            english_ratio=request['english_ratio'],
            topic_keywords=topic_keywords
        )

        print(f"✓ 筛选后候选池: {len(filtered_papers)} 篇")

        # 显示筛选统计
        current_year = datetime.now().year
        recent_count = len([p for p in filtered_papers if p.get('year', 0) >= current_year - 5])
        english_count = len([p for p in filtered_papers if p.get('is_english', False)])

        print(f"  - 近5年: {recent_count} 篇 ({recent_count/len(filtered_papers)*100:.1f}%)")
        print(f"  - 英文: {english_count} 篇 ({english_count/len(filtered_papers)*100:.1f}%)")

        # ========== 步骤4: 生成综述（如果配置了 API Key） ==========
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key and api_key.startswith('sk-'):
            print("\n" + "=" * 60)
            print("步骤4: 生成综述")
            print("=" * 60)

            generator = ReviewGeneratorService(api_key=api_key)

            print("正在调用 DeepSeek API 生成综述...")
            print("(这可能需要 1-2 分钟)")

            review, cited_papers = await generator.generate_review(
                topic=request['topic'],
                papers=filtered_papers[:request['target_count']]
            )

            print(f"✓ 综述生成完成")
            print(f"✓ 被引用文献: {len(cited_papers)} 篇")

            # 显示综述开头
            lines = review.split('\n')
            content_lines = []
            for line in lines:
                if line.startswith('## 参考文献'):
                    break
                content_lines.append(line)
            content = '\n'.join(content_lines)

            print(f"\n📄 综述预览（前500字）:")
            print(content[:500] + "...")

            # 计算最终统计
            stats = filter_service.get_statistics(cited_papers)
            print(f"\n📊 最终统计:")
            print(f"  - 总文献数: {stats.get('total', len(cited_papers))}")
            print(f"  - 近5年: {stats.get('recent_years_count', 0)} ({stats.get('recent_years_ratio', 0):.1%})")
            print(f"  - 英文: {stats.get('english_count', 0)} ({stats.get('english_ratio', 0):.1%})")
            print(f"  - 平均被引: {stats.get('avg_citations', 0):.1f}")

        else:
            print("\n" + "=" * 60)
            print("步骤4: 跳过综述生成（未配置 DEEPSEEK_API_KEY）")
            print("=" * 60)

            # 显示筛选后的文献
            print(f"\n📚 筛选后的 Top 10 文献:")
            for i, paper in enumerate(filtered_papers[:10], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                cited = paper.get('cited_by_count', 0)
                is_en = paper.get('is_english', False)
                lang_mark = "🇬🇧" if is_en else "🇨🇳"
                print(f"  {i}. [{year}] {lang_mark} {title[:65]}... (被引: {cited})")

        # ========== 完成 ==========
        print("\n" + "=" * 80)
        print("✅ 流程测试完成")
        print("=" * 80)

        # 保存结果到文件
        result = {
            'topic': request['topic'],
            'framework': framework,
            'search_queries_count': len(search_queries),
            'total_papers_found': len(unique_papers),
            'filtered_papers_count': len(filtered_papers),
            'timestamp': datetime.now().isoformat()
        }

        with open('test_flow_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"📁 结果已保存到: test_flow_result.json")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'flux' in locals():
            await flux.close()


if __name__ == "__main__":
    asyncio.run(test_complete_flow())
