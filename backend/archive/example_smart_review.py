#!/usr/bin/env python3
"""
智能综述生成器使用示例

演示 SmartReviewGenerator 的完整工作流程：
1. LLM 驱动的 Semantic Scholar 搜索
2. 大纲自动生成
3. Function Calling 撰写综述
"""
import os
import sys
import json
import asyncio
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from services.smart_review_generator import SmartReviewGenerator


async def example_basic_usage():
    """基础使用示例"""
    print("=" * 80)
    print("示例 1: 基础使用")
    print("=" * 80)

    # 加载环境变量
    load_dotenv()

    # 创建生成器
    generator = SmartReviewGenerator(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    )

    # 生成综述
    result = await generator.generate_review(
        topic="符号计算在理论物理中的应用",
        target_paper_count=80,
        max_search_rounds=2,
        model="deepseek-reasoner"
    )

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"smart_review_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 结果已保存到: {output_file}")

    # 也保存 Markdown 格式的综述
    md_file = f"smart_review_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(result["review"])

    print(f"✓ 综述已保存到: {md_file}")

    return result


async def example_custom_search():
    """自定义搜索示例"""
    print("\n" + "=" * 80)
    print("示例 2: 分步执行（自定义搜索）")
    print("=" * 80)

    load_dotenv()

    generator = SmartReviewGenerator(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    )

    topic = "计算机代数系统在密码学中的应用"

    # 分步 1: 只搜索论文
    print("\n[步骤 1] 搜索论文...")
    papers = await generator._intelligent_search(
        topic=topic,
        target_count=60,
        max_rounds=2,
        model="deepseek-reasoner"
    )
    print(f"✓ 找到 {len(papers)} 篇论文")

    # 分步 2: 生成大纲
    print("\n[步骤 2] 生成大纲...")
    outline = await generator._generate_outline(
        topic=topic,
        papers=papers,
        model="deepseek-reasoner"
    )
    print(f"✓ 大纲生成完成")
    print(f"  - 主体章节: {len(outline.get('body_sections', []))}")

    # 分步 3: 撰写综述
    print("\n[步骤 3] 撰写综述...")
    review, cited_papers = await generator._write_review(
        topic=topic,
        papers=papers,
        outline=outline,
        model="deepseek-reasoner"
    )
    print(f"✓ 综述完成，引用 {len(cited_papers)} 篇论文")

    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"custom_review_{timestamp}.md", "w", encoding="utf-8") as f:
        f.write(review)

    print(f"\n✓ 综述已保存")


async def example_with_existing_papers():
    """使用已有论文生成综述示例"""
    print("\n" + "=" * 80)
    print("示例 3: 使用已有 JSON 论文生成综述")
    print("=" * 80)

    load_dotenv()

    from services.review_generator_fc_unified import ReviewGeneratorFCUnified

    # 加载已有论文
    json_path = os.path.join(
        os.path.dirname(__file__),
        "semantic_scholar_results_20260405_114423.json"
    )

    if not os.path.exists(json_path):
        print(f"⚠️  论文文件不存在: {json_path}")
        return

    print(f"\n加载论文: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 展平论文
    papers = []
    for category, category_papers in data.items():
        for paper in category_papers:
            paper["category"] = category
            papers.append(paper)

    print(f"✓ 加载 {len(papers)} 篇论文")

    # 创建大纲
    topic = "计算机代数系统（CAS）的算法实现及应用"

    generator = SmartReviewGenerator(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY")
    )

    outline = await generator._generate_outline(
        topic=topic,
        papers=papers,
        model="deepseek-reasoner"
    )

    print(f"\n✓ 大纲生成完成")

    # 生成综述
    fc_generator = ReviewGeneratorFCUnified(
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )

    review, cited_papers = await fc_generator.generate_review(
        topic=topic,
        papers=papers,
        framework={"outline": outline},
        model="deepseek-reasoner",
        target_citation_count=80,
        min_citation_count=60
    )

    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"existing_papers_review_{timestamp}.md", "w", encoding="utf-8") as f:
        f.write(review)

    print(f"\n✓ 综述已保存，引用 {len(cited_papers)} 篇论文")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="智能综述生成器使用示例"
    )
    parser.add_argument(
        "example",
        choices=["basic", "custom", "existing"],
        default="basic",
        nargs="?",
        help="选择要运行的示例"
    )

    args = parser.parse_args()

    if args.example == "basic":
        asyncio.run(example_basic_usage())
    elif args.example == "custom":
        asyncio.run(example_custom_search())
    elif args.example == "existing":
        asyncio.run(example_with_existing_papers())


if __name__ == "__main__":
    main()
