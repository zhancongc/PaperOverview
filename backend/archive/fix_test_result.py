#!/usr/bin/env python3
"""
修复测试结果的引用规范
"""
import os
import sys
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.citation_validator import CitationValidator


def main():
    json_file = "test_cas_review_20260405_142702.json"

    print(f"加载: {json_file}")
    with open(json_file, "r", encoding="utf-8") as f:
        result = json.load(f)

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

    # 验证并修复
    validator = CitationValidator()
    validation_result = validator.validate_and_fix(main_content, cited_papers)

    # 格式化参考文献
    references_formatted = validator.format_references_ieee(validation_result.fixed_references)

    # 合并最终内容
    final_content = validation_result.fixed_content + "\n\n## References\n\n" + references_formatted

    # 保存
    output_file = "test_cas_review_final.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    print(f"✓ 已保存: {output_file}")

    # 最终检查
    final_cited = validator._extract_cited_indices(validation_result.fixed_content)
    final_unique = sorted(list(set(final_cited)))

    from collections import Counter
    final_counts = Counter(final_cited)
    max_count = max(final_counts.values()) if final_counts else 0

    print("\n最终检查:")
    print(f"  引用文献: {len(final_unique)} 篇")
    print(f"  最大引用次数: {max_count}")
    print(f"  编号连续: {final_unique == list(range(1, len(final_unique) + 1))}")

    checks = [
        ("规则1", all(1 <= idx <= len(validation_result.fixed_references) for idx in final_unique)),
        ("规则2", len(validation_result.fixed_references) == len(final_unique)),
        ("规则3", final_unique == list(range(1, len(final_unique) + 1))),
        ("规则4", max_count <= 2),
        ("规则5", len(validation_result.fixed_references) == len(final_unique))
    ]

    print("\n5条规范:")
    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")


if __name__ == "__main__":
    main()
