"""
检查搜索结果的中文/英文分布
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.scholarflux_wrapper import ScholarFlux


async def check_lang_distribution():
    """检查搜索结果的语言分布"""
    print("=" * 80)
    print("检查搜索结果的语言分布")
    print("=" * 80)

    flux = ScholarFlux()

    try:
        # 测试几个查询
        queries = [
            "铝合金轮毂 质量管理",
            "QFD 质量管理",
            "铝合金轮毂 制造工艺",
        ]

        for query in queries:
            print(f"\n查询: {query}")
            print("-" * 60)

            papers = await flux.search(
                query=query,
                years_ago=10,
                limit=50,
                lang='zh'  # 明确指定中文
            )

            # 统计
            chinese = [p for p in papers if not p.get('is_english', False)]
            english = [p for p in papers if p.get('is_english', False)]

            print(f"总计: {len(papers)} 篇 | 中文: {len(chinese)} 篇 | 英文: {len(english)} 篇")

            # 显示各前3篇
            if chinese:
                print("\n中文文献示例:")
                for i, p in enumerate(chinese[:3], 1):
                    title = p.get('title', 'N/A')
                    year = p.get('year', 'N/A')
                    cited = p.get('cited_by_count', 0)
                    print(f"  {i}. [{year}] {cited}c | {title[:50]}...")

            if english:
                print("\n英文文献示例:")
                for i, p in enumerate(english[:3], 1):
                    title = p.get('title', 'N/A')
                    year = p.get('year', 'N/A')
                    cited = p.get('cited_by_count', 0)
                    print(f"  {i}. [{year}] {cited}c | {title[:50]}...")

    finally:
        await flux.close()


if __name__ == "__main__":
    asyncio.run(check_lang_distribution())
