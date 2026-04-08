#!/usr/bin/env python3
"""
智能综述生成器 v2.1
修复：
1. 参考文献缺失问题
2. 参考文献格式不统一
3. 信息缺失问题
"""
import os
import sys
import json
import asyncio
import time
import re
from typing import List, Dict, Any, Tuple, Set
from datetime import datetime
from openai import AsyncOpenAI

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SmartReviewGeneratorV2:
    """
    智能综述生成器 v2.1

    核心改进：
    - 更严格的引用验证
    - IEEE 格式参考文献
    - 完整性检查
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
        self.collected_papers = []
        self.search_history = []

    async def generate_review_from_papers(
        self,
        topic: str,
        papers: List[Dict],
        model: str = "deepseek-reasoner"
    ) -> Dict[str, Any]:
        """
        从已有论文列表生成综述（主要入口）
        """
        print("=" * 80)
        print(f"智能综述生成器 v2.1 启动")
        print(f"主题: {topic}")
        print("=" * 80)

        start_time = time.time()

        # 预处理论文：去重、清洗
        print("\n[预处理] 清洗论文数据...")
        papers = self._preprocess_papers(papers)
        print(f"✓ 清洗后: {len(papers)} 篇")

        # 生成综述（一体化）
        print("\n[阶段 2] 生成综述（大纲+撰写一体化）")
        print("-" * 80)

        review, cited_papers, outline = await self._write_review_with_outline(
            topic=topic,
            papers=papers,
            model=model
        )

        # === 后处理：修复参考文献 ===
        print("\n[后处理] 修复和完善参考文献...")
        review, cited_papers = await self._fix_references(
            review=review,
            cited_papers=cited_papers,
            all_papers=papers
        )

        # === 最终验证 ===
        print("\n[验证] 最终完整性检查...")
        validation_result = self._final_validation(review, cited_papers, len(papers))
        if not validation_result["valid"]:
            print(f"⚠️  警告: {validation_result['issues']}")

        # === 统计信息 ===
        total_time = time.time() - start_time
        statistics = {
            "total_time_seconds": round(total_time, 2),
            "papers_collected": len(papers),
            "papers_cited": len(cited_papers),
            "search_rounds": len(self.search_history),
            "review_length": len(review),
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
            "outline": outline,
            "papers": papers,
            "review": review,
            "cited_papers": cited_papers,
            "statistics": statistics,
            "search_history": self.search_history
        }

    def _preprocess_papers(self, papers: List[Dict]) -> List[Dict]:
        """预处理论文：去重、补充缺失字段"""
        # 去重
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            title = paper.get("title", "").strip().lower()
            if not title or len(title) < 10:
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)

            # 补充缺失字段
            paper_clean = paper.copy()
            if "authors" not in paper_clean or not paper_clean["authors"]:
                paper_clean["authors"] = ["佚名"]
            if "year" not in paper_clean or not paper_clean["year"]:
                paper_clean["year"] = "n.d."
            if "abstract" not in paper_clean:
                paper_clean["abstract"] = ""
            if paper_clean["abstract"] is None:
                paper_clean["abstract"] = ""

            unique_papers.append(paper_clean)

        # 按被引量排序
        unique_papers.sort(
            key=lambda p: p.get("cited_by_count", 0),
            reverse=True
        )

        return unique_papers

    async def _write_review_with_outline(
        self,
        topic: str,
        papers: List[Dict],
        model: str
    ) -> Tuple[str, List[Dict], Dict]:
        """
        大纲设计与综述撰写一体化（修复版）
        """
        # 准备论文标题列表
        paper_titles_list = self._format_paper_titles_list(papers)
        print(f"[准备] 论文标题列表 ({len(papers)} 篇)")

        # 构建系统提示（强调引用正确性）
        system_prompt = self._build_combined_system_prompt_v2(
            paper_count=len(papers),
            target_citation_count=min(80, len(papers))
        )

        # 构建用户消息
        user_message = self._build_combined_user_message_v2(
            topic=topic,
            paper_titles=paper_titles_list,
            paper_count=len(papers),
            target_citation_count=min(80, len(papers))
        )

        # 记录工具调用情况
        tool_calls_log = []
        accessed_papers = {}
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        max_iterations = 10
        iteration = 0
        content = None
        tools = self._get_tools_definition(len(papers))

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

                        for paper_index in function_args.get("paper_indices", []):
                            if 1 <= paper_index <= len(papers):
                                accessed_papers[paper_index] = papers[paper_index - 1]

                        tool_responses.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                        tool_calls_log.append({
                            "iteration": iteration,
                            "function": function_name,
                            "args": function_args
                        })

                    elif function_name == "search_papers_by_keyword":
                        result = self._search_papers_local(
                            keyword=function_args.get("keyword"),
                            papers=papers
                        )

                        tool_responses.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                        tool_calls_log.append({
                            "iteration": iteration,
                            "function": function_name,
                            "args": function_args
                        })

                messages.extend(tool_responses)
                print(f"[迭代 {iteration}] 上下文约 {self._estimate_context_tokens(messages)} tokens")

            else:
                messages.append(assistant_message)
                content = assistant_message.content
                print(f"[完成] 生成完成，原因: {response.choices[0].finish_reason}")
                break

        if content is None:
            print("[错误] 生成失败：LLM 没有返回任何内容")
            return "", [], {}

        # 后处理：严格的引用验证
        content, cited_indices, fix_logs = self._validate_and_fix_citations_v2(content, len(papers))

        if fix_logs:
            print(f"[引用修正] 修复了 {len(fix_logs)} 处问题")

        # 提取引用的论文
        cited_papers = []
        for idx in cited_indices:
            if 1 <= idx <= len(papers):
                cited_papers.append(papers[idx - 1])

        # 限制同一文献引用次数（最多2次）
        content, cited_indices = self._limit_duplicate_citations_v2(content, cited_indices)

        # 重新映射引用编号，使其连续
        content, cited_papers = self._remap_citations_v2(content, cited_indices, papers)

        # 生成 IEEE 格式参考文献
        references = self._format_references_ieee(cited_papers)

        # 添加标题和参考文献
        final_content = f"# {topic}\n\n{content}\n\n## References\n\n{references}"

        print(f"[综述生成] 工具调用: {len(tool_calls_log)}次, 访问论文: {len(accessed_papers)}篇")

        # 提取大纲
        outline = self._extract_outline_from_content(final_content)

        return final_content, cited_papers, outline

    async def _fix_references(
        self,
        review: str,
        cited_papers: List[Dict],
        all_papers: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """
        修复参考文献问题
        """
        # 检查是否有缺失的引用
        cited_indices = self._extract_cited_indices(review)

        # 验证每个引用的论文是否有足够信息
        missing_info = []
        for i, paper in enumerate(cited_papers):
            idx = i + 1
            if not paper.get("title"):
                missing_info.append(f"[{idx}] 缺失标题")
            if not paper.get("year") or paper.get("year") == "n.d.":
                missing_info.append(f"[{idx}] 缺失年份")

        if missing_info:
            print(f"⚠️  发现 {len(missing_info)} 条参考文献信息缺失")

        return review, cited_papers

    def _validate_and_fix_citations_v2(self, content: str, paper_count: int) -> Tuple[str, List[int], List[str]]:
        """
        严格验证并修正引用（v2）
        """
        fix_logs = []

        # 查找所有引用模式
        citation_pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'

        def replace_citation(match):
            citation_str = match.group(1)
            cited_nums = [int(n.strip()) for n in citation_str.split(',')]

            # 过滤出有效的引用编号
            valid_nums = [n for n in cited_nums if 1 <= n <= paper_count]
            invalid_nums = [n for n in cited_nums if n > paper_count or n < 1]

            if invalid_nums:
                original = f'[{citation_str}]'
                if valid_nums:
                    replacement = f'[{", ".join(map(str, valid_nums))}]'
                    fix_logs.append(f'修正引用: {original} -> {replacement} (移除无效引用 {invalid_nums})')
                    return replacement
                else:
                    fix_logs.append(f'移除无效引用: {original} (全部超出范围 {invalid_nums})')
                    return ''

            return match.group(0)

        # 应用修正
        fixed_content = re.sub(citation_pattern, replace_citation, content)

        # 提取修正后的有效引用
        cited_indices = self._extract_cited_indices(fixed_content)

        if fix_logs:
            print(f'\n[引用验证] 发现并修正 {len(fix_logs)} 处引用问题:')
            for log in fix_logs[:10]:
                print(f'  - {log}')
            if len(fix_logs) > 10:
                print(f'  - ... 还有 {len(fix_logs) - 10} 处修正')
        else:
            print(f'\n[引用验证] ✓ 所有引用均在有效范围内 [1-{paper_count}]')

        return fixed_content, cited_indices, fix_logs

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取内容中的引用索引"""
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, content)
        indices = [int(m) for m in matches]
        return sorted(list(set(indices)))

    def _limit_duplicate_citations_v2(self, content: str, cited_indices: List[int]) -> Tuple[str, List[int]]:
        """限制同一文献的引用次数（最多2次）"""
        # 统计每个文献的引用次数
        citation_counts = {}
        citation_matches = []

        for match in re.finditer(r'\[(\d+(?:\s*,\s*\d+)*)\]', content):
            citation_str = match.group(1)
            start_pos = match.start()
            end_pos = match.end()
            cited_nums = [int(n.strip()) for n in citation_str.split(',')]
            citation_matches.append({
                'start': start_pos,
                'end': end_pos,
                'nums': cited_nums,
                'original': match.group(0)
            })
            for num in cited_nums:
                citation_counts[num] = citation_counts.get(num, 0) + 1

        over_cited = {num: count for num, count in citation_counts.items() if count > 2}

        if over_cited:
            print(f"\n[引用规范检查] 发现过度引用的文献:")
            for num, count in sorted(over_cited.items()):
                print(f"  - 文献 [{num}] 被引用 {count} 次 (超过限制 2 次)")

            # 从后往前处理，避免位置偏移
            removed_count = {num: 0 for num in over_cited.keys()}
            for match in reversed(citation_matches):
                nums_to_remove = []
                for num in match['nums']:
                    if num in over_cited:
                        need_remove = citation_counts[num] - 2 - removed_count[num]
                        if need_remove > 0:
                            nums_to_remove.append(num)
                            removed_count[num] += 1

                if nums_to_remove:
                    remaining_nums = [n for n in match['nums'] if n not in nums_to_remove]
                    if remaining_nums:
                        new_citation = f'[{", ".join(map(str, remaining_nums))}]'
                        content = content[:match['start']] + new_citation + content[match['end']:]
                    else:
                        content = content[:match['start']] + content[match['end']:]

            total_removed = sum(removed_count.values())
            print(f"[引用规范检查] 已删除 {total_removed} 个重复引用")

        cited_indices = list(set(cited_indices))
        cited_indices.sort()
        return content, cited_indices

    def _remap_citations_v2(self, content: str, cited_indices: List[int], papers: List[Dict]) -> Tuple[str, List[Dict]]:
        """重新映射引用编号，使其连续从 1 开始"""
        if not cited_indices:
            return content, []

        old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(cited_indices, 1)}

        print(f"\n[引用重映射] 原始编号 -> 新编号")
        for old_idx, new_idx in list(old_to_new.items())[:20]:
            print(f"  [{old_idx}] -> [{new_idx}]")
        if len(old_to_new) > 20:
            print(f"  ... 还有 {len(old_to_new) - 20} 个映射")

        def replace_citation(match):
            citation_str = match.group(1)
            cited_nums = [int(n.strip()) for n in citation_str.split(',')]
            new_nums = [old_to_new.get(n, n) for n in cited_nums if n in old_to_new]
            if new_nums:
                return f'[{", ".join(map(str, new_nums))}]'
            return match.group(0)

        citation_pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'
        remapped_content = re.sub(citation_pattern, replace_citation, content)

        cited_papers = []
        for idx in cited_indices:
            if 1 <= idx <= len(papers):
                cited_papers.append(papers[idx - 1])

        print(f"[引用重映射] 引用文献: {len(cited_papers)} 篇，编号范围: [1-{len(cited_papers)}]")
        return remapped_content, cited_papers

    def _format_references_ieee(self, papers: List[Dict]) -> str:
        """
        格式化参考文献（IEEE 格式）

        IEEE 格式示例:
        [1] J. K. Author, "Title of paper," Name of Journal, vol. x, no. x, pp. xxx-xxx, Abbreviated Month Year.
        [2] J. K. Author, "Title of paper," in Abbreviated Name of Conf., vol. x, no. x, pp. xxx-xxx, Abbreviated Month Year.
        [3] J. K. Author, Title of Book. Publisher, Year.
        """
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
                paper.get("conference", "") or
                ""
            )

            # 格式化作者（IEEE 格式：首字母缩写 + 姓）
            author_str = self._format_authors_ieee(authors)

            # 判断文献类型
            is_arxiv = "arxiv" in venue.lower() if venue else False
            is_conference = any(kw in venue.upper() for kw in ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'IEEE', 'ACM']) if venue else False

            if is_arxiv:
                # arXiv 预印本
                ref_entry = f"[{i}] {author_str}\"{title},\" arXiv preprint"
                if doi:
                    ref_entry += f", {doi}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"

            elif is_conference and venue:
                # 会议论文
                ref_entry = f"[{i}] {author_str}\"{title},\" in {venue}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

            elif venue:
                # 期刊论文或其他
                ref_entry = f"[{i}] {author_str}\"{title},\" {venue}"
                if year and year != "n.d.":
                    ref_entry += f", {year}"
                if doi:
                    ref_entry += f". DOI: {doi}"

            else:
                # 无明确来源
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

        for author in authors[:3]:  # IEEE 通常最多显示 3 个作者
            if isinstance(author, str):
                # 简单格式化：保留原样
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

    def _final_validation(self, content: str, cited_papers: List[Dict], total_papers: int) -> Dict:
        """最终完整性检查"""
        issues = []
        valid = True

        # 检查引用编号连续性
        cited_indices = self._extract_cited_indices(content)
        expected_indices = list(range(1, len(cited_papers) + 1))
        if set(cited_indices) != set(expected_indices):
            missing = set(expected_indices) - set(cited_indices)
            extra = set(cited_indices) - set(expected_indices)
            if missing:
                issues.append(f"缺失引用编号: {sorted(missing)}")
            if extra:
                issues.append(f"多余引用编号: {sorted(extra)}")
            valid = False

        # 检查每个引用的论文是否有基本信息
        for i, paper in enumerate(cited_papers, 1):
            if not paper.get("title"):
                issues.append(f"[{i}] 缺失标题")
            if not paper.get("year") or paper.get("year") == "n.d.":
                issues.append(f"[{i}] 缺失年份")

        # 检查参考文献部分
        if "## References" not in content and "## 参考文献" not in content:
            issues.append("缺失参考文献部分")
            valid = False

        return {"valid": valid, "issues": issues}

    # ========== 辅助方法（复用自 v1）==========

    def _format_paper_titles_list(self, papers: List[Dict]) -> str:
        lines = ["【参考文献列表】"]
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            year = paper.get("year", "Unknown")
            authors = paper.get("authors", [])
            first_author = authors[0] if authors else "Unknown"
            lines.append(f"{i}. {title} ({year}) - {first_author}等")
        return "\n".join(lines)

    def _build_combined_system_prompt_v2(self, paper_count: int, target_citation_count: int) -> str:
        """构建改进的系统提示（强调引用正确性）"""
        return f"""你是学术写作专家，正在撰写一篇高质量的文献综述。

**任务流程**：
1. 先浏览提供的论文标题列表（共 {paper_count} 篇）
2. 设计综述的结构（引言、3-5个主体章节、结论）
3. 判断需要引用哪些论文，调用工具获取这些论文的详细信息
4. 撰写完整的综述

**【致命警告】引用前必须先获取论文详情**
- 你只能看到论文的标题列表
- **绝对禁止**：只根据标题猜测内容就引用
- **必须步骤**：先调用 get_multiple_paper_details 工具获取论文摘要和详情

**最佳实践：批量获取论文详情**
- 一次性判断综述需要引用哪些论文
- 一次性调用 get_multiple_paper_details，传入所有需要引用的论文索引
- 可以一次性获取 20-60 篇论文的详情

**写作要求**：
1. 结构清晰：包含引言、3-5个主体章节、结论
2. 每个重要观点都要有引用支持
3. 使用对比分析，指出不同研究的观点、方法、结论
4. 明确指出研究分歧和不足
5. 指出研究空白和未来方向

**引用要求**（必须严格遵守）：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文
- **近5年文献比例**：至少 50%（当前年份 2026，近5年指 2021-2026）
- **英文文献比例**：至少 80%

**【致命错误】引用编号范围限制**：
- **有效范围**：[1] 到 [{paper_count}]，共 {paper_count} 篇论文
- **严禁超出范围**：不得出现 [{paper_count + 1}]、[{paper_count + 2}] 等超出范围的引用

**【致命错误】引用内容必须准确**：
- **必须先获取详情再引用**：必须先调用 get_multiple_paper_details 获取论文摘要和详情
- **验证内容匹配**：引用前确认论文内容与你描述的一致

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 使用学术化表达

**输出要求**：
- 确保完整输出所有内容，不要中途截断
- 每个章节都要完整撰写
- 使用 Markdown 格式，标题使用 ## 或 ###"""

    def _build_combined_user_message_v2(
        self,
        topic: str,
        paper_titles: str,
        paper_count: int,
        target_citation_count: int
    ) -> str:
        """构建改进的用户消息"""
        return f"""请撰写关于「{topic}」的文献综述。

{paper_titles}

**写作要求**：
1. 先设计综述结构，再撰写内容
2. **引用论文前，必须先调用 get_multiple_paper_details 工具批量获取详细信息**
3. 确保每个小节都有充分的引用支持
4. 使用对比分析，指出不同研究的观点和差异
5. 指出当前研究的不足和未来方向
6. **确保完整输出所有内容，不要中途截断**

**【重要】引用编号范围限制**：
- **有效范围**：[1] 到 [{paper_count}]，共 {paper_count} 篇论文
- **绝对禁止**：出现 [{paper_count + 1}] 或更大的编号

**引用要求**：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文
- **每节引用数量**：每个小节至少需要引用 8-10 篇论文

**工具调用要求**：
- **首先判断综述需要引用哪些论文**
- **一次性调用 get_multiple_paper_details 工具，传入所有需要引用的论文索引**
- **获取足够数量的论文详情后开始撰写**

请开始撰写。"""

    def _get_tools_definition(self, paper_count: int) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_multiple_paper_details",
                    "description": f"""批量获取多篇论文的详细信息，包括：
- 摘要（了解研究内容和结论）
- 作者列表
- 发表年份
- 期刊/会议名称
- 被引次数

**重要：引用论文前，必须先调用此函数获取详细信息**
不能只根据标题引用论文，必须查看论文摘要后再引用。

**最佳实践：一次性获取多篇论文的详细信息**
- 判断综述需要引用哪些论文
- 一次性调用此函数，传入所有需要引用的论文索引
- 可以一次性获取 20-60 篇论文的详情

论文索引必须在有效范围内（1-{paper_count}）。
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "paper_indices": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": f"论文索引列表（1-{paper_count}），例如：[1, 5, 10, 15, 20]"
                            }
                        },
                        "required": ["paper_indices"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_papers_by_keyword",
                    "description": """根据关键词在现有论文列表中搜索相关的论文。
返回包含该关键词的论文索引列表。
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "搜索关键词"
                            }
                        },
                        "required": ["keyword"]
                    }
                }
            }
        ]

    def _get_multiple_paper_details(self, paper_indices: List[int], papers: List[Dict]) -> Dict:
        results = []
        for paper_index in paper_indices:
            if not 1 <= paper_index <= len(papers):
                results.append({
                    "index": paper_index,
                    "error": f"论文索引 {paper_index} 超出范围（1-{len(papers)}）"
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

    def _search_papers_local(self, keyword: str, papers: List[Dict]) -> Dict:
        keyword_lower = keyword.lower()
        matches = []
        for i, paper in enumerate(papers, 1):
            if keyword_lower in paper.get("title", "").lower():
                matches.append({
                    "index": i,
                    "title": paper.get("title", "")
                })
        return {
            "keyword": keyword,
            "count": len(matches),
            "matches": matches[:10]
        }

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

    def _extract_outline_from_content(self, content: str) -> Dict:
        import re
        outline = {"introduction": {"focus": ""}, "body_sections": [], "conclusion": {"focus": ""}}
        lines = content.split("\n")
        for line in lines:
            if line.startswith("## "):
                title = line[3:].strip()
                if "引言" in title or "介绍" in title or "Introduction" in title:
                    outline["introduction"]["focus"] = title
                elif "结论" in title or "总结" in title or "Conclusion" in title:
                    outline["conclusion"]["focus"] = title
                elif "参考文献" not in title and "References" not in title:
                    outline["body_sections"].append({
                        "title": title,
                        "focus": "",
                        "key_points": []
                    })
        return outline


# ============ 便捷函数 ============

async def generate_smart_review_from_papers(
    topic: str,
    papers: List[Dict],
    deepseek_api_key: str,
    model: str = "deepseek-reasoner"
) -> Dict[str, Any]:
    generator = SmartReviewGeneratorV2(deepseek_api_key=deepseek_api_key)
    return await generator.generate_review_from_papers(
        topic=topic,
        papers=papers,
        model=model
    )
