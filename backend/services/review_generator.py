"""
文献综述生成服务
使用 DeepSeek API
"""
import os
from openai import AsyncOpenAI
from typing import List, Dict
from .aminer_paper_detail import enrich_papers


class ReviewGeneratorService:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", aminer_token: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.aminer_token = aminer_token or os.getenv('AMINER_API_TOKEN')

    async def generate_review(
        self,
        topic: str,
        papers: List[Dict],
        model: str = "deepseek-chat"
    ) -> tuple:
        """
        生成文献综述

        Args:
            topic: 论文主题
            papers: 文献列表
            model: 模型名称

        Returns:
            (综述内容, 实际被引用的文献列表)
        """
        # 构建文献引用信息
        papers_info = self._format_papers_for_prompt(papers)

        # 构建提示词
        system_prompt = """你是一位学术写作专家，擅长撰写高质量的文献综述。

请根据提供的文献列表，撰写一篇结构完整、内容深入的文献综述。

综述结构要求：
1. 引言（介绍研究背景和意义）
2. 主体部分（按主题或时间线组织，分析研究进展）
3. 结论（总结现有研究的不足和未来方向）

写作要求（重要）：
- 使用学术化语言
- 每个重要观点、研究结论或数据引用，都必须在句末添加对应的参考文献序号
- 引用格式：[序号]，例如，"这一观点得到了多项研究的支持[1][2][3]"
- **引用顺序要求：必须从[1]开始按顺序引用，不要跳过前面的编号直接引用后面的文献**
- 引用要求：至少引用 50 篇不同的文献，尽量覆盖更多文献，不要只引用少数几篇
- 引用分布：避免重复引用同一篇文献，**每篇文献引用次数严格不超过2次**
- 分析要深入，不能简单罗列
- 字数：3000-5000字

输出格式：Markdown
注意：不要在输出中包含"参考文献"部分或参考文献列表，只需输出正文内容。"""

        user_prompt = f"""请撰写关于"{topic}"的文献综述。

参考文献列表（共{len(papers)}篇）：
{papers_info}

请开始撰写综述："""

        try:
            content = await self._generate_with_citation_validation(
                topic, papers, system_prompt, user_prompt, model
            )

            # 移除 AI 可能已经生成的参考文献部分
            content = self._remove_existing_references(content)

            # 提取正文中实际引用的文献编号
            cited_indices = self._extract_cited_indices(content)
            print(f"[DEBUG] cited_indices: {sorted(cited_indices)[:20]}")

            if cited_indices:
                # 只保留被引用的文献
                cited_papers = [papers[i - 1] for i in cited_indices if i <= len(papers)]
                print(f"[DEBUG] cited_papers count: {len(cited_papers)}")

                # 按照引用在文中首次出现的顺序重新编号
                print(f"[DEBUG] Before renumbering, first citation in content: ", end="")
                import re
                first_match = re.search(r'\[(\d+)\]', content)
                if first_match:
                    print(f"[{first_match.group(1)}]")
                else:
                    print("none")

                content, cited_papers = self._renumber_citations_by_appearance(content, cited_papers, cited_indices)

                first_match = re.search(r'\[(\d+)\]', content)
                print(f"[DEBUG] After renumbering, first citation in content: ", end="")
                if first_match:
                    print(f"[{first_match.group(1)}]")
                else:
                    print("none")

                # 尝试补充论文详情（作者、DOI等）
                if self.aminer_token:
                    try:
                        cited_papers = await enrich_papers(cited_papers, self.aminer_token)
                    except Exception as e:
                        print(f"[ReviewGenerator] 补充论文详情失败: {e}")

                # 过滤掉佚名论文并更新引用编号
                content, cited_papers = self._filter_anonymous_and_renumber(content, cited_papers)

                # 限制每篇文献的引用次数（最多2次）
                print(f"[DEBUG] Limiting citation count to max 2 per paper")
                before_count = len(re.findall(r'\[(\d+)\]', content))
                content = self._limit_citation_count_v2(content, cited_papers, max_count=2)
                after_count = len(re.findall(r'\[(\d+)\]', content))
                print(f"[DEBUG] Citation count: {before_count} -> {after_count}")

                # 排序并合并正文中的连续引用
                content = self._sort_and_merge_citations(content)

                # 重新格式化参考文献
                references = self._format_references(cited_papers)

                full_review = f"{content}\n\n## 参考文献\n\n{references}"

                # 返回综述和实际被引用的文献
                return full_review, cited_papers
            else:
                # 如果没有引用，使用所有文献
                # 尝试补充论文详情
                if self.aminer_token:
                    try:
                        papers = await enrich_papers(papers, self.aminer_token)
                    except Exception as e:
                        print(f"[ReviewGenerator] 补充论文详情失败: {e}")

                references = self._format_references(papers)

                full_review = f"{content}\n\n## 参考文献\n\n{references}"

                return full_review, papers

        except Exception as e:
            print(f"DeepSeek API error: {e}")
            fallback_review = self._generate_fallback_review(topic, papers)
            return fallback_review, papers  # fallback情况下返回所有文献

    def _format_papers_for_prompt(self, papers: List[Dict]) -> str:
        """格式化论文信息用于 Prompt"""
        formatted = []
        for i, paper in enumerate(papers, 1):
            authors = ", ".join(paper.get("authors", [])[:3])
            if len(paper.get("authors", [])) > 3:
                authors += " 等"

            formatted.append(
                f"[{i}] {paper.get('title', '')}\n"
                f"    作者：{authors}\n"
                f"    年份：{paper.get('year', '')}\n"
                f"    被引量：{paper.get('cited_by_count', 0)}\n"
                f"    摘要：{paper.get('abstract', '')[:200]}..."
            )
        return "\n\n".join(formatted)

    async def _generate_with_citation_validation(
        self, topic: str, papers: List[Dict],
        system_prompt: str, user_prompt: str, model: str,
        min_citations: int = 50, max_retries: int = 2
    ) -> str:
        """
        生成综述并验证引用数量，不足则补充

        Args:
            topic: 主题
            papers: 文献列表
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model: 模型名称
            min_citations: 最少引用数量
            max_retries: 最大重试次数

        Returns:
            生成的综述内容
        """
        content = ""

        for attempt in range(max_retries + 1):
            # 首次生成或补充引用
            if attempt == 0:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=6000
                )
                content = response.choices[0].message.content
            else:
                # 补充引用
                content = await self._add_more_citations(
                    content, papers, topic, min_citations, model
                )

            # 检查引用数量
            cited_indices = self._extract_cited_indices(content)
            unique_cited = len(cited_indices)

            print(f"[ReviewGenerator] 尝试 {attempt + 1}: 引用了 {unique_cited} 篇文献")

            if unique_cited >= min_citations:
                print(f"[ReviewGenerator] 引用数量达标: {unique_cited} >= {min_citations}")
                break

        return content

    async def _add_more_citations(
        self, content: str, papers: List[Dict],
        topic: str, target_count: int, model: str
    ) -> str:
        """
        在现有综述基础上补充更多引用

        Args:
            content: 现有综述内容
            papers: 文献列表
            topic: 主题
            target_count: 目标引用数量
            model: 模型名称

        Returns:
            补充引用后的综述内容
        """
        cited_indices = self._extract_cited_indices(content)

        # 找出未引用的文献
        uncited_indices = [i for i in range(1, len(papers) + 1) if i not in cited_indices]

        if not uncited_indices:
            return content

        # 选择要补充的文献（优先选择高质量文献）
        additional_count = min(len(uncited_indices), target_count - len(cited_indices))
        additional_papers = []

        # 按被引量排序，选择高质量文献
        sorted_uncited = sorted(
            uncited_indices,
            key=lambda i: papers[i-1].get('cited_by_count', 0),
            reverse=True
        )[:additional_count * 2]  # 多选一些，让LLM自己挑选

        for idx in sorted_uncited:
            paper = papers[idx - 1]
            authors = ", ".join(paper.get("authors", [])[:3])
            if len(paper.get("authors", [])) > 3:
                authors += " 等"
            additional_papers.append(f"[{idx}] {paper.get('title', '')} - {authors} ({paper.get('year', '')})")

        # 构建补充引用的提示
        supplement_prompt = f"""请在现有综述基础上，补充更多文献引用以达到{target_count}篇的引用要求。

当前已引用 {len(cited_indices)} 篇文献。

可补充的文献（请从中选择合适的文献添加到相关段落）：
{chr(10).join(additional_papers[:30])}

要求：
1. **引用顺序：在现有引用的基础上继续按顺序编号，不要跳号，不要重复使用已使用的编号**
2. 在综述的适当位置添加这些文献的引用
3. 保持原文结构和内容不变，只添加引用标记
4. 每添加一个引用，在相关句子末尾加上 [序号]
5. 请直接输出修改后的完整综述内容，不要解释

当前综述：
{content}
"""

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是学术写作助手，负责在综述中补充文献引用。"},
                    {"role": "user", "content": supplement_prompt}
                ],
                temperature=0.5,
                max_tokens=6000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ReviewGenerator] 补充引用失败: {e}")
            return content

    def _format_references(self, papers: List[Dict]) -> str:
        """
        格式化参考文献列表（国标 GB/T 7714-2015）
        每条参考文献单独一行
        """
        # 过滤掉没有作者的论文（佚名）- 双重检查
        valid_papers = []
        for paper in papers:
            authors_list = paper.get("authors", [])
            if authors_list and authors_list[0] not in ['佚名', '匿名', '未知作者', '']:
                valid_papers.append(paper)
            else:
                print(f"[ReviewGenerator] 跳过无作者论文: {paper.get('title', 'N/A')[:40]}")

        if not valid_papers:
            return "## 参考文献\n\n暂无参考文献"

        references = []
        for i, paper in enumerate(valid_papers, 1):
            references.append(self._format_single_reference(paper, i))

        return "\n\n".join(references)

    def _format_single_reference(self, paper: Dict, index: int) -> str:
        """格式化单条参考文献"""
        # 作者：最多3位，超过用"等"
        authors_list = paper.get("authors", [])
        if authors_list:
            authors = ",".join(authors_list[:3])
            if len(authors_list) > 3:
                authors += ",等"
        else:
            # 这里的论文已经过滤过，不应该出现佚名
            authors = "未知作者"

        title = paper.get('title', '')
        year = paper.get('year', '')

        # 确定文献类型标识
        paper_type = paper.get('type', '')
        type_map = {
            'journal-article': 'J',
            'article': 'J',
            'book': 'M',
            'chapter': 'M',
            'dataset': 'DB',
            'dissertation': 'D',
            'report': 'R',
            'patent': 'P'
        }
        type_code = type_map.get(paper_type, 'J')  # 默认为期刊 J

        # 获取期刊信息
        primary_location = paper.get('primary_location', {})
        source = primary_location.get('source', {}) or {}

        # 构建期刊信息部分
        journal_info = ""
        journal_name = source.get('display_name', '')
        volume = primary_location.get('volume', '')
        issue = primary_location.get('issue', '')
        pages = primary_location.get('pages', '')

        if journal_name:
            journal_parts = [journal_name]
            if year:
                journal_parts.append(f"{year},")
            if volume:
                journal_parts.append(f"{volume}")
            if issue:
                journal_parts.append(f"({issue})")
            if pages:
                journal_parts.append(f":{pages}")
            journal_info = "".join(journal_parts)
        elif year:
            journal_info = f"{year}"

        # DOI
        doi = paper.get("doi", "")
        doi_suffix = f".DOI:{doi}" if doi else ""

        # 格式：[序号]作者.题名[类型].期刊名,年份,卷(期):页码.DOI:xxx
        return f"[{index}]{authors}.{title}[{type_code}].{journal_info}{doi_suffix}."

    def _remove_existing_references(self, content: str) -> str:
        """移除 AI 可能已经生成的参考文献部分"""
        lines = content.split('\n')
        result = []

        # 查找参考文献标题的位置
        ref_section_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('## 参考文献') or line.strip().startswith('### 参考文献') or line.strip().startswith('# 参考文献'):
                ref_section_start = i
                break

        if ref_section_start == -1:
            return content  # 没有找到参考文献部分，返回原内容

        # 返回参考文献部分之前的内容
        return '\n'.join(lines[:ref_section_start]).strip()

    def _generate_fallback_review(self, topic: str, papers: List[Dict]) -> tuple:
        """生成备用综述（当 API 调用失败时）"""
        references = self._format_references(papers)
        review = f"""# {topic} 文献综述

## 引言

本文综述了关于"{topic}"的相关研究进展，共收集分析了{len(papers)}篇文献。

## 主要研究内容

根据收集的文献，该领域的主要研究方向包括：

1. 理论基础研究
2. 方法论探讨
3. 实证分析
4. 应用研究

## 结论

（注：由于生成服务暂时不可用，以上为框架内容。请查看下方参考文献获取详细信息。）

## 参考文献

{references}
"""
        return review, papers

    def _extract_cited_indices(self, content: str) -> set:
        """
        从正文中提取实际引用的文献编号

        Args:
            content: 正文内容

        Returns:
            被引用的文献编号集合
        """
        import re
        # 匹配 [数字] 格式的引用
        citations = re.findall(r'\[(\d+)\]', content)
        cited_indices = set(int(c) for c in citations)
        return cited_indices

    def _update_citation_numbers(self, content: str, old_to_new: dict) -> str:
        """
        更新正文中的引用编号

        Args:
            content: 正文内容
            old_to_new: 旧编号到新编号的映射

        Returns:
            更新后的正文内容
        """
        import re

        def replace_citation(match):
            old_num = int(match.group(1))
            new_num = old_to_new.get(old_num, old_num)
            return f"[{new_num}]"

        # 替换所有 [数字] 格式的引用
        return re.sub(r'\[(\d+)\]', replace_citation, content)

    def _renumber_citations_by_appearance(self, content: str, cited_papers: List[Dict], cited_indices: set) -> tuple:
        """
        按照引用在文中首次出现的顺序重新编号

        Args:
            content: 正文内容
            cited_papers: 被引用的文献列表
            cited_indices: 被引用的文献编号集合

        Returns:
            (重新编号后的正文, 重新排序后的文献列表)
        """
        import re

        # 找出所有引用及其位置
        citation_pattern = re.compile(r'\[(\d+)\]')
        citations = []

        for match in citation_pattern.finditer(content):
            num = int(match.group(1))
            if num in cited_indices:
                citations.append((match.start(), num))

        # 按照出现顺序排序，去重
        seen = set()
        ordered_old_nums = []
        for _, num in citations:
            if num not in seen:
                seen.add(num)
                ordered_old_nums.append(num)

        # 创建旧编号到新编号的映射（按出现顺序）
        old_to_new = {old: new for new, old in enumerate(ordered_old_nums, 1)}

        # 重新排序文献列表
        reordered_papers = [cited_papers[ordered_old_nums.index(i)] for i in ordered_old_nums]

        # 更新正文中的引用编号
        new_content = self._update_citation_numbers(content, old_to_new)

        return new_content, reordered_papers

    def _limit_citation_count(self, content: str, max_count: int = 2) -> str:
        """
        限制每篇文献的引用次数，删除超过限制的引用

        Args:
            content: 正文内容
            max_count: 每篇文献最大引用次数（默认2次）

        Returns:
            删除多余引用后的正文
        """
        import re

        # 找出所有引用及其位置
        citation_pattern = re.compile(r'\[(\d+)\]')
        citations = []

        for match in citation_pattern.finditer(content):
            num = int(match.group(1))
            citations.append((match.start(), match.end(), num))

        # 统计每个引用编号的出现次数
        citation_count = {}
        for _, _, num in citations:
            citation_count[num] = citation_count.get(num, 0) + 1

        # 找出需要删除的引用位置（保留前max_count次出现）
        to_remove = []
        for num, count in citation_count.items():
            if count > max_count:
                # 找出这个编号的所有出现位置
                occurrences = [(start, end) for start, end, n in citations if n == num]
                # 保留前max_count次，删除后面的
                for start, end in occurrences[max_count:]:
                    to_remove.append((start, end))

        if not to_remove:
            print(f"[DEBUG] No citations to remove, all papers cited <= {max_count} times")
            return content

        print(f"[DEBUG] Removing {len(to_remove)} excess citations")

        # 从后往前删除，避免位置偏移
        for start, end in sorted(to_remove, reverse=True):
            # 检查引用前面的字符，决定如何删除
            prefix = content[:start]
            suffix = content[end:]

            # 找到引用前的字符
            if prefix.endswith('['):
                # 删除整个 [数字]
                content = prefix[:-1] + suffix
            elif prefix.endswith(' ['):
                content = prefix[:-2] + suffix
            elif prefix.endswith(',['):
                content = prefix[:-2] + suffix
            elif re.search(r'\[\d+\]$', prefix[:-len(str(start))+len(prefix)-10]):
                # 前面有其他引用，只删除当前引用
                content = prefix + suffix
            else:
                # 简单删除
                content = prefix + suffix

        # 清理可能的多余方括号和标点
        content = re.sub(r'\[\s*\]', '', content)  # 删除空方括号
        content = re.sub(r',\s*,', ',', content)  # 删除重复逗号
        content = re.sub(r'\s+', ' ', content)  # 合并多余空格

        return content

    def _limit_citation_count_v2(self, content: str, cited_papers: List[Dict], max_count: int = 2) -> str:
        """
        限制每篇文献的引用次数，删除超过限制的引用（简化版）

        Args:
            content: 正文内容（已经重新编号，从[1]开始连续）
            cited_papers: 被引用的文献列表（按引用顺序排列）
            max_count: 每篇文献最大引用次数

        Returns:
            删除多余引用后的正文
        """
        import re

        # 统计每个引用编号的出现次数
        citation_pattern = re.compile(r'\[(\d+)\]')
        citations = []

        for match in citation_pattern.finditer(content):
            num = int(match.group(1))
            citations.append((match.start(), match.end(), num))

        # 统计每个编号的出现次数
        citation_count = {}
        for _, _, num in citations:
            citation_count[num] = citation_count.get(num, 0) + 1

        # 找出需要删除的引用
        to_remove = []
        for num, count in citation_count.items():
            if count > max_count:
                # 找出这个编号的所有出现位置
                occurrences = [(start, end) for start, end, n in citations if n == num]
                # 保留前max_count次，删除后面的
                for start, end in occurrences[max_count:]:
                    to_remove.append((start, end))

        if not to_remove:
            print(f"[DEBUG] No excess citations to remove")
            return content

        print(f"[DEBUG] Need to remove {len(to_remove)} citations from {len(citation_count)} papers")
        print(f"[DEBUG] Before removal, counts: {[(n, citation_count[n]) for n in sorted(citation_count.keys())[:10]]}")

        # 从后往前删除
        result = list(content)
        for start, end in sorted(to_remove, reverse=True):
            # 删除这个引用
            del result[start:end]

        new_content = ''.join(result)

        # 验证删除结果
        new_citations = []
        for match in citation_pattern.finditer(new_content):
            num = int(match.group(1))
            new_citations.append(num)

        new_count = {}
        for num in new_citations:
            new_count[num] = new_count.get(num, 0) + 1

        still_over = {k: v for k, v in new_count.items() if v > max_count}
        if still_over:
            print(f"[DEBUG] WARNING: After removal, still have {len(still_over)} papers over limit")
            print(f"[DEBUG] Still over limit: {[(n, new_count[n]) for n in sorted(still_over.keys())[:5]]}")

        return new_content

    def _filter_anonymous_and_renumber(self, content: str, cited_papers: List[Dict]) -> tuple:
        """
        过滤掉佚名论文并重新编号引用

        Args:
            content: 正文内容
            cited_papers: 被引用的文献列表

        Returns:
            (更新后的正文, 过滤后的文献列表)
        """
        # 找出需要保留的论文（非佚名）
        valid_papers = []
        old_to_new = {}  # 旧编号到新编号的映射

        new_index = 1
        for old_index, paper in enumerate(cited_papers, 1):
            authors_list = paper.get("authors", [])
            if authors_list and authors_list[0] not in ['佚名', '匿名', '未知作者', '']:
                valid_papers.append(paper)
                old_to_new[old_index] = new_index
                new_index += 1
            else:
                print(f"[ReviewGenerator] 过滤掉佚名论文 [{old_index}]: {paper.get('title', 'N/A')[:40]}")

        if old_to_new:
            # 更新正文中的引用编号
            import re
            def replace_citation(match):
                old_num = int(match.group(1))
                new_num = old_to_new.get(old_num)
                if new_num is None:
                    # 这个论文被过滤掉了，删除引用
                    return ''
                return f"[{new_num}]"

            content = re.sub(r'\[(\d+)\]', replace_citation, content)

            # 清理多余的空格和标点（但保留换行符）
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                # 清理每行内的多余空格
                line = re.sub(r'\s+', ' ', line)
                line = re.sub(r',\s*,', ',', line)  # 删除重复逗号
                line = re.sub(r'\[\s*\]', '', line)  # 删除空方括号
                cleaned_lines.append(line)
            content = '\n'.join(cleaned_lines)

            print(f"[ReviewGenerator] 过滤佚名论文: {len(cited_papers)} -> {len(valid_papers)}")

        return content, valid_papers

    def _sort_and_merge_citations(self, content: str) -> str:
        """
        对正文中的引用进行排序和合并

        例如: [35][34][36][47] -> [34-36][47]

        Args:
            content: 正文内容

        Returns:
            处理后的正文
        """
        import re

        # 找出所有连续的引用块（例如 "[35][34][36][47]"）
        # 使用正则表达式匹配一个或多个连续的 [数字]
        citation_block_pattern = re.compile(r'(\[\d+\])+')
        citation_pattern = re.compile(r'\[(\d+)\]')

        def process_citation_block(match):
            block = match.group(0)
            # 提取所有引用编号
            citations = [int(c) for c in citation_pattern.findall(block)]
            if not citations:
                return block

            # 去重并排序
            citations = sorted(set(citations))

            # 合并连续的引用
            merged = []
            i = 0
            while i < len(citations):
                start = citations[i]
                end = start
                while i + 1 < len(citations) and citations[i + 1] == end + 1:
                    end = citations[i + 1]
                    i += 1

                if end - start >= 2:  # 连续3个或以上，使用范围格式
                    merged.append(f"[{start}-{end}]")
                else:
                    # 单个或两个连续引用，分别列出
                    for j in range(start, end + 1):
                        merged.append(f"[{j}]")
                i += 1

            return ''.join(merged)

        # 处理所有引用块
        content = citation_block_pattern.sub(process_citation_block, content)

        return content

    async def close(self):
        await self.client.close()
