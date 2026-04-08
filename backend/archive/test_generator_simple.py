#!/usr/bin/env python3
"""
简单测试生成器
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from services.semantic_scholar_search import SemanticScholarService
from services.smart_review_generator_final import SmartReviewGeneratorFinal


async def main():
    topic = "computer algebra system的算法实现及应用"
    print(f"测试主题: {topic}")
    print("=" * 80)

    # 1. 搜索论文
    print("\n[步骤1] 搜索论文...")
    ss_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    ss_service = SemanticScholarService(api_key=ss_api_key)

    try:
        papers = await ss_service.search_papers(
            query=topic,
            years_ago=10,
            limit=100,
            sort="citationCount:desc"
        )
        print(f"✓ 找到 {len(papers)} 篇论文")

        # 显示前5篇
        for i, p in enumerate(papers[:5], 1):
            print(f"  {i}. [{p.get('year')}] {p.get('title', '')[:60]}... (引用: {p.get('cited_by_count', 0)})")

    finally:
        await ss_service.close()

    if len(papers) < 20:
        print(f"✗ 论文不足，只有 {len(papers)} 篇")
        return

    # 统计一下英文论文比例
    english_count = sum(1 for p in papers if p.get("is_english", False))
    print(f"\n[统计] 英文论文: {english_count}/{len(papers)} ({english_count/len(papers)*100:.1f}%)")

    # 2. 生成综述
    print("\n[步骤2] 生成综述...")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("✗ 未设置 DEEPSEEK_API_KEY")
        return

    generator = SmartReviewGeneratorFinal(
        deepseek_api_key=api_key,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )

    # 构建搜索参数
    search_params = {
        "search_years": 10,
        "target_count": 50,
        "recent_years_ratio": 0.5,
        "search_platform": "Semantic Scholar",
        "sort_by": "被引量降序"
    }

    result = await generator.generate_review_from_papers(
        topic=topic,
        papers=papers,
        model="deepseek-chat",  # 用 chat 模型更快
        search_params=search_params
    )

    # 保存结果
    output_file = "test_review_output.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result["review"])

    print(f"\n✓ 生成完成！")
    print(f"  - 总耗时: {result['statistics']['total_time_seconds']} 秒")
    print(f"  - 引用论文: {result['statistics']['papers_cited']} 篇")
    print(f"  - 综述长度: {result['statistics']['review_length']} 字符")
    print(f"\n结果已保存到: {output_file}")

    # 显示前500字符
    print("\n" + "=" * 80)
    print("综述预览:")
    print("=" * 80)
    print(result["review"][:800])
    print("...")


if __name__ == "__main__":
    asyncio.run(main())
