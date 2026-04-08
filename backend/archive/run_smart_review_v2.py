#!/usr/bin/env python3
"""
运行修复后的智能综述生成器 v2.1
主题: computer algebra system的算法实现及应用

修复：
1. 参考文献缺失问题
2. 参考文献格式不统一（使用IEEE格式）
3. 信息缺失问题
"""
import os
import sys
import json
import asyncio
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from services.smart_review_generator_v2 import SmartReviewGeneratorV2


async def main():
    print("=" * 80)
    print("智能综述生成器 v2.1 - 修复版")
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
    generator = SmartReviewGeneratorV2(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    )

    # 生成综述
    topic = "computer algebra system的算法实现及应用"

    result = await generator.generate_review_from_papers(
        topic=topic,
        papers=papers,
        model="deepseek-reasoner"
    )

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存 JSON 格式（完整数据）
    json_file = f"smart_review_v2_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 完整结果已保存: {json_file}")

    # 保存 Markdown 格式（仅综述）
    md_file = f"smart_review_v2_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(result["review"])
    print(f"✓ 综述已保存: {md_file}")

    # 打印统计
    print("\n" + "=" * 80)
    print("生成统计")
    print("=" * 80)
    stats = result["statistics"]
    print(f"  主题: {result['topic']}")
    print(f"  可用论文: {stats['papers_collected']} 篇")
    print(f"  引用论文: {stats['papers_cited']} 篇")
    print(f"  综述长度: {stats['review_length']} 字符")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
