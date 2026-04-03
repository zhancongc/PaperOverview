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
        specificity_guidance: dict = None,
        target_citation_count: int = 50,
        min_citation_count: int = 50,
        recent_years_ratio: float = 0.5,
        english_ratio: float = 0.3,
        enable_reasoning: bool = False
    ) -> Tuple[str, List[Dict]]:
        """
        一次性生成完整综述（使用 Function Calling）

        Args:
            topic: 论文主题
            papers: 所有论文列表
            framework: 框架信息（包含大纲）
            model: 模型名称
            specificity_guidance: 场景特异性指导
            target_citation_count: 目标引用数量
            min_citation_count: 最小引用数量（默认50）
            recent_years_ratio: 近5年文献比例要求（默认0.5，即50%）
            english_ratio: 英文文献比例要求（默认0.3，即30%）
            enable_reasoning: 是否启用思考模式（仅对 deepseek-reasoner 有效）

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
        print(f"  - 节省比例: ~{95}%")
        print(f"  - 目标引用数: {target_citation_count} 篇")

        # 构建系统提示
        system_prompt = self._build_system_prompt(
            specificity_guidance,
            target_citation_count,
            len(papers),
            recent_years_ratio,
            english_ratio
        )

        # 构建用户消息
        user_message = self._build_user_message(
            topic,
            paper_titles_list,
            framework,
            target_citation_count,
            len(papers),
            recent_years_ratio,
            english_ratio
        )

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

        # 根据模型确定 max_tokens
        def get_max_tokens(model_name: str) -> int:
            """获取模型的最大输出长度"""
            if "reasoner" in model_name:
                return 64000  # deepseek-reasoner 最大 64K
            return 8192  # deepseek-chat 最大 8K

        max_tokens = get_max_tokens(model)
        print(f"[配置] 使用模型: {model}, 最大输出: {max_tokens} tokens")

        # 构建 extra_body 参数（用于控制思考模式）
        extra_body = {}
        if "reasoner" in model and not enable_reasoning:
            # 关闭思考模式，节省输出时间和 tokens
            extra_body["thinking_budget"] = 1  # 设置为最小值，强制跳过思考
            print(f"[配置] 已关闭思考模式，直接输出结果")

        while iteration < max_iterations:
            iteration += 1

            print(f"\n[迭代 {iteration}] 调用 LLM...")

            # 调用 LLM
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=self._get_tools_definition(len(papers)),
                tool_choice="auto",
                temperature=0.7,
                max_tokens=max_tokens,
                extra_body=extra_body if extra_body else None
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

        # 检查引用数量和质量
        current_year = 2026  # 当前年份
        recent_threshold = current_year - 5  # 近5年阈值

        # 统计当前引用情况
        def _check_citation_quality(papers_list):
            """检查引用质量"""
            if not papers_list:
                return {"total": 0, "recent": 0, "recent_ratio": 0, "english": 0, "english_ratio": 0}

            total = len(papers_list)
            recent_count = sum(1 for p in papers_list if p.get("year") and p.get("year", 0) >= recent_threshold)
            english_count = sum(1 for p in papers_list if p.get("lang") == "en")

            return {
                "total": total,
                "recent": recent_count,
                "recent_ratio": recent_count / total if total > 0 else 0,
                "english": english_count,
                "english_ratio": english_count / total if total > 0 else 0
            }

        citation_stats = _check_citation_quality(cited_papers)

        print(f"\n[质量检查] 当前引用统计:")
        print(f"  - 总引用数: {citation_stats['total']} (要求: ≥{min_citation_count})")
        print(f"  - 近5年文献: {citation_stats['recent']} 篇 ({citation_stats['recent_ratio']:.1%}) (要求: ≥{recent_years_ratio:.0%})")
        print(f"  - 英文文献: {citation_stats['english']} 篇 ({citation_stats['english_ratio']:.1%}) (要求: ≥{english_ratio:.0%})")

        # 检查是否需要补充
        needs_supplement = False
        supplement_reasons = []

        if citation_stats['total'] < min_citation_count:
            needs_supplement = True
            supplement_reasons.append(f"数量不足 ({citation_stats['total']} < {min_citation_count})")

        if citation_stats['recent_ratio'] < recent_years_ratio:
            needs_supplement = True
            supplement_reasons.append(f"近5年文献比例不足 ({citation_stats['recent_ratio']:.1%} < {recent_years_ratio:.0%})")

        if citation_stats['english_ratio'] < english_ratio:
            needs_supplement = True
            supplement_reasons.append(f"英文文献比例不足 ({citation_stats['english_ratio']:.1%} < {english_ratio:.0%})")

        if needs_supplement:
            print(f"\n[补充] 需要补充引用: {', '.join(supplement_reasons)}")

            # 获取未引用的论文（过滤掉没有 abstract 的论文）
            cited_indices_set = set(cited_indices)
            uncited_papers = [
                (i + 1, papers[i])
                for i in range(len(papers))
                if (i + 1) not in cited_indices_set
                and papers[i].get("abstract")  # 必须有 abstract
            ]

            # 分类未引用的论文
            recent_uncited = [(idx, p) for idx, p in uncited_papers if p.get("year", 0) >= recent_threshold]
            english_uncited = [(idx, p) for idx, p in uncited_papers if p.get("lang") == "en"]

            # 按优先级排序
            def _paper_priority(item):
                idx, paper = item
                score = 0
                # 近5年加分
                if paper.get("year", 0) >= recent_threshold:
                    score += 100
                # 英文加分
                if paper.get("lang") == "en":
                    score += 50
                # 相关性加分
                score += paper.get('relevance_score', 0) * 10
                # 被引量加分
                score += min(paper.get('cited_by_count', 0) / 10, 50)
                return score

            uncited_papers.sort(key=_paper_priority, reverse=True)

            # 计算需要补充的数量
            need_total = max(0, min_citation_count - citation_stats['total'])
            need_recent = max(0, int(min_citation_count * recent_years_ratio) - citation_stats['recent'])
            need_english = max(0, int(min_citation_count * english_ratio) - citation_stats['english'])

            # 选择要补充的论文
            to_cite = []
            used_indices = set()

            # 优先补充近5年文献
            for idx, paper in recent_uncited:
                if len(to_cite) >= need_total:
                    break
                if idx not in used_indices:
                    to_cite.append((idx, paper))
                    used_indices.add(idx)

            # 补充英文文献
            for idx, paper in english_uncited:
                if len(to_cite) >= need_total:
                    break
                if idx not in used_indices:
                    to_cite.append((idx, paper))
                    used_indices.add(idx)

            # 补充其他高质量论文
            for idx, paper in uncited_papers:
                if len(to_cite) >= need_total:
                    break
                if idx not in used_indices:
                    to_cite.append((idx, paper))
                    used_indices.add(idx)

            if to_cite:
                # 生成补充内容
                supplement_message = self._build_supplement_message(to_cite, content)

                supplement_response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是学术编辑，负责补充文献引用。"},
                        {"role": "user", "content": supplement_message}
                    ],
                    temperature=0.3,
                    max_tokens=max_tokens,
                    extra_body=extra_body if extra_body else None
                )

                content = supplement_response.choices[0].message.content

                # 重新提取引用
                cited_indices = self._extract_cited_indices(content)
                cited_papers = []
                for idx in cited_indices:
                    if 1 <= idx <= len(papers):
                        cited_papers.append(papers[idx - 1])

                # 重新检查质量
                final_stats = _check_citation_quality(cited_papers)
                print(f"  - ✓ 补充后引用: {final_stats['total']} 篇")
                print(f"    - 近5年: {final_stats['recent']} 篇 ({final_stats['recent_ratio']:.1%})")
                print(f"    - 英文: {final_stats['english']} 篇 ({final_stats['english_ratio']:.1%})")

        # 添加标题和参考文献
        final_content = f"# {topic}\n\n{content}"

        references = self._format_references(cited_papers)
        final_content = f"{final_content}\n\n## 参考文献\n\n{references}"

        print(f"\n[完成] 综述生成完毕")
        print(f"  - 总字数: {len(final_content)}")
        print(f"  - 引用文献: {len(cited_papers)} 篇")
        print("=" * 80)

        return final_content, cited_papers

    def _get_tools_definition(self, paper_count: int = 100) -> List[Dict]:
        """定义可用的工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_paper_details",
                    "description": f"""获取论文的详细信息，包括：
- 摘要（了解研究内容和结论）
- 作者列表
- 发表年份
- 期刊/会议名称
- 研究关键词/概念标签
- 被引次数

当你需要引用某篇论文来支持论点时，必须先调用此函数获取详细信息。
不要编造论文内容，只使用工具返回的真实信息。

重要：论文索引必须在有效范围内（1-{paper_count}）。
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "paper_index": {
                                "type": "integer",
                                "description": f"论文在列表中的索引（1-{paper_count}），例如：[5] 表示索引为5的论文"
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

    def _build_system_prompt(
        self,
        specificity_guidance: dict = None,
        target_citation_count: int = 50,
        paper_count: int = 100,
        recent_years_ratio: float = 0.5,
        english_ratio: float = 0.3
    ) -> str:
        """构建系统提示"""
        base_prompt = f"""你是学术写作专家，正在撰写一篇高质量的文献综述。

**重要：使用工具获取论文详情**
- 你只能看到论文的标题列表（共 {paper_count} 篇）
- 当你需要引用某篇论文时，必须先调用 get_paper_details 工具获取摘要和详细信息
- 不要编造论文内容，只使用工具返回的真实信息
- 引用格式：[1]、[2] 等

**写作要求**：
1. 按照提供的大纲结构撰写综述
2. 每个重要观点都要有引用支持
3. 使用对比分析，指出不同研究的观点、方法、结论
4. 明确指出研究分歧和不足
5. 指出研究空白和未来方向

**引用要求**（必须严格遵守，否则任务失败）：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文（硬性要求）
- **近5年文献比例**：至少 {recent_years_ratio:.0%}（当前年份 2026，近5年指 2021-2026）
- **英文文献比例**：至少 {english_ratio:.0%}
- 引用编号范围：[1] 到 [{paper_count}]，不要超出此范围
- **不要过度引用同一篇论文**：同一篇论文不要被引用超过2次
- **按顺序引用**：正文中首次出现的引用应该是[1]，然后是[2]，依此类推
- 优先引用高被引论文（可通过工具查看 cited_by_count）
- 在引用前，务必使用 get_paper_details 工具了解论文内容，包括年份和语言

**重要：主动引用策略**
- 不要等待"需要"才引用，必须主动引用足够数量的论文
- 每个小节至少需要引用 8-10 篇论文
- 在撰写每个观点时，主动寻找可以支撑该观点的论文
- 即使某个观点看起来很明显，也要找到相关文献来支持

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 使用学术化表达

**输出要求**：
- 确保完整输出所有内容，不要中途截断
- 每个章节都要完整撰写
"""

        if specificity_guidance:
            base_prompt += f"\n\n**场景特异性指导**：\n{json.dumps(specificity_guidance, ensure_ascii=False, indent=2)}"

        return base_prompt

    def _build_user_message(
        self,
        topic: str,
        paper_titles: str,
        framework: dict,
        target_citation_count: int = 50,
        paper_count: int = 100,
        recent_years_ratio: float = 0.5,
        english_ratio: float = 0.3
    ) -> str:
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
2. 在需要引用论文时，使用 get_paper_details 工具获取详细信息（包括年份和语言）
3. 确保每个小节都有充分的引用支持
4. 使用对比分析，指出不同研究的观点和差异
5. 指出当前研究的不足和未来方向
6. **确保完整输出所有内容，不要中途截断**

**引用要求**（必须严格遵守，否则任务失败）：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文（硬性要求）
- **每节引用数量**：每个小节至少需要引用 8-10 篇论文
- **近5年文献比例**：至少 {recent_years_ratio:.0%}（当前年份 2026，近5年指 2021-2026）
- **英文文献比例**：至少 {english_ratio:.0%}
- **引用编号范围**：[1] 到 [{paper_count}]，**严禁超出此范围**
- **按顺序引用**：正文中首次出现的引用应该是[1]，然后是[2]，依此类推
- **不要过度引用同一篇论文**：同一篇论文不要被引用超过2次
- 从提供的文献列表中选择最相关的文献进行引用
- 优先引用高质量、高被引的文献
- 每个重要观点都要有引用支持

**主动引用策略**（重要）：
- 不要等待"需要"才引用，必须主动引用足够数量的论文
- 撰写每个观点时，主动调用 get_paper_details 获取论文详情
- 即使某个观点看起来很明显，也要找到相关文献来支持

请开始撰写。
"""

        return message

    def _build_supplement_message(self, to_cite: List[Tuple[int, Dict]], current_content: str) -> str:
        """构建补充引用的消息"""
        papers_info = []
        for idx, paper in to_cite:
            abstract = (paper.get("abstract") or "")[:200]  # 处理 None 情况
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
