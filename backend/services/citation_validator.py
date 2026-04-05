#!/usr/bin/env python3
"""
引用规范验证器（Citation Validator）

严格执行以下 5 条引用规范：

1. ❌ 参考文献列表中没有的文献，正文中禁止引用
2. ❌ 正文引用的文献，参考文献列表中的文献应该是对应的
3. ❌ 正文中引用编号顺序必须是从1开始，依次递增的
4. ❌ 同一个文献禁止引用超过2次
5. ❌ 正文中没有引用的文献，参考文献列表禁止列出
"""
import re
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


@dataclass
class CitationValidationResult:
    """引用验证结果"""
    valid: bool
    issues: List[str]
    fixed_content: str = None
    fixed_references: List[Dict] = None


class CitationValidator:
    """
    引用规范验证器

    核心功能：
    - 验证 5 条引用规范
    - 自动修复问题
    - 重新映射引用编号
    """

    def __init__(self):
        pass

    def validate_and_fix(
        self,
        content: str,
        references: List[Dict]
    ) -> CitationValidationResult:
        """
        验证并修复引用问题

        Args:
            content: 综述正文（包含引用标记 [1], [2], ...）
            references: 参考文献列表（按顺序排列，[0] 是 [1] 的文献）

        Returns:
            CitationValidationResult
        """
        issues = []

        # === 提取正文引用 ===
        cited_indices = self._extract_cited_indices(content)
        unique_cited = sorted(list(set(cited_indices)))

        print(f"[验证] 正文引用编号: {cited_indices[:20]}")
        if len(cited_indices) > 20:
            print(f"[验证] ... 还有 {len(cited_indices) - 20} 个引用")

        # === 规则 1: 参考文献列表中没有的文献，正文中禁止引用 ===
        max_ref_index = len(references)
        invalid_refs = [i for i in unique_cited if i < 1 or i > max_ref_index]

        if invalid_refs:
            issues.append(f"规则1违反: 正文引用了不存在的文献 {invalid_refs}")
            print(f"⚠️  规则1违反: 正文引用了不存在的文献 {invalid_refs}")

        # === 规则 2: 正文引用的文献，参考文献列表中的文献应该是对应的 ===
        # (这条由规则1保证，同时也检查引用的文献有基本信息)
        missing_info = []
        for idx in unique_cited:
            if 1 <= idx <= max_ref_index:
                paper = references[idx - 1]
                if not paper.get("title"):
                    missing_info.append(f"[{idx}] 缺失标题")
                if not paper.get("year"):
                    missing_info.append(f"[{idx}] 缺失年份")

        if missing_info:
            issues.append(f"规则2警告: 参考文献信息缺失: {missing_info[:5]}")
            if len(missing_info) > 5:
                issues[-1] += f" ... 还有 {len(missing_info) - 5} 个"

        # === 规则 3: 正文中引用编号顺序必须是从1开始，依次递增的 ===
        # 检查首次出现顺序
        first_occurrence = []
        seen = set()
        for idx in cited_indices:
            if idx not in seen:
                seen.add(idx)
                first_occurrence.append(idx)

        expected_order = sorted(unique_cited)
        if first_occurrence != expected_order:
            issues.append(f"规则3违反: 首次出现顺序不对。期望: {expected_order[:10]}, 实际: {first_occurrence[:10]}")
            print(f"⚠️  规则3违反: 首次出现顺序不对")
            print(f"    期望: {expected_order[:15]}")
            print(f"    实际: {first_occurrence[:15]}")

        # === 规则 4: 同一个文献禁止引用超过2次 ===
        from collections import Counter
        cite_counts = Counter(cited_indices)
        over_cited = {idx: cnt for idx, cnt in cite_counts.items() if cnt > 2}

        if over_cited:
            issues.append(f"规则4违反: 过度引用的文献 {dict(over_cited)}")
            print(f"⚠️  规则4违反: 过度引用的文献:")
            for idx, cnt in sorted(over_cited.items()):
                print(f"    [{idx}] 被引用 {cnt} 次")

        # === 规则 5: 正文中没有引用的文献，参考文献列表禁止列出 ===
        unused_refs = [i + 1 for i in range(len(references)) if (i + 1) not in unique_cited]

        if unused_refs:
            issues.append(f"规则5违反: 未引用的文献 {unused_refs[:10]}")
            if len(unused_refs) > 10:
                issues[-1] += f" ... 还有 {len(unused_refs) - 10} 个"
            print(f"⚠️  规则5违反: 未引用的文献数量: {len(unused_refs)}")

        # === 自动修复 ===
        print("\n[修复] 开始自动修复...")

        # 修复：按引用顺序重新映射
        fixed_content, fixed_references = self._remap_citations_properly(
            content=content,
            references=references,
            cited_indices=cited_indices
        )

        # 验证修复结果
        print("[验证] 检查修复结果...")
        fixed_cited = self._extract_cited_indices(fixed_content)
        fixed_unique = sorted(list(set(fixed_cited)))

        # 检查修复后的规则
        final_issues = []

        # 规则1: 都在范围内
        max_fixed = len(fixed_references)
        invalid_after = [i for i in fixed_unique if i < 1 or i > max_fixed]
        if invalid_after:
            final_issues.append(f"修复后仍有无效引用: {invalid_after}")

        # 规则3: 顺序正确
        first_after = []
        seen_after = set()
        for idx in fixed_cited:
            if idx not in seen_after:
                seen_after.add(idx)
                first_after.append(idx)

        expected_after = sorted(fixed_unique)
        if first_after != expected_after:
            final_issues.append(f"修复后顺序仍不对: 期望 {expected_after}, 实际 {first_after}")

        # 规则4: 不超过2次
        from collections import Counter
        counts_after = Counter(fixed_cited)
        over_after = {i: c for i, c in counts_after.items() if c > 2}
        if over_after:
            final_issues.append(f"修复后仍有过度引用: {over_after}")

        # 规则5: 都被引用
        unused_after = [i + 1 for i in range(len(fixed_references)) if (i + 1) not in fixed_unique]
        if unused_after:
            final_issues.append(f"修复后仍有未引用文献: {unused_after}")

        if final_issues:
            print(f"⚠️  修复后仍有问题: {final_issues}")
        else:
            print("✓ 所有引用规范已满足")

        return CitationValidationResult(
            valid=len(final_issues) == 0,
            issues=issues + final_issues,
            fixed_content=fixed_content,
            fixed_references=fixed_references
        )

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取正文中的所有引用编号"""
        # 匹配 [1], [1,2], [1, 2, 3] 等格式
        pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'
        matches = re.findall(pattern, content)

        all_indices = []
        for match in matches:
            indices = [int(x.strip()) for x in match.split(',')]
            all_indices.extend(indices)

        return all_indices

    def _remap_citations_properly(
        self,
        content: str,
        references: List[Dict],
        cited_indices: List[int]
    ) -> Tuple[str, List[Dict]]:
        """
        正确重新映射引用，确保符合所有5条规则

        步骤：
        1. 确定首次出现顺序
        2. 按首次出现顺序分配新编号（1, 2, 3...）
        3. 替换引用并限制每个文献最多2次（全局计数）
        4. 只保留被引用的文献
        """
        # === 步骤1: 确定首次出现顺序 ===
        first_occurrence_order = []
        seen = set()
        for idx in cited_indices:
            if idx not in seen:
                seen.add(idx)
                first_occurrence_order.append(idx)

        # === 步骤2: 创建映射：旧编号 -> 新编号 ===
        # 新编号按首次出现顺序分配（1, 2, 3...）
        old_to_new = {
            old_idx: new_idx
            for new_idx, old_idx in enumerate(first_occurrence_order, 1)
        }

        print(f"[修复] 引用映射:")
        for old, new in list(old_to_new.items())[:15]:
            print(f"  [{old}] -> [{new}]")
        if len(old_to_new) > 15:
            print(f"  ... 还有 {len(old_to_new) - 15} 个映射")

        # === 步骤3: 替换正文中的引用，同时应用规则4（最多2次） ===
        from collections import Counter
        global_counts = Counter()

        def replace_citation(match):
            citation_str = match.group(1)
            old_indices = [int(x.strip()) for x in citation_str.split(',')]

            new_indices = []
            for old_idx in old_indices:
                if old_idx in old_to_new:
                    new_idx = old_to_new[old_idx]
                    if global_counts[new_idx] < 2:
                        new_indices.append(new_idx)
                        global_counts[new_idx] += 1

            if new_indices:
                return f'[{", ".join(map(str, new_indices))}]'
            return ''

        # 使用更精确的模式匹配
        content = re.sub(r'\[(\d+(?:\s*,\s*\d+)*)\]', replace_citation, content)

        print(f"[修复] 引用次数统计: {dict(global_counts)}")

        # === 步骤4: 只保留被引用的文献 ===
        new_references = []
        for old_idx in first_occurrence_order:
            if 1 <= old_idx <= len(references):
                new_references.append(references[old_idx - 1])

        print(f"[修复] 参考文献数量: {len(new_references)} 篇")

        return content, new_references

    def format_references_ieee(self, papers: List[Dict]) -> str:
        """格式化 IEEE 参考文献（严格版）"""
        lines = []

        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "Unknown Title")
            authors = paper.get("authors", [])
            year = paper.get("year", "n.d.")
            doi = paper.get("doi", "")

            # 获取期刊/会议信息
            venue = (
                paper.get("venue_name", "") or
                paper.get("venue", "") or
                paper.get("journal", "") or
                ""
            )

            # 格式化作者（IEEE 格式）
            author_str = self._format_authors_strict(authors)

            # 判断文献类型
            is_arxiv = "arxiv" in venue.lower() if venue else False
            is_conference = any(
                kw in venue.upper() for kw in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'IEEE', 'ACM']
            ) if venue else False

            # 构建引用条目（确保每个字段都有）
            if is_arxiv:
                ref_entry = f"[{i}] {author_str}\"{title},\" arXiv preprint"
                if doi:
                    ref_entry += f", {doi}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
            elif is_conference and venue:
                ref_entry = f"[{i}] {author_str}\"{title},\" in {venue}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"
            elif venue:
                ref_entry = f"[{i}] {author_str}\"{title},\" {venue}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"
            else:
                ref_entry = f"[{i}] {author_str}\"{title}\""
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

            lines.append(ref_entry)

        return "\n\n".join(lines)

    def _format_authors_strict(self, authors: List[str]) -> str:
        """严格格式化作者（IEEE 格式）"""
        if not authors:
            return ""

        formatted_authors = []

        for author in authors[:3]:  # IEEE 最多显示 3 个作者
            if isinstance(author, str):
                # 简单格式化
                formatted_authors.append(author)

        if len(authors) == 1:
            return formatted_authors[0] + ", "
        elif len(authors) == 2:
            return " and ".join(formatted_authors) + ", "
        elif len(authors) == 3:
            return ", ".join(formatted_authors[:2]) + ", and " + formatted_authors[2] + ", "
        elif len(authors) > 3:
            return ", ".join(formatted_authors) + ", et al., "

        return ""


# ============ 便捷函数 ============

def validate_citations(
    content: str,
    references: List[Dict]
) -> CitationValidationResult:
    """便捷函数：验证并修复引用"""
    validator = CitationValidator()
    return validator.validate_and_fix(content, references)
