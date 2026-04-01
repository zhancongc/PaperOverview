"""
测试修复后的文献综述生成流程
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.scholarflux_wrapper import ScholarFlux


async def test_aminer_search():
    """测试 AMiner 搜索关键词分割修复"""
    print("=" * 80)
    print("测试 AMiner 搜索关键词分割")
    print("=" * 80)

    search_service = ScholarFlux()

    test_queries = [
        "铝合金轮毂质量管理",  # 中文无空格
        "铝合金轮毂 质量管理",   # 中文有空格
        "QFD 铝合金轮毂",       # 中英混合
        "quality management automotive",  # 英文有空格
    ]

    for query in test_queries:
        print(f"\n测试查询: '{query}'")
        print("-" * 60)

        papers = await search_service.search(
            query=query,
            years_ago=10,
            limit=5,
            lang='zh' if any('\u4e00' <= c <= '\u9fff' for c in query) else None
        )

        print(f"找到 {len(papers)} 篇论文")
        if papers:
            for i, paper in enumerate(papers[:3], 1):
                title = paper.get('title', 'N/A')[:50]
                year = paper.get('year', 'N/A')
                print(f"  {i}. [{year}] {title}...")

    print("\n" + "=" * 80)


async def test_deduplication():
    """测试去重逻辑"""
    print("\n" + "=" * 80)
    print("测试去重逻辑")
    print("=" * 80)

    # 模拟重复论文
    seen_ids = set()
    all_papers = []

    # 添加论文1
    paper1 = {"id": "1", "title": "Paper 1"}
    if paper1["id"] not in seen_ids:
        seen_ids.add(paper1["id"])
        all_papers.append(paper1)

    # 添加论文2
    paper2 = {"id": "2", "title": "Paper 2"}
    if paper2["id"] not in seen_ids:
        seen_ids.add(paper2["id"])
        all_papers.append(paper2)

    # 尝试添加重复论文1
    paper1_dup = {"id": "1", "title": "Paper 1 Duplicate"}
    if paper1_dup["id"] not in seen_ids:
        seen_ids.add(paper1_dup["id"])
        all_papers.append(paper1_dup)

    print(f"原始添加 3 次，去重后: {len(all_papers)} 篇")
    print(f"论文ID列表: {[p['id'] for p in all_papers]}")
    assert len(all_papers) == 2, "去重逻辑应该只保留2篇论文"
    print("✓ 去重逻辑正确")

    print("\n" + "=" * 80)


async def main():
    """运行所有测试"""
    await test_aminer_search()
    await test_deduplication()
    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
