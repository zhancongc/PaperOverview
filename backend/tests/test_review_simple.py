"""
手动测试：综述生成
"""
import sys
import asyncio

sys.path.insert(0, '.')

from services.review_generator import ReviewGeneratorService
from services.paper_search import PaperSearchService
from dotenv import load_dotenv
import os

load_dotenv()

async def run_tests():
    print("=" * 60)
    print("综述生成测试")
    print("=" * 60)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: DEEPSEEK_API_KEY 未配置")
        return

    # 获取少量文献进行测试
    print("\n正在获取文献...")
    search_service = PaperSearchService()
    papers = await search_service.search_papers(
        query="artificial intelligence",
        years_ago=3,
        limit=5
    )

    print(f"获取到 {len(papers)} 篇文献")

    # 生成综述
    print("\n正在生成综述...")
    generator = ReviewGeneratorService(api_key=api_key)
    review, cited_papers = await generator.generate_review(
        topic="人工智能",
        papers=papers
    )

    print(f"\n✓ 综述生成成功！")
    print(f"  长度: {len(review)} 字符")
    print(f"  提供文献: {len(papers)} 篇")
    print(f"  引用文献: {len(cited_papers)} 篇")

    # 统计引用
    import re
    citations = re.findall(r'\[\d+\]', review)
    print(f"  引用数量: {len(set(citations))} 个")

    # 显示预览
    print(f"\n综述预览:")
    print(f"  {review[:200]}...")


if __name__ == "__main__":
    asyncio.run(run_tests())
