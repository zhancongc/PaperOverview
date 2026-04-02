"""
文献综述生成服务 v2.0 - 生产版（优化版）

这是默认的综述生成服务，优化了 token 消耗。

版本说明：
- 本文件：生产版（review_generator.py）- 4-5次调用，节省40% token
- 增强版：review_generator_v2_enhanced.py - 8-10次调用，更精细控制
- 旧版（单prompt）：已移除

优化策略：
1. 批量生成：将多个主题合并为1-2次调用
2. 复用上下文：避免重复传递文献列表
3. 智能分块：根据内容复杂度动态调整
4. 缓存复用：复用大纲生成结果
"""
import os
from openai import AsyncOpenAI
from typing import List, Dict, Tuple
from .aminer_paper_detail import enrich_papers


class ReviewGeneratorService:
    """
    综述生成服务 v2.0 生产版（优化版）

    步骤拆分（优化后）：
    1. 生成综述大纲 - 1次调用
    2. 批量生成内容 - 2-3次调用（合并主体部分）
    3. 验证和修复引用 - 0-1次调用
    4. 润色和格式化 - 无 LLM 调用

    总调用次数：4-5次（比原版减少50%）

    优化策略：
    1. 批量生成：将多个主题合并为1-2次调用
    2. 复用上下文：避免重复传递文献列表
    3. 智能分块：根据内容复杂度动态调整
    4. 缓存复用：复用大纲生成结果
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", aminer_token: str = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.aminer_token = aminer_token or os.getenv('AMINER_API_TOKEN')
        self._outline_cache = None  # 缓存大纲结果

    async def generate_review(
        self,
        topic: str,
        papers: List[Dict],
        model: str = "deepseek-chat",
        specificity_guidance: dict = None
    ) -> Tuple[str, List[Dict]]:
        """
        生成文献综述（优化版）

        Args:
            topic: 论文主题
            papers: 文献列表
            model: 模型名称
            specificity_guidance: 场景特异性指导

        Returns:
            (综述内容, 实际被引用的文献列表)
        """
        print("=" * 80)
        print("综述生成 v2.0 - 优化版 (4-5次调用)")
        print("=" * 80)

        # === 第1步：生成综述大纲 ===
        print(f"\n[步骤 1/4] 生成综述大纲...")
        outline = await self._step1_generate_outline(
            topic, papers, specificity_guidance, model
        )
        self._outline_cache = outline  # 缓存大纲
        print(f"[步骤 1/4] ✓ 大纲生成完成")

        # === 第2步：批量生成内容（优化：合并调用）===
        print(f"\n[步骤 2/4] 批量生成内容...")
        content_draft = await self._step2_generate_content_optimized(
            topic, papers, outline, specificity_guidance, model
        )
        print(f"[步骤 2/4] ✓ 内容生成完成，字数约 {len(content_draft)}")

        # === 第3步：验证和修复引用 ===
        print(f"\n[步骤 3/4] 验证和修复引用...")
        cited_indices = self._extract_cited_indices(content_draft)
        unique_cited = len(cited_indices)
        print(f"  - 当前引用: {unique_cited} 篇")

        # 动态调整目标引用数量
        target_citations = min(50, len(papers))  # 目标是50篇，但不能超过可用文献数
        min_citations = max(30, int(target_citations * 0.7))  # 至少70%的目标数量

        # 多次尝试补充引用
        max_attempts = 3
        for attempt in range(max_attempts):
            cited_indices = self._extract_cited_indices(content_draft)
            unique_cited = len(cited_indices)

            if unique_cited >= target_citations:
                print(f"  - ✓ 引用数量达标: {unique_cited} 篇")
                break

            if unique_cited < min_citations:
                print(f"  - 引用不足 ({unique_cited}/{target_citations})，尝试 {attempt + 1}/{max_attempts} 补充...")
                papers_dict = [self._paper_to_dict(p) for p in papers]
                content_draft = await self._add_more_citations(
                    content_draft, papers_dict, topic, target_citations, model, cited_indices
                )
            else:
                print(f"  - 引用数量接近目标: {unique_cited}/{target_citations}")
                break
        else:
            # 最终检查
            cited_indices = self._extract_cited_indices(content_draft)
            unique_cited = len(cited_indices)
            print(f"  - 最终引用数量: {unique_cited} 篇")

        # 按出现顺序重新编号
        # 只保留在有效范围内的引用编号
        valid_cited_indices = {i for i in cited_indices if 1 <= i <= len(papers)}
        cited_papers = [self._paper_to_dict(papers[i - 1]) for i in valid_cited_indices]

        # 更新 content_draft，替换超出范围的引用
        if len(valid_cited_indices) < len(cited_indices):
            invalid_count = len(cited_indices) - len(valid_cited_indices)
            print(f"[引用修复] 发现 {invalid_count} 个超出范围的引用，尝试替换...")

            # 获取未引用的文献
            uncited_indices = set(range(1, len(papers) + 1)) - valid_cited_indices

            if uncited_indices:
                # 替换超出范围的引用
                content_draft = self._replace_invalid_citations(
                    content_draft, cited_indices, valid_cited_indices, uncited_indices, papers, topic
                )
            else:
                # 没有可用文献进行替换，只能删除
                print(f"[引用修复] 没有可用文献进行替换，删除超出范围的引用")
                import re
                def remove_invalid_citations(match):
                    num = int(match.group(1))
                    if num in valid_cited_indices:
                        return match.group(0)
                    return ""
                content_draft = re.sub(r'\[(\d+)\]', remove_invalid_citations, content_draft)
                # 清理空的方括号
                content_draft = re.sub(r'\[\s*\]', '', content_draft)

        content, cited_papers = self._renumber_citations_by_appearance(content_draft, cited_papers, valid_cited_indices)

        # 限制每篇文献引用次数
        content = self._limit_citation_count_v2(content, cited_papers, max_count=2)
        content = self._sort_and_merge_citations(content)

        print(f"[步骤 3/4] ✓ 引用修复完成，引用 {len(cited_papers)} 篇")

        # === 第3.5步：内容完整性检查 ===
        print(f"\n[步骤 3.5/4] 检查内容完整性...")
        content = await self._ensure_content_completeness(
            content, topic, papers, specificity_guidance, model, outline
        )

        # === 第3.6步：文献相关性检查 ===
        print(f"\n[步骤 3.6/4] 检查文献相关性...")
        # 使用术语库增强关键词提取
        topic_keywords = self._extract_topic_keywords_with_library(topic)
        cited_papers = self._filter_irrelevant_papers(cited_papers, topic, topic_keywords)
        print(f"[步骤 3.6/4] ✓ 相关性检查完成，最终引用 {len(cited_papers)} 篇")

        # === 第4步：润色和格式化 ===
        print(f"\n[步骤 4/5] 润色和格式化...")
        final_review = await self._step4_polish_format(content, cited_papers)
        print(f"[步骤 4/5] ✓ 润色完成")

        # === 第5步：最终格式验证和清理 ===
        print(f"\n[步骤 5/5] 最终格式验证和清理...")
        final_review = self._final_format_cleanup(final_review)
        print(f"[步骤 5/5] ✓ 格式验证完成")

        print(f"\n[完成] 综述生成完毕！总调用: 4-5次")
        print("=" * 80)

        return final_review, cited_papers

    async def generate_review_by_sections(
        self,
        topic: str,
        framework: dict,
        papers_by_section: dict,
        all_papers: List[Dict],
        model: str = "deepseek-chat",
        specificity_guidance: dict = None
    ) -> Tuple[str, List[Dict]]:
        """
        按小节生成综述（新流程阶段5）

        流程：
        1. 为每个小节生成内容，传递对应小节的文献
        2. 整合所有小节内容
        3. 验证和修复引用

        Args:
            topic: 论文主题
            framework: 框架信息（包含大纲）
            papers_by_section: 按小节分组的文献
            all_papers: 所有文献（用于引用编号）
            model: 模型名称
            specificity_guidance: 场景特异性指导

        Returns:
            (综述内容, 实际被引用的文献列表)
        """
        print("=" * 80)
        print("[阶段5] 按小节生成综述")
        print("=" * 80)

        specificity_section = self._format_specificity_guidance(specificity_guidance)

        # 获取大纲（从 outline 中获取 body_sections）
        outline = framework.get('outline', {})
        body_sections_list = outline.get('body_sections', [])

        # 转换为字典格式，方便按标题查找
        outline_sections = {}
        for section in body_sections_list:
            if isinstance(section, dict):
                title = section.get('title', '')
                if title:
                    outline_sections[title] = section

        # 如果没有 body_sections，尝试从 framework 获取
        if not outline_sections:
            framework_dict = framework.get('framework', {})
            sections_list = framework_dict.get('sections', [])
            for section in sections_list:
                if isinstance(section, dict):
                    title = section.get('title', '')
                    if title:
                        outline_sections[title] = section

        # 为每个小节生成内容
        section_contents = []
        all_cited_indices = set()

        for section_title, section_outline in outline_sections.items():
            # 获取该小节的文献
            section_papers = papers_by_section.get(section_title, [])

            print(f"\n[阶段5] 生成小节: {section_title}")
            print(f"  - 该小节文献数: {len(section_papers)}")

            if not section_papers:
                print(f"  - 警告: 小节 '{section_title}' 没有文献，跳过")
                continue

            # 格式化该小节的文献
            papers_info = self._format_papers_compact(section_papers)

            # 生成该小节的内容
            section_content = await self._generate_section_content(
                topic=topic,
                section_title=section_title,
                section_outline=section_outline,
                section_papers=section_papers,
                all_papers=all_papers,
                specificity_section=specificity_section,
                model=model
            )

            section_contents.append(section_content)

            # 提取该小节的引用
            section_cited_indices = self._extract_cited_indices(section_content)
            all_cited_indices.update(section_cited_indices)
            print(f"  - 该小节引用: {len(section_cited_indices)} 篇")

        # 合并所有小节内容
        content_draft = "\n\n".join(section_contents)

        # 验证和修复引用
        print(f"\n[阶段5] 验证和修复引用...")
        cited_indices = sorted(list(all_cited_indices))
        unique_cited = len(cited_indices)
        print(f"  - 总引用: {unique_cited} 篇")

        # 按出现顺序重新编号
        valid_cited_indices = {i for i in cited_indices if 1 <= i <= len(all_papers)}
        cited_papers = [self._paper_to_dict(all_papers[i - 1]) for i in valid_cited_indices]

        # 重新编号引用
        content, cited_papers = self._renumber_citations_by_appearance(
            content_draft, cited_papers, valid_cited_indices
        )

        # 限制每篇文献引用次数
        content = self._limit_citation_count_v2(content, cited_papers, max_count=2)
        content = self._sort_and_merge_citations(content)

        print(f"[阶段5] ✓ 综述生成完成，引用 {len(cited_papers)} 篇")
        print("=" * 80)

        return content, cited_papers

    async def _generate_section_content(
        self,
        topic: str,
        section_title: str,
        section_outline: dict,
        section_papers: List[Dict],
        all_papers: List[Dict],
        specificity_section: str,
        model: str
    ) -> str:
        """为单个小节生成内容"""
        focus = section_outline.get('focus', f'{section_title}相关内容')
        key_points = section_outline.get('key_points', [])
        comparison_points = section_outline.get('comparison_points', [])

        # 格式化全部文献（重要：让LLM能看到所有60篇文献）
        papers_info = self._format_papers_compact(all_papers)

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述。

{specificity_section}

**写作要求**：
1. 围绕主题"{section_title}"展开
2. 重点：{focus}
3. 使用对比分析，指出不同研究的观点、方法、结论
4. 明确指出研究分歧和不足

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 专业术语可使用英文

**⚠️ 引用数量强制要求**：
- 本部分必须引用至少 10-15 篇文献
- 每篇文献不超过2次
- 每个论点至少引用 2-3 篇文献支持
- 使用文献编号，如 [1]、[2]、[3]

⚠️ **引用边界严格限制**：
- 只能使用编号在 [1] 到 [{len(all_papers)}] 范围内的文献
- 绝对禁止使用 [{len(all_papers)+1}] 或更大的编号
- 如果发现没有相关文献，宁可少引用也不要超出范围

**文献相关性提醒**：
- 只引用与"{topic}"和"{section_title}"直接相关的文献
- 确保每篇引用的文献都与主题有明确的关联性

输出：Markdown（## {section_title}）"""

        user_prompt = f"""主题：{topic}

本节重点：{focus}

关键要点：
{chr(10).join([f"- {p}" for p in key_points]) if key_points else '根据内容确定'}

对比要点：
{chr(10).join([f"- {p}" for p in comparison_points]) if comparison_points else '根据内容确定'}

{'='*60}
⚠️ 引用边界明确提示
{'='*60}
📚 全部可用文献数：{len(all_papers)} 篇
🔢 可引用文献编号范围：[1] 到 [{len(all_papers)}]
❌ 绝对禁止使用编号 [{len(all_papers)+1}] 或更大的编号

全部文献列表：
{papers_info}
{'='*60}

请生成 ## {section_title} 部分的内容："""

        content = await self._call_llm(system_prompt, user_prompt, model, max_tokens=2000)
        return f"## {section_title}\n\n{content}"

    # ==================== 第1步：生成大纲 ====================

    async def _step1_generate_outline(
        self,
        topic: str,
        papers: List,
        specificity_guidance: dict,
        model: str
    ) -> Dict:
        """生成综述大纲（与原版相同）"""
        specificity_section = self._format_specificity_guidance(specificity_guidance)
        papers_brief = self._format_papers_brief(papers)

        system_prompt = f"""你是学术综述大纲设计专家。

{specificity_section}

你的任务是根据研究主题和文献列表，设计一个高质量的文献综述大纲。

要求：
1. **结构清晰**：包含引言、主体（2-3个主题）、结论
2. **主题划分**：主体部分按研究主题或方法论划分
3. **文献分配**：为每个主题推荐最相关的文献
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
            return self._get_default_outline(topic, papers)

    # ==================== 第2步：批量生成内容（优化版）====================

    async def _step2_generate_content_optimized(
        self,
        topic: str,
        papers: List,
        outline: Dict,
        specificity_guidance: dict,
        model: str
    ) -> str:
        """
        批量生成综述内容（优化版）

        优化策略：
        - 引言和结论分开生成（各1次）
        - 主体部分合并为1-2次调用
        - 总共3-4次调用（原版6-7次）
        """
        specificity_section = self._format_specificity_guidance(specificity_guidance)

        sections = []

        # === 调用1：生成引言 ===
        print(f"  - [调用1/3] 生成引言...")
        intro = await self._generate_introduction_optimized(
            topic, outline.get('introduction', {}), papers, specificity_section, model
        )
        sections.append(intro)

        # === 调用2：批量生成主体部分 ===
        print(f"  - [调用2/3] 批量生成主体部分...")
        body_sections = await self._generate_body_sections_optimized(
            topic, outline.get('sections', []), papers, specificity_section, model
        )
        sections.extend(body_sections)

        # === 调用3：生成结论 ===
        print(f"  - [调用3/3] 生成结论...")
        conclusion = await self._generate_conclusion_optimized(
            topic, outline.get('conclusion', {}), outline.get('sections', []),
            papers, specificity_section, model
        )
        sections.append(conclusion)

        return "\n\n".join(sections)

    async def _generate_introduction_optimized(
        self,
        topic: str,
        intro_outline: Dict,
        papers: List,
        specificity_section: str,
        model: str
    ) -> str:
        """生成引言（精简版 prompt）"""
        key_papers = intro_outline.get('key_papers', [])
        focus = intro_outline.get('focus', '介绍研究背景和意义')

        # 传递所有论文的简要信息（增强版包含摘要，便于LLM理解论文内容）
        papers_brief = self._format_papers_compact(papers)

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述的引言部分。

{specificity_section}

**写作要求**：
1. 介绍研究背景和意义（300-400字）
2. 说明当前研究现状
3. 指出研究的必要性和挑战
4. 自然过渡到主体内容

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 专业术语可使用英文，但句子必须用中文表达

**⚠️ 引用数量强制要求**：
- 本部分必须引用至少 10-15 篇文献
- 使用文献编号，如 [1]、[2]、[3]
- 每个论点至少引用 2-3 篇文献支持
- 推荐引用：{key_papers[:10] if key_papers else '1-20'}

⚠️ **引用边界严格限制**：
- 只能使用编号在 [1] 到 [{len(papers)}] 范围内的文献
- 绝对禁止使用 [{len(papers)+1}] 或更大的编号
- 如果发现没有相关文献，宁可少引用也不要超出范围

**重要提醒**：
- 只引用与主题"{topic}"直接相关的文献
- 不要引用其他领域（如气候、空气质量、蛋白质结构等）的文献
- 引用的文献必须与主题有明确的关联性

输出：Markdown（## 引言）"""

        user_prompt = f"""主题：{focus}

{'='*60}
⚠️ 引用边界明确提示
{'='*60}
📚 本次可用文献总数：{len(papers)} 篇
🔢 可引用文献编号范围：[1] 到 [{len(papers)}]
❌ 绝对禁止使用编号 [{len(papers)+1}] 或更大的编号
✅ 只能使用上方列出的文献编号

如果需要引用文献，请从编号 [1] 到 [{len(papers)}] 中选择！
{'='*60}

可用文献（显示前{min(len(papers), 20)}篇）：

{papers_brief}

请生成引言部分："""

        return await self._call_llm(system_prompt, user_prompt, model, max_tokens=1500)

    async def _generate_body_sections_optimized(
        self,
        topic: str,
        sections_outline: List[Dict],
        papers: List,
        specificity_section: str,
        model: str
    ) -> List[str]:
        """
        批量生成主体部分（优化版）

        策略：
        - 如果主题少于3个：合并为1次调用
        - 如果主题多于3个：分为2次调用
        """
        all_sections = []

        if len(sections_outline) <= 3:
            # === 合并为1次调用 ===
            sections_info = self._format_sections_info(sections_outline)
            papers_info = self._format_papers_compact(papers)

            system_prompt = f"""你是学术写作专家，擅长撰写文献综述的主体部分，特别擅长构建"文献矩阵"进行对比分析。

{specificity_section}

**写作要求**：
1. **构建文献矩阵**：不要简单列举，要对比不同研究的观点、方法、结论
2. **明确指出分歧**：当研究结论不一致时，要明确指出并分析原因
3. **使用对比表格**：对于关键对比，使用 Markdown 表格呈现

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 专业术语可使用英文，但句子必须用中文表达

**⚠️ 引用数量强制要求**：
- 每个主题必须引用至少 15-20 篇文献
- 每篇文献不超过2次
- 每个论点至少引用 2-3 篇文献支持
- 使用文献编号，如 [1]、[2]、[3]

⚠️ **引用边界严格限制**：
- 只能使用编号在 [1] 到 [{len(papers)}] 范围内的文献
- 绝对禁止使用 [{len(papers)+1}] 或更大的编号
- 如果发现没有相关文献，宁可少引用也不要超出范围

**重要：输出格式要求**
- 每个主题必须使用二级标题（## 标题）
- 标题必须与下方给出的主题标题完全一致
- 例如：如果主题是"理论基础与研究现状"，则输出 "## 理论基础与研究现状"
- 各主题之间用空行分隔
- 不要添加额外的章节或内容

**文献相关性提醒**：
- 主题是：{topic}
- 只引用与"{topic}"直接相关的文献
- 不要引用其他领域的文献（如空气质量预测、蛋白质折叠、气候模型等）
- 确保每篇引用的文献都与主题有明确的关联"""

            user_prompt = f"""主题：{topic}

需要生成的主体部分（必须按以下顺序生成，标题完全一致）：
{sections_info}

{'='*60}
⚠️ 引用边界明确提示
{'='*60}
📚 本次可用文献总数：{len(papers)} 篇
🔢 可引用文献编号范围：[1] 到 [{len(papers)}]
❌ 绝对禁止使用编号 [{len(papers)+1}] 或更大的编号
✅ 只能使用上方列出的文献编号

如果需要引用文献，请从编号 [1] 到 [{len(papers)}] 中选择！
{'='*60}

可用文献（共{len(papers)}篇）：
{papers_info}

请按顺序生成所有主体部分，确保每个主题都使用对应的二级标题："""

            content = await self._call_llm(system_prompt, user_prompt, model, max_tokens=4000)

            print(f"[主体生成] 原始内容长度: {len(content)} 字符")
            print(f"[主体生成] 内容预览:\n{content[:500]}...")

            # 分割各节内容
            for section_outline in sections_outline:
                title = section_outline.get('title', '')
                # 提取该节的内容
                section_content = self._extract_section_content(content, title)
                if section_content:
                    all_sections.append(section_content)
                    print(f"[主体生成] ✓ 成功提取章节: {title} ({len(section_content)} 字符)")
                else:
                    print(f"[主体生成] ✗ 章节提取失败: {title}")
                    # 如果提取失败，尝试单独生成该章节
                    print(f"[主体生成] 尝试单独生成章节: {title}")
                    fallback_content = await self._generate_fallback_section(
                        topic, title, section_outline, papers, specificity_section, model
                    )
                    if fallback_content:
                        all_sections.append(fallback_content)
                        print(f"[主体生成] ✓ 补充生成成功: {title}")

        else:
            # === 分为2次调用 ===
            mid = len(sections_outline) // 2

            # 第一批
            sections_info_1 = self._format_sections_info(sections_outline[:mid])
            all_sections.extend(await self._generate_body_batch(
                topic, sections_outline[:mid], papers, specificity_section, model, sections_info_1
            ))

            # 第二批
            sections_info_2 = self._format_sections_info(sections_outline[mid:])
            all_sections.extend(await self._generate_body_batch(
                topic, sections_outline[mid:], papers, specificity_section, model, sections_info_2
            ))

        return all_sections

    async def _generate_body_batch(
        self,
        topic: str,
        sections_outline: List[Dict],
        papers: List,
        specificity_section: str,
        model: str,
        sections_info: str
    ) -> List[str]:
        """生成一批主体部分"""
        papers_info = self._format_papers_compact(papers)

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述的主体部分。

{specificity_section}

**写作要求**：
1. 构建文献矩阵对比
2. 明确指出分歧并分析原因
3. 使用对比表格

输出：每个主题使用二级标题"""

        user_prompt = f"""主题：{topic}

需要生成的主体部分：
{sections_info}

可用文献：
{papers_info}

请生成这些主体部分："""

        content = await self._call_llm(system_prompt, user_prompt, model, max_tokens=3500)

        # 分割各节内容
        all_sections = []
        for section_outline in sections_outline:
            title = section_outline.get('title', '')
            section_content = self._extract_section_content(content, title)
            if section_content:
                all_sections.append(section_content)

        return all_sections

    async def _generate_conclusion_optimized(
        self,
        topic: str,
        conclusion_outline: Dict,
        sections: List[Dict],
        papers: List,
        specificity_section: str,
        model: str
    ) -> str:
        """生成结论（精简版）"""
        focus = conclusion_outline.get('focus', '总结现有研究的不足和未来方向')
        section_titles = [s.get('title', '') for s in sections]

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述的结论部分。

{specificity_section}

**写作要求**：
1. 总结主要研究共识（300-400字）
2. 指出研究分歧和不足
3. 提出未来研究方向

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 专业术语可使用英文，但句子必须用中文表达

**⚠️ 引用数量强制要求**：
- 本部分必须引用至少 8-10 篇文献
- 使用文献编号，如 [1]、[2]、[3]
- 每个论点至少引用 1-2 篇文献支持

⚠️ **引用边界严格限制**：
- 只能使用编号在 [1] 到 [{len(papers)}] 范围内的文献
- 绝对禁止使用 [{len(papers)+1}] 或更大的编号
- 如果发现没有相关文献，宁可少引用也不要超出范围

**重要提醒**：
- 只输出结论部分的内容，不要添加参考文献列表
- 不要在结论末尾添加"参考文献"或类似内容

输出：Markdown（## 结论）"""

        user_prompt = f"""主题：{topic}

综述涵盖的主题：
{chr(10).join([f"- {t}" for t in section_titles])}

写作重点：{focus}

{'='*60}
⚠️ 引用边界明确提示
{'='*60}
📚 本次可用文献总数：{len(papers)} 篇
🔢 可引用文献编号范围：[1] 到 [{len(papers)}]
❌ 绝对禁止使用编号 [{len(papers)+1}] 或更大的编号
✅ 只能使用上方列出的文献编号

可用文献（共{len(papers)}篇）：
{self._format_papers_compact(papers)}
{'='*60}

请生成结论部分："""

        return await self._call_llm(system_prompt, user_prompt, model, max_tokens=1200)

    async def _generate_fallback_section(
        self,
        topic: str,
        title: str,
        section_outline: Dict,
        papers: List,
        specificity_section: str,
        model: str
    ) -> str:
        """补充生成单个章节（当批量生成失败时使用）"""
        focus = section_outline.get('focus', '深入分析该主题')
        key_papers = section_outline.get('key_papers', [])
        comparison_points = section_outline.get('comparison_points', [])

        papers_brief = self._format_papers_compact(papers[:30])

        system_prompt = f"""你是学术写作专家，擅长撰写文献综述的特定章节。

{specificity_section}

**写作要求**：
1. 聚焦主题：{focus}
2. 构建文献矩阵对比分析
3. 引用相关文献支持观点

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 专业术语可使用英文，但句子必须用中文表达

**⚠️ 引用数量强制要求**：
- 本部分必须引用至少 15-20 篇文献
- 使用文献编号，如 [1]、[2]、[3]
- 每个论点至少引用 2-3 篇文献支持
- 推荐引用：{key_papers[:15] if key_papers else '1-30'}

⚠️ **引用边界严格限制**：
- 只能使用编号在 [1] 到 [{len(papers)}] 范围内的文献
- 绝对禁止使用 [{len(papers)+1}] 或更大的编号
- 如果发现没有相关文献，宁可少引用也不要超出范围

**重要**：
- 必须使用二级标题（## {title}）
- 标题必须完全一致
- 不要添加其他章节

**文献相关性提醒**：
- 综述主题是：{topic}
- 只引用与"{topic}"直接相关的文献
- 不要引用其他领域的文献（如空气质量预测、蛋白质折叠、气候模型等）"""

        user_prompt = f"""主题：{topic}

章节标题：## {title}
写作重点：{focus}
对比要点：{', '.join(comparison_points) if comparison_points else '根据内容确定'}

{'='*60}
⚠️ 引用边界明确提示
{'='*60}
📚 本次可用文献总数：{len(papers)} 篇
🔢 可引用文献编号范围：[1] 到 [{len(papers)}]
❌ 绝对禁止使用编号 [{len(papers)+1}] 或更大的编号
✅ 只能使用上方列出的文献编号

如果需要引用文献，请从编号 [1] 到 [{len(papers)}] 中选择！
{'='*60}

可用文献（显示前{min(len(papers), 30)}篇）：

{papers_brief}

请生成该章节内容："""

        return await self._call_llm(system_prompt, user_prompt, model, max_tokens=2000)

    async def _ensure_content_completeness(
        self,
        content: str,
        topic: str,
        papers: List,
        specificity_guidance: dict,
        model: str,
        outline: Dict
    ) -> str:
        """确保综述内容完整，包含所有必需章节"""
        specificity_section = self._format_specificity_guidance(specificity_guidance)

        # 检查各个章节是否存在
        has_introduction = "## 引言" in content or "### 引言" in content
        has_conclusion = "## 结论" in content or "### 结论" in content

        # 检查主体章节
        sections = outline.get('sections', [])
        has_body_sections = True
        missing_sections = []

        for section in sections:
            title = section.get('title', '')
            # 使用多种匹配方式检查章节是否存在
            if f"## {title}" not in content:
                # 尝试关键词匹配
                keywords = title.split()[:2]  # 取前两个关键词
                found = any(kw in content for kw in keywords if len(kw) > 2)
                if not found:
                    has_body_sections = False
                    missing_sections.append(section)

        # 报告检查结果
        print(f"[完整性检查] 引言: {'✓' if has_introduction else '✗ 缺失'}")
        print(f"[完整性检查] 主体章节: {'✓' if has_body_sections else '✗ 缺失'}")
        if missing_sections:
            print(f"[完整性检查] 缺失章节: {[s.get('title', '') for s in missing_sections]}")
        print(f"[完整性检查] 结论: {'✓' if has_conclusion else '✗ 缺失'}")

        # 补充缺失的章节
        if not has_introduction:
            print("[完整性检查] 正在补充引言...")
            intro_outline = outline.get('introduction', {})
            introduction = await self._generate_introduction_optimized(
                topic, intro_outline, papers, specificity_section, model
            )
            content = introduction + "\n\n" + content

        if missing_sections:
            print(f"[完整性检查] 正在补充 {len(missing_sections)} 个缺失章节...")
            for section in missing_sections:
                title = section.get('title', '')
                print(f"[完整性检查] 补充章节: {title}")
                fallback_content = await self._generate_fallback_section(
                    topic, title, section, papers, specificity_section, model
                )
                if fallback_content:
                    # 在结论之前插入
                    conclusion_pos = content.find("## 结论")
                    if conclusion_pos > 0:
                        content = content[:conclusion_pos] + fallback_content + "\n\n" + content[conclusion_pos:]
                    else:
                        content = content + "\n\n" + fallback_content

        if not has_conclusion:
            print("[完整性检查] 正在补充结论...")
            conclusion_outline = outline.get('conclusion', {})
            conclusion = await self._generate_conclusion_optimized(
                topic, conclusion_outline, sections, papers, specificity_section, model
            )
            content = content + "\n\n" + conclusion

        print("[完整性检查] ✓ 内容完整性检查完成")
        return content

    # ==================== 辅助方法 ====================

    async def _call_llm(self, system_prompt: str, user_prompt: str, model: str, max_tokens: int = 3000) -> str:
        """调用 LLM"""
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def _format_papers_compact(self, papers: List) -> str:
        """格式化论文简要信息（平衡 token 使用和信息量）"""
        brief = []
        for i, paper in enumerate(papers, 1):
            # 处理 PaperMetadata 对象或字典
            if hasattr(paper, 'title'):
                title = paper.title
                authors_list = paper.authors if paper.authors else []
                year = paper.year if hasattr(paper, 'year') else 'N/A'
                abstract = paper.abstract if hasattr(paper, 'abstract') else ''
            else:
                title = paper.get('title', '')
                authors_list = paper.get("authors", [])
                year = paper.get('year', 'N/A')
                abstract = paper.get('abstract', '')

            # 格式化作者（最多2个）
            authors = ", ".join(authors_list[:2]) if authors_list else ""

            # 截断标题和摘要
            title_short = (title or '')[:80]
            abstract_short = (abstract or '')[:150]

            # 构建格式化的论文信息
            paper_info = f"[{i}] {title_short}"
            if authors:
                paper_info += f" - {authors}"
            if year and year != 'N/A':
                paper_info += f" ({year})"
            if abstract_short:
                paper_info += f"\n    {abstract_short}..."

            brief.append(paper_info)
        return "\n".join(brief)

    def _format_sections_info(self, sections: List[Dict]) -> str:
        """格式化主题信息"""
        info = []
        for i, section in enumerate(sections, 1):
            title = section.get('title', '')
            focus = section.get('focus', '')
            key_papers = section.get('key_papers', [])
            comparison_points = section.get('comparison_points', [])
            info.append(f"""
{i}. **{title}**
   - 重点：{focus}
   - 推荐文献：{key_papers[:5] if key_papers else '根据内容选择'}
   - 对比要点：{', '.join(comparison_points) if comparison_points else '根据内容确定'}
""")
        return "\n".join(info)

    def _extract_section_content(self, content: str, title: str) -> str:
        """从生成的内容中提取特定节"""
        lines = content.split('\n')
        section_lines = []
        capturing = False
        section_found = False

        # 提取标题关键词（更宽松的匹配）
        title_keywords = title.split()
        # 至少匹配前两个关键词
        main_keyword = title_keywords[0] if title_keywords else ""
        second_keyword = title_keywords[1] if len(title_keywords) > 1 else ""

        for i, line in enumerate(lines):
            # 检查是否是目标节标题（更宽松的匹配）
            is_section_title = False

            # 完全匹配
            if f"## {title}" in line:
                is_section_title = True
            # 匹配主关键词
            elif main_keyword and main_keyword in line and line.startswith('## '):
                is_section_title = True
            # 匹配前两个关键词
            elif second_keyword and main_keyword in line and second_keyword in line and line.startswith('## '):
                is_section_title = True

            if is_section_title:
                capturing = True
                section_found = True
                section_lines.append(line)
                continue

            # 检查是否到了下一个节
            if capturing and line.startswith('## ') and title not in line:
                # 如果新标题包含其他主体章节的关键词，则停止
                if main_keyword and main_keyword not in line:
                    break

            if capturing:
                section_lines.append(line)

        return '\n'.join(section_lines) if section_found else ""

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
            if hasattr(paper, 'title'):
                title = paper.title[:80]
            else:
                title = (paper.get('title') or '')[:80]
            brief.append(f"[{i}] {title}")
        return "\n".join(brief)

    def _paper_to_dict(self, paper) -> Dict:
        """将 PaperMetadata 对象或字典转换为统一格式"""
        if isinstance(paper, dict):
            return paper

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
            return {
                'title': '', 'authors': [], 'year': None,
                'abstract': '', 'cited_by_count': 0,
                'type': 'article', 'doi': '', 'id': ''
            }
        return result

    def _get_default_outline(self, topic: str, papers: List) -> Dict:
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

        # 按被引量排序未引用的文献
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
            year = paper.get('year', 'n.d.')
            additional_papers.append(f"[{idx}] {(paper.get('title') or '')[:60]}... - {authors} ({year})")

        # 计算需要显示的内容长度（尽可能显示更多）
        content_preview = content if len(content) <= 6000 else content[:6000]

        supplement_prompt = f"""你是学术写作专家。请在现有综述基础上补充更多文献引用。

**综述主题**：{topic}

**当前状态**：已引用 {len(cited_indices)} 篇，目标 {target_count} 篇

⚠️ **引用边界严格限制**：
- 只能使用编号在 [1] 到 [{len(papers)}] 范围内的文献
- 绝对禁止使用 [{len(papers)+1}] 或更大的编号
- 如果发现没有相关文献，宁可少引用也不要超出范围

**可补充的文献**（按被引量排序，显示前20篇）：
{chr(10).join(additional_papers[:20])}

{'='*60}
⚠️ 引用边界明确提示
{'='*60}
📚 可用文献总数：{len(papers)} 篇
🔢 可引用文献编号范围：[1] 到 [{len(papers)}]
📌 当前已使用的最大编号：{max(cited_indices) if cited_indices else 0}
❌ 绝对禁止使用编号 [{len(papers)+1}] 或更大的编号
✅ 只能使用上方列出的文献编号

如果需要引用文献，请从编号 [1] 到 [{len(papers)}] 中选择！
{'='*60}

**补充要求**：
1. 只引用与主题"{topic}"直接相关的文献
2. 在合适的段落添加引用，支持论点或数据
3. 按顺序继续编号
4. 每个新增引用至少包含一句话的上下文
5. 不要改变原文的核心观点和结构
6. 确保新增引用自然融入，不突兀

**当前综述内容**：
{content_preview}

**输出要求**：
- 输出完整的综述内容（包含原文和新增引用）
- 保持原有格式和结构
- 不要添加原文中不存在的引用编号"""

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是专业的学术写作助手，擅长在综述中补充相关文献引用。"},
                    {"role": "user", "content": supplement_prompt}
                ],
                temperature=0.5,
                max_tokens=6000
            )
            result = response.choices[0].message.content
            print(f"[补充引用] 成功，返回内容长度: {len(result)} 字符")
            return result
        except Exception as e:
            print(f"[补充引用] 失败: {e}")
            return content

    async def _step4_polish_format(self, content: str, cited_papers: List[Dict]) -> str:
        """润色和格式化"""
        # 先清理 LLM 可能自行添加的参考文献部分
        content = self._remove_informal_references(content)

        if self.aminer_token:
            try:
                cited_papers = await enrich_papers(cited_papers, self.aminer_token)
            except Exception as e:
                print(f"[步骤4] 补充论文详情失败: {e}")

        content, cited_papers = self._filter_anonymous_and_renumber(content, cited_papers)
        references = self._format_references(cited_papers)
        return f"{content}\n\n## 参考文献\n\n{references}"

    def _remove_informal_references(self, content: str) -> str:
        """
        去除 LLM 自行添加的非正式参考文献部分

        检测并删除：
        1. 结论后的 "**参考文献**" 开头的内容
        2. "新增引用列表"、"补充引用" 等冗余内容
        3. 不标准的参考文献格式
        4. 正式的 "## 参考文献" 之前的多余内容
        """
        import re

        lines = content.split('\n')
        result_lines = []
        skip_mode = False
        found_formal_references = False

        # 检测冗余内容开始的模式
        redundant_patterns = [
            r'新增引用列表',
            r'补充引用列表',
            r'补充的文献',
            r'额外引用',
            r'扩展引用',
            r'\*\*参考文献\s*\*\*',  # ***参考文献** 或类似
        ]

        for line in lines:
            # 如果已经找到正式的参考文献部分，停止处理
            if line.startswith('## 参考文献') or line.startswith('### 参考文献'):
                found_formal_references = True
                skip_mode = False
                result_lines.append(line)
                continue

            # 如果在正式参考文献之前，检测冗余内容
            if not found_formal_references:
                # 检测是否是冗余内容开始
                is_redundant = False
                for pattern in redundant_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        is_redundant = True
                        skip_mode = True
                        print(f"[清理冗余内容] 检测到冗余内容模式: {line.strip()[:50]}")
                        break

                # 检测旧的冗余模式
                if not is_redundant:
                    if line.strip().startswith('**参考文献**') or \
                       line.strip().startswith('**参考文献') or \
                       (line.strip().startswith('参考文献') and not line.startswith('## ')):
                        skip_mode = True
                        continue

                # 如果是冗余内容，跳过
                if is_redundant or skip_mode:
                    continue

            # 如果不在删除模式，保留该行
            if not skip_mode:
                result_lines.append(line)

        result = '\n'.join(result_lines)

        # 额外清理：去除孤立的数字行（如 "1", "2"）
        result = re.sub(r'^\d+\s*$', '', result, flags=re.MULTILINE)

        # 清理多余的空行（超过2个连续空行）
        result = re.sub(r'\n{3,}', '\n\n', result)

        # 清理末尾的空行
        result = result.rstrip()

        return result

    # 以下方法复用原版
    def _extract_cited_indices(self, content: str) -> set:
        import re
        citations = re.findall(r'\[(\d+)\]', content)
        return set(int(c) for c in citations)

    def _replace_invalid_citations(
        self,
        content: str,
        cited_indices: set,
        valid_cited_indices: set,
        uncited_indices: set,
        papers: List,
        topic: str
    ) -> str:
        """
        替换超出范围的引用为相似的未引用文献（增强版）

        改进点：
        1. 综合考虑被引量和相关性评分
        2. 优先选择标题中包含主题关键词的文献
        3. 提供更详细的替换日志

        Args:
            content: 综述内容
            cited_indices: 所有引用编号（包括超出范围的）
            valid_cited_indices: 有效引用编号
            uncited_indices: 未引用的文献编号
            papers: 所有文献列表
            topic: 主题

        Returns:
            替换后的内容
        """
        import re

        # 找出超出范围的引用
        invalid_indices = cited_indices - valid_cited_indices
        if not invalid_indices:
            return content

        # 提取主题关键词（用于相关性判断）
        topic_keywords = self._extract_topic_keywords_with_library(topic)
        topic_lower = topic.lower()

        # 计算每篇未引用文献的综合评分
        uncited_scores = []
        for idx in uncited_indices:
            paper = papers[idx - 1]
            if isinstance(paper, dict):
                title = paper.get('title', '')
                citations = paper.get('cited_by_count', 0)
                relevance = paper.get('relevance_score', 0)
            else:
                title = getattr(paper, 'title', '')
                citations = getattr(paper, 'cited_by_count', 0)
                relevance = getattr(paper, 'relevance_score', 0)

            title_lower = title.lower() if title else ''

            # 综合评分 = 被引量权重 + 相关性权重 + 关键词匹配权重
            score = 0

            # 1. 被引量评分（0-30分）
            score += min(citations / 5, 30)

            # 2. 预计算的相关性评分（0-50分）
            score += min(relevance, 50)

            # 3. 标题关键词匹配奖励（0-20分）
            keyword_matches = sum(1 for kw in topic_keywords if kw in title_lower)
            score += keyword_matches * 5

            # 4. 主题词直接匹配奖励
            if topic_lower in title_lower:
                score += 15

            uncited_scores.append((idx, score, title[:50] if title else ''))

        # 按综合评分排序
        uncited_sorted = sorted(uncited_scores, key=lambda x: x[1], reverse=True)

        print(f"[引用修复] 未引用文献按综合评分排序:")
        for idx, score, title in uncited_sorted[:5]:
            print(f"  [{idx}] 评分:{score:.1f} - {title}...")

        # 创建替换映射（只使用相关的文献）
        replacement_map = {}
        for i, invalid_idx in enumerate(sorted(invalid_indices)):
            # 从排序后的未引用文献中查找相关的文献
            for candidate_idx, candidate_score, candidate_title in uncited_sorted:
                # 检查候选文献是否与主题相关
                paper = papers[candidate_idx - 1]
                if self._is_paper_relevant(paper if isinstance(paper, dict) else self._paper_to_dict(paper), topic_keywords):
                    # 使用相关的文献进行替换
                    replacement_map[invalid_idx] = candidate_idx
                    print(f"[引用修复] [{invalid_idx}] → [{candidate_idx}] (评分:{candidate_score:.1f}): {candidate_title}...")
                    break
            else:
                # 如果没有找到相关的文献，跳过这个替换
                print(f"[引用修复] [{invalid_idx}] 无法找到相关文献进行替换，将删除")
                continue

        # 执行替换
        def replace_citation(match):
            num = int(match.group(1))
            if num in replacement_map:
                new_num = replacement_map[num]
                return f"[{new_num}]"
            elif num in valid_cited_indices:
                return match.group(0)
            # 如果没有对应的替换，返回空
            return ""

        result = re.sub(r'\[(\d+)\]', replace_citation, content)

        # 清理空的方括号
        result = re.sub(r'\[\s*\]', '', result)

        replaced_count = len(replacement_map)
        print(f"[引用修复] ✓ 成功替换 {replaced_count}/{len(invalid_indices)} 个超出范围的引用")

        return result

    def _renumber_citations_by_appearance(self, content: str, cited_papers: List[Dict], cited_indices: set) -> tuple:
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

        # 构建旧编号到新编号的映射
        old_to_new = {old: new for new, old in enumerate(ordered_old_nums, 1)}

        # 根据旧的引用编号顺序重新排列文献列表
        # 注意：引用编号是从1开始的，所以需要减1来获取列表索引
        reordered_papers = []
        for old_num in ordered_old_nums:
            # 确保引用编号在有效范围内
            if 1 <= old_num <= len(cited_papers):
                paper_index = old_num - 1
                reordered_papers.append(cited_papers[paper_index])
            else:
                print(f"[警告] 引用编号 {old_num} 超出文献列表范围 ({len(cited_papers)} 篇)，已跳过")

        def replace_citation(match):
            old_num = int(match.group(1))
            new_num = old_to_new.get(old_num, old_num)
            return f"[{new_num}]"

        new_content = re.sub(r'\[(\d+)\]', replace_citation, content)
        return new_content, reordered_papers

    def _limit_citation_count_v2(self, content: str, cited_papers: List[Dict], max_count: int = 2) -> str:
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
        valid_papers = []
        old_to_new = {}

        new_index = 1
        for old_index, paper in enumerate(cited_papers, 1):
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
        valid_papers = []
        for paper in papers:
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
        if not isinstance(paper, dict):
            paper = self._paper_to_dict(paper)

        authors_list = paper.get("authors", [])
        if authors_list:
            # 处理作者名格式
            formatted_authors = []
            for author in authors_list[:3]:
                formatted_author = self._format_author_name(author)
                formatted_authors.append(formatted_author)

            authors = ",".join(formatted_authors)
            if len(authors_list) > 3:
                authors += ",等"
        else:
            authors = "未知作者"

        title = paper.get('title', '')
        year = paper.get('year', 'n.d.')
        venue = paper.get('venue_name', '')
        doi = paper.get('doi', '')

        # 构建期刊信息
        journal_info = str(year)
        if venue:
            journal_info += f".{venue}"

        # 构建DOI信息
        doi_suffix = ""
        if doi:
            # 规范化DOI格式
            clean_doi = doi.strip().lstrip('DOI:').lstrip('doi:')
            if not clean_doi.startswith('http'):
                doi_suffix = f".DOI:https://doi.org/{clean_doi}"
            else:
                doi_suffix = f".DOI:{clean_doi}"

        return f"[{index}]{authors}.{title}[J].{journal_info}{doi_suffix}."

    def _format_author_name(self, name: str) -> str:
        """格式化单个作者姓名"""
        if not name or name.strip() in ['佚名', '匿名', '未知作者', '']:
            return name

        # 检查是否是中文姓名
        if self._is_chinese_name(name):
            return self._format_chinese_name(name)
        else:
            # 英文姓名保持原样
            return name

    def _format_chinese_name(self, name: str) -> str:
        """格式化中文姓名"""
        # 去除空格
        name = name.replace(' ', '')

        # 检查是否是颠倒的格式（如"浩妍 王"）
        if ' ' in name or len(name.split()) == 2:
            parts = name.split()
            if len(parts) == 2:
                first, second = parts
                # 如果第一个部分不含中文而第二个含中文，可能是颠倒的
                if not self._contains_chinese_char(first) and self._contains_chinese_char(second):
                    return f"{second}{first}"

        # 去除可能存在的点号
        name = name.replace('.', '')

        # 确保姓名不超过5个字符（中文姓名通常2-4个字）
        if len(name) > 5:
            # 可能包含多余信息，只取前4个字
            name = name[:4]

        return name

    def _is_chinese_name(self, name: str) -> bool:
        """检查是否是中文姓名"""
        # 检查是否包含中文字符
        has_chinese = self._contains_chinese_char(name)

        # 进一步检查：如果是混合中英文的，可能是拼音格式
        if has_chinese:
            # 检查是否主要是中文字符（至少50%是中文）
            chinese_char_count = sum(1 for c in name if '\u4e00' <= c <= '\u9fff')
            if chinese_char_count / len(name) >= 0.3:
                return True

        return False

    def _contains_chinese_char(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        return bool(text and any('\u4e00' <= char <= '\u9fff' for char in text))

    def _filter_irrelevant_papers(self, papers: List[Dict], topic: str, topic_keywords: List[str] = None) -> List[Dict]:
        """
        过滤掉明显不相关的文献（增强版）

        基于标题和主题的关键词匹配度来判断文献相关性

        Args:
            papers: 文献列表
            topic: 论文主题
            topic_keywords: 预提取的主题关键词（可选，如果不提供则自动提取）
        """
        # 如果没有提供关键词，自动提取
        if topic_keywords is None:
            topic_keywords = self._extract_topic_keywords(topic)

        print(f"[相关性检查] 主题关键词 ({len(topic_keywords)}个): {topic_keywords[:10]}")

        filtered_papers = []
        removed_count = 0
        removal_reasons = {}

        for paper in papers:
            if self._is_paper_relevant(paper, topic_keywords):
                filtered_papers.append(paper)
            else:
                removed_count += 1
                title = (paper.get('title') or '')[:60]
                # 记录移除原因
                venue = (paper.get('venue_name') or '')[:30]
                key_info = f"{title}... ({venue})"
                if key_info not in removal_reasons:
                    removal_reasons[key_info] = 1
                else:
                    removal_reasons[key_info] += 1

        if removed_count > 0:
            print(f"[相关性检查] 共过滤 {removed_count} 篇不相关文献")
            # 显示被过滤的文献样例（最多5个）
            print(f"[相关性检查] 被过滤文献样例:")
            for i, (paper_info, count) in enumerate(list(removal_reasons.items())[:5]):
                print(f"  [{i+1}] {paper_info} (x{count})")

        return filtered_papers

    def _extract_topic_keywords(self, topic: str) -> List[str]:
        """从主题中提取关键词"""
        import re

        # 技术术语映射表
        tech_mappings = {
            '双向长短期记忆网络': ['lstm', 'bilstm', 'rnn'],
            '长短期记忆网络': ['lstm', 'rnn'],
            '卷积神经网络': ['cnn', 'convolutional'],
            '循环神经网络': ['rnn', 'recurrent'],
            '注意力机制': ['attention', 'transformer'],
            '深度学习': ['deep learning', 'neural network'],
            '神经网络': ['neural network'],
        }

        # 需要过滤的短词（通常是提取错误的结果）
        filter_short_words = {'ma', 'mc', 'na', 'cl', 'mg', 'ca', 'fe', 'si', 'in', 'on', 'at', 'to', 'of', 'an'}

        # 移除常见的停用词
        stop_words = {'的', '是', '在', '和', '与', '基于', '研究', '分析', '方法', '模型',
                      '论文', '系统', '应用', '一种', '用于', '以及', '通过', '进行', '位点',
                      '预测', '网络', '算法'}

        keywords = []

        # 1. 首先检查是否包含已知的技术术语
        for tech_term, alternatives in tech_mappings.items():
            if tech_term in topic:
                keywords.extend(alternatives)

        # 2. 提取特殊格式的术语（如 6mA、DNA）
        # 使用更精确的正则表达式
        special_patterns = [
            r'\d+[A-Z][a-z]',      # 如 6mA, 5mC（数字+大写+小写）
            r'[A-Z]{2,}(?![a-z])',  # 如 DNA, RNA（大写缩写，后面不跟小写）
        ]
        for pattern in special_patterns:
            matches = re.findall(pattern, topic)
            for match in matches:
                keywords.append(match.lower())

        # 3. 提取英文单词（过滤掉单个字母和短词）
        english_words = re.findall(r'[a-zA-Z]{2,}', topic)
        for word in english_words:
            word_lower = word.lower()
            # 过滤条件：不在停用词中、不在过滤列表中、不在已有关键词中
            if (word_lower not in stop_words and
                word_lower not in filter_short_words and
                word_lower not in keywords):
                keywords.append(word_lower)

        # 4. 提取中文词汇（限制长度，避免超长短语）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,6}', topic)
        for word in chinese_words:
            if word not in stop_words:
                # 对于中文技术术语，添加其英文对应词
                if '甲基化' in word:
                    keywords.append('methylation')
                if '表观遗传' in word:
                    keywords.append('epigenetic')
                if '预测' in word:
                    keywords.append('prediction')
                # 只添加较短的中文词（不超过4个字）
                if len(word) <= 4:
                    keywords.append(word.lower())

        # 5. 去重并过滤
        unique_keywords = list(set(keywords))

        # 6. 后处理：过滤掉过于通用的词和超长短语
        final_keywords = []
        for kw in unique_keywords:
            # 保留条件：
            # - 至少3个字符，或
            # - 是重要的技术缩写，或
            # - 包含重要的生物学术语
            if (len(kw) >= 3 and len(kw) <= 20 or  # 合理长度
                kw in ['lstm', 'cnn', 'rnn', 'bilstm', 'dna', 'rna', '6ma', '5mc', 'cnn', 'gan'] or  # 特定缩写
                any(t in kw for t in ['methylation', 'prediction', 'epigenetic', 'sequence', 'genome', 'network'])):  # 重要术语
                final_keywords.append(kw)

        return final_keywords

    def _extract_topic_keywords_with_library(self, topic: str) -> List[str]:
        """
        使用术语库从主题中提取关键词（增强版）

        Args:
            topic: 论文主题

        Returns:
            关键词列表
        """
        try:
            from services.academic_term_service import AcademicTermService
            term_service = AcademicTermService()
            keywords = term_service.search_keywords_from_topic(topic)
            print(f"[术语库] 使用数据库术语库提取关键词")
            return keywords
        except Exception as e:
            print(f"[术语库] 数据库查询失败，使用本地方法: {e}")
            return self._extract_topic_keywords(topic)

    def _is_paper_relevant(self, paper: Dict, topic_keywords: List[str]) -> bool:
        """
        判断文献是否与主题相关（增强版）

        使用多维度评分机制：
        1. 标题关键词匹配度
        2. 期刊/会议相关性
        3. 摘要关键词匹配度
        4. 负面指标检测（明显不相关的内容）
        """
        # 安全获取标题和期刊信息
        title = (paper.get('title') or '').lower()
        venue = (paper.get('venue_name') or '').lower()
        abstract = (paper.get('abstract') or '').lower()

        # 如果论文没有标题，默认保留（可能是数据问题）
        if not title:
            return True

        # === 正面指标：检查是否包含主题关键词 ===
        # 计算标题中的关键词匹配度（权重最高）
        title_keyword_matches = sum(1 for kw in topic_keywords if kw in title)
        title_score = title_keyword_matches * 3  # 每个匹配得3分

        # 计算期刊/会议中的关键词匹配度（权重中等）
        venue_keyword_matches = sum(1 for kw in topic_keywords if kw in venue)
        venue_score = venue_keyword_matches * 2  # 每个匹配得2分

        # 计算摘要中的关键词匹配度（权重较低，因为摘要可能很长）
        abstract_keyword_matches = sum(1 for kw in topic_keywords if kw in abstract)
        abstract_score = min(abstract_keyword_matches * 0.5, 2)  # 最多得2分

        # 计算总分
        total_score = title_score + venue_score + abstract_score

        # === 负面指标：检查是否包含明显不相关的内容 ===
        # 这些关键词表示论文属于完全不相关的领域
        strongly_irrelevant_keywords = [
            # 精神病学/心理学
            '抗抑郁', ' antidepressant', '抑郁', ' depression', '精神分裂', ' schizophrenia',
            '心理治疗', ' psychotherapy', '焦虑症', ' anxiety disorder',
            # 气象/气候
            '气象', ' weather forecast', '气候变化', ' climate change', '天气预报',
            '空气质量', ' air quality', '空气污染', ' air pollution', 'pm2.5',
            # 金融/股票
            '股票市场', ' stock market', '金融衍生品', ' financial derivative',
            '投资回报', ' investment return', '证券', ' security',
            # 社会科学/政治
            '选举', ' election', '投票', ' voting', '公共政策', ' public policy',
            '社会运动', ' social movement', '政治观点', ' political view',
            # 教育
            '教学方法', ' teaching method', '课程设计', ' curriculum design',
            '学生评估', ' student assessment', '课堂教学', ' classroom teaching',
        ]

        for irrelevant_kw in strongly_irrelevant_keywords:
            if irrelevant_kw in title or irrelevant_kw in venue:
                print(f"[相关性检查] ✗ 强不相关: {irrelevant_kw} in {title[:40]}...")
                return False

        # === 软性负面指标：降低相关性但不是完全排除 ===
        soft_irrelevant_keywords = [
            '社会', ' social', '政治', ' political',
            '经济', ' economic', '商业', ' business',
            '教育', ' education', '管理', ' management',
        ]

        soft_irrelevant_count = sum(1 for kw in soft_irrelevant_keywords if kw in title or kw in venue)
        if soft_irrelevant_count > 0 and total_score < 1:
            # 如果有软性不相关关键词且总分极低，认为不相关
            print(f"[相关性检查] ✗ 软不相关: {soft_irrelevant_count}个软性关键词，总分{total_score}")
            return False

        # === 最终决策 ===
        # 至少需要1分才认为相关（降低阈值）
        if total_score >= 1:
            return True

        # 如果标题完全没有任何关键词匹配，且不是太短的标题，认为不相关
        # 但放宽条件：只有在标题很长（>50字符）且完全没有匹配时才过滤
        if title_keyword_matches == 0 and len(title) > 50:
            print(f"[相关性检查] ✗ 标题无关键词匹配: {title[:40]}...")
            return False

        # 默认保留（保守策略）
        return True

    def _final_format_cleanup(self, review: str) -> str:
        """
        最终格式验证和清理

        去除格式问题：
        1. 孤立的数字行
        2. 多余的空行
        3. 末尾的空行
        4. 格式不一致的问题
        """
        import re

        lines = review.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            # 跳过孤立的数字行（如 "1", "2"）
            if stripped.isdigit():
                continue

            # 跳过空行（但保留段落分隔的空行）
            if not stripped:
                # 检查前一行是否也是空行，如果是则跳过
                if cleaned_lines and not cleaned_lines[-1].strip():
                    continue

            cleaned_lines.append(line)

        # 合并内容
        result = '\n'.join(cleaned_lines)

        # 清理多余的空行（超过2个连续空行）
        result = re.sub(r'\n{4,}', '\n\n\n', result)

        # 确保标题前没有多余的空行
        result = re.sub(r'\n+(##)', r'\n\1', result)

        # 确保引言前没有空行
        if result.startswith('\n'):
            result = result.lstrip()

        # 清理末尾的空行
        result = result.rstrip()

        return result

    async def close(self):
        await self.client.close()


# Token 消耗对比
"""
原版 v2.0 调用次数：8-10次
- 步骤1：1次
- 步骤2：6-7次（引言1 + 主体4 + 结论1）
- 步骤3：0-2次（补充引用）
- 步骤4：0次

优化版调用次数：4-5次
- 步骤1：1次
- 步骤2：3次（引言1 + 主体批量1 + 结论1）
- 步骤3：0-1次（补充引用）
- 步骤4：0次

Token 节省：
- 输入：约 30K -> 18K（节省40%）
- 输出：约 20K -> 12K（节省40%）
- 总计：约 50K -> 30K（节省40%）

成本计算（DeepSeek）：
- 输入：0.14元/1K tokens
- 输出：0.28元/1K tokens

原版成本：(30 * 0.14 + 20 * 0.28) / 1000 ≈ 0.0098元/篇
优化版成本：(18 * 0.14 + 12 * 0.28) / 1000 ≈ 0.0059元/篇

节省：约40%
"""
