"""
测试 Semantic Scholar API 搜索
"""
import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from services.semantic_scholar_search import SemanticScholarService


async def test_semantic_scholar_search():
    """测试Semantic Scholar搜索"""

    # 获取API key
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        print(f"✅ 已加载 Semantic Scholar API Key: {api_key[:10]}...")
    else:
        print("⚠️  未设置 SEMANTIC_SCHOLAR_API_KEY 环境变量，将使用默认速率限制")

    # 创建服务
    service = SemanticScholarService(api_key=api_key)

    # 测试搜索
    queries = [
        "Computer Algebra System",
        "Symbolic Computation",
        '"computer algebra" AND algorithm',
        '"symbolic integration" OR "Gröbner basis"',
        'Mathematica OR "Maple" OR "Maxima" OR "SageMath"',
    ]

    # 保存所有搜索结果
    all_results = {}

    for query in queries:
        print("\n" + "=" * 80)
        print(f"搜索: {query}")
        print("=" * 80)

        try:
            papers = await service.search_papers(
                query=query,
                years_ago=10,  # 近10年
                limit=100,  # 获取更多结果
                sort="citationCount:desc"  # 按引用量排序
            )

            print(f"\n找到 {len(papers)} 篇论文\n")

            # 保存结果
            all_results[query] = papers

            # 打印前10篇
            for i, paper in enumerate(papers[:10], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                citations = paper.get('citationCount', 0)
                venue = paper.get('venue') or paper.get('publicationVenue') or 'N/A'

                # 处理作者信息（可能是字符串列表或字典列表）
                authors = paper.get('authors', [])
                if authors and isinstance(authors[0], dict):
                    author_names = ', '.join([a.get('name', 'N/A') for a in authors[:3]])
                elif authors:
                    author_names = ', '.join([str(a) for a in authors[:3]])
                else:
                    author_names = 'N/A'

                print(f"{i}. {title[:70]}")
                print(f"   年份: {year} | 被引: {citations} | 来源: {venue}")
                print(f"   作者: {author_names}")
                print()

            if len(papers) > 10:
                print(f"... 还有 {len(papers) - 10} 篇论文未显示")

        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            import traceback
            traceback.print_exc()

    # 关闭服务
    await service.close()

    # 保存结果到文件
    if all_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"semantic_scholar_results_{timestamp}.json"
        filepath = Path(__file__).parent / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 80}")
        print(f"✅ 搜索结果已保存到: {filename}")
        print(f"{'=' * 80}")

        # 统计信息
        total_papers = sum(len(papers) for papers in all_results.values())
        print(f"\n统计信息:")
        print(f"  - 搜索查询数: {len(all_results)}")
        print(f"  - 总论文数: {total_papers}")
        for query, papers in all_results.items():
            print(f"  - {query}: {len(papers)} 篇")


if __name__ == "__main__":
    asyncio.run(test_semantic_scholar_search())
