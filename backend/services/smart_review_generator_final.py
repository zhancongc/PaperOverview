#!/usr/bin/env python3
"""
智能综述生成器 - 最终版（完全符合 5 条引用规范）

5条引用规范：
1. ✅ 参考文献列表中没有的文献，正文中禁止引用
2. ✅ 正文引用的文献，参考文献列表中的文献应该是对应的
3. ✅ 正文中引用编号顺序必须是从1开始，依次递增的
4. ✅ 同一个文献禁止引用超过2次
5. ✅ 正文中没有引用的文献，参考文献列表禁止列出
"""
import os
import sys
import json
import asyncio
import time
import re
from typing import List, Dict, Any, Tuple, Set
from collections import Counter
from datetime import datetime
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SmartReviewGeneratorFinal:
    """
    智能综述生成器 - 最终版

    核心特点：
    - 完全符合 5 条引用规范
    - 内置严格的引用验证
    - IEEE 格式参考文献
    """

    def __init__(
        self,
        deepseek_api_key: str,
        semantic_scholar_api_key: str = None,
        deepseek_base_url: str = "https://api.deepseek.com"
    ):
        self.llm_client = AsyncOpenAI(
            api_key=deepseek_api_key,
            base_url=deepseek_base_url
        )
        self.semantic_scholar_api_key = semantic_scholar_api_key

    async def generate_review_from_papers(
        self,
        topic: str,
        papers: List[Dict],
        model: str = "deepseek-reasoner",
        search_params: Dict[str, Any] = None,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """
        从论文列表生成综述（主要入口）

        Args:
            topic: 研究主题
            papers: 论文列表
            model: 模型名称
            search_params: 搜索和筛选参数，用于生成方法论说明
                {
                    "search_years": 搜索年份范围（默认10年）,
                    "target_count": 目标文献数量（默认50篇）,
                    "recent_years_ratio": 近5年文献占比要求（默认0.5）,
                    "english_ratio": 英文文献占比要求（默认0.3）,
                    "search_platform": 搜索平台（默认"Semantic Scholar"）,
                    "sort_by": 排序方式（默认"citationCount:desc"）
                }
        """
        logger.debug("=" * 80)
        logger.debug("智能综述生成器 - 最终版")
        logger.debug(f"主题: {topic}")
        logger.debug("=" * 80)

        start_time = time.time()

        # === 步骤 1: 预处理论文 ===
        logger.debug("\n[步骤 1] 预处理论文...")
        papers = self._preprocess_papers(papers)
        logger.debug(f"✓ 清洗后: {len(papers)} 篇")

        # === 步骤 2: 生成综述（初始版）===
        logger.debug("\n[步骤 2] 生成初始综述...")
        raw_content, accessed_paper_indices = await self._generate_raw_review(
            topic=topic,
            papers=papers,
            model=model,
            search_params=search_params,
            total_papers_count=len(papers)
        )

        # === 步骤 3: 提取并排序引用 ===
        logger.debug("\n[步骤 3] 处理引用...")
        cited_sequence = self._extract_cited_indices(raw_content)
        logger.debug(f"  初始引用次数: {len(cited_sequence)}")

        # === 步骤 4: 应用 5 条引用规范 ===
        logger.debug("\n[步骤 4] 应用 5 条引用规范...")
        final_content, final_references = self._apply_citation_rules(
            content=raw_content,
            cited_sequence=cited_sequence,
            all_papers=papers
        )

        # === 步骤 5: 格式化参考文献 (IEEE) ===
        logger.debug("\n[步骤 5] 格式化参考文献 (IEEE)...")
        references_formatted = self._format_references_ieee(final_references)

        # === 步骤 6: 合并最终内容 ===
        final_review = final_content + "\n\n## References\n\n" + references_formatted

        # === 步骤 7: 最终验证 ===
        logger.debug("\n[步骤 7] 最终验证...")
        validation_result = self._final_validation(final_review, final_references)

        if validation_result["valid"]:
            logger.debug("✓ 所有引用规范检查通过！")
        else:
            logger.debug("⚠️  警告: 仍有问题")
            for issue in validation_result["issues"]:
                logger.debug(f"  - {issue}")

        # === 统计 ===
        total_time = time.time() - start_time
        statistics = {
            "total_time_seconds": round(total_time, 2),
            "papers_collected": len(papers),
            "papers_cited": len(final_references),
            "review_length": len(final_review),
            "generated_at": datetime.now().isoformat()
        }

        logger.debug("\n" + "=" * 80)
        logger.debug("生成完成统计")
        logger.debug(f"  - 总耗时: {statistics['total_time_seconds']} 秒")
        logger.debug(f"  - 可用论文: {statistics['papers_collected']} 篇")
        logger.debug(f"  - 引用论文: {statistics['papers_cited']} 篇")
        logger.debug(f"  - 综述长度: {statistics['review_length']} 字符")
        logger.debug("=" * 80)

        return {
            "topic": topic,
            "review": final_review,
            "cited_papers": final_references,
            "statistics": statistics,
            "validation": validation_result
        }

    def _preprocess_papers(self, papers: List[Dict]) -> List[Dict]:
        """预处理论文：去重、补充缺失字段"""
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            title = paper.get("title", "").strip().lower()
            if not title or len(title) < 10:
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)

            paper_clean = paper.copy()
            if "authors" not in paper_clean or not paper_clean["authors"]:
                paper_clean["authors"] = ["佚名"]
            if "year" not in paper_clean or not paper_clean["year"]:
                paper_clean["year"] = "n.d."
            if "abstract" not in paper_clean or paper_clean["abstract"] is None:
                paper_clean["abstract"] = ""

            unique_papers.append(paper_clean)

        unique_papers.sort(
            key=lambda p: p.get("cited_by_count", 0),
            reverse=True
        )

        return unique_papers

    async def _generate_raw_review(
        self,
        topic: str,
        papers: List[Dict],
        model: str,
        search_params: Dict[str, Any] = None,
        total_papers_count: int = 0,
        language: str = "zh"
    ) -> Tuple[str, Set[int]]:
        """生成初始综述（不进行引用映射）"""
        paper_titles_list = self._format_paper_titles_list(papers, language)
        logger.debug(f"[准备] 论文标题列表 ({len(papers)} 篇)")

        system_prompt = self._build_system_prompt(len(papers), language)
        user_message = self._build_user_message(
            topic=topic,
            paper_titles=paper_titles_list,
            paper_count=len(papers),
            search_params=search_params,
            total_papers_count=total_papers_count,
            language=language
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        tools = self._get_tools_definition(len(papers))
        accessed_indices = set()
        content = None
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = await self.llm_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.4,
                max_tokens=64000 if "reasoner" in model else 8192
            )

            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                messages.append(assistant_message)
                tool_responses = []

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if function_name == "get_multiple_paper_details":
                        result = self._get_multiple_paper_details(
                            paper_indices=function_args.get("paper_indices", []),
                            papers=papers
                        )

                        for idx in function_args.get("paper_indices", []):
                            accessed_indices.add(idx)

                        tool_responses.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                messages.extend(tool_responses)
                logger.debug(f"[迭代 {iteration}] 上下文约 {self._estimate_context_tokens(messages)} tokens")

            else:
                messages.append(assistant_message)
                content = assistant_message.content
                logger.debug("[完成] 生成完成")
                break

        if content is None:
            raise Exception("生成失败：LLM 没有返回内容")

        return content, accessed_indices

    def _apply_citation_rules(
        self,
        content: str,
        cited_sequence: List[int],
        all_papers: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """
        应用 5 条引用规范

        返回: (修复后的内容, 最终参考文献列表)
        """
        # === 规则 0: 标准化引用格式 ===
        # 将 [8], [9] 或 [8],[9] 转换为 [8, 9]
        # 匹配 [数字] 后面跟着可选的逗号和空格，然后是 [数字]
        import re
        content = re.sub(r'\[(\d+)\]\s*,\s*\[(\d+)\]', r'[\1, \2]', content)
        # 处理更多连续的引用：[8], [9], [10] -> [8, 9, 10]
        while re.search(r'\[(\d+(?:,\s*\d+)*)\],\s*\[\d+\]', content):
            content = re.sub(r'\[(\d+(?:,\s*\d+)*)\],\s*\[(\d+)\]', r'[\1, \2]', content)

        # === 规则 1 & 2: 只保留有效引用 ===
        max_paper_idx = len(all_papers)

        # === 先确定哪些文献被引用，以及它们的首次出现顺序 ===
        first_occurrence = []
        seen = set()
        for idx in cited_sequence:
            if 1 <= idx <= max_paper_idx and idx not in seen:
                seen.add(idx)
                first_occurrence.append(idx)

        # === 规则 3: 创建映射，按首次出现顺序分配新编号 1, 2, 3... ===
        old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(first_occurrence, 1)}

        logger.debug("[规范] 应用引用映射:")
        for old, new in list(old_to_new.items())[:15]:
            logger.debug(f"  [{old}] -> [{new}]")
        if len(old_to_new) > 15:
            logger.debug(f"  ... 还有 {len(old_to_new) - 15} 个映射")

        # === 替换内容中的引用，并同时应用规则 4（最多 2 次）===
        # 使用全局计数器
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

        # === 规则 5: 只保留被引用的文献 ===
        final_references = []
        for old_idx in first_occurrence:
            if 1 <= old_idx <= len(all_papers):
                final_references.append(all_papers[old_idx - 1])

        logger.debug(f"[规范] 最终参考文献: {len(final_references)} 篇")
        logger.debug(f"[规范] 引用次数统计: {dict(global_counts)}")

        # === 规则 6: 修正正文中声称的论文数量 ===
        content = self._fix_paper_count_claims(content, len(final_references))

        return content, final_references

    def _fix_paper_count_claims(self, content: str, actual_count: int) -> str:
        """
        修正正文中声称的论文数量，使其与最终实际引用数量一致。
        解决"精选出40篇"但实际只有27篇参考文献的不一致问题。
        """

        def replace_count(match):
            prefix = match.group(1)  # "精选" "筛选" 等前缀词
            old_num = int(match.group(2))
            if old_num != actual_count:
                logger.debug(f"[数字校正] '{prefix}{old_num}篇' -> '{prefix}{actual_count}篇' (实际引用数)")
            return f'{prefix}{actual_count}篇'

        # 匹配 "精选出 X 篇" "筛选出了 X 篇" 等
        content = re.sub(
            r'(精选|筛选|选出|保留|纳入|最终选出|最终保留)\s*(?:出\s*|了\s*)?(\d+)\s*篇',
            replace_count,
            content
        )

        # 匹配 "X 篇核心文献" "X 篇相关文献"
        def replace_x_documents(match):
            old_num = int(match.group(1))
            suffix = match.group(2)
            if old_num != actual_count:
                logger.debug(f"[数字校正] '{old_num}篇{suffix}' -> '{actual_count}篇{suffix}'")
            return f'{actual_count}篇{suffix}'

        content = re.sub(
            r'(\d+)\s*篇(核心|相关|重要|关键)文献',
            replace_x_documents,
            content
        )

        return content

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取正文中的所有引用编号（按出现顺序）"""
        pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'
        matches = re.findall(pattern, content)

        all_indices = []
        for match in matches:
            indices = [int(x.strip()) for x in match.split(',')]
            all_indices.extend(indices)

        return all_indices

    def _final_validation(self, content: str, references: List[Dict]) -> Dict:
        """最终验证 5 条规范"""
        issues = []
        valid = True

        cited_sequence = self._extract_cited_indices(content)
        unique_cited = sorted(list(set(cited_sequence)))

        # 规则 1: 只引用列表中有的文献
        max_ref = len(references)
        invalid_refs = [i for i in unique_cited if i < 1 or i > max_ref]
        if invalid_refs:
            issues.append(f"规则1违反: 引用了不存在的文献 {invalid_refs}")
            valid = False

        # 规则 2: 引用与列表对应
        if len(unique_cited) != len(references):
            issues.append(f"规则2违反: 引用数 {len(unique_cited)} != 列表数 {len(references)}")
            valid = False

        # 规则 3: 编号从1开始依次递增
        expected = list(range(1, len(unique_cited) + 1))
        if unique_cited != expected:
            issues.append(f"规则3违反: 编号不连续。期望 {expected[:10]}, 实际 {unique_cited[:10]}")
            valid = False

        # 规则 4: 不超过2次
        from collections import Counter
        counts = Counter(cited_sequence)
        over_cited = {i: c for i, c in counts.items() if c > 2}
        if over_cited:
            issues.append(f"规则4违反: 过度引用 {over_cited}")
            valid = False

        # 规则 5: 只列出被引用的
        if len(references) != len(unique_cited):
            issues.append(f"规则5违反: 未引用的文献在列表中")
            valid = False

        return {"valid": valid, "issues": issues}

    def _format_references_ieee(self, papers: List[Dict]) -> str:
        """格式化 IEEE 参考文献"""
        lines = []

        current_year = datetime.now().year

        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "Unknown Title")
            authors = paper.get("authors", [])
            year = paper.get("year", "n.d.")
            doi = paper.get("doi", "")

            venue = (
                paper.get("venue_name", "") or
                paper.get("venue", "") or
                paper.get("journal", "") or
                ""
            )

            # === DOI/标识符处理 ===
            arxiv_id = self._extract_arxiv_id(paper)
            doi = self._validate_and_clean_doi(doi, arxiv_id, year, current_year, venue)

            author_str = self._format_authors_ieee(authors)

            is_arxiv = "arxiv" in venue.lower() if venue else False
            is_conference = any(
                kw in venue.upper() for kw in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'IEEE', 'ACM']
            ) if venue else False

            if is_arxiv:
                ref_entry = f"[{i}] {author_str}\"{title},\" arXiv preprint"
                if arxiv_id:
                    ref_entry += f", arXiv:{arxiv_id}"
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
                elif arxiv_id:
                    ref_entry += f", arXiv:{arxiv_id}"

            lines.append(ref_entry)

        return "\n\n".join(lines)

    def _validate_and_clean_doi(
        self, doi: str, arxiv_id: str, year, current_year: int, venue: str
    ) -> str:
        """
        验证并清理 DOI：
        1. 非白名单前缀的 DOI 降级（如会议平台自编号 10.52202/...）
        2. 当年/次年的会议论文统一降级为 arXiv（可能尚未正式出版）
        3. 无效格式 DOI 清除
        """
        if not doi:
            return ""

        # DOI 格式基础校验：必须是 10.xxxx/xxxx 格式
        if not re.match(r'^10\.\d{4,}/', doi):
            return ""

        # 白名单前缀：可靠的学术出版商
        TRUSTED_PREFIXES = [
            '10.1109/',   # IEEE
            '10.1145/',   # ACM
            '10.1038/',   # Nature
            '10.1126/',   # Science
            '10.1007/',   # Springer
            '10.1016/',   # Elsevier
            '10.1021/',   # ACS
            '10.1063/',   # AIP
            '10.1080/',   # Taylor & Francis
            '10.1162/',   # MIT Press
            '10.1371/',   # PLOS
            '10.1523/',   # Society for Neuroscience
            '10.48550/',  # arXiv (via DOI)
            '10.18653/',  # ACL
            '10.5555/',   # AAAI
            '10.1609/',   # AAAI
            '10.4204/',   # EPTCS/LIPIcs
            '10.4230/',   # Dagstuhl/LIPIcs
        ]

        is_trusted = any(doi.startswith(prefix) for prefix in TRUSTED_PREFIXES)

        # 非白名单 DOI：回退到 arXiv ID 或清空
        if not is_trusted:
            if arxiv_id:
                logger.debug(f"[DOI过滤] 非白名单DOI '{doi}' -> 回退 arXiv:{arxiv_id}")
                return ""
            else:
                logger.debug(f"[DOI过滤] 非白名单DOI '{doi}' -> 清空")
                return ""

        # 当年或未来年份的会议论文：可能尚未正式出版，降级
        try:
            paper_year = int(year) if year else 0
        except (ValueError, TypeError):
            paper_year = 0

        if paper_year >= current_year:
            conference_keywords = ['CVPR', 'ICCV', 'ECCV', 'NeurIPS', 'ICML', 'ICLR',
                                   'AAAI', 'IJCAI', 'ACL', 'EMNLP', 'CVF']
            venue_upper = venue.upper() if venue else ""
            is_conference_paper = any(kw in venue_upper for kw in conference_keywords)

            if is_conference_paper:
                if arxiv_id:
                    logger.debug(f"[预印本降级] {paper_year}年会议论文 '{title[:40]}...' -> arXiv:{arxiv_id}")
                    return ""
                else:
                    # 有可信 DOI 但可能是预分配的，保留但加警告
                    logger.debug(f"[预印本警告] {paper_year}年会议论文使用DOI '{doi}' (可能尚未正式出版)")

        return doi

    def _extract_arxiv_id(self, paper: Dict) -> str:
        """从论文数据中提取 arXiv ID"""
        # 从 DOI 提取
        doi = paper.get("doi", "")
        if doi and "10.48550/arXiv" in doi:
            match = re.search(r'arXiv\.(\d+\.\d+)', doi)
            if match:
                return match.group(1)

        # 从 externalIds 提取
        ext_ids = paper.get("externalIds", {})
        if ext_ids and ext_ids.get("ArXiv"):
            return ext_ids["ArXiv"]

        # 从 abstract 提取
        abstract = paper.get("abstract", "") or ""
        match = re.search(r'arXiv:(\d+\.\d+)', abstract)
        if match:
            return match.group(1)

        # 从 paperId 判断（Semantic Scholar 的 arXiv ID 格式）
        paper_id = paper.get("id", "") or paper.get("paperId", "")
        if paper_id and re.match(r'^\d{4}\.\d{4,5}$', paper_id):
            return paper_id

        return ""

    def _format_authors_ieee(self, authors: List[str]) -> str:
        """格式化作者（IEEE 格式）"""
        if not authors:
            return ""

        formatted_authors = []
        for author in authors[:3]:
            if isinstance(author, str):
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

    # ========== 辅助方法 ==========

    def _format_paper_titles_list(self, papers: List[Dict], language: str = "zh") -> str:
        if language == "en":
            lines = ["[Reference List]"]
            for i, paper in enumerate(papers, 1):
                title = paper.get("title", "")
                year = paper.get("year", "Unknown")
                authors = paper.get("authors", [])
                first_author = authors[0] if authors else "Unknown"
                et_al = " et al." if len(authors) > 1 else ""
                lines.append(f"{i}. {title} ({year}) - {first_author}{et_al}")
        else:
            lines = ["【参考文献列表】"]
            for i, paper in enumerate(papers, 1):
                title = paper.get("title", "")
                year = paper.get("year", "Unknown")
                authors = paper.get("authors", [])
                first_author = authors[0] if authors else "Unknown"
                lines.append(f"{i}. {title} ({year}) - {first_author}等")
        return "\n".join(lines)

    def _build_system_prompt(self, paper_count: int, language: str = "zh") -> str:
        if language == "en":
            return f"""You are an academic writing expert, currently writing a high-quality literature review.

**Task Process**:
1. First browse the provided paper title list (total {paper_count} papers)
2. **Judge paper relevance**: Only select papers truly relevant to the research topic, do not cite irrelevant papers
3. Design the review structure (introduction, 3-5 main chapters, conclusion)
4. Determine which papers need to be cited (prioritize recent high-relevance papers from the last 5 years), use tools to get detailed information
5. Write the complete review

**【Important】Paper Selection Priority**:
1. **Topic relevance (veto power)**: Only cite papers highly relevant to the research topic, firmly do not cite irrelevant papers
2. **Recency (high priority)**: Among topic-relevant papers, prioritize research published in the last 5 years
3. **Academic impact (reference)**: On the basis of meeting the above conditions, appropriately consider citation counts

**【Important】Citation Rules**:
- Only use [number] format for citations, such as [1], [2, 3]
- Citation number range: [1] to [{paper_count}]
- Get paper details before citing
- Do not fabricate content
- Do not cite the same paper more than twice
- Each paper can only appear once in the reference list

**【Absolutely Prohibited】Literature Laundry List**:
❌ Do not write: "A did this, B did that, C did something else"
❌ Do not simply list literature without analysis
❌ Do not lack critical thinking as the author

**【Must Achieve】Comparative Analysis & Critical Thinking**:
✅ Must add "comparative analysis" paragraphs
✅ Must explain "why choose this rather than that"
✅ Must analyze the **essential differences** of different methods/systems (such as memory management mechanisms, algorithm complexity, architectural design, etc.)
✅ Must point out the **pros and cons** and **applicable scenarios** of different studies
✅ Must demonstrate your **independent judgment** and **critical thinking** as the author

**Writing Paradigm Shift**:
❌ Wrong paradigm: "Maxima provides calculus functionality, SymPy is a Python library, Cadabra2 is for tensor computation"
✅ Correct paradigm: "Although Maxima [1] is implemented based on Lisp and excels at symbolic computation, it does not support modern programming paradigms; SymPy [2], as a Python native library, integrates seamlessly with the scientific computing ecosystem but has limited performance when processing large-scale expressions; Cadabra3 [3] is specifically designed for tensor computation, providing domain-specific abstraction layers that significantly simplify complex operations in general relativity"

**【Important】Table Usage Requirements**:
Must use tables in the following situations:
1. **Horizontal comparison**: When comparing methods, features, results of multiple studies
2. **Vertical comparison**: When showing the development timeline of the same field
3. **Classification summary**: When systematically organizing multiple technologies, algorithms or systems

Table design requirements:
- Use Markdown table format
- Tables should have clear titles (e.g., "Table 1: Comparison of Major Computer Algebra Systems")
- Table column titles should be clear
- Each table must be referenced in the text (e.g., "see Table 1")
- Table content should be concise and focused
- Citations in tables use [1], [2] format

Table content must include:
- **Core differences** of different methods/systems (not just listing features)
- **Pros and cons comparison**
- **Applicable scenarios** analysis
- Performance/efficiency **quantitative comparison** (if data available)

**【Each chapter must include】**:
1. Development timeline of the field
2. Classification of different schools/methods/systems
3. **In-depth comparative analysis paragraphs** (critically analyze pros and cons of different solutions)
4. Your independent judgment and insights

**Language Requirements**:
- Only use English for writing
- Use academic expressions

**Output Requirements**:
- Use Markdown format, main title use ##, first-level section titles use ###, second-level section titles (like 1.1, 2.1) use ####, ensure all numbered headings have corresponding Markdown heading symbols, do not use bold alone instead of headings
- Ensure complete output of all content
- Insert 1-2 comparison tables
- Each main chapter should have a dedicated "Comparative Analysis" subsection
"""
        else:
            return f"""你是学术写作专家，正在撰写一篇高质量的文献综述。

**任务流程**：
1. 先浏览提供的论文标题列表（共 {paper_count} 篇）
2. **判断论文主题相关性**：只选择与研究主题真正相关的论文，不相关的论文不要引用
3. 设计综述的结构（引言、3-5个主体章节、结论）
4. 判断需要引用哪些论文（优先选择近5年的高相关文献），调用工具获取这些论文的详细信息
5. 撰写完整的综述

**【重要】论文选择优先级**：
1. **主题相关性（一票否决）**：只引用与研究主题高度相关的论文，不相关的坚决不引用
2. **时间新近度（高优先级）**：在主题相关的论文中，优先选择近 5 年发表的研究
3. **学术影响力（参考）**：在满足上述条件的基础上，适当考虑被引次数

**【重要】引用规则**：
- 只使用 [数字] 格式引用，如 [1]、[2, 3]
- 引用编号范围：[1] 到 [{paper_count}]
- 先获取论文详情再引用
- 不要编造内容
- 同一篇文献禁止引用超过2次
- 每篇文献在参考文献列表中只能出现一次

**【绝对禁止】文献堆砌（Laundry List）**：
❌ 禁止这样写："A 做了这个，B 做了那个，C 做了其他"
❌ 禁止只罗列文献而不进行分析
❌ 禁止缺乏作者自身的批判性思维

**【必须做到】对比分析与批判性思维**：
✅ 必须增加"对比分析"段落
✅ 必须说明"为什么选这个而不选那个"
✅ 必须分析不同方法/系统的**本质区别**（如内存管理机制、算法复杂度、架构设计等）
✅ 必须指出不同研究的**优缺点**和**适用场景**
✅ 必须体现你作为作者的**独立判断**和**批判性思维**

**写作范式转换**：
❌ 错误范式："Maxima 提供了微积分功能，SymPy 是 Python 库，Cadabra2 用于张量计算"
✅ 正确范式："Maxima [1] 基于 Lisp 实现，擅长符号计算但不支持现代编程范式；SymPy [2] 作为 Python 原生库，与科学计算生态无缝集成，但在处理大规模表达式时性能受限；Cadabra3 [3] 专门针对张量计算设计，提供了领域特定的抽象层，显著简化了广义相对论中的复杂运算"

**【重要】表格使用要求**：
在以下情况下必须使用表格：
1. **横向对比**：当比较多个研究的方法、特点、结果时
2. **纵向对比**：当展示同一领域不同时期的发展脉络时
3. **分类总结**：当需要系统整理多种技术、算法或系统时

表格设计要求：
- 使用 Markdown 表格格式
- 表格要有明确的标题（如 "表1：主要计算机代数系统对比"）
- 表格列标题要清晰
- 每个表格都要在正文中引用（如"见表1"）
- 表格内容要简洁，重点突出
- 表格中的引用使用 [1]、[2] 等格式

表格内容必须包括：
- 不同方法/系统的**核心区别**（不仅仅是罗列功能）
- **优缺点对比**
- **适用场景**分析
- 性能/效率**量化对比**（如有数据）

**【每个章节必须包含】**：
1. 该领域的发展脉络梳理
2. 不同流派/方法/系统的分类
3. **深度对比分析段落**（批判性分析不同方案的优劣）
4. 你的独立判断和见解

**语言要求**：
- 只使用中文撰写
- 使用学术化表达

**输出要求**：
- 使用 Markdown 格式，主标题使用 ##，一级节标题使用 ###，二级节标题（如 1.1、2.1）使用 ####，确保所有层级的编号标题都带有对应的 Markdown 标题符号，不要仅用粗体代替标题
- 确保完整输出所有内容
- 插入 1-2 个对比表格
- 每个主体章节都要有专门的"对比分析"小节
"""

    def _build_user_message(
        self,
        topic: str,
        paper_titles: str,
        paper_count: int,
        search_params: Dict[str, Any] = None,
        total_papers_count: int = 0,
        language: str = "zh"
    ) -> str:
        # 构建方法论描述
        methodology_description = self._build_methodology_description(
            search_params, total_papers_count, paper_count, language
        )

        if language == "en":
            return f"""Please write a literature review on "{topic}".

**【Important】Paper Selection Principles (Must Read)**:
When browsing the following paper list and writing the review, please strictly follow:
1. **Topic relevance (veto power)**: Only cite papers truly relevant to "{topic}", firmly do not cite irrelevant papers
2. **Time priority (high priority)**: Among topic-relevant papers, prioritize research published in the last 5 years
3. **Quality reference**: On the basis of meeting the above conditions, appropriately reference citation counts

{paper_titles}

**【Introduction must include】Literature Search and Screening Methodology**:
At the end of the introduction (or as an independent "2. Literature Search Strategy" subsection), you must add a dedicated paragraph explaining your literature inclusion and exclusion criteria.

**Methodology Description (please organize in your own words, do not copy directly)**:
{methodology_description}

**【Core Requirements】Critical Thinking & Comparative Analysis**:
⚠️  Do not write a laundry list of "A did this, B did that"
⚠️  Must demonstrate your critical thinking as the author
⚠️  Each main chapter must include a "Comparative Analysis" subsection

**Writing Requirements**:
1. First design the review structure, then write the content
2. Before citing papers, must first call get_multiple_paper_details tool to batch get detailed information
3. Ensure each subsection has sufficient citation support
4. **In-depth comparative analysis**: Don't just say "what exists", explain "why choose this rather than that". Analyze the **essential differences** of different methods in architectural design, algorithm complexity, memory management, performance, etc.
5. Point out current research limitations, failure cases, and future directions
6. Ensure complete output of all content, do not truncate midway
7. **Each main chapter must have a dedicated comparative analysis paragraph**

**【Emphasis】Table Requirements**:
- Insert 1-2 comparison tables at appropriate positions
- Table types can be: system comparison, algorithm comparison, method comparison, timeline comparison, etc.
- Tables must include: core differences, pros and cons, applicable scenarios, and other in-depth analysis content
- Each table must have a title and be referenced in the text
- Tables must also mark corresponding literature citations [1], [2], etc.

**【Writing Examples】**:
❌ Do not write: "Maxima provides calculus functionality, SymPy is a Python library, Cadabra2 is used for tensor computation."
✅ Should write: "Although Maxima [5], SymPy [8], and Cadabra2 [6] are all computer algebra systems, their design philosophies and applicable scenarios have essential differences. Maxima is implemented based on Lisp, inheriting the tradition of MACSYMA, and performs excellently in symbolic integration and simplification; SymPy, as a pure Python implementation, although slightly inferior in performance, has become popular in engineering applications due to its seamless integration with modern data science ecosystems; while Cadabra2 adopts domain-specific design and is several times more efficient than general-purpose systems in tensor field theory expression. In high-concurrency scenarios, SymPy's memory management mechanism is more flexible, which explains why it is gradually gaining dominance in industrial applications [8, 23]."

Now please start writing. First design the review structure (outline), then write the complete content according to the structure."""
        else:
            return f"""请撰写关于「{topic}」的文献综述。

**【重要】论文选择原则（必读）**：
在浏览以下论文列表和撰写综述时，请严格遵循：
1. **主题相关性（一票否决）**：只引用与「{topic}」真正相关的论文，不相关的论文坚决不引用
2. **时间优先（高优先级）**：在主题相关的论文中，优先选择近 5 年发表的研究
3. **质量参考**：在满足上述条件的基础上，可适当参考被引次数

{paper_titles}

**【引言部分必须包含】文献检索与筛选方法论**：
在引言的末尾（或者作为独立的"2. 文献检索策略"小节），必须加入一个专门段落，说明你的文献纳入与排除标准（Inclusion/Exclusion Criteria）。

**方法论说明（请用自己的话组织，不要直接复制）**：
{methodology_description}

**【核心要求】批判性思维与对比分析**：
⚠️  不要写成"A做了这个，B做了那个"的文献堆砌
⚠️  必须体现你作为作者的批判性思维
⚠️  每个主体章节都必须包含"对比分析"小节

**写作要求**：
1. 先设计综述结构，再撰写内容
2. 引用论文前，必须先调用 get_multiple_paper_details 工具批量获取详细信息
3. 确保每个小节都有充分的引用支持
4. **深度对比分析**：不要只说"有什么"，要说"为什么选这个而不选那个"。分析不同方法在架构设计、算法复杂度、内存管理、性能表现等方面的**本质区别**
5. 指出当前研究的不足、失败案例和未来方向
6. 确保完整输出所有内容，不要中途截断
7. **每个主体章节都要有专门的对比分析段落**

**【强调】表格要求**：
- 在适当的位置插入 1-2 个对比表格
- 表格类型可以是：系统对比、算法对比、方法对比、时期对比等
- 表格必须包含：核心区别、优缺点、适用场景等深度分析内容
- 每个表格都要有标题，并在正文中引用
- 表格中也要标注相应的文献引用 [1]、[2] 等

**【写作范例】**：
❌ 不要这样写："Maxima 提供了微积分功能，SymPy 是一个 Python 库，Cadabra2 用于张量计算。"
✅ 应该这样写："尽管 Maxima [5]、SymPy [8] 和 Cadabra2 [6] 都是计算机代数系统，但它们的设计哲学和适用场景存在本质差异。Maxima 基于 Lisp 实现，继承了 MACSYMA 的传统，在符号积分和化简方面表现优异；SymPy 作为纯 Python 实现，虽然性能略逊，但与现代数据科学生态系统的无缝集成使其在工程领域更受欢迎；而 Cadabra2 采用领域特定设计，在张量场论中的表达效率是通用系统的数倍。在高并发场景下，SymPy 的内存管理机制更为灵活，这解释了为何它在工业界应用中逐渐占据主导地位 [8, 23]。"

请开始撰写。"""

    def _get_tools_definition(self, paper_count: int) -> List[Dict]:
        return [{
            "type": "function",
            "function": {
                "name": "get_multiple_paper_details",
                "description": f"""批量获取多篇论文的详细信息。

论文索引必须在有效范围内（1-{paper_count}）。
""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paper_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": f"论文索引列表（1-{paper_count}）"
                        }
                    },
                    "required": ["paper_indices"]
                }
            }
        }]

    def _get_multiple_paper_details(self, paper_indices: List[int], papers: List[Dict]) -> Dict:
        results = []
        for paper_index in paper_indices:
            if not 1 <= paper_index <= len(papers):
                results.append({
                    "index": paper_index,
                    "error": f"论文索引 {paper_index} 超出范围"
                })
                continue
            paper = papers[paper_index - 1]
            abstract = paper.get("abstract", "")
            if abstract is None:
                abstract = ""
            results.append({
                "index": paper_index,
                "title": paper.get("title", ""),
                "authors": paper.get("authors", [])[:5],
                "year": paper.get("year"),
                "venue": paper.get("venue_name", ""),
                "abstract": abstract[:2000],
                "cited_by_count": paper.get("cited_by_count", 0)
            })
        return {"papers": results, "count": len(results)}

    def _estimate_context_tokens(self, messages: List[Any]) -> int:
        total_chars = 0
        for msg in messages:
            if hasattr(msg, 'role'):
                role = msg.role or ""
                content = msg.content or ""
                tool_calls = msg.tool_calls if hasattr(msg, 'tool_calls') else None
            else:
                role = msg.get("role", "")
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")
            total_chars += len(role) + len(content) + 20
            if tool_calls:
                for tc in tool_calls:
                    total_chars += len(tc.function.name) + len(tc.function.arguments) + 50
        return total_chars // 3

    def _build_methodology_description(
        self,
        search_params: Dict[str, Any] = None,
        total_papers_count: int = 0,
        cited_papers_count: int = 0,
        language: str = "zh"
    ) -> str:
        """
        构建文献检索与筛选方法论描述

        Args:
            search_params: 搜索参数
            total_papers_count: 初始检索到的文献总数
            cited_papers_count: 最终引用的文献数
            language: 语言 (zh/en)

        Returns:
            方法论描述文本
        """
        if search_params is None:
            search_params = {}

        # 提取参数，提供默认值
        search_years = search_params.get("search_years", 10)
        target_count = search_params.get("target_count", 50)
        recent_years_ratio = search_params.get("recent_years_ratio", 0.5)
        search_platform = search_params.get("search_platform", "Semantic Scholar")
        sort_by = search_params.get("sort_by", "被引量降序" if language == "zh" else "citation count descending")

        # 构建描述
        if language == "en":
            description_parts = []
            description_parts.append("**Literature Search Strategy**:")
            description_parts.append(
                f"This review is based on literature search from the {search_platform} academic database, "
                f"covering publications from the past {search_years} years ({datetime.now().year - search_years}-{datetime.now().year})."
            )

            if total_papers_count > 0:
                description_parts.append(
                    f"The initial search retrieved {total_papers_count} relevant papers, "
                    f"which were screened in multiple rounds after sorting by {sort_by}."
                )

            description_parts.append("**Literature Inclusion Criteria**:")
            description_parts.append(
                "1) Topic relevance (veto power): The review author independently judges whether each paper is highly relevant to the research topic. "
                "Irrelevant literature is not included in the review, which is a prerequisite for literature selection;"
            )
            description_parts.append(
                f"2) Recency (high priority): Among topic-relevant literature, priority is given to research published in the last 5 years (target ratio {int(recent_years_ratio * 100)}%), "
                "to ensure the review reflects the latest academic progress;"
            )
            description_parts.append(
                "3) Quality preference: On the basis of meeting the above conditions, citation counts are appropriately considered "
                "to ensure the review is built upon influential academic achievements."
            )

            if cited_papers_count > 0:
                description_parts.append(
                    f"Through the above screening process, {cited_papers_count} papers were finally selected from the initial literature pool for in-depth analysis and review writing."
                )

            return "\n".join(description_parts)
        else:
            description_parts = []

            description_parts.append("**文献检索策略**：")
            description_parts.append(
                f"本综述基于 {search_platform} 学术数据库进行文献检索，"
                f"检索时间范围为过去 {search_years} 年（{datetime.now().year - search_years}-{datetime.now().year}）。"
            )

            if total_papers_count > 0:
                description_parts.append(
                    f"初始检索获得 {total_papers_count} 篇相关文献，"
                    f"按 {sort_by} 排序后进行多轮筛选。"
                )

            description_parts.append("**文献纳入标准**：")
            description_parts.append(
                "1) 主题相关性（一票否决制）：由本综述作者独立判断论文是否与研究主题高度相关，"
                "不相关文献不纳入综述，这是文献入选的先决条件；"
            )
            description_parts.append(
                f"2) 时间新近度（高优先级）：在主题相关的文献中，优先选择近 5 年发表的研究（目标占比 {int(recent_years_ratio * 100)}%），"
                "以确保综述反映最新学术进展；"
            )
            description_parts.append(
                "3) 质量优选：在满足上述条件的基础上，适当考虑被引次数，"
                "以确保综述建立在有影响力的学术成果基础之上。"
            )

            if cited_papers_count > 0:
                description_parts.append(
                    f"经过上述筛选流程，最终从初始文献池中精选出 {cited_papers_count} 篇文献进行深入分析和综述撰写。"
                )

            return "\n".join(description_parts)
