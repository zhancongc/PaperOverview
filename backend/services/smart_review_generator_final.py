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
        model: str = "deepseek-reasoner"
    ) -> Dict[str, Any]:
        """
        从论文列表生成综述（主要入口）
        """
        print("=" * 80)
        print(f"智能综述生成器 - 最终版")
        print(f"主题: {topic}")
        print("=" * 80)

        start_time = time.time()

        # === 步骤 1: 预处理论文 ===
        print("\n[步骤 1] 预处理论文...")
        papers = self._preprocess_papers(papers)
        print(f"✓ 清洗后: {len(papers)} 篇")

        # === 步骤 2: 生成综述（初始版）===
        print("\n[步骤 2] 生成初始综述...")
        raw_content, accessed_paper_indices = await self._generate_raw_review(
            topic=topic,
            papers=papers,
            model=model
        )

        # === 步骤 3: 提取并排序引用 ===
        print("\n[步骤 3] 处理引用...")
        cited_sequence = self._extract_cited_indices(raw_content)
        print(f"  初始引用次数: {len(cited_sequence)}")

        # === 步骤 4: 应用 5 条引用规范 ===
        print("\n[步骤 4] 应用 5 条引用规范...")
        final_content, final_references = self._apply_citation_rules(
            content=raw_content,
            cited_sequence=cited_sequence,
            all_papers=papers
        )

        # === 步骤 5: 格式化参考文献 (IEEE) ===
        print("\n[步骤 5] 格式化参考文献 (IEEE)...")
        references_formatted = self._format_references_ieee(final_references)

        # === 步骤 6: 合并最终内容 ===
        final_review = final_content + "\n\n## References\n\n" + references_formatted

        # === 步骤 7: 最终验证 ===
        print("\n[步骤 7] 最终验证...")
        validation_result = self._final_validation(final_review, final_references)

        if validation_result["valid"]:
            print("✓ 所有引用规范检查通过！")
        else:
            print("⚠️  警告: 仍有问题")
            for issue in validation_result["issues"]:
                print(f"  - {issue}")

        # === 统计 ===
        total_time = time.time() - start_time
        statistics = {
            "total_time_seconds": round(total_time, 2),
            "papers_collected": len(papers),
            "papers_cited": len(final_references),
            "review_length": len(final_review),
            "generated_at": datetime.now().isoformat()
        }

        print("\n" + "=" * 80)
        print("生成完成统计")
        print(f"  - 总耗时: {statistics['total_time_seconds']} 秒")
        print(f"  - 可用论文: {statistics['papers_collected']} 篇")
        print(f"  - 引用论文: {statistics['papers_cited']} 篇")
        print(f"  - 综述长度: {statistics['review_length']} 字符")
        print("=" * 80)

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
        model: str
    ) -> Tuple[str, Set[int]]:
        """生成初始综述（不进行引用映射）"""
        paper_titles_list = self._format_paper_titles_list(papers)
        print(f"[准备] 论文标题列表 ({len(papers)} 篇)")

        system_prompt = self._build_system_prompt(len(papers))
        user_message = self._build_user_message(topic, paper_titles_list, len(papers))

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
                print(f"[迭代 {iteration}] 上下文约 {self._estimate_context_tokens(messages)} tokens")

            else:
                messages.append(assistant_message)
                content = assistant_message.content
                print(f"[完成] 生成完成")
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

        print(f"[规范] 应用引用映射:")
        for old, new in list(old_to_new.items())[:15]:
            print(f"  [{old}] -> [{new}]")
        if len(old_to_new) > 15:
            print(f"  ... 还有 {len(old_to_new) - 15} 个映射")

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

        print(f"[规范] 最终参考文献: {len(final_references)} 篇")
        print(f"[规范] 引用次数统计: {dict(global_counts)}")

        return content, final_references

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

            author_str = self._format_authors_ieee(authors)

            is_arxiv = "arxiv" in venue.lower() if venue else False
            is_conference = any(
                kw in venue.upper() for kw in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'IEEE', 'ACM']
            ) if venue else False

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

    def _format_paper_titles_list(self, papers: List[Dict]) -> str:
        lines = ["【参考文献列表】"]
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            year = paper.get("year", "Unknown")
            authors = paper.get("authors", [])
            first_author = authors[0] if authors else "Unknown"
            lines.append(f"{i}. {title} ({year}) - {first_author}等")
        return "\n".join(lines)

    def _build_system_prompt(self, paper_count: int) -> str:
        return f"""你是学术写作专家，正在撰写一篇高质量的文献综述。

**任务流程**：
1. 先浏览提供的论文标题列表（共 {paper_count} 篇）
2. 设计综述的结构（引言、3-5个主体章节、结论）
3. 判断需要引用哪些论文，调用工具获取这些论文的详细信息
4. 撰写完整的综述

**【重要】引用规则**：
- 只使用 [数字] 格式引用，如 [1]、[2, 3]
- 引用编号范围：[1] 到 [{paper_count}]
- 先获取论文详情再引用
- 不要编造内容

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

表格内容可以包括：
- 不同算法的性能对比
- 不同系统的功能特性对比
- 不同研究的方法、结果对比
- 不同时期的技术发展总结

**语言要求**：
- 只使用中文撰写
- 使用学术化表达

**输出要求**：
- 使用 Markdown 格式，标题使用 ## 或 ###
- 确保完整输出所有内容
- 至少包含 1-2 个对比表格
"""

    def _build_user_message(self, topic: str, paper_titles: str, paper_count: int) -> str:
        return f"""请撰写关于「{topic}」的文献综述。

{paper_titles}

**写作要求**：
1. 先设计综述结构，再撰写内容
2. 引用论文前，必须先调用 get_multiple_paper_details 工具批量获取详细信息
3. 确保每个小节都有充分的引用支持
4. 使用对比分析，指出不同研究的观点和差异
5. 指出当前研究的不足和未来方向
6. 确保完整输出所有内容，不要中途截断

**【强调】表格要求**：
- 在适当的位置插入 1-3 个对比表格
- 表格类型可以是：系统对比、算法对比、方法对比、时期对比等
- 每个表格都要有标题，并在正文中引用
- 表格中也要标注相应的文献引用 [1]、[2] 等

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
