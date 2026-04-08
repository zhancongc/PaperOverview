#!/usr/bin/env python3
"""
使用已有 JSON 论文生成综述
直接使用 semantic_scholar_results_20260405_114423.json
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


async def main():
    print("=" * 80)
    print("从已有 JSON 生成综述 - 一体化版本")
    print("=" * 80)

    # 加载环境变量
    load_dotenv()

    # 加载已有论文
    json_path = os.path.join(
        os.path.dirname(__file__),
        "semantic_scholar_results_20260405_114423.json"
    )

    if not os.path.exists(json_path):
        print(f"错误: 论文文件不存在: {json_path}")
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

    # 创建生成器
    generator = SmartReviewGenerator(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    )

    # 直接调用一体化综述生成
    topic = "computer algebra system的算法实现及应用"

    print(f"\n[阶段 2] 生成综述（大纲+撰写一体化）")
    print("-" * 80)

    review, cited_papers, outline = await generator._write_review_with_outline(
        topic=topic,
        papers=papers,
        model="deepseek-reasoner"
    )

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存 Markdown 格式
    md_file = f"cas_review_integrated_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(review)
    print(f"\n✓ 综述已保存: {md_file}")

    # 打印统计
    print("\n" + "=" * 80)
    print("生成统计")
    print("=" * 80)
    print(f"  主题: {topic}")
    print(f"  可用论文: {len(papers)} 篇")
    print(f"  引用论文: {len(cited_papers)} 篇")
    print(f"  综述长度: {len(review)} 字符")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
