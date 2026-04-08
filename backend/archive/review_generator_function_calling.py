"""
⚠️ 已废弃 - 请使用 review_generator_fc_unified.py

综述生成服务 - Function Calling 版本 [已废弃]

此模块已被 review_generator_fc_unified.py 替代。
保留仅为向后兼容，新项目请使用 Function Calling 统一版本。

使用渐进式信息披露：
1. 初始只发送论文标题列表
2. LLM 需要时通过 function calling 获取论文详情
3. 节省 token + 提升注意力

优点：
- 减少 60-70% 的 token 消耗（不发送摘要）
- LLM 注意力更集中（标题列表 vs 完整元数据）
- 按需获取，只获取真正需要的文献
"""
import os
import warnings
import json
from openai import AsyncOpenAI
from typing import List, Dict, Tuple, Callable


class ReviewGeneratorFunctionCalling:
    """
    ⚠️ 已废弃 - 请使用 ReviewGeneratorFCUnified

    使用 Function Calling 的综述生成器 [已废弃]

    请使用 review_generator_fc_unified.py 中的 ReviewGeneratorFCUnified 类。
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        warnings.warn(
            "ReviewGeneratorFunctionCalling 已废弃，请使用 ReviewGeneratorFCUnified",
            DeprecationWarning,
            stacklevel=2
        )
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_review_with_tools(
        self,
        topic: str,
        papers: List[Dict],
        framework: dict,
        model: str = "deepseek-chat",
        specificity_guidance: dict = None
    ) -> Tuple[str, List[Dict]]:
        """
        ⚠️ 已废弃 - 请使用 ReviewGeneratorFCUnified.generate_review

        使用 function calling 生成综述 [已废弃]

        Args:
            topic: 论文主题
            papers: 所有论文列表
            framework: 框架信息
            model: 模型名称
            specificity_guidance: 场景特异性指导

        Returns:
            (综述内容, 实际被引用的文献列表)
        """
        warnings.warn(
            "ReviewGeneratorFunctionCalling.generate_review_with_tools 已废弃，请使用 ReviewGeneratorFCUnified.generate_review",
            DeprecationWarning,
            stacklevel=2
        )

        print("=" * 80)
        print("综述生成 - Function Calling 版本")
        print("=" * 80)

        # 准备论文标题列表（轻量级）
        paper_titles_list = self._format_paper_titles_list(papers)
        print(f"\n[准备] 论文标题列表 ({len(papers)} 篇):")
        print(f"  - 标题列表 token 估算: ~{len(paper_titles_list) // 4} tokens")
        print(f"  - 完整元数据 token 估算: ~{len(json.dumps(papers, ensure_ascii=False)) // 4} tokens")
        print(f"  - 节省比例: ~{70}%")

        # 获取大纲
        outline = framework.get('outline', {})
        body_sections = outline.get('body_sections', [])

        # 构建系统提示
        system_prompt = self._build_system_prompt(specificity_guidance)

        # 构建初始用户消息
        user_message = self._build_initial_message(topic, paper_titles_list, body_sections)

        # 记录工具调用情况
        tool_calls_log = []
        accessed_papers = {}  # {paper_index: paper}

        # === 多轮对话循环 ===
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        max_iterations = 20  # 最多20轮对话（防止无限循环）
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            print(f"\n[迭代 {iteration}] 调用 LLM...")

            # 调用 LLM
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=self._get_tools_definition(),
                tool_choice="auto",  # 让模型决定是否调用工具
                temperature=0.7
            )

            assistant_message = response.choices[0].message

            # 检查是否要调用工具
            if assistant_message.tool_calls:
                print(f"  - 模型请求 {len(assistant_message.tool_calls)} 个工具调用")

                # 添加助手消息（包含 tool_calls）
                messages.append(assistant_message)

                # 处理每个工具调用
                tool_responses = []
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    print(f"    [{function_name}] 参数: {function_args}")

                    # 执行工具调用
                    if function_name == "get_paper_details":
                        result = self._get_paper_details(
                            paper_index=function_args.get("paper_index"),
                            papers=papers
                        )

                        # 记录访问的论文
                        paper_index = function_args.get("paper_index")
                        if 1 <= paper_index <= len(papers):
                            accessed_papers[paper_index] = papers[paper_index - 1]

                        print(f"      → 返回 {len(str(result))} 字符")

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
                        result = self._search_papers_by_keyword(
                            keyword=function_args.get("keyword"),
                            papers=papers
                        )

                        print(f"      → 找到 {result.get('count', 0)} 篇匹配论文")

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

                # 批量添加工具响应
                messages.extend(tool_responses)

            else:
                # 没有工具调用，对话结束
                print(f"  - 生成完成，无更多工具调用")

                # 添加最终回复
                messages.append(assistant_message)

                content = assistant_message.content
                break

        # === 后处理 ===
        print(f"\n[统计] 工具调用情况:")
        print(f"  - 总迭代次数: {iteration}")
        print(f"  - 工具调用次数: {len(tool_calls_log)}")
        print(f"  - 访问的论文数: {len(accessed_papers)}")

        # 提取引用的论文
        cited_indices = self._extract_cited_indices(content)
        cited_papers = []

        for idx in cited_indices:
            if 1 <= idx <= len(papers):
                cited_papers.append(papers[idx - 1])

        print(f"  - 引用的论文数: {len(cited_papers)}")

        # 添加参考文献
        references = self._format_references(cited_papers)
        final_content = f"# {topic}\n\n{content}\n\n## 参考文献\n\n{references}"

        return final_content, cited_papers

    async def generate_review_by_sections_with_tools(
        self,
        topic: str,
        framework: dict,
        papers_by_section: dict,
        all_papers: List[Dict],
        model: str = "deepseek-chat",
        specificity_guidance: dict = None
    ) -> Tuple[str, List[Dict]]:
        """
        按小节生成综述（Function Calling 版本）

        结合两种方式的优点：
        1. 按小节生成，保持引用绑定
        2. 使用 Function Calling，减少 token 消耗

        Args:
            topic: 论文主题
            framework: 框架信息
            papers_by_section: 按小节分组的文献
            all_papers: 所有文献（用于全局编号）
            model: 模型名称
            specificity_guidance: 场景特异性指导

        Returns:
            (综述内容, 实际被引用的文献列表)
        """
        print("=" * 80)
        print("[阶段5] 按小节生成综述 - Function Calling 版本")
        print("=" * 80)

        # 准备所有论文的标题列表（轻量级）
        paper_titles_list = self._format_paper_titles_list(all_papers)
        print(f"\n[准备] 论文标题列表 ({len(all_papers)} 篇):")
        print(f"  - 标题列表 token 估算: ~{len(paper_titles_list) // 4} tokens")
        print(f"  - 节省比例: ~70%")

        # 获取大纲
        outline = framework.get('outline', {})
        body_sections = outline.get('body_sections', [])

        # 转换为字典格式，方便按标题查找
        outline_sections = {}
        for section in body_sections:
            if isinstance(section, dict):
                title = section.get('title', '')
                if title:
                    outline_sections[title] = section

        # 为每个小节生成内容
        section_contents = []
        all_cited_papers = {}  # 存储所有被引用的文献 {paper_id: paper}
        cited_indices_by_section = {}  # 每个小节的引用索引
        total_tool_calls = 0  # 总工具调用次数

        for section_title, section_outline in outline_sections.items():
            # 获取该小节的专属文献
            section_papers = papers_by_section.get(section_title, [])

            print(f"\n[阶段5] 生成小节: {section_title}")
            print(f"  - 该小节专属文献数: {len(section_papers)}")

            if not section_papers:
                print(f"  - 警告: 小节 '{section_title}' 没有专属文献，跳过")
                continue

            # 准备该小节的论文标题列表
            section_paper_titles = self._format_paper_titles_list(section_papers)

            # 生成该小节的内容
            section_content, section_cited_papers, tool_calls = await self._generate_section_with_tools(
                topic=topic,
                section_title=section_title,
                section_outline=section_outline,
                section_papers=section_papers,
                specificity_guidance=specificity_guidance,
                model=model
            )

            total_tool_calls += tool_calls

            # 提取引用索引
            section_cited_indices = self._extract_cited_indices(section_content)
            cited_count = len(section_cited_indices)
            total_count = len(section_papers)

            print(f"  - 该小节引用: {cited_count}/{total_count} 篇")
            print(f"  - 工具调用次数: {tool_calls}")

            # 如果引用不足，补充引用
            if cited_count < min(5, total_count):  # 至少引用5篇或全部引用
                print(f"  - ⚠️ 引用数量不足，正在补充...")
                section_content = await self._supplement_section_citations_with_tools(
                    section_content=section_content,
                    section_title=section_title,
                    section_papers=section_papers,
                    topic=topic,
                    model=model
                )
                section_cited_indices = self._extract_cited_indices(section_content)
                print(f"  - ✓ 补充后引用: {len(section_cited_indices)}/{total_count} 篇")

            section_contents.append(section_content)
            cited_indices_by_section[section_title] = section_cited_indices

            # 记录被引用的文献
            for idx in section_cited_indices:
                if 1 <= idx <= len(section_papers):
                    paper = section_papers[idx - 1]
                    paper_id = paper.get('id')
                    if paper_id:
                        all_cited_papers[paper_id] = paper

        # 合并所有小节内容
        content_draft = "\n\n".join(section_contents)

        # 构建最终的文献列表（去重）
        cited_papers = list(all_cited_papers.values())
        cited_papers = [self._paper_to_dict(p) for p in cited_papers]

        # 重新编号引用（全局重新编号）
        paper_id_to_new_index = {}
        for i, paper in enumerate(cited_papers, 1):
            paper_id_to_new_index[paper.get('id')] = i

        # 替换所有引用编号
        import re
        def replace_citation(match):
            old_index = int(match.group(1))
            for section_title, indices in cited_indices_by_section.items():
                if old_index in indices:
                    if old_index <= len(papers_by_section.get(section_title, [])):
                        section_papers = papers_by_section.get(section_title, [])
                        if old_index <= len(section_papers):
                            paper = section_papers[old_index - 1]
                            paper_id = paper.get('id')
                            if paper_id in paper_id_to_new_index:
                                return f"[{paper_id_to_new_index[paper_id]}]"
            return match.group(0)

        content = re.sub(r'\[(\d+)\]', replace_citation, content_draft)

        # 添加综述标题和参考文献
        title_line = f"# {topic}\n\n"
        content = title_line + content

        references = self._format_references(cited_papers)
        content = f"{content}\n\n## 参考文献\n\n{references}"

        print(f"\n[阶段5] ✓ 综述生成完成")
        print(f"  - 总工具调用次数: {total_tool_calls}")
        print(f"  - 引用论文数: {len(cited_papers)}")
        print("=" * 80)

        return content, cited_papers

    async def _generate_section_with_tools(
        self,
        topic: str,
        section_title: str,
        section_outline: dict,
        section_papers: List[Dict],
        specificity_guidance: dict,
        model: str
    ) -> Tuple[str, List[Dict], int]:
        """
        为单个小节生成内容（Function Calling 版本）

        Returns:
            (小节内容, 被引用的论文, 工具调用次数)
        """
        focus = section_outline.get('focus', f'{section_title}相关内容')
        key_points = section_outline.get('key_points', [])
        comparison_points = section_outline.get('comparison_points', [])

        # 准备该小节的论文标题列表（轻量级）
        paper_titles_list = self._format_paper_titles_list(section_papers)

        # 构建系统提示
        specificity_section = self._format_specificity_guidance(specificity_guidance)
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

**引用规范**：
- 每个重要观点都要有引用
- 在正文中引用时，使用"作者(年份)"格式，如"Zhang et al. (2023)提出..."或"(Zhang et al., 2023)"
- **禁止在正文中直接使用论文标题作为引用方式**
- 在引用论文前，使用 get_paper_details 工具获取论文详细信息（包括作者、年份等）
- 不要编造论文内容
"""

        # 构建用户消息
        key_points_str = "\n".join([f"  - {p}" for p in key_points]) if key_points else ""
        comparison_str = "\n".join([f"  - {p}" for p in comparison_points]) if comparison_points else ""

        user_message = f"""请撰写关于「{section_title}」的小节内容。

{paper_titles_list}

**重点论述**：
{focus}

**关键点**：
{key_points_str if key_points_str else "  - 根据文献内容总结"}

**对比分析**：
{comparison_str if comparison_str else "  - 比较不同研究的观点和方法"}

请开始撰写。需要引用论文时，使用 get_paper_details 工具获取详细信息。
"""

        # 多轮对话循环
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        tool_calls_count = 0
        max_iterations = 15
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # 调用 LLM
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=self._get_tools_definition(),
                tool_choice="auto",
                temperature=0.7
            )

            assistant_message = response.choices[0].message

            # 检查是否要调用工具
            if assistant_message.tool_calls:
                tool_calls_count += len(assistant_message.tool_calls)
                messages.append(assistant_message)

                # 处理工具调用
                tool_responses = []
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if function_name == "get_paper_details":
                        result = self._get_paper_details(
                            paper_index=function_args.get("paper_index"),
                            papers=section_papers
                        )
                        tool_responses.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                    elif function_name == "search_papers_by_keyword":
                        result = self._search_papers_by_keyword(
                            keyword=function_args.get("keyword"),
                            papers=section_papers
                        )
                        tool_responses.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                messages.extend(tool_responses)

            else:
                messages.append(assistant_message)
                break

        content = assistant_message.content

        # 提取被引用的论文
        cited_indices = self._extract_cited_indices(content)
        cited_papers = []
        for idx in cited_indices:
            if 1 <= idx <= len(section_papers):
                cited_papers.append(section_papers[idx - 1])

        return content, cited_papers, tool_calls_count

    async def _supplement_section_citations_with_tools(
        self,
        section_content: str,
        section_title: str,
        section_papers: List[Dict],
        topic: str,
        model: str
    ) -> str:
        """补充引用（使用工具获取论文信息）"""
        cited_indices = self._extract_cited_indices(section_content)
        missing_indices = [i for i in range(1, len(section_papers) + 1) if i not in cited_indices]

        if not missing_indices:
            return section_content

        # 选择前5篇未引用的论文
        to_add = missing_indices[:5]

        # 获取这些论文的信息
        papers_info = []
        for idx in to_add:
            paper = section_papers[idx - 1]
            papers_info.append(f"{idx}. {paper.get('title', '')} - {paper.get('abstract', '')[:200]}...")

        # 构建补充消息
        supplement_message = f"""请在以下内容中补充引用这些论文：

{chr(10).join(papers_info)}

要求：
1. 在适当位置添加引用 [{']}, ['.join(map(str, to_add))}]
2. 保持内容连贯性
3. 只输出补充后的完整内容
"""

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是学术编辑，负责补充文献引用。"},
                {"role": "user", "content": supplement_message + "\n\n原文：\n" + section_content}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

    def _format_specificity_guidance(self, specificity_guidance: dict = None) -> str:
        """格式化场景特异性指导"""
        if not specificity_guidance:
            return ""

        sections = []
        for key, value in specificity_guidance.items():
            if value:
                sections.append(f"- {key}: {value}")

        if sections:
            return "**场景特异性指导**：\n" + "\n".join(sections)
        return ""

    def _paper_to_dict(self, paper: Dict) -> Dict:
        """确保论文是字典格式"""
        if hasattr(paper, 'to_paper_dict'):
            return paper.to_paper_dict()
        return dict(paper)

    def _get_tools_definition(self) -> List[Dict]:
        """定义可用的工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_paper_details",
                    "description": """获取论文的详细信息，包括：
- 摘要（摘要是最重要的，用于了解研究内容）
- 作者
- 发表年份
- 期刊/会议
- 研究关键词/概念标签

当你需要引用某篇论文来支持论点时，调用此函数获取详细信息。
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "paper_index": {
                                "type": "integer",
                                "description": "论文在列表中的索引（1-60），例如：[5] 表示索引为5的论文"
                            }
                        },
                        "required": ["paper_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_papers_by_keyword",
                    "description": """根据关键词搜索相关的论文。
当你在列表中找不到与某个主题相关的论文时，可以使用此函数搜索。

返回包含该关键词的论文索引列表。
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "搜索关键词，例如：'深度学习'、'质量'"
                            }
                        },
                        "required": ["keyword"]
                    }
                }
            }
        ]

    def _get_paper_details(self, paper_index: int, papers: List[Dict]) -> Dict:
        """获取论文详细信息（工具函数实现）"""
        if not 1 <= paper_index <= len(papers):
            return {
                "error": f"论文索引 {paper_index} 超出范围（1-{len(papers)}）"
            }

        paper = papers[paper_index - 1]

        return {
            "index": paper_index,
            "title": paper.get("title", ""),
            "authors": paper.get("authors", [])[:5],  # 最多5个作者
            "year": paper.get("year"),
            "venue": paper.get("venue_name", ""),
            "abstract": paper.get("abstract", "")[:2000],  # 限制摘要长度
            "concepts": paper.get("concepts", [])[:10],  # 最多10个概念
            "cited_by_count": paper.get("cited_by_count", 0)
        }

    def _search_papers_by_keyword(self, keyword: str, papers: List[Dict]) -> Dict:
        """根据关键词搜索论文（工具函数实现）"""
        keyword_lower = keyword.lower()
        matches = []

        for i, paper in enumerate(papers, 1):
            # 在标题中搜索
            if keyword_lower in paper.get("title", "").lower():
                matches.append({
                    "index": i,
                    "title": paper.get("title", "")
                })
                continue

            # 在概念标签中搜索
            concepts = paper.get("concepts", [])
            if concepts:
                for concept in concepts:
                    if concept and keyword_lower in concept.lower():
                        matches.append({
                            "index": i,
                            "title": paper.get("title", "")
                        })
                        break

        return {
            "keyword": keyword,
            "count": len(matches),
            "matches": matches[:10]  # 最多返回10个结果
        }

    def _format_paper_titles_list(self, papers: List[Dict]) -> str:
        """格式化论文标题列表（轻量级）"""
        lines = ["【参考文献列表】"]
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            year = paper.get("year", "Unknown")
            first_author = paper.get("authors", ["Unknown"])[0] if paper.get("authors") else "Unknown"

            lines.append(f"{i}. {title} ({year}) - {first_author}等")

        return "\n".join(lines)

    def _build_system_prompt(self, specificity_guidance: dict = None) -> str:
        """构建系统提示"""
        base_prompt = """你是学术写作专家，正在撰写一篇文献综述。

**重要：使用工具获取论文详情**
- 你只能看到论文的标题列表
- 当你需要引用某篇论文时，必须先调用 get_paper_details 工具获取摘要
- 不要编造论文内容，只使用工具返回的真实信息

**写作要求**：
1. 按小节结构撰写综述
2. 每个小节都要有引用支持
3. 使用对比分析，指出不同研究的观点
4. 明确指出研究分歧和不足
5. 只使用中文撰写
6. 引用格式：[1]、[2] 等

**引用规范**：
- 每个重要观点都要有引用
- 在正文中引用时，使用"作者(年份)"格式，如"Zhang et al. (2023)提出..."或"(Zhang et al., 2023)"
- **禁止在正文中直接使用论文标题作为引用方式**
- 不要过度引用同一篇论文
- 优先引用高被引论文（可通过工具查看 cited_by_count）
"""

        if specificity_guidance:
            base_prompt += f"\n\n**场景特异性指导**：\n{json.dumps(specificity_guidance, ensure_ascii=False)}"

        return base_prompt

    def _build_initial_message(self, topic: str, paper_titles: str, sections: List[Dict]) -> str:
        """构建初始用户消息"""
        message = f"""请撰写关于「{topic}」的文献综述。

{paper_titles}

**综述结构**：
"""

        # 添加小节结构
        for section in sections:
            if isinstance(section, dict):
                title = section.get("title", "")
                focus = section.get("focus", "")
                message += f"\n### {title}\n重点：{focus}\n"

        message += """

请开始撰写。在需要引用论文时，使用 get_paper_details 工具获取详细信息。
"""

        return message

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取内容中的引用索引"""
        import re
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, content)
        indices = [int(m) for m in matches]
        return sorted(set(indices))

    def _format_references(self, papers: List[Dict]) -> str:
        """格式化参考文献"""
        lines = []
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", "")
            venue = paper.get("venue_name", "")

            if authors:
                author_str = f"{authors[0]}等" if len(authors) > 1 else authors[0]
            else:
                author_str = "Unknown"

            lines.append(f"{i}. {author_str}. {title}. {venue}, {year}.")

        return "\n".join(lines)


# 便捷函数
async def generate_review_with_function_calling(
    topic: str,
    papers: List[Dict],
    framework: dict,
    api_key: str,
    model: str = "deepseek-chat"
) -> Tuple[str, List[Dict]]:
    """
    使用 function calling 生成综述

    Args:
        topic: 论文主题
        papers: 论文列表
        framework: 框架信息
        api_key: API密钥
        model: 模型名称

    Returns:
        (综述内容, 被引用的论文)
    """
    generator = ReviewGeneratorFunctionCalling(api_key=api_key)
    return await generator.generate_review_with_tools(
        topic=topic,
        papers=papers,
        framework=framework,
        model=model
    )
