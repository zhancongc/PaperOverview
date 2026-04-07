"""
引用拆分服务
当同一处引用超过3篇文献时，自动拆分为结构化表述
避免[1-5]式的笼统堆砌

DEPRECATED: 此模块为 v5.x 旧版本遗留代码，当前 v6.0 流程已不再使用。
保留仅用于历史参考，新代码请使用 PaperSearchAgent + SmartReviewGeneratorFinal。
"""
import warnings
warnings.warn(
    "citation_splitter 模块已废弃，v6.0 流程不再使用",
    DeprecationWarning,
    stacklevel=2
)
import re
import os
from typing import List, Dict, Tuple, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class CitationSplitter:
    """引用拆分器"""

    # 检测连续引用的正则表达式
    # 匹配 [1-5] 或 [1][2][3][4][5] 或 [1,2,3,4,5] 等格式
    CONTINUOUS_CITATION_PATTERN = re.compile(
        r'\[(\d+)(?:[-–—]\s*(\d+)|\s*,\s*\d+\s*(?:,\s*\d+\s*){2,}|(?:\]\s*\[\d+\]\s*){2,})\]'
    )

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    def detect_continuous_citations(self, text: str) -> List[Dict]:
        """
        检测文本中的连续引用

        Args:
            text: 综述文本

        Returns:
            连续引用列表，每个包含：
            - match_str: 匹配的原始字符串
            - start: 起始位置
            - end: 结束位置
            - citation_indices: 引用的文献编号列表
        """
        results = []

        for match in self.CONTINUOUS_CITATION_PATTERN.finditer(text):
            match_str = match.group(0)
            start, end = match.span()

            # 解析引用编号
            indices = self._parse_citation_indices(match_str)

            # 只处理引用数量>3的情况
            if len(indices) > 3:
                results.append({
                    "match_str": match_str,
                    "start": start,
                    "end": end,
                    "citation_indices": indices
                })

        return results

    def _parse_citation_indices(self, citation_str: str) -> List[int]:
        """
        解析引用字符串，提取文献编号

        Args:
            citation_str: 引用字符串，如 [1-5] 或 [1,2,3,4,5]

        Returns:
            文献编号列表
        """
        indices = []

        # 处理 [1-5] 格式
        range_match = re.match(r'\[(\d+)[-–—](\d+)\]', citation_str)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            indices = list(range(start, end + 1))
        else:
            # 处理 [1,2,3,4,5] 或 [1][2][3][4][5] 格式
            numbers = re.findall(r'\d+', citation_str)
            indices = [int(n) for n in numbers]

        return sorted(set(indices))  # 去重并排序

    async def split_citation(
        self,
        text: str,
        papers: List[Dict],
        citation_indices: List[int],
        context: str = ""
    ) -> str:
        """
        拆分连续引用为结构化表述

        Args:
            text: 原始文本段落
            papers: 论文列表
            citation_indices: 引用的文献编号
            context: 上下文信息（主题、章节等）

        Returns:
            拆分后的文本
        """
        if len(citation_indices) <= 3:
            return text  # 不拆分

        # 获取被引用的论文
        cited_papers = []
        for idx in citation_indices:
            if idx <= len(papers):
                cited_papers.append({
                    "index": idx,
                    "paper": papers[idx - 1]
                })

        if not cited_papers:
            return text

        # 提取关键信息用于拆分
        paper_summaries = []
        for item in cited_papers:
            paper = item["paper"]
            summary = self._extract_paper_summary(paper, item["index"])
            paper_summaries.append(summary)

        # 使用LLM生成拆分后的表述
        if self.client:
            split_text = await self._split_with_llm(text, paper_summaries, context)
        else:
            split_text = self._split_with_rules(text, paper_summaries)

        return split_text

    def _extract_paper_summary(self, paper: Dict, index: int) -> Dict:
        """
        提取论文关键信息

        Args:
            paper: 论文信息
            index: 引用编号

        Returns:
            论文摘要信息
        """
        # 提取作者（只取第一作者的姓氏）
        authors = paper.get("authors", [])
        first_author = authors[0] if authors else "Unknown"

        # 提取年份
        year = paper.get("year", "Unknown")

        # 提取标题的核心观点（前100字）
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")

        # 尝试提取核心观点（从摘要第一句）
        key_finding = ""
        if abstract:
            sentences = abstract.split("。")
            if sentences:
                key_finding = sentences[0][:100]

        return {
            "index": index,
            "first_author": first_author,
            "year": year,
            "title": title,
            "key_finding": key_finding,
            "full_citation": f"[{index}]"
        }

    async def _split_with_llm(
        self,
        text: str,
        paper_summaries: List[Dict],
        context: str
    ) -> str:
        """
        使用LLM生成拆分后的表述

        Args:
            text: 原始文本
            paper_summaries: 论文摘要列表
            context: 上下文

        Returns:
            拆分后的文本
        """
        # 构建论文信息
        papers_info = "\n".join([
            f"文献{p['index']}: {p['first_author']}等({p['year']}) - {p['title'][:60]}..."
            for p in paper_summaries
        ])

        # 提取引用周围的上下文
        context_start = max(0, text.find("[") - 100)
        context_end = min(len(text), text.find("]") + 100)
        surrounding_context = text[context_start:context_end]

        prompt = f"""请将以下综述中的连续引用拆分为结构化表述。

原始文本片段：
{surrounding_context}

可引用的文献：
{papers_info}

要求：
1. 将连续引用拆分为"A等[x]...；B等[y]则..."的结构化表述
2. 根据作者、年份、研究主题进行分组
3. 保持学术语气和逻辑连贯性
4. 只返回替换后的文本片段，不要有其他内容

示例：
- 原文：多项研究表明该效应显著[1-5]
- 拆分：Zhang等[1]、Wang等[2]发现该效应显著；而Li等[3]则指出...

请返回拆分后的文本片段："""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位学术写作专家，擅长优化综述的引用表述。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 引用分割需要准确理解原文
                max_tokens=500
            )

            split_text = response.choices[0].message.content.strip()

            # 替换原引用
            return self._replace_citation_in_text(text, split_text)

        except Exception as e:
            print(f"[CitationSplitter] LLM拆分失败: {e}，使用规则拆分")
            return self._split_with_rules(text, paper_summaries)

    def _split_with_rules(
        self,
        text: str,
        paper_summaries: List[Dict]
    ) -> str:
        """
        使用规则生成拆分后的表述

        Args:
            text: 原始文本
            paper_summaries: 论文摘要列表

        Returns:
            拆分后的文本
        """
        if len(paper_summaries) <= 3:
            return text

        # 分组策略：按年份或主题分组
        groups = self._group_papers(paper_summaries)

        # 生成分组表述
        group_texts = []
        for group in groups:
            if len(group) == 1:
                p = group[0]
                group_texts.append(f"{p['first_author']}等{p['full_citation']}")
            elif len(group) == 2:
                p1, p2 = group
                group_texts.append(f"{p1['first_author']}等{p1['full_citation']}、{p2['first_author']}等{p2['full_citation']}")
            else:
                # 多篇文献，只列第一作者
                authors = "、".join([f"{p['first_author']}等{p['full_citation']}" for p in group[:3]])
                if len(group) > 3:
                    authors += f"等{len(group)}篇研究"
                group_texts.append(authors)

        # 用分号连接不同组
        split_citation = "；".join(group_texts)

        return self._replace_citation_in_text(text, split_citation)

    def _group_papers(self, paper_summaries: List[Dict]) -> List[List[Dict]]:
        """
        对论文进行分组

        Args:
            paper_summaries: 论文摘要列表

        Returns:
            分组后的论文列表
        """
        # 简单分组策略：按年代分组
        current_year = 2024  # 假设当前年份

        recent_papers = [p for p in paper_summaries if p.get("year", 0) >= current_year - 5]
        older_papers = [p for p in paper_summaries if p.get("year", 0) < current_year - 5]

        groups = []

        if recent_papers:
            groups.append(recent_papers[:2])  # 最近的研究最多2篇
        if older_papers:
            groups.append(older_papers[:3])  # 较早的研究最多3篇

        # 如果还有剩余，添加到最后的组
        all_grouped = sum(groups, [])
        remaining = [p for p in paper_summaries if p not in all_grouped]
        if remaining:
            groups.append(remaining)

        return groups if groups else [paper_summaries]

    def _replace_citation_in_text(self, text: str, replacement: str) -> str:
        """
        在文本中替换引用

        Args:
            text: 原始文本
            replacement: 替换内容

        Returns:
            替换后的文本
        """
        # 找到第一个连续引用
        match = self.CONTINUOUS_CITATION_PATTERN.search(text)
        if match:
            start, end = match.span()
            return text[:start] + replacement + text[end:]

        return text

    async def split_all_citations(
        self,
        text: str,
        papers: List[Dict],
        context: str = ""
    ) -> Tuple[str, List[Dict]]:
        """
        拆分文本中的所有连续引用

        Args:
            text: 综述文本
            papers: 论文列表
            context: 上下文信息

        Returns:
            (拆分后的文本, 拆分记录列表)
        """
        split_records = []

        # 检测所有连续引用
        continuous_citations = self.detect_continuous_citations(text)

        for citation_info in continuous_citations:
            indices = citation_info["citation_indices"]
            original_str = citation_info["match_str"]

            # 拆分引用
            text = await self.split_citation(text, papers, indices, context)

            # 记录拆分
            split_records.append({
                "original": original_str,
                "indices": indices,
                "count": len(indices),
                "split": True
            })

        return text, split_records

    def generate_split_summary(self, split_records: List[Dict]) -> str:
        """
        生成拆分操作摘要

        Args:
            split_records: 拆分记录列表

        Returns:
            摘要字符串
        """
        if not split_records:
            return "未发现需要拆分的连续引用"

        total_citations = sum(r["count"] for r in split_records)
        avg_citations = total_citations / len(split_records) if split_records else 0

        return f"""引用拆分摘要：
- 拆分处数: {len(split_records)}
- 涉及文献: {total_citations}篇次
- 平均每处: {avg_citations:.1f}篇
- 效果: 避免了[1-N]式的笼统堆砌，提高了可读性"""


class StructuredReviewFormatter:
    """结构化综述格式化器"""

    def __init__(self):
        self.splitter = CitationSplitter()

    async def format_review(
        self,
        content: str,
        papers: List[Dict],
        enable_splitting: bool = True
    ) -> Tuple[str, Dict]:
        """
        格式化综述内容（包括引用拆分）

        Args:
            content: 原始综述内容
            papers: 论文列表
            enable_splitting: 是否启用引用拆分

        Returns:
            (格式化后的内容, 格式化统计)
        """
        stats = {
            "original_length": len(content),
            "citations_split": 0,
            "split_details": []
        }

        if enable_splitting:
            # 拆分连续引用
            content, split_records = await self.splitter.split_all_citations(content, papers)

            stats["citations_split"] = len(split_records)
            stats["split_details"] = split_records
            stats["split_summary"] = self.splitter.generate_split_summary(split_records)

        stats["final_length"] = len(content)

        return content, stats

    def format_citation_with_authors(
        self,
        paper: Dict,
        citation_number: int,
        style: str = "chinese"
    ) -> str:
        """
        生成带作者信息的引用

        Args:
            paper: 论文信息
            citation_number: 引用编号
            style: 引用样式 (chinese, western)

        Returns:
            格式化的引用字符串
        """
        authors = paper.get("authors", [])

        if style == "chinese":
            if authors:
                first_author = authors[0]
                if len(authors) > 2:
                    author_text = f"{first_author}等"
                else:
                    author_text = "、".join(authors)
            else:
                author_text = "佚名"

            year = paper.get("year", "")
            if year:
                return f"{author_text}({year})[{citation_number}]"
            else:
                return f"{author_text}[{citation_number}]"

        else:  # western
            if authors:
                if len(authors) == 1:
                    author_text = authors[0]
                elif len(authors) == 2:
                    author_text = f"{authors[0]} & {authors[1]}"
                else:
                    author_text = f"{authors[0]} et al."
            else:
                author_text = "Anonymous"

            year = paper.get("year", "")
            if year:
                return f"{author_text} ({year})[{citation_number}]"
            else:
                return f"{author_text}[{citation_number}]"


# 便捷导出函数
async def split_continuous_citations(
    text: str,
    papers: List[Dict],
    context: str = ""
) -> Tuple[str, List[Dict]]:
    """
    拆分文本中的连续引用

    Args:
        text: 综述文本
        papers: 论文列表
        context: 上下文

    Returns:
        (拆分后的文本, 拆分记录)
    """
    splitter = CitationSplitter()
    return await splitter.split_all_citations(text, papers, context)


def detect_continuous_citations(text: str) -> List[Dict]:
    """
    检测文本中的连续引用

    Args:
        text: 文本

    Returns:
        连续引用列表
    """
    splitter = CitationSplitter()
    return splitter.detect_continuous_citations(text)
