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
from typing import List, Dict, Tuple, Any


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

        # === 去重：基于标题去重，保留被引量高的版本 ===
        original_count = len(papers)
        papers = self._deduplicate_papers_by_title(papers)
        dedup_count = original_count - len(papers)

        if dedup_count > 0:
            print(f"[去重] 原始文献数: {original_count}")
            print(f"[去重] 去重后文献数: {len(papers)}")
            print(f"[去重] 移除重复文献: {dedup_count} 篇")

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

        # 根据论文数量动态设置迭代次数
        # 现在使用批量获取，只需要 1 次工具调用即可获取所有需要的论文详情
        # 设置 5 轮应该足够（包括可能的搜索等额外操作）
        max_iterations = 5
        iteration = 0
        content = None  # 初始化 content 变量

        # 根据模型确定 max_tokens
        def get_max_tokens(model_name: str) -> int:
            """获取模型的最大输出长度"""
            if "reasoner" in model_name:
                return 64000  # deepseek-reasoner 最大 64K
            return 8192  # deepseek-chat 最大 8K

        max_tokens = get_max_tokens(model)
        print(f"[配置] 使用模型: {model}, 最大输出: {max_tokens} tokens")
        print(f"[配置] 最大迭代次数: {max_iterations} 轮")

        # 构建 extra_body 参数（用于控制思考模式）
        extra_body = {}
        if "reasoner" in model and not enable_reasoning:
            # 关闭思考模式，节省输出时间和 tokens
            extra_body["thinking_budget"] = 1  # 设置为最小值，强制跳过思考
            print(f"[配置] 已关闭思考模式，直接输出结果")

        while iteration < max_iterations:
            iteration += 1

            # 调用 LLM
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=self._get_tools_definition(len(papers)),
                tool_choice="auto",
                temperature=0.4,  # 学术综述生成：平衡准确性和流畅性
                max_tokens=max_tokens,
                extra_body=extra_body if extra_body else None
            )

            assistant_message = response.choices[0].message

            # 检查是否要调用工具
            if assistant_message.tool_calls:
                # 添加助手消息（包含 tool_calls）
                messages.append(assistant_message)

                # 处理每个工具调用
                tool_responses = []
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # 执行工具调用
                    if function_name == "get_multiple_paper_details":
                        result = self._get_multiple_paper_details(
                            paper_indices=function_args.get("paper_indices", []),
                            papers=papers
                        )

                        # 记录访问的论文
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
                        result = self._search_papers_by_keyword(
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

                # 批量添加工具响应
                messages.extend(tool_responses)

                # 估算并打印上下文长度
                context_tokens = self._estimate_context_tokens(messages)
                print(f"[迭代 {iteration}] 上下文约 {context_tokens} tokens")

            else:
                # 没有工具调用，对话结束
                # 添加最终回复
                messages.append(assistant_message)

                content = assistant_message.content

                # 检查内容是否被截断
                finish_reason = response.choices[0].finish_reason
                if finish_reason == "length":
                    print(f"[警告] 生成内容因达到max_tokens限制而被截断！")
                    print(f"[警告] 当前内容长度: {len(content)} 字符")
                elif finish_reason == "content_filter":
                    print(f"[警告] 生成内容因内容过滤被截断！")
                else:
                    print(f"[完成] 生成完成，原因: {finish_reason}")

                break

        # === 后处理 ===
        print(f"[综述生成] 工具调用: {len(tool_calls_log)}次, 访问论文: {len(accessed_papers)}篇, 迭代: {iteration}轮")

        # 检查 content 是否已生成
        if content is None:
            print(f"[错误] 生成失败：LLM 没有返回任何内容")
            print(f"[错误] 可能原因：达到最大迭代次数 ({max_iterations}) 但 LLM 仍在调用工具")
            # 返回空内容
            return "", []

        # === 引用验证和修正 ===
        # 验证并修正内容中的引用，确保所有引用都在有效范围内
        content, cited_indices, fix_logs = self._validate_and_fix_citations(content, len(papers))

        # 提取引用的论文（使用修正后的 cited_indices）
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

            # 根据标题判断是否为英文文献
            def _is_english(paper):
                title = paper.get("title", "")
                return not any('\u4e00' <= char <= '\u9fff' for char in title)

            english_count = sum(1 for p in papers_list if _is_english(p))

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

            # 根据标题判断是否为英文文献
            def _is_english(paper):
                title = paper.get("title", "")
                return not any('\u4e00' <= char <= '\u9fff' for char in title)

            english_uncited = [(idx, p) for idx, p in uncited_papers if _is_english(p)]

            # 按优先级排序
            def _paper_priority(item):
                idx, paper = item
                score = 0
                # 近5年加分
                if paper.get("year", 0) >= recent_threshold:
                    score += 100
                # 英文加分
                if _is_english(paper):
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

                print(f"  - 准备补充 {len(to_cite)} 篇论文的引用")
                print(f"  - 原内容长度: {len(content)} 字符")

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

                new_content = supplement_response.choices[0].message.content
                finish_reason = supplement_response.choices[0].finish_reason

                print(f"  - 补充后长度: {len(new_content)} 字符")
                print(f"  - 完成原因: {finish_reason}")

                # 检查内容是否变短（可能被截断）
                if len(new_content) < len(content) * 0.8:
                    print(f"  - ⚠️ 警告：补充后内容变短，可能被截断，保留原内容")
                    # 保留原内容，不替换
                elif finish_reason == "length":
                    print(f"  - ⚠️ 警告：补充内容因达到max_tokens限制而被截断，保留原内容")
                    # 保留原内容，不替换
                else:
                    content = new_content

                # 验证并修正补充后的引用
                content, cited_indices, _ = self._validate_and_fix_citations(content, len(papers))
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
                    "name": "get_multiple_paper_details",
                    "description": f"""批量获取多篇论文的详细信息，包括：
- 摘要（了解研究内容和结论）
- 作者列表
- 发表年份
- 期刊/会议名称
- 研究关键词/概念标签
- 被引次数

**重要：引用论文前，必须先调用此函数获取详细信息**
不能只根据标题引用论文，必须查看论文摘要后再引用。
不要编造论文内容，只使用工具返回的真实信息。

**最佳实践：一次性获取多篇论文的详细信息**
- 判断综述需要引用哪些论文（根据主题和大纲）
- 一次性调用此函数，传入所有需要引用的论文索引
- 可以一次性获取 10-50 篇论文的详情

论文索引必须在有效范围内（1-{paper_count}）。
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "paper_indices": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": f"论文索引列表（1-{paper_count}），例如：[1, 5, 10, 15, 20]表示获取第1、5、10、15、20篇论文的详细信息"
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

    def _get_multiple_paper_details(self, paper_indices: List[int], papers: List[Dict]) -> Dict:
        """批量获取论文详细信息（工具函数实现）"""
        results = []

        for paper_index in paper_indices:
            if not 1 <= paper_index <= len(papers):
                results.append({
                    "index": paper_index,
                    "error": f"论文索引 {paper_index} 超出范围（1-{len(papers)}）"
                })
                continue

            paper = papers[paper_index - 1]

            results.append({
                "index": paper_index,
                "title": paper.get("title", ""),
                "authors": paper.get("authors", [])[:5],  # 最多5个作者
                "year": paper.get("year"),
                "venue": paper.get("venue_name", ""),
                "abstract": paper.get("abstract", "")[:2000],  # 限制摘要长度
                "concepts": paper.get("concepts", [])[:10],  # 最多10个概念
                "cited_by_count": paper.get("cited_by_count", 0)
            })

        return {
            "papers": results,
            "count": len(results)
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

**【致命警告】引用前必须先获取论文详情**
- 你只能看到论文的标题列表（共 {paper_count} 篇）
- **绝对禁止**：只根据标题猜测内容就引用
- **必须步骤**：
  1. 先调用 get_multiple_paper_details 工具获取论文摘要和详情
  2. 仔细阅读论文摘要，确认其内容与你描述的一致
  3. 然后在正文中引用
- **常见错误示例**（必须避免）：
  * ❌ 说 "ClarifyGPT 框架通过澄清需求提升代码质量[13]"
    但实际 [13] 是 "Syntax and Domain Aware Model"（完全不同）
  * ❌ 说 "SWE-PolyBench[12] 通过数据增强缓解低资源语言问题"
    但实际 [12] 是基准测试，不是数据增强方法
  * ✅ 正确做法：先调用 get_multiple_paper_details([10, 12, 13])，
    确认 [10] 是 ClarifyGPT 后，引用 [10] 而非 [13]

**最佳实践：批量获取论文详情**
- **一次性判断综述需要引用哪些论文**（根据主题和大纲）
- **一次性调用 get_multiple_paper_details，传入所有需要引用的论文索引**
- 可以一次性获取 10-50 篇论文的详情，极大提高效率
- 例如：如果需要引用 [1, 2, 5, 10, 15, 20, 25, 30]，就一次性传入这个数组

**写作要求**：
1. 按照提供的大纲结构撰写综述
2. 每个重要观点都要有引用支持
3. 使用对比分析，指出不同研究的观点、方法、结论
4. 明确指出研究分歧和不足
5. 指出研究空白和未来方向

**批判性分析要求（针对基于翻译的方法）**：
- **必须讨论不可翻译的语言特性**：某些语言特性无法通过翻译保留，例如：
  * Rust 的所有权（ownership）和借用（borrowing）系统
  * Haskell 的惰性求值（lazy evaluation）
  * Idris 的依赖类型（dependent types）
  * Python 的动态类型和元编程能力
- **翻译可能引入新错误**：翻译过程本身可能引入与原始代码无关的缺陷，导致评估结果失真
- **区分翻译质量与原始代码质量**：必须讨论如何区分翻译引入的问题和原始代码本身的问题
- **3.3 节专门要求**：在"翻译引入的误差和挑战"部分中，必须增加一段专门讨论不可翻译的语言特性，并明确指出这是基于翻译的方法的**固有上限**（fundamental upper bound）

**结论部分补充要求**：
- 在指出未来方向时，必须明确说明：
  "对于具有强独特性的低资源语言（如 Rust、Haskell、Idris 等），需要探索直接评估或跨语言表示学习等替代路径，因为翻译方法存在固有的局限性。"

**结论部分写作要求（重要）**：
- 结论应简洁明了，重点突出
- **未来研究方向严格限制为 3-4 条**，不要罗列过多方向
- 每个方向控制在 2-3 行以内，避免冗长描述
- 突出最核心、最紧迫的研究方向，建议包括：
  1) 多语言评估基准开发（扩展到低资源语言）
  2) 语义保持的翻译方法优化（处理不可翻译特性）
  3) 评估框架的领域适应与工程化（偏差校正、不确定性量化、实际应用）
- 第 4 条可选：如需要，可添加"跨学科融合"或"长期展望"
- **其他次要方向**：合并到上述方向中或简要提及
- **格式要求**：
  * 使用简洁的标题（不超过 15 字）
  * 每条方向用 1-2 句话说明核心内容
  * 避免展开论述细节

**引用要求**（必须严格遵守，否则任务失败）：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文（硬性要求）
- **近5年文献比例**：至少 {recent_years_ratio:.0%}（当前年份 2026，近5年指 2021-2026）
- **英文文献比例**：至少 {english_ratio:.0%}

**【致命错误】引用编号范围限制**：
- **有效范围**：[1] 到 [{paper_count}]，共 {paper_count} 篇论文
- **严禁超出范围**：不得出现 [{paper_count + 1}]、[{paper_count + 2}] 等超出范围的引用
- **示例说明**：如果只有 34 篇论文，则最大引用编号是 [34]，绝不能出现 [35]、[36]...[40] 等
- **系统验证**：生成后系统会自动检测并移除超出范围的引用

**【致命错误】引用内容必须准确**：
- **先获取详情再引用**：必须先调用 get_multiple_paper_details 获取论文摘要和详情
- **验证内容匹配**：引用前确认论文内容与你描述的一致
- **避免张冠李戴**：
  * 错误示例：说 "ClarifyGPT 框架[13]" 但 [13] 实际是其他论文
  * 正确做法：确认 [13] 的标题确实是 ClarifyGPT，否则使用正确的编号
- **常见错误**：混淆相似标题的论文、作者姓名相近的论文

**【致命错误】引用编号顺序要求**：
- **按顺序引用**：正文中首次出现的引用应该是[1]，然后是[2]，依此类推
- **避免跳跃**：不要出现 [1, 5, 10] 这样的大跨度跳跃
- **连贯引用**：相关观点应使用连续的引用编号，如 [1,2,3] 而非 [1,5,10]
- **错误示例**："[9,42]" 当只有 34 篇论文时，[42] 不存在
- **错误示例**："[1,12]" 当 [12] 与描述内容不符时

**其他引用规范**：
- **不要过度引用同一篇论文**：同一篇论文不要被引用超过2次
- **优先引用高被引论文**（可通过工具查看 cited_by_count）
- **每个小节至少引用 8-10 篇论文**

**工具调用要求**（必须严格遵守）：
- **首先判断综述需要引用哪些论文**
- **一次性调用 get_multiple_paper_details 工具，传入所有需要引用的论文索引**
- **这是唯一的工具调用，获取足够数量的论文详情后开始撰写**
- 目标是获取至少 {target_citation_count} 篇论文的详情

**重要：主动引用策略**
- 根据主题和大纲，主动判断需要引用哪些论文
- 每个小节至少需要引用 8-10 篇论文
- 一次性获取所有相关论文的详情，然后开始撰写
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
2. **引用论文前，必须先调用 get_multiple_paper_details 工具批量获取详细信息**
3. 确保每个小节都有充分的引用支持
4. 使用对比分析，指出不同研究的观点和差异
5. 指出当前研究的不足和未来方向
6. **确保完整输出所有内容，不要中途截断**

**【重要】引用编号范围限制**：
- **有效范围**：[1] 到 [{paper_count}]，共 {paper_count} 篇论文
- **绝对禁止**：出现 [{paper_count + 1}] 或更大的编号
- **示例**：如果 {paper_count}=34，则 [35]、[36]...[50] 都是无效的
- **系统会自动检测并移除**超出范围的引用

**【重要】引用内容必须准确**：
- **必须先查看论文详情**（通过 get_multiple_paper_details 工具）
- **确认论文内容与你的描述一致**
- **错误示例（必须避免）**：
  * ❌ 说 "ClarifyGPT 框架[13]通过澄清需求提升代码质量"
    但实际 [13] 是 "Syntax and Domain Aware Model"（完全不同的论文）
  * ❌ 说 "SWE-PolyBench[12]通过数据增强缓解低资源语言问题"
    但实际 [12] 是多语言基准测试，不是数据增强方法
  * ❌ 说 "CORRECT框架[23]在漏洞检测中F1分数达到0.7"
    但实际 [23] 是其他论文，CORRECT框架可能不在列表中
- **正确做法**：
  1. 先调用 get_multiple_paper_details([1,2,3,4,5,10,12,13...])
  2. 查看返回的论文详情，确认标题和内容
  3. 引用时使用正确的编号，如 ClarifyGPT 是 [10] 就用 [10]

**【重要】引用编号顺序要求**：
- **按顺序引用**：从 [1] 开始，依次使用 [2]、[3]...
- **避免大跨度跳跃**：不要出现 [1, 5, 10, 20]
- **相关观点用连续编号**：[1,2,3] 而非 [1,5,10]

**引用要求**（必须严格遵守，否则任务失败）：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文（硬性要求）
- **每节引用数量**：每个小节至少需要引用 8-10 篇论文
- **近5年文献比例**：至少 {recent_years_ratio:.0%}（当前年份 2026，近5年指 2021-2026）
- **英文文献比例**：至少 {english_ratio:.0%}
- **不要过度引用同一篇论文**：同一篇论文不要被引用超过2次
- 从提供的文献列表中选择最相关的文献进行引用
- 优先引用高质量、高被引的文献
- 每个重要观点都要有引用支持

**工具调用要求**（必须严格遵守）：
- **首先判断综述需要引用哪些论文**（根据主题和大纲）
- **一次性调用 get_multiple_paper_details 工具，传入所有需要引用的论文索引**
- **这是唯一的工具调用，获取足够数量的论文详情后开始撰写**
- 目标是获取至少 {target_citation_count} 篇论文的详情

**主动引用策略**（重要）：
- 根据主题和大纲，主动判断需要引用哪些论文
- 一次性获取所有相关论文的详情，然后开始撰写
- 即使某个观点看起来很明显，也要找到相关文献来支持

**结论部分写作要求（重要）**：
- 结论应简洁明了，重点突出
- **未来研究方向严格限制为 3-4 条**
- 每个方向控制在 2-3 行以内
- 突出最核心、最紧迫的研究方向：
  1) 多语言评估基准开发
  2) 语义保持的翻译方法优化
  3) 评估框架的领域适应与工程化（可选第4条）
- 其他次要方向合并或简要提及

请开始撰写。
"""

        return message

    def _build_supplement_message(self, to_cite: List[Tuple[int, Dict]], current_content: str) -> str:
        """构建补充引用的消息"""
        papers_info = []
        for idx, paper in to_cite:
            abstract = (paper.get("abstract") or "")[:200]  # 处理 None 情况
            papers_info.append(f"[{idx}] {paper.get('title', '')}\n摘要：{abstract}...")

        # 如果内容太长（>8000字符），只发送前半部分和后半部分
        content_to_send = current_content
        if len(current_content) > 8000:
            # 发送前4000字符 + 后4000字符
            content_to_send = f"""{current_content[:4000]}

...（中间部分省略）...

{current_content[-4000:]}"""

        return f"""请在以下综述内容中补充引用这些论文：

【需要补充引用的论文】
{chr(10).join(papers_info)}

【当前综述】
{content_to_send}

要求：
1. 在适当位置添加引用（使用 [序号] 格式）
2. 保持内容连贯性
3. 必须输出完整的综述内容，不要省略任何段落
4. 不要改变原文的结构和内容，只添加引用
"""

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取内容中的引用索引"""
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, content)
        indices = [int(m) for m in matches]
        return sorted(set(indices))

    def _validate_and_fix_citations(self, content: str, paper_count: int) -> tuple[str, List[int], List[str]]:
        """
        验证并修正内容中的引用

        Args:
            content: 生成的综述内容
            paper_count: 论文总数（最大有效引用编号）

        Returns:
            (修正后的内容, 有效引用列表, 修正日志)
        """
        import re

        # 查找所有引用模式，包括 [1], [1,2], [1, 2, 3] 等
        citation_pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'
        fix_logs = []

        def replace_citation(match):
            citation_str = match.group(1)
            # 解析引用编号
            cited_nums = [int(n.strip()) for n in citation_str.split(',')]

            # 过滤出有效的引用编号
            valid_nums = [n for n in cited_nums if 1 <= n <= paper_count]
            invalid_nums = [n for n in cited_nums if n > paper_count or n < 1]

            # 如果有无效引用，记录并修正
            if invalid_nums:
                original = f'[{citation_str}]'
                if valid_nums:
                    replacement = f'[{", ".join(map(str, valid_nums))}]'
                    fix_logs.append(f'修正引用: {original} -> {replacement} (移除无效引用 {invalid_nums})')
                    return replacement
                else:
                    fix_logs.append(f'移除无效引用: {original} (全部超出范围 {invalid_nums})')
                    return ''  # 完全移除

            return match.group(0)  # 保持原样

        # 应用修正
        fixed_content = re.sub(citation_pattern, replace_citation, content)

        # 提取修正后的有效引用
        cited_indices = self._extract_cited_indices(fixed_content)

        # 打印修正日志
        if fix_logs:
            print(f'\n[引用验证] 发现并修正 {len(fix_logs)} 处引用问题:')
            for log in fix_logs[:10]:  # 只显示前10条
                print(f'  - {log}')
            if len(fix_logs) > 10:
                print(f'  - ... 还有 {len(fix_logs) - 10} 处修正')
            print(f'[引用验证] 修正后有效引用: {len(cited_indices)} 篇')
        else:
            print(f'\n[引用验证] ✓ 所有引用均在有效范围内 [1-{paper_count}]')

        return fixed_content, cited_indices, fix_logs

    def _estimate_context_tokens(self, messages: List[Any]) -> int:
        """估算上下文的 token 数量"""
        total_chars = 0
        for msg in messages:
            # 处理 Pydantic 模型和字典两种类型
            if hasattr(msg, 'role'):
                role = msg.role or ""
                content = msg.content or ""
                tool_calls = msg.tool_calls if hasattr(msg, 'tool_calls') else None
            else:
                role = msg.get("role", "")
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")

            # 角色名约 10 个字符
            total_chars += len(role) + len(content) + 20

            # 如果有工具调用，也需要计算
            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    arguments = tool_call.function.arguments
                    total_chars += len(function_name) + len(arguments) + 50

        # 粗略估算：中文约 1.5 字符/token，英文约 4 字符/token
        # 这里使用保守的估算：3 字符/token
        estimated_tokens = total_chars // 3
        return estimated_tokens

    def _format_references(self, papers: List[Dict]) -> str:
        """
        格式化参考文献（中国国标 GB/T 7714-2015）

        格式示例：
        - 期刊论文：[序号] 作者. 题名[J]. 期刊名, 年, 卷(期): 页码. DOI
        - 会议论文：[序号] 作者. 题名[C]//会议论文集名. 年: 页码. DOI
        - 预印本：[序号] 作者. 题名. arXiv preprint arXiv:xxxx.xxxx
        """
        lines = []
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", "")
            doi = paper.get("doi", "")

            # 尝试从多个可能的字段获取期刊/会议信息
            venue = (
                paper.get("venue_name", "") or
                paper.get("venue", "") or
                paper.get("journal", "") or
                paper.get("conference", "") or
                paper.get("primary_location", {}).get("source", {}).get("display_name", "") or
                ""
            )

            # 格式化作者（中国国标：姓在前，名在后，用等）
            if authors and len(authors) > 0:
                if len(authors) <= 3:
                    author_list = []
                    for author in authors[:3]:
                        # 简化处理：直接使用原名称
                        # 实际应该分离姓和名，但这里简化处理
                        if isinstance(author, str):
                            author_list.append(author)
                    author_str = ", ".join(author_list)
                else:
                    # 超过3个作者，只列出前3个加"等"
                    author_list = [a for a in authors[:3] if isinstance(a, str)]
                    author_str = ", ".join(author_list) + ", 等"
            else:
                author_str = "佚名"

            # 判断文献类型和格式
            if "arXiv" in venue or (doi and "arXiv" in str(doi)):
                # arXiv 预印本
                if doi and "arXiv" in str(doi):
                    # 提取 arXiv ID（格式：arXiv:YYMM.NNNNN 或 arXiv:YYMM.NNNNNvV）
                    doi_str = str(doi)

                    # 方法1：从 arXiv.org/abs/ 提取
                    if "arxiv.org/abs/" in doi_str.lower():
                        arxiv_id = doi_str.lower().split("arxiv.org/abs/")[-1]
                    # 方法2：从 10.48550/arXiv. 提取
                    elif "10.48550/arxiv." in doi_str.lower():
                        arxiv_id = doi_str.lower().split("10.48550/arxiv.")[-1]
                    # 方法3：其他 arXiv 格式
                    elif "arxiv:" in doi_str.lower():
                        arxiv_id = doi_str.lower().split("arxiv:")[-1]
                    else:
                        arxiv_id = doi_str

                    # 清理 arXiv ID（移除 URL 参数、版本号等）
                    arxiv_id = arxiv_id.split("?")[0].strip()
                    arxiv_id = arxiv_id.split("#")[0].strip()
                    arxiv_id = arxiv_id.split("v")[0].strip()  # 移除版本号（如 v1, v2）

                    ref_entry = f"[{i}] {author_str}. {title}. arXiv preprint arXiv:{arxiv_id}"
                else:
                    ref_entry = f"[{i}] {author_str}. {title}. arXiv preprint."

            elif venue and any(keyword in venue.upper() for keyword in
                ['PROCEEDINGS', 'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'IEEE', 'ACM']):
                # 会议论文
                ref_entry = f"[{i}] {author_str}. {title}[C]//{venue}. {year}."
                if doi:
                    ref_entry += f" DOI: {doi}"

            elif venue and any(keyword in venue.upper() for keyword in
                ['JOURNAL', 'TRANSACTIONS', 'LETTERS', 'REVIEW', 'NATURE', 'SCIENCE']):
                # 期刊论文
                ref_entry = f"[{i}] {author_str}. {title}[J]. {venue}, {year}."
                if doi:
                    ref_entry += f" DOI: {doi}"

            elif venue:
                # 其他有来源的文献
                ref_entry = f"[{i}] {author_str}. {title}[J]. {venue}, {year}."
                if doi:
                    ref_entry += f" DOI: {doi}"

            else:
                # 无明确来源的文献
                ref_entry = f"[{i}] {author_str}. {title}. {year}."
                if doi:
                    ref_entry += f" DOI: {doi}"

            lines.append(ref_entry)

        return "\n".join(lines)

    def _deduplicate_papers_by_title(self, papers: List[Dict]) -> List[Dict]:
        """
        基于标题去重，保留被引量高的版本

        去重策略：
        1. 标题归一化（小写、去除特殊字符）
        2. 优先保留被引量高的
        3. 被引量相同时，优先保留有 DOI 的
        4. 被引量和 DOI 都相同时，优先保留年份新的

        Args:
            papers: 论文列表

        Returns:
            去重后的论文列表
        """
        seen_titles = {}
        unique_papers = []

        for paper in papers:
            title = paper.get("title", "").strip().lower()
            # 去除特殊字符和空格，但保留基本单词分隔符
            title = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in title)
            title = ' '.join(title.split())  # 标准化空格

            if not title or len(title) < 10:  # 跳过过短的标题
                continue

            if title not in seen_titles:
                seen_titles[title] = len(unique_papers)
                unique_papers.append(paper)
            else:
                # 发现重复，比较被引量、DOI、年份
                existing_idx = seen_titles[title]
                existing_paper = unique_papers[existing_idx]

                existing_citations = existing_paper.get("cited_by_count", 0)
                current_citations = paper.get("cited_by_count", 0)

                existing_doi = existing_paper.get("doi", "")
                current_doi = paper.get("doi", "")

                existing_year = existing_paper.get("year", 0)
                current_year = paper.get("year", 0)

                # 决定是否替换
                should_replace = False

                # 优先保留被引量高的
                if current_citations > existing_citations:
                    should_replace = True
                # 被引量相同时，优先保留有 DOI 的
                elif current_citations == existing_citations:
                    if current_doi and not existing_doi:
                        should_replace = True
                    # 都有或都没有 DOI 时，优先保留年份新的
                    elif current_year > existing_year:
                        should_replace = True

                if should_replace:
                    unique_papers[existing_idx] = paper
                    print(f"[去重] 替换重复文献: {paper.get('title', 'N/A')[:50]}... (被引: {current_citations} > {existing_citations})")

        return unique_papers


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
