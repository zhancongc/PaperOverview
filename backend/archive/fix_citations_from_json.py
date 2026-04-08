#!/usr/bin/env python3
"""
从 JSON 结果修复引用规范
使用专用的 citation_validator
"""
import os
import sys
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.citation_validator import CitationValidator


def main():
    print("=" * 80)
    print("引用规范修复工具 - 从 JSON 结果")
    print("=" * 80)

    # 加载之前生成的 JSON 结果
    json_file = "smart_review_final_20260405_141353.json"

    if not os.path.exists(json_file):
        print(f"错误: JSON 文件不存在: {json_file}")
        return

    print(f"\n加载 JSON 结果: {json_file}")

    with open(json_file, "r", encoding="utf-8") as f:
        result = json.load(f)

    review_content = result["review"]
    cited_papers = result["cited_papers"]

    print(f"✓ 综述长度: {len(review_content)} 字符")
    print(f"✓ 引用论文: {len(cited_papers)} 篇")

    # === 分离正文和参考文献 ===
    print("\n分离正文和参考文献...")

    ref_section_markers = ["## References", "## 参考文献", "**参考文献**", "References"]
    ref_start = -1

    for marker in ref_section_markers:
        idx = review_content.find(marker)
        if idx != -1 and (ref_start == -1 or idx < ref_start):
            ref_start = idx

    if ref_start == -1:
        print("⚠️  未找到参考文献部分")
        main_content = review_content
    else:
        main_content = review_content[:ref_start]
        print(f"✓ 找到参考文献部分 (位置: {ref_start})")

    # === 验证并修复 ===
    print("\n" + "=" * 80)
    print("开始验证引用规范...")
    print("=" * 80)

    validator = CitationValidator()
    validation_result = validator.validate_and_fix(main_content, cited_papers)

    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)

    if validation_result.valid:
        print("✓ 所有引用规范已满足")
    else:
        print("发现问题:")
        for i, issue in enumerate(validation_result.issues, 1):
            print(f"  {i}. {issue}")

    # === 格式化参考文献 ===
    print("\n格式化参考文献 (IEEE 格式)...")
    references_formatted = validator.format_references_ieee(validation_result.fixed_references)

    # === 合并最终内容 ===
    final_content = validation_result.fixed_content + "\n\n## References\n\n" + references_formatted

    # === 保存结果 ===
    output_file = "smart_review_final_fixed.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"\n✓ 最终验证后的综述已保存: {output_file}")

    # === 最终检查 ===
    print("\n" + "=" * 80)
    print("最终检查")
    print("=" * 80)

    final_cited = validator._extract_cited_indices(validation_result.fixed_content)
    final_unique = sorted(list(set(final_cited)))

    print(f"引用文献数量: {len(final_unique)}")
    print(f"引用编号范围: [{final_unique[0]}] - [{final_unique[-1]}]")
    print(f"引用编号连续: {final_unique == list(range(1, len(final_unique) + 1))}")

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
         all(1 <= idx <= len(validation_result.fixed_references) for idx in final_unique)),
        ("规则2: 引用与列表对应",
         len(validation_result.fixed_references) == len(final_unique)),
        ("规则3: 引用编号从1开始依次递增",
         final_unique == list(range(1, len(final_unique) + 1))),
        ("规则4: 同一文献不超过2次",
         max_count <= 2),
        ("规则5: 只列出被引用的文献",
         len(validation_result.fixed_references) == len(final_unique))
    ]

    for name, passed in checks:
        status = "✓ 通过" if passed else "✗ 未通过"
        print(f"{name}: {status}")

    all_passed = all(passed for _, passed in checks)
    print("\n" + ("✓ 所有引用规范检查通过！" if all_passed else "✗ 仍有问题需要修复"))

    # === 同时保存 JSON 版本 ===
    json_output = {
        "review": final_content,
        "cited_papers": validation_result.fixed_references,
        "validation_passed": all_passed
    }

    with open("smart_review_final_fixed.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    print(f"✓ JSON 版本已保存: smart_review_final_fixed.json")


if __name__ == "__main__":
    main()
