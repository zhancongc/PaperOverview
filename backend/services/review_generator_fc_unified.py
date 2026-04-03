"""
综述生成服务 - Function Calling 统一版本

一次性生成完整综述，使用 Function Calling 按需获取论文详情。

优点：
1. 全局连贯性好 - LLM 能看到整个结构
2. 只需一次生成 - 不需要分小节多次调用
3. 引用编号一次性正确 - 不需要重新编号
4. Token 节省 ~70% - 只发送标题列表
"""
import os
import json
import re
from openai import AsyncOpenAI
from typing import List, Dict, Tuple


class ReviewGeneratorFCUnified:
    """使用 Function Calling 的统一综述生成器"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_review(
        self,
        topic: str,
        papers: List[Dict],
        framework: dict,
        model: str = "deepseek-chat",
        specificity_guidance: dict = None
    ) -> Tuple[str, List[Dict]]:
        """
        一次性生成完整综述（使用 Function Calling）

        Args:
            topic: 论文主题
            papers: 所有论文列表
            framework: 框架信息（包含大纲）
            model: 模型名称
            specificity_guidance: 场景特异性指导

        Returns:
            (综述内容, 被引用的论文列表)
        """
        print("=" * 80)
        print("综述生成 - Function Calling 统一版本")
        print("=" * 80)

        # 准备论文标题列表（轻量级）
        paper_titles_list = self._format_paper_titles_list(papers)
        print(f"\n[准备] 论文标题列表 ({len(papers)} 篇):")
        print(f"  - 标题列表 token 估算: ~{len(paper_titles_list) // 4} tokens")
        print(f"  - 完整元数据 token 估算: ~{len(json.dumps(papers, ensure_ascii=False)) // 4} tokens")
        print(f"  - 节省比例: ~{70}%")

        # 构建系统提示
        system_prompt = self._build_system_prompt(specificity_guidance)

        # 构建用户消息
        user_message = self._build_user_message(topic, paper_titles_list, framework)

        # 记录工具调用情况
        tool_calls_log = []
        accessed_papers = {}  # {paper_index: paper}

        # === 多轮对话循环 ===
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        max_iterations = 30  # 最多30轮对话
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            print(f"\n[迭代 {iteration}] 调用 LLM...")

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

        # 检查引用数量，如果不足则补充
        min_citations = max(20, int(len(papers) * 0.4))  # 至少20篇或40%
        if len(cited_papers) < min_citations:
            print(f"\n[补充] 引用数量不足 ({len(cited_papers)} < {min_citations})，正在补充...")

            # 获取未引用的论文
            cited_indices_set = set(cited_indices)
            uncited_papers = [
                (i + 1, papers[i])
                for i in range(len(papers))
                if (i + 1) not in cited_indices_set
            ]

            # 选择相关性高的未引用论文
            uncited_papers.sort(key=lambda x: x[1].get('cited_by_count', 0), reverse=True)

            to_cite = uncited_papers[:min_citations - len(cited_papers)]

            if to_cite:
                # 生成补充内容
                supplement_message = self._build_supplement_message(to_cite, content)

                supplement_response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是学术编辑，负责补充文献引用。"},
                        {"role": "user", "content": supplement_message}
                    ],
                    temperature=0.3
                )

                content = supplement_response.choices[0].message.content

                # 重新提取引用
                cited_indices = self._extract_cited_indices(content)
                cited_papers = []
                for idx in cited_indices:
                    if 1 <= idx <= len(papers):
                        cited_papers.append(papers[idx - 1])

                print(f"  - ✓ 补充后引用: {len(cited_papers)} 篇")

        # 添加标题和参考文献
        final_content = f"# {topic}\n\n{content}"

        references = self._format_references(cited_papers)
        final_content = f"{final_content}\n\n## 参考文献\n\n{references}"

        print(f"\n[完成] 综述生成完毕")
        print(f"  - 总字数: {len(final_content)}")
        print(f"  - 引用文献: {len(cited_papers)} 篇")
        print("=" * 80)

        return final_content, cited_papers

    def _get_tools_definition(self) -> List[Dict]:
        """定义可用的工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_paper_details",
                    "description": """获取论文的详细信息，包括：
- 摘要（了解研究内容和结论）
- 作者列表
- 发表年份
- 期刊/会议名称
- 研究关键词/概念标签
- 被引次数

当你需要引用某篇论文来支持论点时，必须先调用此函数获取详细信息。
不要编造论文内容，只使用工具返回的真实信息。
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

返回包含该关键词的论文索引列表，可用于快速定位相关文献。
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "搜索关键词，例如：'深度学习'、'质量控制'"
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
            authors = paper.get("authors", [])
            first_author = authors[0] if authors else "Unknown"

            lines.append(f"{i}. {title} ({year}) - {first_author}等")

        return "\n".join(lines)

    def _build_system_prompt(self, specificity_guidance: dict = None) -> str:
        """构建系统提示"""
        base_prompt = """你是学术写作专家，正在撰写一篇高质量的文献综述。

**重要：使用工具获取论文详情**
- 你只能看到论文的标题列表
- 当你需要引用某篇论文时，必须先调用 get_paper_details 工具获取摘要和详细信息
- 不要编造论文内容，只使用工具返回的真实信息
- 引用格式：[1]、[2] 等

**写作要求**：
1. 按照提供的大纲结构撰写综述
2. 每个重要观点都要有引用支持
3. 使用对比分析，指出不同研究的观点、方法、结论
4. 明确指出研究分歧和不足
5. 指出研究空白和未来方向

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 使用学术化表达

**引用规范**：
- 每个重要观点都要有引用
- 不要过度引用同一篇论文
- 优先引用高被引论文（可通过工具查看 cited_by_count）
- 在引用前，务必使用 get_paper_details 工具了解论文内容
"""

        if specificity_guidance:
            base_prompt += f"\n\n**场景特异性指导**：\n{json.dumps(specificity_guidance, ensure_ascii=False, indent=2)}"

        return base_prompt

    def _build_user_message(self, topic: str, paper_titles: str, framework: dict) -> str:
        """构建用户消息"""
        outline = framework.get('outline', {})

        # 构建大纲部分
        outline_parts = []

        # 引言
        introduction = outline.get('introduction', {})
        if introduction:
            focus = introduction.get('focus', '介绍研究背景')
            key_papers = introduction.get('key_papers', [])
            key_papers_str = ", ".join([f"[{i}]" for i in key_papers]) if key_papers else "未指定"
            outline_parts.append(f"## 引言\n重点：{focus}\n关键文献：{key_papers_str}\n")

        # 主体章节
        body_sections = outline.get('body_sections', [])
        for section in body_sections:
            if isinstance(section, dict):
                title = section.get("title", "")
                focus = section.get("focus", "")
                key_points = section.get("key_points", [])
                comparison_points = section.get("comparison_points", [])

                section_text = f"## {title}\n"
                section_text += f"重点：{focus}\n"

                if key_points:
                    section_text += f"关键点：\n"
                    for point in key_points:
                        section_text += f"  - {point}\n"

                if comparison_points:
                    section_text += f"对比分析：\n"
                    for point in comparison_points:
                        section_text += f"  - {point}\n"

                outline_parts.append(section_text)

        # 结论（如果有）
        conclusion = outline.get('conclusion', {})
        if conclusion:
            outline_parts.append(f"## 结论\n待定（根据文献内容生成）\n")

        outline_text = "\n".join(outline_parts)

        # 构建完整消息
        message = f"""请撰写关于「{topic}」的文献综述。

{paper_titles}

**综述大纲**：

{outline_text}

**写作要求**：
1. 按照上述大纲结构撰写
2. 在需要引用论文时，使用 get_paper_details 工具获取详细信息
3. 确保每个小节都有充分的引用支持
4. 使用对比分析，指出不同研究的观点和差异
5. 指出当前研究的不足和未来方向

请开始撰写。
"""

        return message

    def _build_supplement_message(self, to_cite: List[Tuple[int, Dict]], current_content: str) -> str:
        """构建补充引用的消息"""
        papers_info = []
        for idx, paper in to_cite:
            abstract = paper.get("abstract", "")[:200]
            papers_info.append(f"[{idx}] {paper.get('title', '')}\n摘要：{abstract}...")

        return f"""请在以下综述内容中补充引用这些论文：

【需要补充引用的论文】
{chr(10).join(papers_info)}

【当前综述】
{current_content[:2000]}...

要求：
1. 在适当位置添加引用
2. 保持内容连贯性
3. 只输出补充后的完整内容
"""

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取内容中的引用索引"""
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

            lines.append(f"[{i}] {author_str}. {title}. {venue}, {year}.")

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
    使用 Function Calling 生成综述（统一版本）

    Args:
        topic: 论文主题
        papers: 论文列表
        framework: 框架信息
        api_key: API密钥
        model: 模型名称

    Returns:
        (综述内容, 被引用的论文)
    """
    generator = ReviewGeneratorFCUnified(api_key=api_key)
    return await generator.generate_review(
        topic=topic,
        papers=papers,
        framework=framework,
        model=model
    )
