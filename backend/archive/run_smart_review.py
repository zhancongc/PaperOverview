#!/usr/bin/env python3
"""
运行智能综述生成器
主题: computer algebra system的算法实现及应用
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
    print("智能综述生成器 - 一体化版本")
    print("=" * 80)

    # 加载环境变量
    load_dotenv()

    # 创建生成器
    generator = SmartReviewGenerator(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    )

    # 生成综述
    topic = "computer algebra system的算法实现及应用"

    result = await generator.generate_review(
        topic=topic,
        target_paper_count=100,
        max_search_rounds=2,
        model="deepseek-reasoner"
    )

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存 JSON 格式（完整数据）
    json_file = f"smart_review_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 完整结果已保存: {json_file}")

    # 保存 Markdown 格式（仅综述）
    md_file = f"smart_review_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(result["review"])
    print(f"✓ 综述已保存: {md_file}")

    # 打印统计
    print("\n" + "=" * 80)
    print("生成统计")
    print("=" * 80)
    stats = result["statistics"]
    print(f"  主题: {result['topic']}")
    print(f"  收集论文: {stats['papers_collected']} 篇")
    print(f"  引用论文: {stats['papers_cited']} 篇")
    print(f"  搜索轮数: {stats['search_rounds']} 轮")
    print(f"  总耗时: {stats['total_time_seconds']} 秒")
    print(f"  综述长度: {stats['review_length']} 字符")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
