#!/usr/bin/env python3
"""
测试引用规范验证器
验证 5 条引用规则并自动修复
"""
import os
import sys
import json
import re

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.citation_validator import CitationValidator


def main():
    print("=" * 80)
    print("引用规范验证器 - 测试")
    print("=" * 80)

    # 加载之前生成的综述
    review_file = "smart_review_v2_20260405_135649.md"

    if not os.path.exists(review_file):
        print(f"错误: 综述文件不存在: {review_file}")
        print("请先运行 run_smart_review_v2.py 生成综述")
        return

    print(f"\n加载综述: {review_file}")

    with open(review_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 分离正文和参考文献
    print("\n分离正文和参考文献...")

    # 找到参考文献部分
    ref_section_markers = ["## References", "## 参考文献", "**参考文献**", "References"]
    ref_start = -1

    for marker in ref_section_markers:
        idx = content.find(marker)
        if idx != -1 and (ref_start == -1 or idx < ref_start):
            ref_start = idx

    if ref_start == -1:
        print("⚠️  未找到参考文献部分")
        main_content = content
        references_text = ""
    else:
        main_content = content[:ref_start]
        references_text = content[ref_start:]
        print(f"✓ 找到参考文献部分 (位置: {ref_start})")

    # 加载原始论文数据来重建参考文献列表
    json_path = "semantic_scholar_results_20260405_114423.json"

    print(f"\n加载原始论文: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 展平论文
    all_papers = []
    for category, papers in data.items():
        for paper in papers:
            paper["category"] = category
            all_papers.append(paper)

    print(f"✓ 加载 {len(all_papers)} 篇论文")

    # 从正文中提取引用，找出引用了哪些论文
    from services.citation_validator import CitationValidator
    validator = CitationValidator()

    cited_indices = validator._extract_cited_indices(main_content)
    unique_cited = sorted(list(set(cited_indices)))

    print(f"\n正文引用了 {len(unique_cited)} 篇不同的文献")
    print(f"引用编号: {unique_cited[:20]}")
    if len(unique_cited) > 20:
        print(f"... 还有 {len(unique_cited) - 20} 个")

    # 重建参考文献列表（只包含被引用的）
    references_list = []
    for idx in unique_cited:
        if 1 <= idx <= len(all_papers):
            references_list.append(all_papers[idx - 1])

    print(f"\n重建参考文献列表: {len(references_list)} 篇")

    # === 验证并修复 ===
    print("\n" + "=" * 80)
    print("开始验证引用规范...")
    print("=" * 80)

    result = validator.validate_and_fix(main_content, references_list)

    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)

    if result.valid:
        print("✓ 所有引用规范已满足")
    else:
        print("✗ 存在问题")
        for issue in result.issues:
            print(f"  - {issue}")

    # === 格式化参考文献 ===
    print("\n格式化参考文献 (IEEE 格式)...")
    references_formatted = validator.format_references_ieee(result.fixed_references)

    # === 合并最终内容 ===
    final_content = result.fixed_content + "\n\n## References\n\n" + references_formatted

    # === 保存结果 ===
    output_file = "review_validated_20260405.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"\n✓ 验证后的综述已保存: {output_file}")

    # === 最终检查 ===
    print("\n" + "=" * 80)
    print("最终检查")
    print("=" * 80)

    final_cited = validator._extract_cited_indices(result.fixed_content)
    final_unique = sorted(list(set(final_cited)))

    print(f"引用文献数量: {len(final_unique)}")
    print(f"引用编号范围: [{final_unique[0]}] - [{final_unique[-1]}]")
    print(f"引用编号连续: {final_unique == list(range(1, len(final_unique) + 1))}")

    # 检查每个文献的引用次数
    from collections import Counter
    final_counts = Counter(final_cited)
    max_count = max(final_counts.values()) if final_counts else 0

    print(f"单篇最大引用次数: {max_count}")
    print(f"所有文献引用次数 ≤ 2: {max_count <= 2}")

    print("\n" + "=" * 80)
    print("5条引用规范检查结果")
    print("=" * 80)

    checks = [
        ("规则1: 只引用列表中有的文献",
         all(1 <= idx <= len(result.fixed_references) for idx in final_unique)),
        ("规则2: 引用与列表对应",
         len(result.fixed_references) == len(final_unique)),
        ("规则3: 引用编号从1开始依次递增",
         final_unique == list(range(1, len(final_unique) + 1))),
        ("规则4: 同一文献不超过2次",
         max_count <= 2),
        ("规则5: 只列出被引用的文献",
         len(result.fixed_references) == len(final_unique))
    ]

    for name, passed in checks:
        status = "✓ 通过" if passed else "✗ 未通过"
        print(f"{name}: {status}")

    all_passed = all(passed for _, passed in checks)
    print("\n" + ("✓ 所有引用规范检查通过！" if all_passed else "✗ 仍有问题需要修复"))


if __name__ == "__main__":
    main()
