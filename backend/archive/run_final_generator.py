#!/usr/bin/env python3
"""
运行最终版综述生成器
使用 303 篇 CAS 论文，完全符合 5 条引用规范
"""
import os
import sys
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

from services.smart_review_generator_final import SmartReviewGeneratorFinal


async def main():
    print("=" * 80)
    print("最终版综述生成器")
    print("=" * 80)

    # === 加载论文数据 ===
    json_file = "semantic_scholar_results_20260405_114423.json"

    if not os.path.exists(json_file):
        print(f"错误: 论文数据文件不存在: {json_file}")
        return

    print(f"\n加载论文数据: {json_file}")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 展平论文
    all_papers = []
    for category, papers in data.items():
        for paper in papers:
            paper["category"] = category
            all_papers.append(paper)

    print(f"✓ 加载 {len(all_papers)} 篇论文")

    # === 初始化生成器 ===
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 请设置 DEEPSEEK_API_KEY 环境变量")
        return

    generator = SmartReviewGeneratorFinal(
        deepseek_api_key=api_key
    )

    # === 生成综述 ===
    topic = "computer algebra system的算法实现及应用"

    result = await generator.generate_review_from_papers(
        topic=topic,
        papers=all_papers,
        model="deepseek-reasoner"
    )

    # === 保存结果 ===
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存 Markdown 版本
    md_file = f"smart_review_final_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(result["review"])
    print(f"\n✓ 综述已保存: {md_file}")

    # 保存 JSON 版本（包含引用论文）
    json_output = {
        "topic": result["topic"],
        "review": result["review"],
        "cited_papers": result["cited_papers"],
        "statistics": result["statistics"],
        "validation": result["validation"]
    }

    json_file = f"smart_review_final_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"✓ 完整数据已保存: {json_file}")

    # === 最终验证结果 ===
    print("\n" + "=" * 80)
    print("引用规范验证结果")
    print("=" * 80)

    if result["validation"]["valid"]:
        print("✓ 所有 5 条引用规范已通过验证！")
    else:
        print("✗ 存在问题:")
        for issue in result["validation"]["issues"]:
            print(f"  - {issue}")

    print("\n" + "=" * 80)
    print("生成完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
