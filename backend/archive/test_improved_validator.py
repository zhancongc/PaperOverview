#!/usr/bin/env python3
"""
测试改进版引用验证器
解决：
1. arXiv 预印本显示 arXiv ID
2. 作者为空不显示"佚名"
3. Unicode 编码问题
"""
import os
import sys
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.citation_validator_v2 import CitationValidatorV2


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
    validator = CitationValidatorV2()
    validation_result = validator.validate_and_fix(main_content, cited_papers)

    # 使用改进版格式化
    print("\n使用改进版 IEEE 格式化...")
    references_formatted = validator.format_references_ieee_improved(validation_result.fixed_references)

    # 合并最终内容
    final_content = validation_result.fixed_content + "\n\n## References\n\n" + references_formatted

    # 保存
    output_file = "test_cas_review_improved.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    print(f"✓ 已保存: {output_file}")

    # 显示一些改进示例
    print("\n" + "=" * 80)
    print("改进示例")
    print("=" * 80)

    # 查找有问题的文献并展示改进
    for i, paper in enumerate(cited_papers[:15], 1):
        authors = paper.get("authors", [])
        venue = paper.get("venue_name", "") or paper.get("venue", "")
        doi = paper.get("doi", "")

        has_issue = False
        issue_desc = []

        if not authors or len(authors) == 0:
            has_issue = True
            issue_desc.append("作者为空")

        if venue and "arxiv" in venue.lower():
            arxiv_id = validator._extract_arxiv_id(paper, doi)
            if arxiv_id:
                has_issue = True
                issue_desc.append(f"arXiv 论文 (ID: {arxiv_id})")

        # 检查可能的 Unicode 问题
        for author in authors:
            if "¨" in author:
                has_issue = True
                issue_desc.append(f"可能有编码问题: {author}")

        if has_issue:
            print(f"\n[{i}] {paper.get('title', '')[:50]}...")
            print(f"    问题: {', '.join(issue_desc)}")

    print("\n" + "=" * 80)
    print("请查看 test_cas_review_improved.md 查看完整改进结果")
    print("=" * 80)


if __name__ == "__main__":
    main()
