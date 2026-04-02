"""
文献综述生成服务 v2.0 - 增强版（精细控制版）

这是增强版的综述生成服务，提供更精细的步骤控制。

版本说明：
- 生产版：review_generator.py - 4-5次调用，节省40% token（推荐）
- 本文件：增强版（review_generator_v2_enhanced.py）- 8-10次调用，更精细控制
- 旧版（单prompt）：已移除

与生产版相比：
- 每个主体主题单独生成，质量更高
- 更详细的对比分析要求
- 适合需要最高质量综述的场景
"""
import os
from openai import AsyncOpenAI
from typing import List, Dict, Tuple
from .aminer_paper_detail import enrich_papers


class ReviewGeneratorServiceV2:
    """
    综述生成服务 v2.0 - 多步骤生成

    步骤拆分：
    1. 生成综述大纲 - 确定结构和主题划分
    2. 逐节生成内容 - 专注于内容质量和对比分析
    3. 验证和修复引用 - 确保引用符合规范
    4. 润色和格式化 - 提升可读性
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", aminer_token: str = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.aminer_token = aminer_token or os.getenv('AMINER_API_TOKEN')

    async def generate_review(
        self,
        topic: str,
        papers: List[Dict],
        model: str = "deepseek-chat",
        specificity_guidance: dict = None
    ) -> Tuple[str, List[Dict]]:
        """
        生成文献综述（多步骤版本）

        Args:
            topic: 论文主题
            papers: 文献列表
            model: 模型名称
            specificity_guidance: 场景特异性指导

        Returns:
            (综述内容, 实际被引用的文献列表)
        """
        print("=" * 80)
        print("综述生成 v2.0 - 多步骤生成")
        print("=" * 80)

        # === 第1步：生成综述大纲 ===
        print(f"\n[步骤 1/4] 生成综述大纲...")
        outline = await self._step1_generate_outline(
            topic, papers, specificity_guidance, model
        )
        print(f"[步骤 1/4] ✓ 大纲生成完成，包含 {len(outline.get('sections', []))} 个主题")

        # === 第2步：逐节生成内容 ===
        print(f"\n[步骤 2/4] 逐节生成内容...")
        content_draft = await self._step2_generate_sections(
            topic, papers, outline, specificity_guidance, model
        )
        print(f"[步骤 2/4] ✓ 内容生成完成，字数约 {len(content_draft)} 字符")

        # === 第3步：验证和修复引用 ===
        print(f"\n[步骤 3/4] 验证和修复引用...")
        content_fixed, cited_papers = await self._step3_validate_citations(
            content_draft, papers, topic, model
        )
        print(f"[步骤 3/4] ✓ 引用修复完成，引用 {len(cited_papers)} 篇文献")

        # === 第4步：润色和格式化 ===
        print(f"\n[步骤 4/4] 润色和格式化...")
        final_review = await self._step4_polish_format(
            content_fixed, cited_papers
        )
        print(f"[步骤 4/4] ✓ 润色完成")

        print(f"\n[完成] 综述生成完毕！")
        print("=" * 80)

        return final_review, cited_papers

    def _paper_to_dict(self, paper) -> Dict:
        """
        将 PaperMetadata 对象或字典转换为统一格式
        """
        if isinstance(paper, dict):
            return paper

        # 处理 PaperMetadata 对象
        result = {}
        if hasattr(paper, 'title'):
            result['title'] = paper.title or ''
            result['authors'] = paper.authors if paper.authors else []
            result['year'] = paper.year
            result['abstract'] = paper.abstract if paper.abstract else ''
            result['cited_by_count'] = paper.cited_by_count if paper.cited_by_count else 0
            result['type'] = paper.paper_type if hasattr(paper, 'paper_type') else 'article'
            result['doi'] = paper.doi if hasattr(paper, 'doi') else ''
            result['id'] = paper.id if hasattr(paper, 'id') else ''
        else:
            # 默认返回空字典
            return {
                'title': '',
                'authors': [],
                'year': None,
                'abstract': '',
                'cited_by_count': 0,
                'type': 'article',
                'doi': '',
                'id': ''
            }
        return result

    # ==================== 第1步：生成综述大纲 ====================

    async def _step1_generate_outline(
        self,
        topic: str,
        papers: List[Dict],
        specificity_guidance: dict,
        model: str
    ) -> Dict:
        """
        生成综述大纲

        专注任务：
        - 确定综述结构
        - 划分主题
        - 为每个主题分配相关文献
        """
        # 构建场景特异性指导
        specificity_section = self._format_specificity_guidance(specificity_guidance)

        # 构建文献简要信息（用于大纲分配）
        papers_brief = self._format_papers_brief(papers)

        system_prompt = f"""你是学术综述大纲设计专家。

{specificity_section}

你的任务是根据研究主题和文献列表，设计一个高质量的文献综述大纲。

要求：
1. **结构清晰**：包含引言、主体（2-4个主题）、结论
2. **主题划分**：主体部分按研究主题或方法论划分
3. **文献分配**：为每个主题推荐最相关的文献（使用文献编号）
4. **逻辑连贯**：各主题之间要有逻辑关系

输出格式（JSON）：
{{
    "introduction": {{
        "focus": "引言部分的写作重点",
        "key_papers": [1, 2, 3]
    }},
    "sections": [
        {{
            "title": "主题标题",
            "focus": "该主题的写作重点",
            "key_papers": [4, 5, 6, 7],
            "comparison_points": ["对比点1", "对比点2"]
        }}
    ],
    "conclusion": {{
        "focus": "结论部分的写作重点",
        "key_papers": [8, 9]
    }}
}}"""

        user_prompt = f"""请为以下研究主题设计综述大纲：

**主题**：{topic}

**文献列表**（共{len(papers)}篇）：
{papers_brief}

请输出JSON格式的大纲："""

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=2000
            )

            import json
            outline = json.loads(response.choices[0].message.content)
            return outline

        except Exception as e:
            print(f"[步骤1] 生成大纲失败: {e}")
            # 返回默认大纲
            return self._get_default_outline(topic, papers)

    # ==================== 第2步：逐节生成内容 ====================

    async def _step2_generate_sections(
        self,
        topic: str,
        papers: List[Dict],
        outline: Dict,
        specificity_guidance: dict,
        model: str
    ) -> str:
        """
        逐节生成综述内容

        专注任务：
        - 生成各节内容
        - 构建文献矩阵对比
        - 确保引用正确
        """
        specificity_section = self._format_specificity_guidance(specificity_guidance)
        papers_info = self._format_papers_for_prompt(papers)

        sections = []

        # 生成引言
        print(f"  - 生成引言...")
        intro = await self._generate_introduction(
            topic, outline.get('introduction', {}), papers, specificity_section, model
        )
        sections.append(intro)

        # 生成主体各节
        for i, section_outline in enumerate(outline.get('sections', []), 1):
            print(f"  - 生成主体 {i}/{len(outline.get('sections', []))}: {section_outline.get('title', '')}...")
            section = await self._generate_section(
                topic, section_outline, papers, specificity_section, model
            )
            sections.append(section)

        # 生成结论
        print(f"  - 生成结论...")
        conclusion = await self._generate_conclusion(
            topic, outline.get('conclusion', {}), outline.get('sections', []),
            papers, specificity_section, model
        )
        sections.append(conclusion)

        return "\n\n".join(sections)

    async def _generate_introduction(
        self,
        topic: str,
        intro_outline: Dict,
        papers: List[Dict],
        specificity_section: str,
        model: str
    ) -> str:
        """生成引言部分"""
        key_papers = intro_outline.get('key_papers', [])
        focus = intro_outline.get('focus', '介绍研究背景和意义')

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述的引言部分。

{specificity_section}

**引言写作要求**：
1. 介绍研究背景和意义
2. 说明当前研究现状
3. 指出研究的必要性
4. 自然过渡到主体内容

**引用要求**：
- 只使用文献编号，如 [1]、[2]
- 推荐优先引用：{key_papers[:10] if key_papers else '根据内容选择'}
- 本部分引用 5-10 篇即可

输出格式：Markdown（二级标题 ## 引言）"""

        user_prompt = f"""请撰写关于"{topic}"的引言部分。

**写作重点**：{focus}

**可用文献**（共{len(papers)}篇，使用编号引用）：
{self._format_papers_for_prompt(papers, max_papers=30)}

请输出引言部分："""

        return await self._call_llm(system_prompt, user_prompt, model)

    async def _generate_section(
        self,
        topic: str,
        section_outline: Dict,
        papers: List[Dict],
        specificity_section: str,
        model: str
    ) -> str:
        """生成主体部分的一个主题"""
        title = section_outline.get('title', '')
        focus = section_outline.get('focus', '')
        key_papers = section_outline.get('key_papers', [])
        comparison_points = section_outline.get('comparison_points', [])

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述的主体部分，特别擅长构建"文献矩阵"进行对比分析。

{specificity_section}

**主题写作要求**：
1. **构建文献矩阵**：不要简单列举，要对比不同研究的观点、方法、结论
2. **明确指出分歧**：当研究结论不一致时，要明确指出
3. **分析原因**：探讨分歧产生的可能原因

**对比分析示例**：
✓ 正确写法：
  在XX问题上，现有研究存在显著分歧。张三(2019)[5]认为...；而李四(2020)[8]则指出...；这种分歧可能源于...

**引用要求**：
- 优先引用：{key_papers[:15] if key_papers else '根据内容选择'}
- 本部分引用 10-15 篇
- 每篇文献不超过2次

输出格式：Markdown（二级标题 ## {title}）"""

        user_prompt = f"""请撰写关于"{topic}"综述的主题：{title}

**写作重点**：{focus}

**对比要点**：{', '.join(comparison_points) if comparison_points else '根据内容自行确定'}

**可用文献**（共{len(papers)}篇）：
{self._format_papers_for_prompt(papers)}

请输出该主题部分："""

        return await self._call_llm(system_prompt, user_prompt, model)

    async def _generate_conclusion(
        self,
        topic: str,
        conclusion_outline: Dict,
        sections: List[Dict],
        papers: List[Dict],
        specificity_section: str,
        model: str
    ) -> str:
        """生成结论部分"""
        focus = conclusion_outline.get('focus', '总结现有研究的不足和未来方向')

        # 汇总所有主题
        section_titles = [s.get('title', '') for s in sections]

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述的结论部分。

{specificity_section}

**结论写作要求**：
1. 总结主要研究共识
2. 指出研究分歧和不足
3. 提出未来研究方向
4. 回应研究主题的核心问题

**引用要求**：
- 结论部分引用要少，主要引用关键文献
- 本部分引用 3-5 篇即可

输出格式：Markdown（二级标题 ## 结论）"""

        user_prompt = f"""请撰写关于"{topic}"综述的结论部分。

**综述已涵盖的主题**：
{chr(10).join([f"- {t}" for t in section_titles])}

**写作重点**：{focus}

**可用文献**：
{self._format_papers_for_prompt(papers, max_papers=20)}

请输出结论部分："""

        return await self._call_llm(system_prompt, user_prompt, model)

    # ==================== 第3步：验证和修复引用 ====================

    async def _step3_validate_citations(
        self,
        content: str,
        papers: List,
        topic: str,
        model: str
    ) -> Tuple[str, List[Dict]]:
        """
        验证和修复引用

        专注任务：
        - 检查引用数量
        - 修复引用格式
        - 补充缺失的引用
        """
        # 将所有论文转换为字典格式
        papers_dict = [self._paper_to_dict(p) for p in papers]

        # 提取当前引用
        cited_indices = self._extract_cited_indices(content)
        unique_cited = len(cited_indices)

        print(f"  - 当前引用: {unique_cited} 篇")

        # 检查是否需要补充引用
        min_citations = 30  # 降低要求，因为分步生成更容易控制
        if unique_cited < min_citations:
            print(f"  - 引用不足，补充中...")
            content = await self._add_more_citations(
                content, papers_dict, topic, min_citations, model, cited_indices
            )
            cited_indices = self._extract_cited_indices(content)
            print(f"  - 补充后引用: {len(cited_indices)} 篇")

        # 按出现顺序重新编号
        cited_papers = [papers_dict[i - 1] for i in cited_indices if i <= len(papers_dict)]
        content, cited_papers = self._renumber_citations_by_appearance(content, cited_papers, cited_indices)

        # 限制每篇文献引用次数
        content = self._limit_citation_count_v2(content, cited_papers, max_count=2)

        # 排序和合并引用
        content = self._sort_and_merge_citations(content)

        return content, cited_papers

    # ==================== 第4步：润色和格式化 ====================

    async def _step4_polish_format(
        self,
        content: str,
        cited_papers: List[Dict]
    ) -> str:
        """
        润色和格式化

        专注任务：
        - 格式化参考文献
        - 合并最终版本
        """
        # 尝试补充论文详情
        if self.aminer_token:
            try:
                cited_papers = await enrich_papers(cited_papers, self.aminer_token)
            except Exception as e:
                print(f"[步骤4] 补充论文详情失败: {e}")

        # 过滤佚名论文
        content, cited_papers = self._filter_anonymous_and_renumber(content, cited_papers)

        # 格式化参考文献
        references = self._format_references(cited_papers)

        # 合并最终版本
        full_review = f"{content}\n\n## 参考文献\n\n{references}"

        return full_review

    # ==================== 辅助方法 ====================

    async def _call_llm(self, system_prompt: str, user_prompt: str, model: str) -> str:
        """调用 LLM"""
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        return response.choices[0].message.content

    def _format_specificity_guidance(self, specificity_guidance: dict) -> str:
        """格式化场景特异性指导"""
        if not specificity_guidance:
            return ""

        core_scenario = specificity_guidance.get('core_scene', '')
        research_field = specificity_guidance.get('research_field', '')
        main_technology = specificity_guidance.get('main_technology', '')
        scene_specificity = specificity_guidance.get('scene_specificity', '')
        review_requirement = specificity_guidance.get('review_requirement', '')
        lack_research_statement = specificity_guidance.get('lack_research_statement', '')

        return f"""
【场景特异性指导】
- 核心场景实体：{core_scenario}
- 研究领域：{research_field}
- 主要技术：{main_technology}
- 场景特殊性：{scene_specificity}
- 写作要求：{review_requirement}
- 缺乏文献处理：{lack_research_statement}
"""

    def _format_papers_brief(self, papers: List) -> str:
        """格式化论文简要信息（用于大纲）"""
        brief = []
        for i, paper in enumerate(papers, 1):
            # 处理 PaperMetadata 对象或字典
            if hasattr(paper, 'title'):
                title = paper.title[:80]
            else:
                title = paper.get('title', '')[:80]
            brief.append(f"[{i}] {title}")
        return "\n".join(brief)

    def _format_papers_for_prompt(self, papers: List, max_papers: int = None) -> str:
        """格式化论文信息用于 Prompt"""
        if max_papers:
            papers = papers[:max_papers]

        formatted = []
        for i, paper in enumerate(papers, 1):
            # 处理 PaperMetadata 对象或字典
            if hasattr(paper, 'title'):
                title = paper.title
                authors_list = paper.authors if paper.authors else []
                year = paper.year
                abstract = paper.abstract if paper.abstract else ''
            else:
                title = paper.get('title', '')
                authors_list = paper.get("authors", [])
                year = paper.get('year', '')
                abstract = paper.get('abstract', '')

            authors = ", ".join(authors_list[:3]) if authors_list else "未知作者"
            if len(authors_list) > 3:
                authors += " 等"

            formatted.append(
                f"[{i}] {title}\n"
                f"    作者：{authors}\n"
                f"    年份：{year or 'N/A'}\n"
                f"    摘要：{(abstract or 'N/A')[:200]}..."
            )
        return "\n\n".join(formatted)

    def _get_default_outline(self, topic: str, papers: List[Dict]) -> Dict:
        """获取默认大纲"""
        return {
            "introduction": {
                "focus": "介绍研究背景和意义",
                "key_papers": list(range(1, min(6, len(papers) + 1)))
            },
            "sections": [
                {
                    "title": "理论基础与研究现状",
                    "focus": "梳理相关理论和方法",
                    "key_papers": list(range(1, min(16, len(papers) + 1))),
                    "comparison_points": ["方法差异", "理论分歧"]
                },
                {
                    "title": "主要研究进展",
                    "focus": "总结当前研究的主要成果",
                    "key_papers": list(range(16, min(31, len(papers) + 1))),
                    "comparison_points": ["研究结论对比", "应用效果"]
                }
            ],
            "conclusion": {
                "focus": "总结不足和未来方向",
                "key_papers": list(range(max(1, len(papers) - 5), len(papers) + 1))
            }
        }

    async def _add_more_citations(
        self, content: str, papers: List[Dict],
        topic: str, target_count: int, model: str, cited_indices: set
    ) -> str:
        """补充引用"""
        uncited_indices = [i for i in range(1, len(papers) + 1) if i not in cited_indices]

        if not uncited_indices:
            return content

        additional_count = min(len(uncited_indices), target_count - len(cited_indices))
        additional_papers = []

        sorted_uncited = sorted(
            uncited_indices,
            key=lambda i: papers[i-1].get('cited_by_count', 0),
            reverse=True
        )[:additional_count * 2]

        for idx in sorted_uncited:
            paper = papers[idx - 1]
            authors_list = paper.get("authors", [])
            authors = ", ".join(authors_list[:3]) if authors_list else "未知作者"
            if len(authors_list) > 3:
                authors += " 等"
            additional_papers.append(f"[{idx}] {paper.get('title', '')} - {authors} ({paper.get('year', '')})")

        supplement_prompt = f"""请在现有综述基础上，补充更多文献引用。

当前已引用 {len(cited_indices)} 篇，目标 {target_count} 篇。

可补充的文献：
{chr(10).join(additional_papers[:20])}

要求：
1. 按顺序继续编号
2. 添加到合适位置
3. 直接输出修改后的完整综述

当前综述：
{content[:4000]}
"""

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是学术写作助手，负责在综述中补充文献引用。"},
                    {"role": "user", "content": supplement_prompt}
                ],
                temperature=0.5,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[补充引用] 失败: {e}")
            return content

    # ==================== 以下方法从原版复用 ====================

    def _extract_cited_indices(self, content: str) -> set:
        """从正文中提取实际引用的文献编号"""
        import re
        citations = re.findall(r'\[(\d+)\]', content)
        return set(int(c) for c in citations)

    def _renumber_citations_by_appearance(self, content: str, cited_papers: List[Dict], cited_indices: set) -> tuple:
        """按照引用在文中首次出现的顺序重新编号"""
        import re

        citation_pattern = re.compile(r'\[(\d+)\]')
        citations = []

        for match in citation_pattern.finditer(content):
            num = int(match.group(1))
            if num in cited_indices:
                citations.append((match.start(), num))

        seen = set()
        ordered_old_nums = []
        for _, num in citations:
            if num not in seen:
                seen.add(num)
                ordered_old_nums.append(num)

        old_to_new = {old: new for new, old in enumerate(ordered_old_nums, 1)}
        reordered_papers = [cited_papers[ordered_old_nums.index(i)] for i in ordered_old_nums]

        def replace_citation(match):
            old_num = int(match.group(1))
            new_num = old_to_new.get(old_num, old_num)
            return f"[{new_num}]"

        new_content = re.sub(r'\[(\d+)\]', replace_citation, content)

        return new_content, reordered_papers

    def _limit_citation_count_v2(self, content: str, cited_papers: List[Dict], max_count: int = 2) -> str:
        """限制每篇文献的引用次数"""
        import re

        citation_pattern = re.compile(r'\[(\d+)\]')
        citations = []

        for match in citation_pattern.finditer(content):
            num = int(match.group(1))
            citations.append((match.start(), match.end(), num))

        citation_count = {}
        for _, _, num in citations:
            citation_count[num] = citation_count.get(num, 0) + 1

        to_remove = []
        for num, count in citation_count.items():
            if count > max_count:
                occurrences = [(start, end) for start, end, n in citations if n == num]
                for start, end in occurrences[max_count:]:
                    to_remove.append((start, end))

        if not to_remove:
            return content

        result = list(content)
        for start, end in sorted(to_remove, reverse=True):
            del result[start:end]

        return ''.join(result)

    def _sort_and_merge_citations(self, content: str) -> str:
        """对正文中的引用进行排序和合并"""
        import re

        citation_block_pattern = re.compile(r'(\[\d+\])+')
        citation_pattern = re.compile(r'\[(\d+)\]')

        def process_citation_block(match):
            block = match.group(0)
            citations = [int(c) for c in citation_pattern.findall(block)]
            if not citations:
                return block

            citations = sorted(set(citations))

            merged = []
            i = 0
            while i < len(citations):
                start = citations[i]
                end = start
                while i + 1 < len(citations) and citations[i + 1] == end + 1:
                    end = citations[i + 1]
                    i += 1

                if end - start >= 2:
                    merged.append(f"[{start}-{end}]")
                else:
                    for j in range(start, end + 1):
                        merged.append(f"[{j}]")
                i += 1

            return ''.join(merged)

        return citation_block_pattern.sub(process_citation_block, content)

    def _filter_anonymous_and_renumber(self, content: str, cited_papers: List[Dict]) -> tuple:
        """过滤掉佚名论文并重新编号引用"""
        valid_papers = []
        old_to_new = {}

        new_index = 1
        for old_index, paper in enumerate(cited_papers, 1):
            # 确保是字典格式
            if not isinstance(paper, dict):
                paper = self._paper_to_dict(paper)

            authors_list = paper.get("authors", [])
            if authors_list and authors_list[0] not in ['佚名', '匿名', '未知作者', '']:
                valid_papers.append(paper)
                old_to_new[old_index] = new_index
                new_index += 1

        if old_to_new:
            import re
            def replace_citation(match):
                old_num = int(match.group(1))
                new_num = old_to_new.get(old_num)
                if new_num is None:
                    return ''
                return f"[{new_num}]"

            content = re.sub(r'\[(\d+)\]', replace_citation, content)

            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                line = re.sub(r'\s+', ' ', line)
                line = re.sub(r',\s*,', ',', line)
                line = re.sub(r'\[\s*\]', '', line)
                cleaned_lines.append(line)
            content = '\n'.join(cleaned_lines)

        return content, valid_papers

    def _format_references(self, papers: List) -> str:
        """格式化参考文献列表"""
        valid_papers = []
        for paper in papers:
            # 确保是字典格式
            if not isinstance(paper, dict):
                paper = self._paper_to_dict(paper)

            authors_list = paper.get("authors", [])
            if authors_list and authors_list[0] not in ['佚名', '匿名', '未知作者', '']:
                valid_papers.append(paper)

        if not valid_papers:
            return "## 参考文献\n\n暂无参考文献"

        references = []
        for i, paper in enumerate(valid_papers, 1):
            references.append(self._format_single_reference(paper, i))

        return "\n\n".join(references)

    def _format_single_reference(self, paper, index: int) -> str:
        """格式化单条参考文献"""
        # 确保是字典格式
        if not isinstance(paper, dict):
            paper = self._paper_to_dict(paper)

        authors_list = paper.get("authors", [])
        if authors_list:
            authors = ",".join(authors_list[:3])
            if len(authors_list) > 3:
                authors += ",等"
        else:
            authors = "未知作者"

        title = paper.get('title', '')
        year = paper.get('year', '')

        paper_type = paper.get('type', '')
        type_map = {
            'journal-article': 'J', 'article': 'J', 'book': 'M',
            'chapter': 'M', 'dataset': 'DB', 'dissertation': 'D',
            'report': 'R', 'patent': 'P'
        }
        type_code = type_map.get(paper_type, 'J')

        journal_info = ""
        if year:
            journal_info = f"{year}"
        else:
            journal_info = "n.d."

        doi = paper.get("doi", "")
        doi_suffix = f".DOI:{doi}" if doi else ""

        return f"[{index}]{authors}.{title}[{type_code}].{journal_info}{doi_suffix}."

    async def close(self):
        await self.client.close()


# 测试代码
async def test_v2_generator():
    """测试 v2 生成器"""
    print("测试综述生成 v2.0")

    # 模拟数据
    topic = "基于机器学习的图像识别研究"
    papers = [
        {
            "id": f"paper_{i}",
            "title": f"关于机器学习图像识别的研究 {i}",
            "authors": ["张三", "李四"],
            "year": 2020 + i % 5,
            "abstract": "这是一篇关于机器学习图像识别的研究论文...",
            "cited_by_count": 100 - i * 5,
            "type": "journal-article"
        }
        for i in range(1, 31)
    ]

    generator = ReviewGeneratorServiceV2(
        api_key="test_key",
        aminer_token=None
    )

    try:
        # 只测试大纲生成
        outline = await generator._step1_generate_outline(
            topic, papers, None, "deepseek-chat"
        )
        print(f"大纲: {outline}")
    finally:
        await generator.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_v2_generator())
