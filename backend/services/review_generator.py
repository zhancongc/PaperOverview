"""
文献综述生成服务
使用 DeepSeek API
"""
import os
from openai import AsyncOpenAI
from typing import List, Dict


class ReviewGeneratorService:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

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
- 引用要求：至少引用 50 篇不同的文献，尽量覆盖更多文献，不要只引用少数几篇
- 引用分布：避免重复引用同一篇文献，每篇文献引用次数最好不超过2次
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

            if cited_indices:
                # 只保留被引用的文献
                cited_papers = [papers[i - 1] for i in cited_indices if i <= len(papers)]

                # 创建旧编号到新编号的映射
                old_to_new = {old: new for new, old in enumerate(sorted(cited_indices), 1)}

                # 更新正文中的引用编号
                content = self._update_citation_numbers(content, old_to_new)

                # 重新格式化参考文献
                references = self._format_references(cited_papers)

                full_review = f"{content}\n\n## 参考文献\n\n{references}"

                # 返回综述和实际被引用的文献
                return full_review, cited_papers
            else:
                # 如果没有引用，使用所有文献
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
1. 在综述的适当位置添加这些文献的引用
2. 保持原文结构和内容不变，只添加引用标记
3. 每添加一个引用，在相关句子末尾加上 [序号]
4. 请直接输出修改后的完整综述内容，不要解释

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
        """格式化参考文献列表（国标 GB/T 7714-2015）"""
        references = []
        for i, paper in enumerate(papers, 1):
            # 作者：最多3位，超过用"等"
            authors_list = paper.get("authors", [])
            if authors_list:
                authors = ",".join(authors_list[:3])
                if len(authors_list) > 3:
                    authors += ",等"
            else:
                authors = "佚名"

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

            # 获取期刊信息（如果有）
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
            ref = f"[{i}]{authors}.{title}[{type_code}].{journal_info}{doi_suffix}."
            references.append(ref)
        return "\n\n".join(references)

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

    async def close(self):
        await self.client.close()
