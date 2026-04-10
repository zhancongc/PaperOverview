"""
多格式引用格式化服务

支持：IEEE, APA, MLA, GB/T 7714
"""
import re
from typing import List, Dict
from enum import Enum
from datetime import datetime


class CitationFormat(Enum):
    """引用格式枚举"""
    IEEE = "ieee"
    APA = "apa"
    MLA = "mla"
    GB_T_7714 = "gb_t_7714"


class CitationFormatter:
    """
    引用格式化器

    支持多种学术引用格式的转换和生成
    """

    def __init__(self):
        self.current_year = datetime.now().year

    def format_references(
        self,
        papers: List[Dict],
        format: CitationFormat = CitationFormat.IEEE
    ) -> str:
        """
        格式化参考文献列表

        Args:
            papers: 论文列表
            format: 引用格式

        Returns:
            格式化后的参考文献字符串
        """
        if format == CitationFormat.IEEE:
            return self._format_ieee(papers)
        elif format == CitationFormat.APA:
            return self._format_apa(papers)
        elif format == CitationFormat.MLA:
            return self._format_mla(papers)
        elif format == CitationFormat.GB_T_7714:
            return self._format_gb_t_7714(papers)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_ieee(self, papers: List[Dict]) -> str:
        """
        IEEE 格式

        格式：Author(s), "Title," in Venue, Year.
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

            # 提取 arXiv ID
            arxiv_id = self._extract_arxiv_id(paper, doi)

            # 格式化作者
            author_str = self._format_authors_ieee(authors)

            # 判断文献类型
            is_arxiv = venue and "arxiv" in venue.lower()
            is_conference = venue and any(
                kw in venue.upper() for kw in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'IEEE', 'ACM']
            )

            # 构建引用条目
            if is_arxiv:
                ref_entry = f"[{i}] {author_str}\"{title},\" arXiv preprint"
                if arxiv_id:
                    ref_entry += f" arXiv:{arxiv_id}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

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
                # 没有 venue 时，至少显示 DOI 或年份
                ref_entry = f"[{i}] {author_str}\"{title}\""
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"
                elif arxiv_id:
                    ref_entry += f", arXiv:{arxiv_id}"

            lines.append(ref_entry)

        return "\n\n".join(lines)

    def _format_apa(self, papers: List[Dict]) -> str:
        """
        APA 格式（第7版）

        格式：Author, A. A. (Year). Title. Source. DOI/URL
        """
        lines = []
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", "n.d.")
            venue = paper.get("venue_name", "") or paper.get("venue", "") or paper.get("journal", "")
            doi = paper.get("doi", "")
            url = paper.get("url", "")

            # 格式化作者 (APA: 姓, 名首字母.)
            author_str = self._format_authors_apa(authors)

            # 判断文献类型
            is_arxiv = venue and "arxiv" in venue.lower()
            is_conference = venue and any(
                kw in venue.upper() for kw in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP']
            )

            # 构建引用
            ref_entry = f"{i}. {author_str}({year}). {title}."

            if is_arxiv:
                ref_entry += " arXiv preprint"
                arxiv_id = self._extract_arxiv_id(paper, doi)
                if arxiv_id:
                    ref_entry += f" (arXiv:{arxiv_id})"
            elif is_conference and venue:
                ref_entry += f" In {venue}"
            elif venue:
                ref_entry += f" {venue}"

            # 添加 DOI 或 URL
            if doi:
                ref_entry += f" https://doi.org/{doi}"
            elif url and "arxiv" not in url.lower():
                ref_entry += f" {url}"

            lines.append(ref_entry)

        return "\n".join(lines)

    def _format_mla(self, papers: List[Dict]) -> str:
        """
        MLA 格式（第9版）

        格式：Author. "Title." Source, Date. Location.
        """
        lines = []
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", "")
            venue = paper.get("venue_name", "") or paper.get("venue", "") or paper.get("journal", "")
            doi = paper.get("doi", "")
            url = paper.get("url", "")

            # 格式化作者 (MLA: 名 姓)
            author_str = self._format_authors_mla(authors)

            # 判断文献类型
            is_arxiv = venue and "arxiv" in venue.lower()
            is_conference = venue and any(
                kw in venue.upper() for kw in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP']
            )

            # 构建引用
            ref_entry = f'{i}. {author_str}"{title}."'

            if is_arxiv:
                ref_entry += " arXiv preprint"
                arxiv_id = self._extract_arxiv_id(paper, doi)
                if arxiv_id:
                    ref_entry += f", arXiv {arxiv_id}"
            elif is_conference and venue:
                ref_entry += f" {venue}"
            elif venue:
                ref_entry += f" {venue}"

            # 添加日期
            if year:
                ref_entry += f", {year}"

            # 添加 DOI 或 URL
            if doi:
                ref_entry += f", doi:{doi}"
            elif url and "arxiv" not in url.lower():
                ref_entry += f", {url}"

            lines.append(ref_entry)

        return "\n".join(lines)

    def _format_gb_t_7714(self, papers: List[Dict]) -> str:
        """
        GB/T 7714-2015 格式（中国国家标准）

        格式：作者. 题名[文献类型]. 出版地: 出版者, 年份.
        """
        lines = []
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", "")
            venue = paper.get("venue_name", "") or paper.get("venue", "") or paper.get("journal", "")
            doi = paper.get("doi", "")
            url = paper.get("url", "")

            # 判断文献类型
            doc_type = self._get_document_type_gb(paper)

            # 格式化作者
            author_str = self._format_authors_gb(authors)

            # 构建引用
            ref_entry = f"{i}. {author_str}{title}[{doc_type}]."

            if venue:
                ref_entry += f" {venue}"

            if year:
                ref_entry += f", {year}"

            if doi:
                ref_entry += f". DOI: {doi}"
            elif url and "arxiv" not in url.lower():
                ref_entry += f". {url}"

            lines.append(ref_entry)

        return "\n".join(lines)

    # ==================== 作者格式化辅助方法 ====================

    def _format_authors_ieee(self, authors: List[str]) -> str:
        """IEEE 格式作者：最多 3 个作者，超过用 et al."""
        if not authors:
            return ""

        # 过滤"佚名"等无效作者
        valid_authors = [a for a in authors if a.strip() not in ["佚名", "Anonymous", "unknown", ""]]

        if not valid_authors:
            return ""

        if len(valid_authors) == 1:
            return valid_authors[0] + ", "
        elif len(valid_authors) == 2:
            return " and ".join(valid_authors) + ", "
        elif len(valid_authors) == 3:
            return ", ".join(valid_authors[:2]) + ", and " + valid_authors[2] + ", "
        else:
            return ", ".join(valid_authors[:3]) + ", et al., "

    def _format_authors_apa(self, authors: List[str]) -> str:
        """APA 格式作者：姓, 名首字母. & 名首字母. 姓"""
        if not authors:
            return ""

        valid_authors = [a for a in authors if a.strip() not in ["佚名", "Anonymous", "unknown", ""]]

        if not valid_authors:
            return ""

        formatted = []
        for author in valid_authors[:20]:  # APA 最多列出20个作者
            parts = author.strip().split()
            if len(parts) >= 2:
                last_name = parts[-1]
                initials = " ".join([p[0] + "." for p in parts[:-1]])
                formatted.append(f"{last_name}, {initials}")
            else:
                formatted.append(author)

        if len(formatted) == 1:
            return formatted[0] + " "
        elif len(formatted) == 2:
            return f"{formatted[0]} & {formatted[1]} "
        else:
            return ", ".join(formatted[:-1]) + f", & {formatted[-1]} "

    def _format_authors_mla(self, authors: List[str]) -> str:
        """MLA 格式作者：名 姓"""
        if not authors:
            return ""

        valid_authors = [a for a in authors if a.strip() not in ["佚名", "Anonymous", "unknown", ""]]

        if not valid_authors:
            return ""

        if len(valid_authors) == 1:
            return f"{valid_authors[0]}. "
        elif len(valid_authors) == 2:
            return f"{valid_authors[0]}, and {valid_authors[1]}. "
        else:
            return f"{valid_authors[0]}, et al. "

    def _format_authors_gb(self, authors: List[str]) -> str:
        """GB/T 7714 格式作者：最多列出前3位，超过用"等" """
        if not authors:
            return ""

        valid_authors = [a for a in authors if a.strip() not in ["佚名", "Anonymous", "unknown", ""]]

        if not valid_authors:
            return ""

        if len(valid_authors) <= 3:
            return ", ".join(valid_authors) + ". "
        else:
            return ", ".join(valid_authors[:3]) + ", 等. "

    # ==================== 其他辅助方法 ====================

    def _extract_arxiv_id(self, paper: Dict, doi: str) -> str:
        """
        从论文数据中提取 arXiv ID
        """
        # 从 DOI 提取
        if doi:
            # 匹配 10.48550/arXiv.2208.11946 格式
            doi_match = re.search(r'10\.48550/(arxiv\.|arXiv:)?(\d+\.\d+)', doi, re.IGNORECASE)
            if doi_match:
                return f"{doi_match.group(2)}"

            # 匹配包含 arxiv.org/abs/ 的 DOI
            doi_match2 = re.search(r'(arxiv\.org/abs/|arXiv:)(\d+\.\d+)', doi, re.IGNORECASE)
            if doi_match2:
                return f"{doi_match2.group(2)}"

        # 从 abstract 中查找
        abstract = paper.get("abstract", "")
        if abstract:
            abs_match = re.search(r'arXiv:(\d+\.\d+)', abstract, re.IGNORECASE)
            if abs_match:
                return f"{abs_match.group(1)}"

        # 从 paper ID 判断
        paper_id = paper.get("id", "")
        if paper_id and re.match(r'\d+\.\d+', paper_id):
            return paper_id

        return ""

    def _get_document_type_gb(self, paper: Dict) -> str:
        """
        判断 GB/T 7714 文献类型

        类型标识：
        - M: 专著
        - J: 期刊
        - C: 会议论文
        - D: 学位论文
        - P: 专利
        - S: 标准
        - EB/OL: 电子公告（在线）
        """
        venue = (paper.get("venue_name", "") or
                 paper.get("venue", "") or
                 paper.get("journal", "")).lower()

        # 会议论文
        if any(kw in venue for kw in ['proceedings', 'conference', 'symposium', 'workshop']):
            return "C"

        # 期刊论文（扩大判断范围）
        if any(kw in venue for kw in ['journal', 'transactions', 'letters', 'review', 'science',
                                        'international', 'nature', 'cell', 'science']):
            return "J"

        # arXiv 预印本
        if 'arxiv' in venue:
            return "EB/OL"

        # 如果有 DOI 和年份，很可能是期刊文章
        if paper.get("doi") and paper.get("year") and venue:
            return "J"

        # 默认为期刊（比专著更常见）
        return "J"


def format_references(papers: List[Dict], format: str = "ieee") -> str:
    """
    便捷函数：格式化参考文献

    Args:
        papers: 论文列表
        format: 引用格式 (ieee/apa/mla/gb_t_7714)

    Returns:
        格式化后的参考文献字符串
    """
    formatter = CitationFormatter()

    try:
        format_enum = CitationFormat(format)
        return formatter.format_references(papers, format_enum)
    except ValueError:
        # 不支持的格式，默认使用 IEEE
        return formatter.format_references(papers, CitationFormat.IEEE)
