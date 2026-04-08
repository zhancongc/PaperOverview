#!/usr/bin/env python3
"""
测试主题：computer algebra system的算法实现及应用
使用最终版综述生成器
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
from services.citation_validator import CitationValidator


async def main():
    print("=" * 80)
    print("测试主题：computer algebra system的算法实现及应用")
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
    md_file = f"test_cas_review_{timestamp}.md"
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

    json_file = f"test_cas_review_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"✓ 完整数据已保存: {json_file}")

    # === 用 citation_validator 再验证一次 ===
    print("\n" + "=" * 80)
    print("使用 CitationValidator 双重验证")
    print("=" * 80)

    review_content = result["review"]
    cited_papers = result["cited_papers"]

    # 分离正文和参考文献
    ref_section_markers = ["## References", "## 参考文献", "**参考文献**", "References"]
    ref_start = -1

    for marker in ref_section_markers:
        idx = review_content.find(marker)
        if idx != -1 and (ref_start == -1 or idx < ref_start):
            ref_start = idx

    main_content = review_content[:ref_start] if ref_start != -1 else review_content

    validator = CitationValidator()
    validation_result = validator.validate_and_fix(main_content, cited_papers)

    if validation_result.valid:
        print("✓ CitationValidator 验证通过！")
    else:
        print("✗ CitationValidator 发现问题:")
        for issue in validation_result.issues:
            print(f"  - {issue}")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
