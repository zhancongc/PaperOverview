"""
详细检查搜索结果的 is_english 字段
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.scholarflux_wrapper import ScholarFlux


async def check_is_english_field():
    """检查 is_english 字段"""
    print("=" * 80)
    print("检查 is_english 字段")
    print("=" * 80)

    flux = ScholarFlux()

    try:
        # 搜索 "QFD 铝合金轮毂"
        print("\n搜索: QFD 铝合金轮毂")
        print("-" * 60)

        papers = await flux.search(
            query="QFD 铝合金轮毂",
            years_ago=10,
            limit=30,
            lang='zh'
        )

        # 统计
        marked_english = [p for p in papers if p.get('is_english', False)]
        marked_chinese = [p for p in papers if not p.get('is_english', False)]

        print(f"\n总计: {len(papers)} 篇")
        print(f"标记为英文: {len(marked_english)} 篇")
        print(f"标记为中文: {len(marked_chinese)} 篇")

        # 显示标记为中文的文献（应该确实是中文）
        print("\n标记为中文的文献（前10篇）:")
        for i, p in enumerate(marked_chinese[:10], 1):
            title = p.get('title', 'N/A')
            year = p.get('year', 'N/A')
            cited = p.get('cited_by_count', 0)
            print(f"  {i}. [{year}] {cited}c | {title}")

        # 显示标记为英文的文献
        if marked_english:
            print("\n标记为英文的文献（前5篇）:")
            for i, p in enumerate(marked_english[:5], 1):
                title = p.get('title', 'N/A')
                year = p.get('year', 'N/A')
                cited = p.get('cited_by_count', 0)
                print(f"  {i}. [{year}] {cited}c | {title}")

    finally:
        await flux.close()


if __name__ == "__main__":
    asyncio.run(check_is_english_field())
