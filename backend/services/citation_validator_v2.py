#!/usr/bin/env python3
"""
引用规范验证器 v2 - 改进版

解决问题：
1. arXiv 预印本需要显示 arXiv ID
2. 作者为空时不显示"佚名"
3. 处理 Unicode 编码问题（如 K¨okçü -> Kökçü）
4. 确保所有文献都有出处信息
"""
import re
import unicodedata
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


@dataclass
class CitationValidationResult:
    """引用验证结果"""
    valid: bool
    issues: List[str]
    fixed_content: str = None
    fixed_references: List[Dict] = None


class CitationValidatorV2:
    """
    引用规范验证器 v2 - 改进版
    """

    def __init__(self):
        pass

    def validate_and_fix(
        self,
        content: str,
        references: List[Dict]
    ) -> CitationValidationResult:
        """验证并修复引用问题"""
        issues = []

        # 提取正文引用
        cited_indices = self._extract_cited_indices(content)
        unique_cited = sorted(list(set(cited_indices)))

        # 规则检查（简化版，主要用于报告问题）
        max_ref_index = len(references)
        invalid_refs = [i for i in unique_cited if i < 1 or i > max_ref_index]
        if invalid_refs:
            issues.append(f"规则1违反: 正文引用了不存在的文献 {invalid_refs}")

        # 自动修复引用
        fixed_content, fixed_references = self._remap_citations_properly(
            content=content,
            references=references,
            cited_indices=cited_indices
        )

        # 验证修复结果
        fixed_cited = self._extract_cited_indices(fixed_content)
        fixed_unique = sorted(list(set(fixed_cited)))

        final_issues = []
        from collections import Counter
        counts_after = Counter(fixed_cited)
        over_after = {i: c for i, c in counts_after.items() if c > 2}
        if over_after:
            final_issues.append(f"修复后仍有过度引用: {over_after}")

        return CitationValidationResult(
            valid=len(final_issues) == 0,
            issues=issues + final_issues,
            fixed_content=fixed_content,
            fixed_references=fixed_references
        )

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取正文中的所有引用编号"""
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
        """重新映射引用，确保符合所有规则"""
        # 确定首次出现顺序
        first_occurrence_order = []
        seen = set()
        for idx in cited_indices:
            if idx not in seen:
                seen.add(idx)
                first_occurrence_order.append(idx)

        # 创建映射
        old_to_new = {
            old_idx: new_idx
            for new_idx, old_idx in enumerate(first_occurrence_order, 1)
        }

        # 替换引用，同时限制每个最多2次
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

        content = re.sub(r'\[(\d+(?:\s*,\s*\d+)*)\]', replace_citation, content)

        # 只保留被引用的文献
        new_references = []
        for old_idx in first_occurrence_order:
            if 1 <= old_idx <= len(references):
                new_references.append(references[old_idx - 1])

        return content, new_references

    def format_references_ieee_improved(self, papers: List[Dict]) -> str:
        """
        改进版 IEEE 参考文献格式化

        解决的问题：
        1. arXiv 预印本显示 arXiv ID
        2. 作者为空时不显示"佚名"
        3. 修复 Unicode 编码问题
        4. 确保所有文献都有出处
        """
        lines = []

        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "Unknown Title")
            authors = paper.get("authors", [])
            year = paper.get("year", "n.d.")
            doi = paper.get("doi", "")

            # 获取 venue 信息
            venue = (
                paper.get("venue_name", "") or
                paper.get("venue", "") or
                paper.get("journal", "") or
                ""
            )

            # 修复作者名字的 Unicode 问题，并过滤"佚名"
            authors_clean = self._fix_author_unicode(authors)
            authors_filtered = [a for a in authors_clean if a.strip() not in ["佚名", "Anonymous", "unknown"]]

            # 格式化作者（IEEE 格式）
            author_str = self._format_authors_improved(authors_filtered)

            # 判断文献类型
            is_arxiv = venue and "arxiv" in venue.lower()
            arxiv_id = self._extract_arxiv_id(paper, doi)

            is_conference = venue and any(
                kw in venue.upper() for kw in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'IEEE', 'ACM']
            )

            # 构建引用条目
            if is_arxiv:
                ref_entry = f"[{i}] {author_str}\"{title}\""
                if arxiv_id:
                    ref_entry += f", arXiv preprint {arxiv_id}"
                else:
                    ref_entry += ", arXiv preprint"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

            elif is_conference and venue:
                ref_entry = f"[{i}] {author_str}\"{title}\""
                ref_entry += f", in {venue}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

            elif venue:
                ref_entry = f"[{i}] {author_str}\"{title}\""
                ref_entry += f", {venue}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

            else:
                # 没有 venue 时，至少显示 DOI 或年份
                ref_entry = f"[{i}] {author_str}\"{title}\""
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

            lines.append(ref_entry)

        return "\n\n".join(lines)

    def _fix_author_unicode(self, authors: List[str]) -> List[str]:
        """
        修复作者名字的 Unicode 编码问题

        例如：K¨okçü -> Kökçü
        """
        fixed_authors = []
        for author in authors:
            if not isinstance(author, str):
                continue
            # 归一化 Unicode
            author_normalized = unicodedata.normalize('NFC', author)
            # 修复常见的编码问题
            author_fixed = author_normalized.replace('¨o', 'ö').replace('¨u', 'ü').replace('¨a', 'ä')
            author_fixed = author_fixed.replace('K¨okçü', 'Kökçü')
            fixed_authors.append(author_fixed)
        return fixed_authors

    def _format_authors_improved(self, authors: List[str]) -> str:
        """
        改进版作者格式化

        - 作者为空时不显示任何内容
        - 过滤掉"佚名"作者
        - IEEE 格式：最多 3 个作者，超过用 et al.
        """
        if not authors:
            return ""

        formatted_authors = []
        for author in authors[:3]:
            if isinstance(author, str):
                # 过滤掉"佚名"
                if author.strip() in ["佚名", "Anonymous", "unknown", ""]:
                    continue
                formatted_authors.append(author)

        if len(formatted_authors) == 0:
            return ""
        elif len(formatted_authors) == 1:
            return formatted_authors[0] + ", "
        elif len(formatted_authors) == 2:
            return " and ".join(formatted_authors) + ", "
        elif len(formatted_authors) == 3:
            return ", ".join(formatted_authors[:2]) + ", and " + formatted_authors[2] + ", "
        elif len(authors) > 3:
            return ", ".join(formatted_authors) + ", et al., "

        return ""

    def _extract_arxiv_id(self, paper: Dict, doi: str) -> str:
        """
        从论文数据中提取 arXiv ID

        尝试多种方式：
        1. 从 DOI 提取（如 10.48550/arXiv.2208.11946 -> arXiv:2208.11946）
        2. 从 DOI 提取另一种格式（如 10.1016/j.jsc.2023.102276，这种需要看是否有其他线索）
        3. 从 paper ID 提取
        4. 从 abstract 或其他字段查找
        """
        # 从 DOI 提取 - 标准 arXiv DOI 格式
        if doi:
            # 匹配 10.48550/arXiv.2208.11946 格式
            doi_match = re.search(r'10\.48550/(arxiv\.|arXiv:)?(\d+\.\d+)', doi, re.IGNORECASE)
            if doi_match:
                return f"arXiv:{doi_match.group(2)}"

            # 匹配包含 arxiv.org/abs/ 的 DOI
            doi_match2 = re.search(r'(arxiv\.org/abs/|arXiv:)(\d+\.\d+)', doi, re.IGNORECASE)
            if doi_match2:
                return f"arXiv:{doi_match2.group(2)}"

            # 从 DOI 的后缀中尝试提取（如 10.1016/j.jsc.2023.102276 -> 2310.xxxx?）
            # 这种不一定是 arXiv ID，但我们可以试试从其他字段找

        # 从 abstract 中查找 arXiv ID
        abstract = paper.get("abstract", "")
        if abstract:
            abs_match = re.search(r'arXiv:(\d+\.\d+)', abstract, re.IGNORECASE)
            if abs_match:
                return f"arXiv:{abs_match.group(1)}"

        # 从 paper ID 尝试（如果是 arXiv ID 格式）
        paper_id = paper.get("id", "")
        if paper_id and re.match(r'\d+\.\d+', paper_id):
            return f"arXiv:{paper_id}"

        return ""


def validate_citations_v2(
    content: str,
    references: List[Dict]
) -> CitationValidationResult:
    """便捷函数：验证并修复引用（v2）"""
    validator = CitationValidatorV2()
    return validator.validate_and_fix(content, references)
