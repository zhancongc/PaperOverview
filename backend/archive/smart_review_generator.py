#!/usr/bin/env python3
"""
智能综述生成器（SmartReviewGenerator）

整合完整流程：
1. Semantic Scholar 智能搜索（Function Calling）
2. 论文去重与筛选
3. 综述大纲生成
4. 综述撰写（Function Calling 按需获取论文详情）

设计理念：
- LLM 驱动搜索策略：让 LLM 决定搜索什么关键词
- 渐进式信息披露：先标题列表，再按需获取详情
- 多轮搜索优化：根据已有文献调整搜索策略
"""
import os
import json
import asyncio
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
from openai import AsyncOpenAI


class SmartReviewGenerator:
    """
    智能综述生成器

    核心特性：
    - LLM 驱动的 Semantic Scholar 搜索
    - Function Calling 按需获取论文详情
    - 多轮搜索优化策略
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

    async def generate_review(
        self,
        topic: str,
        target_paper_count: int = 100,
        max_search_rounds: int = 3,
        model: str = "deepseek-reasoner"
    ) -> Dict[str, Any]:
        """
        生成完整综述（阶段2和3合并）

        Args:
            topic: 综述主题
            target_paper_count: 目标收集论文数量
            max_search_rounds: 最大搜索轮数
            model: 使用的模型

        Returns:
            {
                "topic": str,
                "papers": list,
                "review": str,
                "cited_papers": list,
                "statistics": dict
            }
        """
        print("=" * 80)
        print(f"智能综述生成器启动")
        print(f"主题: {topic}")
        print("=" * 80)

        start_time = time.time()

        # === 阶段 1: LLM 驱动的文献搜索 ===
        print("\n[阶段 1] 智能文献搜索")
        print("-" * 80)

        papers = await self._intelligent_search(
            topic=topic,
            target_count=target_paper_count,
            max_rounds=max_search_rounds,
            model=model
        )

        print(f"\n✓ 搜索完成，共收集 {len(papers)} 篇论文")

        # === 阶段 2: 直接生成综述（大纲 + 撰写合并）===
        print("\n[阶段 2] 生成综述（大纲+撰写一体化）")
        print("-" * 80)

        review, cited_papers, outline = await self._write_review_with_outline(
            topic=topic,
            papers=papers,
            model=model
        )

        print(f"✓ 综述生成完成，引用 {len(cited_papers)} 篇论文")

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
        print(f"  - 收集论文: {statistics['papers_collected']} 篇")
        print(f"  - 引用论文: {statistics['papers_cited']} 篇")
        print(f"  - 搜索轮数: {statistics['search_rounds']} 轮")
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

    async def _intelligent_search(
        self,
        topic: str,
        target_count: int,
        max_rounds: int,
        model: str
    ) -> List[Dict]:
        """
        智能搜索：LLM 决定搜索策略

        使用 Function Calling 让 LLM 决定搜索什么关键词
        """
        all_papers = []
        seen_ids = set()

        for round_num in range(1, max_rounds + 1):
            print(f"\n[搜索轮次 {round_num}/{max_rounds}]")

            # 让 LLM 生成搜索关键词
            search_queries = await self._generate_search_queries(
                topic=topic,
                existing_papers=all_papers,
                round_num=round_num,
                model=model
            )

            print(f"  生成搜索关键词: {search_queries}")

            # 执行搜索
            round_papers = []
            for query in search_queries:
                print(f"    搜索: {query}")
                papers = await self._search_semantic_scholar(query)
                round_papers.extend(papers)
                await asyncio.sleep(1)  # 避免 rate limit

            # 去重
            new_papers = []
            for paper in round_papers:
                paper_id = paper.get("id", paper.get("title", ""))
                if paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    new_papers.append(paper)

            all_papers.extend(new_papers)

            # 记录搜索历史
            self.search_history.append({
                "round": round_num,
                "queries": search_queries,
                "found": len(round_papers),
                "new": len(new_papers),
                "total": len(all_papers)
            })

            print(f"  本轮新增: {len(new_papers)} 篇，累计: {len(all_papers)} 篇")

            # 检查是否达到目标
            if len(all_papers) >= target_count:
                print(f"  ✓ 达到目标数量 {target_count}")
                break

            # 如果这轮新增很少，提前结束
            if len(new_papers) < 5 and round_num > 1:
                print(f"  ⚠️  新增论文过少，提前结束搜索")
                break

        # 按被引量排序
        all_papers.sort(
            key=lambda p: p.get("cited_by_count", 0),
            reverse=True
        )

        return all_papers

    async def _generate_search_queries(
        self,
        topic: str,
        existing_papers: List[Dict],
        round_num: int,
        model: str
    ) -> List[str]:
        """让 LLM 生成搜索关键词"""

        existing_summary = ""
        if existing_papers:
            # 摘要现有论文标题
            titles = [p.get("title", "") for p in existing_papers[:20]]
            existing_summary = f"\n\n已找到的论文标题示例:\n{chr(10).join(f'  - {t}' for t in titles)}"

        system_prompt = f"""你是学术文献搜索专家。请为研究主题生成 Semantic Scholar 搜索关键词。

**研究主题**: {topic}

**搜索轮次**: 第 {round_num} 轮

**要求**:
1. 生成 3-5 个 Semantic Scholar 搜索查询
2. 关键词应该具体、学术化
3. 避免重复之前的搜索方向
4. 每个查询是简单的短语，不要使用复杂布尔逻辑

**示例**:
- computer algebra system algorithm
- symbolic computation applications
- Gröbner basis CAS
- Mathematica algorithms
- symbolic integration

{existing_summary}

请输出 JSON 格式: {{ "queries": ["query1", "query2", "query3"] }}"""

        response = await self.llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("queries", [])
        except:
            # 失败时返回默认查询
            return [topic, f'"{topic}" AND review', f'"{topic}" AND algorithm']

    async def _search_semantic_scholar(self, query: str, limit: int = 50) -> List[Dict]:
        """搜索 Semantic Scholar"""
        import httpx

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,authors,year,citationCount,venue,journal,doi,fieldsOfStudy"
        }

        headers = {}
        if self.semantic_scholar_api_key:
            headers["x-api-key"] = self.semantic_scholar_api_key

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                data = response.json()

                papers = []
                for item in data.get("data", []):
                    paper = {
                        "id": item.get("paperId", ""),
                        "title": item.get("title", ""),
                        "abstract": item.get("abstract"),
                        "authors": [a.get("name", "") for a in item.get("authors", [])],
                        "year": item.get("year"),
                        "cited_by_count": item.get("citationCount", 0),
                        "venue": item.get("venue", ""),
                        "journal": item.get("journal", {}).get("name", ""),
                        "venue_name": item.get("venue", ""),
                        "doi": item.get("doi"),
                        "concepts": item.get("fieldsOfStudy", []),
                        "source": "semantic_scholar",
                        "search_query": query
                    }
                    papers.append(paper)

                return papers

        except Exception as e:
            print(f"    搜索失败: {e}")
            return []

    async def _generate_outline(
        self,
        topic: str,
        papers: List[Dict],
        model: str
    ) -> Dict:
        """生成综述大纲"""

        # 提供论文标题示例
        paper_titles = [p.get("title", "") for p in papers[:30]]

        system_prompt = """你是学术综述大纲设计专家。请为研究主题设计高质量的综述大纲。

要求:
1. 包含引言、2-5个主体章节、结论
2. 每个章节有明确的写作重点
3. 章节之间逻辑连贯
4. 输出 JSON 格式

输出格式:
{
    "introduction": {
        "focus": "引言的写作重点"
    },
    "body_sections": [
        {
            "title": "章节标题",
            "focus": "该章节的写作重点",
            "key_points": ["要点1", "要点2", "要点3"]
        }
    ],
    "conclusion": {
        "focus": "结论的写作重点"
    }
}"""

        user_prompt = f"""研究主题: {topic}

可用论文标题示例:
{chr(10).join(f'  - {t}' for t in paper_titles)}

请设计综述大纲:"""

        response = await self.llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        try:
            return json.loads(response.choices[0].message.content)
        except:
            # 返回默认大纲
            return {
                "introduction": {"focus": "介绍研究背景和意义"},
                "body_sections": [
                    {"title": "研究现状", "focus": "梳理相关研究", "key_points": ["主要理论", "技术进展"]},
                    {"title": "核心技术", "focus": "探讨关键技术", "key_points": ["算法", "实现"]},
                    {"title": "应用与挑战", "focus": "分析应用场景和挑战", "key_points": ["应用案例", "未来方向"]}
                ],
                "conclusion": {"focus": "总结研究现状和未来方向"}
            }

    async def _write_review_with_outline(
        self,
        topic: str,
        papers: List[Dict],
        model: str
    ) -> Tuple[str, List[Dict], Dict]:
        """
        大纲设计与综述撰写一体化（合并阶段2和3）

        LLM 在一个流程中完成：
        1. 先查看论文标题列表
        2. 设计综述结构
        3. 按需调用工具获取论文详情
        4. 直接撰写完整综述
        """
        # 去重
        from services.review_generator_fc_unified import ReviewGeneratorFCUnified

        # 使用一个轻量级的生成器
        # 首先准备论文标题列表
        paper_titles_list = self._format_paper_titles_list(papers)

        print(f"[准备] 论文标题列表 ({len(papers)} 篇)")

        # 构建系统提示（合并大纲生成和综述撰写）
        system_prompt = self._build_combined_system_prompt(
            paper_count=len(papers),
            target_citation_count=min(80, len(papers))
        )

        # 构建用户消息
        user_message = self._build_combined_user_message(
            topic=topic,
            paper_titles=paper_titles_list,
            paper_count=len(papers),
            target_citation_count=min(80, len(papers))
        )

        # 记录工具调用情况
        tool_calls_log = []
        accessed_papers = {}

        # 多轮对话循环
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        max_iterations = 10
        iteration = 0
        content = None

        # 获取工具定义
        tools = self._get_tools_definition(len(papers))

        while iteration < max_iterations:
            iteration += 1

            # 调用 LLM
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

        # 后处理：引用验证、修正、去重、重映射
        from services.review_generator_fc_unified import ReviewGeneratorFCUnified
        temp_generator = ReviewGeneratorFCUnified(
            api_key=self.llm_client.api_key,
            base_url=self.llm_client.base_url
        )

        # 验证并修正引用
        content, cited_indices, _ = temp_generator._validate_and_fix_citations(content, len(papers))

        # 限制重复引用
        content, cited_indices = temp_generator._limit_duplicate_citations(content, cited_indices)

        # 重新映射引用
        content, cited_papers = temp_generator._remap_citations(content, cited_indices, papers)

        # 添加标题和参考文献
        final_content = f"# {topic}\n\n{content}"
        references = temp_generator._format_references(cited_papers)
        final_content = f"{final_content}\n\n## 参考文献\n\n{references}"

        print(f"[综述生成] 工具调用: {len(tool_calls_log)}次, 访问论文: {len(accessed_papers)}篇")

        # 提取大纲（从生成的内容中简单提取，或者返回空）
        outline = self._extract_outline_from_content(final_content)

        return final_content, cited_papers, outline

    async def _write_review(
        self,
        topic: str,
        papers: List[Dict],
        outline: Dict,
        model: str
    ) -> Tuple[str, List[Dict]]:
        """
        撰写综述（使用 Function Calling）- 保留旧方法兼容性

        这部分复用 review_generator_fc_unified 的逻辑
        """
        # 导入复用
        from services.review_generator_fc_unified import ReviewGeneratorFCUnified

        generator = ReviewGeneratorFCUnified(
            api_key=self.llm_client.api_key,
            base_url=self.llm_client.base_url
        )

        framework = {"outline": outline}

        # 调用现有生成器
        review, cited_papers = await generator.generate_review(
            topic=topic,
            papers=papers,
            framework=framework,
            model=model,
            target_citation_count=min(80, len(papers)),
            min_citation_count=min(50, len(papers)),
            recent_years_ratio=0.5,
            english_ratio=0.8,
            enable_reasoning=False
        )

        return review, cited_papers

    # ========== 辅助方法 ==========

    def _format_paper_titles_list(self, papers: List[Dict]) -> str:
        """格式化论文标题列表"""
        lines = ["【参考文献列表】"]
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            year = paper.get("year", "Unknown")
            authors = paper.get("authors", [])
            first_author = authors[0] if authors else "Unknown"
            lines.append(f"{i}. {title} ({year}) - {first_author}等")
        return "\n".join(lines)

    def _build_combined_system_prompt(self, paper_count: int, target_citation_count: int) -> str:
        """构建合并后的系统提示"""
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

**引用要求**：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文
- **近5年文献比例**：至少 50%（当前年份 2026，近5年指 2021-2026）
- **英文文献比例**：至少 80%

**【致命错误】引用编号范围限制**：
- **有效范围**：[1] 到 [{paper_count}]，共 {paper_count} 篇论文
- **严禁超出范围**：不得出现 [{paper_count + 1}]、[{paper_count + 2}] 等超出范围的引用

**语言要求**：
- 只使用中文撰写
- 禁止中英文混用
- 使用学术化表达

**输出要求**：
- 确保完整输出所有内容，不要中途截断
- 每个章节都要完整撰写
- 使用 Markdown 格式，标题使用 ## 或 ###"""

    def _build_combined_user_message(
        self,
        topic: str,
        paper_titles: str,
        paper_count: int,
        target_citation_count: int
    ) -> str:
        """构建合并后的用户消息"""
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

**【重要】引用内容必须准确**：
- **必须先查看论文详情**（通过 get_multiple_paper_details 工具）
- **确认论文内容与你的描述一致**

**引用要求**：
- **总引用数量**：必须至少引用 {target_citation_count} 篇不同的论文
- **每节引用数量**：每个小节至少需要引用 8-10 篇论文
- 从提供的文献列表中选择最相关的文献进行引用

**工具调用要求**：
- **首先判断综述需要引用哪些论文**
- **一次性调用 get_multiple_paper_details 工具，传入所有需要引用的论文索引**
- **获取足够数量的论文详情后开始撰写**

请开始撰写。"""

    def _get_tools_definition(self, paper_count: int) -> List[Dict]:
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
        """批量获取论文详细信息"""
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
        """在本地论文列表中搜索"""
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
        """估算上下文 token 数"""
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
        """从生成的内容中简单提取大纲"""
        import re
        outline = {"introduction": {"focus": ""}, "body_sections": [], "conclusion": {"focus": ""}}

        # 简单提取：查找 Markdown 标题
        lines = content.split("\n")
        for line in lines:
            if line.startswith("## "):
                title = line[3:].strip()
                if "引言" in title or "介绍" in title:
                    outline["introduction"]["focus"] = title
                elif "结论" in title or "总结" in title:
                    outline["conclusion"]["focus"] = title
                else:
                    outline["body_sections"].append({
                        "title": title,
                        "focus": "",
                        "key_points": []
                    })

        return outline


# ============ 便捷函数 ============

async def generate_smart_review(
    topic: str,
    deepseek_api_key: str,
    semantic_scholar_api_key: str = None,
    target_paper_count: int = 100,
    model: str = "deepseek-reasoner"
) -> Dict[str, Any]:
    """
    便捷函数：生成智能综述

    Args:
        topic: 综述主题
        deepseek_api_key: DeepSeek API Key
        semantic_scholar_api_key: Semantic Scholar API Key (可选)
        target_paper_count: 目标收集论文数量
        model: 使用的模型

    Returns:
        完整的综述结果
    """
    generator = SmartReviewGenerator(
        deepseek_api_key=deepseek_api_key,
        semantic_scholar_api_key=semantic_scholar_api_key
    )

    return await generator.generate_review(
        topic=topic,
        target_paper_count=target_paper_count,
        model=model
    )


if __name__ == "__main__":
    # 测试代码
    from dotenv import load_dotenv
    load_dotenv()

    async def test():
        generator = SmartReviewGenerator(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        )

        result = await generator.generate_review(
            topic="Transformer 模型在代码生成中的应用",
            target_paper_count=50,
            max_search_rounds=2
        )

        # 保存结果
        with open("smart_review_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n结果已保存到 smart_review_result.json")

    asyncio.run(test())
