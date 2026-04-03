"""
综述生成任务执行器
将同步的生成逻辑包装成异步任务
"""
import os
import warnings
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session

from services.task_manager import TaskManager, TaskStatus, task_manager
from services.smart_paper_search import SmartPaperSearchService
from services.paper_filter import PaperFilterService
from services.paper_field_classifier import EnhancedPaperFilterService
from services.review_generator import ReviewGeneratorService
from services.review_generator_fc_unified import ReviewGeneratorFCUnified
from services.reference_validator import ReferenceValidator
from services.review_record_service import ReviewRecordService
from services.citation_order_checker import CitationOrderChecker
from services.scholarflux_wrapper import ScholarFlux
from database import get_db


class ReviewTaskExecutor:
    """综述生成任务执行器"""

    def __init__(self):
        self.scholarflux = ScholarFlux()
        self.search_service = SmartPaperSearchService(self.scholarflux, get_db)
        self.filter_service = PaperFilterService()
        self.enhanced_filter_service = EnhancedPaperFilterService()
        self.record_service = ReviewRecordService()
        self.validator = ReferenceValidator()
        self.citation_checker = CitationOrderChecker()

    async def execute_task(self, task_id: str, db_session: Session):
        """
        执行综述生成任务

        Args:
            task_id: 任务ID
            db_session: 数据库会话
        """
        task = task_manager.get_task(task_id)
        if not task:
            print(f"[TaskExecutor] 任务不存在: {task_id}")
            return

        # 尝试获取执行槽位（并发控制）
        acquired = await task_manager.acquire_slot(task_id)
        if not acquired:
            # 无法获取槽位，等待当前任务完成后再重试
            print(f"[TaskExecutor] 无法获取执行槽位，任务 {task_id} 将等待")
            task_manager.update_task_status(
                task_id,
                TaskStatus.PENDING,
                progress={"step": "waiting", "message": "等待可用执行槽位..."}
            )
            return

        params = task.params
        topic = task.topic

        # 更新状态为处理中
        task_manager.update_task_status(task_id, TaskStatus.PROCESSING)

        try:
            # 创建数据库记录
            record = self.record_service.create_record(
                db_session=db_session,
                topic=topic,
                target_count=params.get('target_count', 50),
                recent_years_ratio=params.get('recent_years_ratio', 0.5),
                english_ratio=params.get('english_ratio', 0.3)
            )

            # 更新进度
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "generating_outline", "message": "正在生成大纲和搜索关键词..."}
            )

            # === 阶段1: 生成大纲和搜索关键词 ===
            print("\n" + "=" * 80)
            print("[阶段1] 生成综述大纲和搜索关键词")
            print("=" * 80)

            outline = await self._generate_review_outline(topic)
            framework = {'outline': outline}

            print(f"[阶段1] 大纲和关键词生成完成:")
            print(f"  - 引言: {outline.get('introduction', {}).get('focus', '')[:50]}...")
            print(f"  - 主体章节: {len(outline.get('body_sections', []))} 个")

            # 从大纲中提取搜索关键词
            section_keywords = {}
            for section in outline.get('body_sections', []):
                if isinstance(section, dict):
                    title = section.get('title', '')
                    search_keywords = section.get('search_keywords', [])
                    section_keywords[title] = search_keywords
                    print(f"    - {title}")
                    print(f"      搜索关键词: {', '.join(search_keywords)}")

            print(f"  - 结论: 待定（根据文献内容生成）")

            # 获取场景特异性指导（保留这个功能）
            from services.hybrid_classifier import FrameworkGenerator
            gen = FrameworkGenerator()
            analysis_result = await gen.generate_framework(topic, enable_llm_validation=True)
            specificity_guidance = analysis_result.get('specificity_guidance', {})

            # 将关键词整合到 framework
            framework['section_keywords'] = section_keywords
            framework['specificity_guidance'] = specificity_guidance

            # 准备搜索查询（将关键词转换为查询格式）
            search_queries = []
            for keywords in section_keywords.values():
                for kw in keywords:
                    search_queries.append({'query': kw, 'lang': 'mixed'})

            # === 阶段2: 搜索词优化（基本语言优化） ===
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "optimizing_keywords", "message": "正在优化搜索关键词..."}
            )

            print("\n" + "=" * 80)
            print("[阶段2] 搜索词优化（基本语言优化）")
            print("=" * 80)

            # 只做基本的语言优化：根据数据源类型使用不同语言
            # 不扩展同义词、近义词（留到阶段3数量不足时再用）
            optimized_queries = self._optimize_search_queries_basic(
                search_queries=search_queries,
                topic=topic
            )

            print(f"[阶段2] 搜索词优化完成:")
            print(f"  - 原始搜索词: {len(search_queries)} 个")
            print(f"  - 优化后搜索词: {len(optimized_queries)} 个")
            print(f"  - 注意：同义词/近义词扩展将在阶段3数量不足时使用")

            # === 阶段3: 按小节搜索文献 ===
            search_result = await self._search_literature_by_sections(
                topic=topic,
                optimized_queries=optimized_queries,
                params=params,
                framework=framework,
                task_id=task_id
            )

            if not search_result['all_papers']:
                raise Exception(f'未找到关于「{topic}」的相关文献')

            # === 阶段4: 质量过滤（不再精简数量） ===
            filter_result = await self._filter_papers_by_quality(
                search_result=search_result,
                topic=topic,
                framework=framework,
                params=params,
                task_id=task_id
            )

            if not filter_result['all_papers']:
                raise Exception(f'筛选后没有足够的文献')

            all_papers = filter_result['all_papers']
            total_count = len(all_papers)

            print(f"\n[阶段4] 质量过滤完成:")
            print(f"  - 总文献数: {total_count}")
            print(f"  - 说明: 将所有高质量文献标题发送给LLM，由LLM按需选择引用")

            # === 阶段5: 生成综述（Function Calling 统一版本） ===
            api_key = os.getenv("DEEPSEEK_API_KEY")

            if not api_key:
                raise Exception("DEEPSEEK_API_KEY not configured")

            # 计算目标引用数
            target_citation_count = params.get('target_count', 50)

            print(f"\n[阶段5] 生成综述（Function Calling 统一版本）")
            print(f"[阶段5] 候选文献数: {total_count} 篇")
            print(f"[阶段5] 目标引用数: {target_citation_count} 篇")
            print(f"[阶段5] 使用渐进式信息披露，LLM按需选择最相关的文献")

            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "generating", "message": f"正在生成综述（从{total_count}篇候选中选择）..."}
            )

            # 使用 Function Calling 统一版本生成器
            fc_generator = ReviewGeneratorFCUnified(api_key=api_key)

            # 一次性生成完整综述
            review, cited_papers = await fc_generator.generate_review(
                topic=topic,
                papers=all_papers,
                framework=framework,
                target_citation_count=target_citation_count,
                min_citation_count=params.get('target_count', 50),
                recent_years_ratio=params.get('recent_years_ratio', 0.5),
                english_ratio=params.get('english_ratio', 0.3),
                specificity_guidance=specificity_guidance,
                model=params.get('review_model', 'deepseek-chat'),  # 默认使用 chat，需要长综述时可指定 reasoner
                enable_reasoning=params.get('enable_reasoning', False)  # 默认关闭思考模式
            )

            # 5. 最终验证
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "validating", "message": "正在验证引用..."}
            )

            # Function Calling 版本已经在内部处理了引用验证和补充
            # 这里只做最终验证
            final_validation = self.validator.validate_review(review=review, papers=cited_papers)

            # 6. 计算统计信息
            stats = self.filter_service.get_statistics(cited_papers)

            # 标记文献是否被引用
            cited_paper_ids = {p.get('id') for p in cited_papers}
            for paper in all_papers:
                if 'relevance_score' not in paper:
                    paper['relevance_score'] = 0
                paper['cited'] = paper.get('id') in cited_paper_ids

            # 7. 最终验证
            final_validation = self.validator.validate_review(review=review, papers=cited_papers)

            # 8. 保存记录
            record = self.record_service.update_success(
                db_session=db_session,
                record=record,
                review=review,
                papers=cited_papers,
                statistics=stats
            )

            # 任务完成
            task_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                result={
                    "id": record.id,
                    "topic": topic,
                    "review": review,
                    "papers": cited_papers,
                    "candidate_pool": all_papers,
                    "statistics": stats,
                    "analysis": framework,
                    "cited_papers_count": len(cited_papers),
                    "validation": final_validation,
                    "created_at": record.created_at.isoformat()
                }
            )

        except Exception as e:
            import traceback
            traceback.print_exc()

            # 确保槽位被释放（如果还没被释放）
            if task_id in task_manager._running_tasks:
                task_manager.release_slot(task_id)

            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

            # 更新数据库记录为失败
            try:
                if 'record' in locals():
                    self.record_service.update_failure(
                        db_session=db_session,
                        record=record,
                        error_message=str(e)
                    )
            except:
                pass

    # ==================== 新增：阶段3增强文献搜索方法 ====================

    async def _search_literature_by_sections(
        self,
        topic: str,
        optimized_queries: list,
        params: dict,
        framework: dict,
        task_id: str
    ) -> dict:
        """
        按小节搜索文献（新流程阶段3）

        流程：
        1. 优先从数据库搜索
        2. 数据库不足时使用API补充（根据数据源使用优化后的查询）
        3. 小节内部去重
        4. 小节间去重，保留文献数量少的小节的文献
        5. 文献数量不足时继续搜索

        Args:
            topic: 论文主题
            optimized_queries: 优化后的搜索查询列表（包含source、lang等信息）
            params: 参数配置
            framework: 框架信息
            task_id: 任务ID

        Returns:
            {
                'sections': {
                    '小节名': [论文列表],
                    ...
                },
                'all_papers': [所有论文（去重后）],
                'stats': 统计信息
            }
        """
        # === 阶段3 输入 ===
        print("\n" + "=" * 80)
        print("[阶段3] 按小节搜索文献")
        print("=" * 80)
        print(f"[阶段3] 输入:")
        print(f"  - 主题: {topic}")
        print(f"  - 优化查询数: {len(optimized_queries)}")
        print(f"  - 目标年份范围: 近{params.get('search_years', 10)}年")

        # 获取小节关键词
        section_keywords = framework.get('section_keywords', {})

        # 获取小节列表（从 outline 或 framework）
        outline = framework.get('outline', {})
        body_sections = outline.get('body_sections', [])

        # 如果 outline 中没有小节，尝试从 framework.sections 获取
        if not body_sections:
            framework_dict = framework.get('framework', {})
            body_sections = framework_dict.get('sections', [])

        # 提取小节标题
        section_titles = []
        for section in body_sections:
            if isinstance(section, dict):
                title = section.get('title', '')
            else:
                title = str(section)
            if title and title not in ['引言', '结论']:
                section_titles.append(title)

        print(f"[阶段3] 检测到 {len(section_titles)} 个小节")
        for title in section_titles:
            keywords = section_keywords.get(title, [])
            print(f"  - {title}: {len(keywords)} 个关键词")

        # 检查是否有关键词的小节
        sections_with_keywords = [title for title in section_titles if section_keywords.get(title)]
        if not sections_with_keywords:
            print(f"[阶段3] 警告: 所有小节都没有关键词，使用通用关键词")
            # 使用主题作为通用关键词
            sections_with_keywords = section_titles[:1] if section_titles else []
            if sections_with_keywords:
                section_keywords[sections_with_keywords[0]] = [topic]

        # 获取数据库session
        from database import db
        db_session_gen = db.get_session()
        db_session = next(db_session_gen)

        try:
            # 按小节搜索文献（先不去重，收集所有文献）
            raw_papers_by_section = {}

            for section_title in section_titles:
                if section_title in ['引言', '结论']:
                    continue  # 跳过引言和结论

                keywords = section_keywords.get(section_title, [])
                if not keywords:
                    print(f"[阶段3] 小节 '{section_title}' 没有关键词，跳过")
                    continue

                print(f"[阶段3] 正在搜索小节: {section_title}")
                print(f"[阶段3] 该小节关键词: {keywords}")

                section_papers = []
                section_seen_ids = set()  # 小节内部去重

                # === 使用优化后的查询进行搜索 ===
                # 为每个关键词找到对应的优化查询
                section_optimized_queries = []
                for keyword in keywords:
                    # 找到所有与这个关键词相关的优化查询
                    related_queries = [
                        q for q in optimized_queries
                        if q.get('original_query') == keyword or
                        q.get('query') == keyword or
                        keyword.lower() in q.get('query', '').lower()
                    ]
                    section_optimized_queries.extend(related_queries)

                # 如果没有找到优化的查询，使用原始关键词
                if not section_optimized_queries:
                    for keyword in keywords:
                        section_optimized_queries.append({
                            'query': keyword,
                            'lang': 'mixed',
                            'source': 'all'
                        })

                print(f"[阶段3] 该小节优化查询数: {len(section_optimized_queries)}")

                # 去重优化查询
                seen_queries = set()
                unique_optimized_queries = []
                for q in section_optimized_queries:
                    query_key = (q['query'], q.get('source', 'all'))
                    if query_key not in seen_queries:
                        seen_queries.add(query_key)
                        unique_optimized_queries.append(q)

                # === 渐进式搜索策略 ===
                # 第1轮：使用原始关键词搜索
                # 第2轮：如果数量不足，使用同义词搜索
                # 第3轮：如果还不足，使用简化查询

                section_papers = []
                section_seen_ids = set()  # 小节内部去重
                target_papers_per_section = 30  # 每小节目标文献数

                for round_num in range(1, 4):  # 最多3轮
                    if round_num == 1:
                        round_queries = unique_optimized_queries
                        round_name = "原始关键词"
                    elif round_num == 2:
                        # 生成同义词查询
                        round_queries = self._generate_synonym_queries(
                            keywords,
                            section_papers,
                            section_seen_ids
                        )
                        round_name = "同义词扩展"
                        if not round_queries:
                            print(f"[阶段3] 第2轮: 没有可用的同义词，跳过")
                            continue
                    else:  # round_num == 3
                        # 生成简化查询
                        round_queries = self._generate_simplified_queries(
                            keywords,
                            section_papers,
                            section_seen_ids
                        )
                        round_name = "简化查询"
                        if not round_queries:
                            print(f"[阶段3] 第3轮: 没有可用的简化查询，跳过")
                            break

                    print(f"\n[阶段3] === {round_name}搜索（第{round_num}轮） ===")

                    # 为当前轮次的查询进行搜索
                    for i, opt_query in enumerate(round_queries[:5]):  # 每轮最多5个查询
                        query = opt_query['query']
                        lang = opt_query.get('lang', 'mixed')
                        source = opt_query.get('source', 'all')

                        task_manager.update_task_status(
                            task_id,
                            TaskStatus.PROCESSING,
                            progress={"step": "searching", "message": f"正在搜索 {section_title}: {query}..."}
                        )

                        # === 步骤1: 优先从数据库搜索 ===
                        from services.paper_metadata_dao import PaperMetadataDAO
                        dao = PaperMetadataDAO(db_session)

                        db_papers = dao.search_papers(
                            keyword=query,
                            min_year=datetime.now().year - params.get('search_years', 10),
                            limit=50
                        )

                        # 转换为字典格式
                        db_papers_dict = [p.to_paper_dict() for p in db_papers]

                        # 添加数据库搜索结果
                        for paper in db_papers_dict:
                            paper_id = paper.get("id")
                            if paper_id and paper_id not in section_seen_ids:
                                section_seen_ids.add(paper_id)
                                section_papers.append(paper)

                        # === 步骤2: 如果数据库搜索结果不足，使用API补充 ===
                        if len(db_papers_dict) < 20:  # 如果数据库搜索结果少于20篇

                            # 根据数据源类型调用不同的API
                            api_papers = await self._search_with_source(
                                query=query,
                                lang=lang,
                                source=source,
                                years_ago=params.get('search_years', 10),
                                limit=30
                            )

                            # 添加API搜索结果（去重）
                            for paper in api_papers:
                                paper_id = paper.get("id")
                                if paper_id and paper_id not in section_seen_ids:
                                    section_seen_ids.add(paper_id)
                                    section_papers.append(paper)

                    # 检查当前轮次搜索后是否达到目标数量
                    current_count = len(section_papers)
                    print(f"[阶段3] 第{round_num}轮搜索完成: 获得 {current_count} 篇文献")

                    if current_count >= target_papers_per_section:
                        print(f"[阶段3] ✓ 已达到目标数量 {target_papers_per_section}，停止扩展搜索")
                        break

                    if round_num == 1:
                        print(f"[阶段3] 数量不足，准备使用同义词扩展...")
                    elif round_num == 2:
                        print(f"[阶段3] 数量仍不足，准备使用简化查询...")

                        print(f"[阶段3] API补充 '{keyword}': 新增 {len(api_papers)} 篇")

                print(f"[阶段3] 小节 '{section_title}' 搜索到 {len(section_papers)} 篇文献（去重后）")
                raw_papers_by_section[section_title] = section_papers

        finally:
            # 确保数据库session总是被关闭
            db_session.close()

        # 小节间去重：保留文献数量少的小节的文献
        print(f"\n[阶段3] 小节间去重...")

        # 计算每个小节的文献数量
        section_paper_counts = {
            title: len(papers) for title, papers in raw_papers_by_section.items()
        }

        # 收集所有 paper_id 及其所属小节
        paper_id_to_sections = {}  # {paper_id: [(section_title, paper), ...]}
        for section_title, section_papers in raw_papers_by_section.items():
            for paper in section_papers:
                paper_id = paper.get('id')
                if paper_id:
                    if paper_id not in paper_id_to_sections:
                        paper_id_to_sections[paper_id] = []
                    paper_id_to_sections[paper_id].append((section_title, paper))

        # 找出重复的 paper_id（出现在多个小节）
        duplicate_paper_ids = {
            pid: sections for pid, sections in paper_id_to_sections.items()
            if len(sections) > 1
        }

        if duplicate_paper_ids:
            print(f"[阶段3] 发现 {len(duplicate_paper_ids)} 个重复的 paper_id，正在去重...")

            # 对于每个重复的 paper_id，只保留文献数量少的小节的文献
            papers_to_remove = set()  # {(section_title, paper_id), ...}

            for paper_id, sections in duplicate_paper_ids.items():
                # 按小节文献数量升序排序（文献少的优先保留）
                sections_sorted = sorted(sections, key=lambda x: section_paper_counts[x[0]])

                # 保留第一个（文献数量最少的小节），删除其余的
                kept_section, kept_paper = sections_sorted[0]
                removed_sections = sections_sorted[1:]

                for removed_section, _ in removed_sections:
                    papers_to_remove.add((removed_section, paper_id))

                if len(removed_sections) > 0:
                    removed_section_names = [s[0] for s in removed_sections]
                    print(f"  - paper_id={paper_id[:20]}...: 保留 '{kept_section}'，删除 {removed_section_names}")

            # 执行去重
            papers_by_section = {}
            for section_title, section_papers in raw_papers_by_section.items():
                # 过滤掉需要删除的文献
                filtered_papers = []
                for paper in section_papers:
                    paper_id = paper.get('id')
                    if (section_title, paper_id) not in papers_to_remove:
                        filtered_papers.append(paper)

                papers_by_section[section_title] = filtered_papers
                removed_count = len(section_papers) - len(filtered_papers)
                if removed_count > 0:
                    print(f"[阶段3] 小节 '{section_title}': 删除 {removed_count} 篇重复文献，保留 {len(filtered_papers)} 篇")
                else:
                    print(f"[阶段3] 小节 '{section_title}': {len(filtered_papers)} 篇（无重复）")
        else:
            print(f"[阶段3] ✓ 没有发现小节间重复文献")
            papers_by_section = raw_papers_by_section

        # 合并所有文献（用于统计，但不用于分配）
        all_papers = []
        for papers in papers_by_section.values():
            all_papers.extend(papers)

        # 统计信息
        stats = self._calculate_paper_stats(all_papers)
        print(f"\n[阶段3] 去重后统计:")
        print(f"  - 总文献数: {stats['total']}")
        print(f"  - 中文: {stats['chinese']}")
        print(f"  - 英文: {stats['english']}")
        print(f"  - 小节分布:")
        for section_title, papers in papers_by_section.items():
            print(f"    - {section_title}: {len(papers)} 篇")

        # 检查文献数量是否达标，不足则继续搜索
        min_target_papers = 200  # 目标至少200篇
        max_search_rounds = 3  # 最多搜索3轮
        search_round = 1

        while stats['total'] < min_target_papers and search_round <= max_search_rounds:
            print(f"\n[阶段3] ⚠️ 文献数量不足（{stats['total']} < {min_target_papers}），第 {search_round} 轮补充搜索...")

            # 获取数据库session
            db_session_gen = db.get_session()
            db_session = next(db_session_gen)

            try:
                # 为每个小节补充搜索
                for section_title, section_papers in papers_by_section.items():
                    keywords = section_keywords.get(section_title, [])
                    if not keywords:
                        continue

                    # 收集已有的 paper_id，避免重复
                    existing_ids = {p.get('id') for p in section_papers if p.get('id')}

                    # 为每个关键词补充搜索
                    for keyword in keywords[:3]:  # 最多3个关键词
                        # 数据库搜索
                        from services.paper_metadata_dao import PaperMetadataDAO
                        dao = PaperMetadataDAO(db_session)

                        db_papers = dao.search_papers(
                            keyword=keyword,
                            min_year=datetime.now().year - params.get('search_years', 10),
                            limit=50
                        )

                        # 转换为字典格式并过滤已存在的
                        db_papers_dict = [p.to_paper_dict() for p in db_papers]
                        new_papers = [p for p in db_papers_dict if p.get('id') not in existing_ids]

                        # 添加到小节文献池
                        for paper in new_papers:
                            paper_id = paper.get('id')
                            if paper_id and paper_id not in existing_ids:
                                section_papers.append(paper)
                                existing_ids.add(paper_id)

                        # 如果数据库不足，用API补充
                        if len(new_papers) < 20:
                            api_papers = await self.search_service.search(
                                query=keyword,
                                years_ago=params.get('search_years', 10),
                                limit=30,
                                use_all_sources=True
                            )

                            for paper in api_papers:
                                paper_id = paper.get('id')
                                if paper_id and paper_id not in existing_ids:
                                    section_papers.append(paper)
                                    existing_ids.add(paper_id)

                    papers_by_section[section_title] = section_papers

            finally:
                db_session.close()

            # 重新统计
            all_papers = []
            for papers in papers_by_section.values():
                all_papers.extend(papers)

            stats = self._calculate_paper_stats(all_papers)
            print(f"[阶段3] 第 {search_round} 轮补充搜索后:")
            print(f"  - 总文献数: {stats['total']}")

            search_round += 1

        print(f"\n[阶段3] 搜索完成:")
        print(f"  - 总文献数: {stats['total']}")
        print(f"  - 中文: {stats['chinese']}")
        print(f"  - 英文: {stats['english']}")
        print(f"  - 小节分布:")
        for section_title, papers in papers_by_section.items():
            print(f"    - {section_title}: {len(papers)} 篇")

        # AMiner论文详情补充
        all_papers = await self._enrich_aminer_papers(all_papers)

        # === 阶段3 输出 ===
        print(f"[阶段3] 输出:")
        print(f"  - 总文献数: {len(all_papers)}")
        print(f"  - 英文文献: {stats['english']}")
        print(f"  - 中文文献: {stats['chinese']}")
        print(f"  - 小节数: {len(papers_by_section)}")
        print("=" * 80)

        return {
            'sections': papers_by_section,
            'all_papers': all_papers,
            'stats': stats
        }

    async def _filter_papers_to_target(
        self,
        search_result: dict,
        topic: str,
        framework: dict,
        params: dict,
        task_id: str
    ) -> dict:
        """
        ⚠️ 已废弃 - 请使用 _filter_papers_by_quality

        此方法不再被调用，保留仅为向后兼容。

        精简文献到目标数量（旧流程阶段4）

        流程：
        1. 在50～60之间随机取一个数N
        2. 按相关性筛选
        3. 分小节筛选，保证总数为N

        Args:
            search_result: 搜索结果（按小节分组）
            topic: 论文主题
            framework: 框架信息
            params: 参数配置
            task_id: 任务ID

        Returns:
            {
                'sections': {
                    '小节名': [论文列表],
                    ...
                },
                'all_papers': [所有论文（去重后）],
                'total_count': N
            }
        """
        warnings.warn(
            "_filter_papers_to_target 已废弃，请使用 _filter_papers_by_quality",
            DeprecationWarning,
            stacklevel=2
        )

        print("\n" + "=" * 80)
        print("[阶段4] 为每个小节分配专属文献")
        print("=" * 80)

        papers_by_section = search_result['sections']
        all_papers = search_result['all_papers']

        print(f"[阶段4] 输入文献数（去重前）: {len(all_papers)}")

        # 在50～60之间随机取一个数N
        import random
        random.seed(42)  # 固定随机种子
        N = random.randint(50, 60)
        print(f"[阶段4] 随机目标数量: N = {N}")

        # 提取主题关键词
        topic_keywords = []
        section_keywords_dict = framework.get('section_keywords', {})
        for keywords in section_keywords_dict.values():
            topic_keywords.extend(keywords)

        # 筛选参数
        recent_years_ratio = params.get('recent_years_ratio', 0.5)
        english_ratio = params.get('english_ratio', 0.3)

        task_manager.update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress={"step": "filtering", "message": f"正在为每个小节分配专属文献（目标{N}篇）..."}
        )

        # 为每个小节筛选专属文献
        filtered_by_section = {}
        total_assigned = 0

        # 计算每个小节应该分配的文献数量（按比例）
        section_counts = {title: len(papers) for title, papers in papers_by_section.items()}
        total_papers = sum(section_counts.values())

        # 按比例分配N篇文献给每个小节
        section_targets = {}
        for title, count in section_counts.items():
            if total_papers > 0:
                section_targets[title] = max(1, int(N * count / total_papers))
            else:
                section_targets[title] = 1

        # 调整分配确保总和为N
        allocated = sum(section_targets.values())
        if allocated < N:
            # 按比例增加
            for title in section_targets:
                if allocated < N:
                    section_targets[title] += 1
                    allocated += 1
        elif allocated > N:
            # 按比例减少
            for title in section_targets:
                if section_targets[title] > 1 and allocated > N:
                    section_targets[title] -= 1
                    allocated -= 1

        print(f"[阶段4] 小节专属文献分配:")
        for title, target in section_targets.items():
            original = section_counts.get(title, 0)
            print(f"  - {title}: {original}篇 → {target}篇专属")

        # 对每个小节进行筛选（只从该小节的文献池中筛选）
        for section_title, section_papers in papers_by_section.items():
            target_count = section_targets.get(section_title, 1)

            # 获取该小节的专属关键词
            section_specific_keywords = section_keywords_dict.get(section_title, topic_keywords)

            # 检查是否需要允许跨学科论文（如证明方法普适性的章节）
            enable_field_filter = not self._is_generalizability_section(section_title)

            # 使用增强筛选服务筛选该小节的专属文献
            filtered_papers, filter_stats = self.enhanced_filter_service.filter_and_sort_with_field(
                papers=section_papers,
                section_name=section_title,
                target_count=target_count,
                recent_years_ratio=recent_years_ratio,
                english_ratio=english_ratio,
                topic_keywords=section_specific_keywords,
                enable_field_filter=enable_field_filter,
                use_llm_classification=False
            )

            # 截取到目标数量
            filtered_papers = filtered_papers[:target_count]
            filtered_by_section[section_title] = filtered_papers

            # 输出筛选结果
            filter_msg = f"[阶段4] 小节 '{section_title}': 筛选到 {len(filtered_papers)} 篇专属文献"
            if enable_field_filter and filter_stats.get('field_filtered', 0) > 0:
                filter_msg += f" (过滤了 {filter_stats['field_filtered']} 篇跨学科论文)"
            print(filter_msg)

        # 统计最终分配的文献总数
        final_total = sum(len(papers) for papers in filtered_by_section.values())
        all_papers_flat = [p for papers in filtered_by_section.values() for p in papers]

        stats = self.filter_service.get_statistics(all_papers_flat)

        # 统计各领域的论文数量
        field_stats = {}
        for paper in all_papers_flat:
            field = paper.get('field', 'unknown')
            field_stats[field] = field_stats.get(field, 0) + 1

        print(f"\n[阶段4] 专属文献分配完成:")
        print(f"  - 总文献数: {final_total} (目标: {N})")
        print(f"  - 英文文献: {stats['english_count']}")
        print(f"  - 近5年文献: {stats['recent_count']} ({stats['recent_ratio']:.1%})")
        print(f"  - 领域分布: {field_stats}")
        print(f"  - 小节分布:")
        for section_title, papers in filtered_by_section.items():
            print(f"    - {section_title}: {len(papers)} 篇")

        return {
            'sections': filtered_by_section,
            'all_papers': [p for papers in filtered_by_section.values() for p in papers],
            'total_count': final_total
        }

    async def _filter_papers_by_quality(
        self,
        search_result: dict,
        topic: str,
        framework: dict,
        params: dict,
        task_id: str
    ) -> dict:
        """
        质量过滤（新流程阶段4）

        只做质量过滤，不做数量精简。
        保留所有高质量文献，让LLM按需选择。

        Args:
            search_result: 搜索结果
            topic: 论文主题
            framework: 框架信息
            params: 参数配置
            task_id: 任务ID

        Returns:
            {
                'all_papers': [质量过滤后的论文列表],
                'total_count': 论文数量
            }
        """
        print("\n" + "=" * 80)
        print("[阶段4] 质量过滤")
        print("=" * 80)
        print(f"[阶段4] 输入:")
        print(f"  - 输入文献数: {len(search_result['all_papers'])}")

        all_papers = search_result['all_papers']

        task_manager.update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress={"step": "filtering", "message": f"正在进行质量过滤..."}
        )

        # 1. 去重（基于 paper.id）
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            paper_id = paper.get('id')
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                unique_papers.append(paper)

        print(f"[阶段4] 去重后: {len(unique_papers)} 篇")

        # 2. 质量过滤（过滤低质量文献）
        from services.paper_quality_filter import PaperQualityFilter
        quality_filter = PaperQualityFilter()

        filtered_papers = []
        removed_count = 0

        for paper in unique_papers:
            # 计算质量得分
            quality_score = quality_filter.get_paper_quality_score(paper)

            # 过滤低质量文献
            if quality_score >= 30:  # 质量得分阈值
                paper['quality_score'] = quality_score
                filtered_papers.append(paper)
            else:
                removed_count += 1

        print(f"[阶段4] 质量过滤: 移除 {removed_count} 篇低质量文献")
        print(f"[阶段4] 保留文献数: {len(filtered_papers)} 篇")

        # 3. 增强相关性评分（添加到论文中）
        section_keywords = framework.get('section_keywords', {})
        topic_keywords = []
        for keywords in section_keywords.values():
            topic_keywords.extend(keywords)

        for paper in filtered_papers:
            # 使用增强筛选服务计算相关性评分
            score = self.enhanced_filter_service._calculate_enhanced_relevance_score(
                paper=paper,
                topic_keywords=topic_keywords
            )
            paper['relevance_score'] = score

        # 4. 按相关性评分排序
        filtered_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        print(f"[阶段4] 已添加相关性评分并排序")

        # 5. 统计信息
        stats = self.filter_service.get_statistics(filtered_papers)

        print(f"\n[阶段4] 质量过滤完成:")
        print(f"  - 总文献数: {len(filtered_papers)}")
        print(f"  - 英文文献: {stats['english_count']}")
        print(f"  - 近5年文献: {stats['recent_count']} ({stats['recent_ratio']:.1%})")
        print(f"  - 平均被引: {stats['avg_citations']:.1f}")

        # 打印筛选后的参考文献列表（前50篇）
        print(f"\n[阶段4] 筛选后的参考文献列表（前50篇）:")
        print(f"{'序号':<6}{'标题':<60}{'年份':<8}{'被引':<8}{'语言'}")
        print("-" * 100)
        for i, paper in enumerate(filtered_papers[:50], 1):
            title = paper.get('title', '')[:57] + '...' if len(paper.get('title', '')) > 57 else paper.get('title', '')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            lang = '英文' if paper.get('lang') == 'en' else '中文'
            print(f"{i:<6}{title:<60}{year:<8}{cited:<8}{lang}")
        if len(filtered_papers) > 50:
            print(f"... (还有 {len(filtered_papers) - 50} 篇文献未显示)")
        print("-" * 100)

        # 6. 如果文献数量仍然太少，尝试补充
        min_papers = 50
        if len(filtered_papers) < min_papers:
            print(f"\n[阶段4] ⚠️ 文献数量不足（{len(filtered_papers)} < {min_papers}）")
            print(f"[阶段4] 这通常意味着搜索结果本身较少，建议：")
            print(f"  1. 扩大搜索年份范围")
            print(f"  2. 使用更通用的搜索关键词")
            print(f"  3. 检查数据源配置是否正确")

        # === 阶段4 输出 ===
        print(f"[阶段4] 输出:")
        print(f"  - 保留文献数: {len(filtered_papers)}")
        print(f"  - 移除低质量: {removed_count} 篇")
        print("=" * 80)

        return {
            'all_papers': filtered_papers,
            'total_count': len(filtered_papers)
        }

    def _calculate_paper_stats(self, papers: list) -> dict:
        """计算文献统计信息"""
        chinese_count = sum(1 for p in papers if not p.get('is_english', True))
        english_count = sum(1 for p in papers if p.get('is_english', False))

        return {
            'total': len(papers),
            'chinese': chinese_count,
            'english': english_count
        }

    def _is_generalizability_section(self, section_title: str) -> bool:
        """
        检查小节是否关于"证明方法普适性"

        这类小节允许引用跨学科的文献。

        Args:
            section_title: 小节标题

        Returns:
            是否允许跨学科引用
        """
        generalizability_keywords = [
            "普适性", "通用性", "适用性", "跨领域", "多领域",
            "泛化", "广泛应用", "不同领域", "多种场景",
            "generalizability", "generalization", "cross-domain",
            "multi-domain", "versatility", "applicability"
        ]

        section_lower = section_title.lower()
        for keyword in generalizability_keywords:
            if keyword.lower() in section_lower:
                return True

        return False

    async def _enrich_aminer_papers(self, papers: list) -> list:
        """补充AMiner论文详情"""
        aminer_token = os.getenv("AMINER_API_TOKEN")
        if not aminer_token:
            return papers

        try:
            from services.aminer_paper_detail import enrich_papers
            enriched = await enrich_papers(papers, aminer_token)
            print(f"[TaskExecutor] AMiner详情补充完成: {len(papers)}篇")
            return enriched
        except Exception as e:
            print(f"[TaskExecutor] AMiner详情补充失败: {e}")
            return papers

    async def _validate_and_fix_review(
        self,
        review: str,
        papers: list,
        generator: 'ReviewGeneratorService',
        task_id: str
    ) -> tuple:
        """
        增强的综述验证和修复方法

        检查项：
        1. 正文引用是否严格在参考文献范围内
        2. 引用是否一一对应
        3. 文献格式是否为国标格式

        Args:
            review: 综述草稿
            papers: 文献列表
            generator: 综述生成器实例
            task_id: 任务ID

        Returns:
            (修复后的内容, 引用的文献列表)
        """
        from services.reference_validator import ReferenceValidator
        from services.citation_order_checker import CitationOrderChecker

        validator = ReferenceValidator()
        citation_checker = CitationOrderChecker()

        # 分离内容和参考文献
        content, references_section = validator._split_review_and_references(review)

        print(f"[验证] 开始验证和修复综述...")

        # === 检查1：正文引用是否严格在参考文献范围内 ===
        print(f"[验证] 检查1: 引用范围验证...")
        citation_check_result = citation_checker.check_order(content, papers_count=len(papers))

        if citation_check_result.get('exceeds_range', False):
            max_citation = citation_check_result.get('max_citation', 0)
            papers_count = citation_check_result.get('papers_count', 0)
            print(f"[验证] ✗ 检测到超出范围的引用（最大: {max_citation}，文献数: {papers_count}），正在修复...")
            content = citation_checker.remove_out_of_range_citations(content, len(papers))
        else:
            print(f"[验证] ✓ 引用范围检查通过")

        # === 检查2：引用是否一一对应并连续 ===
        print(f"[验证] 检查2: 引用顺序验证...")
        citations = citation_checker.extract_citations(content)

        if citations:
            # 提取引用编号
            cited_indices = [int(c['number']) for c in citations]

            # 检查是否有重复或跳跃
            unique_sorted = sorted(set(cited_indices))
            if unique_sorted != list(range(1, len(unique_sorted) + 1)):
                print(f"[验证] ✗ 引用编号不连续，需要重新排序...")
                fixed_content, number_mapping = citation_checker.fix_citation_order(content, citations)

                # 根据新的引用顺序重新构建文献列表
                new_to_old = {}
                for item in number_mapping:
                    new_to_old[item['new']] = item['old']

                cited_papers = []
                for new_index in sorted(new_to_old.keys()):
                    old_index = new_to_old[new_index]
                    # 确保旧索引在有效范围内
                    if 1 <= old_index <= len(papers):
                        cited_papers.append(papers[old_index - 1])

                content = fixed_content
                print(f"[验证] ✓ 引用顺序已修复，共引用{len(cited_papers)}篇文献")
            else:
                # 只保留在有效范围内的引用编号
                valid_cited_indices = {i for i in cited_indices if 1 <= i <= len(papers)}
                cited_papers = [papers[i - 1] for i in sorted(valid_cited_indices)]
                print(f"[验证] ✓ 引用顺序检查通过，共引用{len(cited_papers)}篇文献")
        else:
            print(f"[验证] ⚠ 未检测到任何引用")
            cited_papers = []

        # === 检查3：每篇文献引用次数限制 ===
        print(f"[验证] 检查3: 引用次数验证...")
        content = self._limit_citation_count(content, max_count=2)
        print(f"[验证] ✓ 引用次数限制已应用")

        # === 检查4：文献格式验证（国标格式）===
        print(f"[验证] 检查4: 文献格式验证...")
        # _format_references 已使用国标格式，这里只需确保格式正确
        references = generator._format_references(cited_papers)

        # 验证格式
        format_errors = self._validate_reference_format(references)
        if format_errors:
            print(f"[验证] ✗ 发现{len(format_errors)}个格式错误，正在修复...")
            # 重新生成参考文献
            references = generator._format_references(cited_papers)
        else:
            print(f"[验证] ✓ 文献格式检查通过")

        # === 最终检查：确保没有超出范围的引用 ===
        print(f"[验证] 最终检查...")
        final_check = citation_checker.check_order(content, papers_count=len(cited_papers))
        if final_check.get('exceeds_range', False):
            print(f"[验证] ✗ 最终检查发现超出范围的引用，正在修复...")
            content = citation_checker.remove_out_of_range_citations(content, len(cited_papers))

        # 组合最终综述
        final_review = f"{content}\n\n## 参考文献\n\n{references}"

        print(f"[验证] ✓ 验证和修复完成")

        return final_review, cited_papers

    def _limit_citation_count(self, content: str, max_count: int = 2) -> str:
        """
        限制每篇文献的引用次数

        Args:
            content: 综述内容
            max_count: 最大引用次数

        Returns:
            修复后的内容
        """
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

    def _validate_reference_format(self, references: str) -> list:
        """
        验证参考文献格式是否符合国标格式

        Args:
            references: 参考文献字符串

        Returns:
            格式错误列表
        """
        errors = []

        # 基本格式检查
        lines = references.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # 检查是否以 [数字] 开头
            if not line.startswith('['):
                errors.append(f"第{i}行: 未以引用编号开头")
                continue

            # 检查是否包含必要元素
            if '[J]' not in line and '[M]' not in line and '[C]' not in line:
                errors.append(f"第{i}行: 缺少文献类型标识")

        return errors

    async def _generate_review_outline(self, topic: str) -> dict:
        """
        生成综述大纲

        Returns:
            {
                'introduction': {
                    'focus': '...',
                    'key_papers': []
                },
                'body_sections': [
                    {
                        'title': '章节标题',
                        'focus': '写作重点',
                        'key_points': ['要点1', '要点2'],
                        'comparison_points': ['对比点1', '对比点2']
                    },
                    ...
                ],
                'conclusion': {
                    'focus': '待定（根据文献内容生成）'
                }
            }
        """
        # === 阶段1 输入 ===
        print("\n" + "=" * 80)
        print("[阶段1] 生成综述大纲")
        print("=" * 80)
        print(f"[阶段1] 输入:")
        print(f"  - 主题: {topic}")

        import os
        from openai import AsyncOpenAI

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DEEPSEEK_API_KEY not configured")

        client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        system_prompt = """你是学术综述大纲设计专家。

你的任务是根据研究主题，设计一个高质量的文献综述大纲，并为每个章节生成搜索关键词。

要求：
1. **结构清晰**：包含引言、主体（2-5个主题章节）
2. **主题划分**：主体部分按研究主题或方法论划分
3. **逻辑连贯**：各主题之间要有逻辑关系
4. **结论待定**：结论部分需要根据实际文献内容来定，大纲中只需说明
5. **搜索关键词**：每个章节需要生成2-3个搜索关键词

**搜索关键词生成规则**：
- 从论文主题和章节标题中提取关键词
- 关键词应该是可以在文献数据库（如知网、Web of Science）中搜索的术语
- 关键词应该在论文的"标题"或"关键词"字段中出现
- 例如：主题"基于DMAIC的高通芯片质量管理研究"，章节"DMAIC在质量管理领域的研究进展"
  - 搜索关键词：["DMAIC", "质量管理", "高通芯片"]

输出格式（JSON）：
{
    "introduction": {
        "focus": "引言部分的写作重点",
        "key_papers": []
    },
    "body_sections": [
        {
            "title": "章节标题",
            "focus": "该章节的写作重点",
            "key_points": ["要点1", "要点2", "要点3"],
            "comparison_points": ["对比点1", "对比点2"],
            "search_keywords": ["关键词1", "关键词2", "关键词3"]
        }
    ],
    "conclusion": {
        "focus": "结论部分将根据实际文献内容总结研究现状、指出不足和未来方向"
    }
}

注意：
- body_sections 应该包含 2-5 个章节
- 每个章节的 key_points 应该有 3-5 个要点
- 每个章节的 comparison_points 应该有 2-3 个对比点
- 每个章节的 search_keywords 应该有 2-3 个关键词"""

        user_prompt = f"""请为以下研究主题设计综述大纲：

**主题**：{topic}

请输出JSON格式的大纲："""

        try:
            response = await client.chat.completions.create(
                model="deepseek-chat",
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

            # 验证每个章节是否有 search_keywords
            for section in outline.get('body_sections', []):
                if isinstance(section, dict):
                    if 'search_keywords' not in section or not section['search_keywords']:
                        # 如果LLM没有生成，则自动生成
                        title = section.get('title', '')
                        section['search_keywords'] = self._auto_generate_keywords(topic, title)

            # 打印生成的大纲和关键词
            print("\n" + "=" * 80)
            print("[阶段1] 生成的综述大纲")
            print("=" * 80)

            # 引言
            introduction = outline.get('introduction', {})
            if introduction:
                print(f"\n【引言】")
                print(f"  重点: {introduction.get('focus', 'N/A')}")
                key_papers = introduction.get('key_papers', [])
                if key_papers:
                    print(f"  关键文献: {', '.join([f'[{i}]' for i in key_papers])}")

            # 主体章节
            print(f"\n【主体章节】")
            for i, section in enumerate(outline.get('body_sections', []), 1):
                if isinstance(section, dict):
                    print(f"\n  章节{i}: {section.get('title', 'N/A')}")
                    print(f"    重点: {section.get('focus', 'N/A')}")
                    keywords = section.get('search_keywords', [])
                    if keywords:
                        print(f"    搜索关键词: {', '.join(keywords)}")

            # 结论
            conclusion = outline.get('conclusion', {})
            if conclusion:
                print(f"\n【结论】")
                print(f"  重点: {conclusion.get('focus', 'N/A')}")

            print("\n" + "=" * 80)

            # === 阶段1 输出 ===
            print(f"[阶段1] 输出:")
            print(f"  - 章节数: {len(outline.get('body_sections', []))} 个主体章节")
            print("=" * 80)

            return outline

        except Exception as e:
            print(f"[阶段1] 生成大纲失败: {e}")
            # 返回默认大纲
            return {
                "introduction": {
                    "focus": "介绍研究背景和意义",
                    "key_papers": []
                },
                "body_sections": [
                    {
                        "title": "理论基础与研究现状",
                        "focus": "梳理相关理论和方法",
                        "key_points": ["基本概念", "主要理论", "研究方法"],
                        "comparison_points": ["方法差异", "理论分歧"],
                        "search_keywords": self._auto_generate_keywords(topic, "理论基础与研究现状")
                    },
                    {
                        "title": "主要研究进展",
                        "focus": "总结当前研究的主要成果",
                        "key_points": ["技术进展", "应用案例", "效果评估"],
                        "comparison_points": ["研究结论对比", "应用效果"],
                        "search_keywords": self._auto_generate_keywords(topic, "主要研究进展")
                    }
                ],
                "conclusion": {
                    "focus": "结论部分将根据实际文献内容总结研究现状、指出不足和未来方向"
                }
            }

    def _auto_generate_keywords(self, topic: str, section_title: str) -> list:
        """
        自动生成搜索关键词（当LLM没有生成时使用）

        Args:
            topic: 论文主题
            section_title: 章节标题

        Returns:
            2-3个关键词列表
        """
        keywords = []

        # 从主题中提取关键词
        topic_keywords = self._extract_topic_keywords(topic)
        if topic_keywords:
            keywords.append(topic_keywords[0])  # 取第一个最重要的关键词

        # 从章节标题中提取关键词
        section_keywords = self._extract_chinese_words(section_title)
        if section_keywords:
            # 取前2个最重要的词
            keywords.extend(section_keywords[:2])

        # 去重并限制数量
        keywords = list(set(keywords))[:3]

        # 如果还是不足2个，补充通用的章节关键词
        if len(keywords) < 2:
            generic_keywords = ["研究", "应用", "方法", "现状", "进展"]
            for kw in generic_keywords:
                if kw not in keywords:
                    keywords.append(kw)
                    if len(keywords) >= 3:
                        break

        return keywords[:3]

    def _extract_topic_keywords(self, topic: str) -> list:
        """从主题中提取关键词"""
        import re

        keywords = []

        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]{2,}', topic)
        keywords.extend([w.lower() for w in english_words])

        # 提取中文词汇（2-4个字）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', topic)
        keywords.extend(chinese_words)

        return list(set(keywords))

    def _extract_chinese_words(self, text: str) -> list:
        """从文本中提取中文词汇"""
        import re
        # 提取2-4个字的中文词汇
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        return words

    def _optimize_search_queries_basic(
        self,
        search_queries: list,
        topic: str
    ) -> list:
        """
        基本搜索词优化（只做语言优化，不扩展同义词）

        Args:
            search_queries: 原始搜索查询列表
            topic: 论文主题

        Returns:
            优化后的搜索查询列表
        """
        # === 阶段2 输入 ===
        print("\n" + "=" * 80)
        print("[阶段2] 优化搜索查询")
        print("=" * 80)
        print(f"[阶段2] 输入:")
        print(f"  - 原始查询数: {len(search_queries)}")
        for i, q in enumerate(search_queries[:5], 1):
            print(f"    {i}. {q.get('query', 'N/A')}")
        if len(search_queries) > 5:
            print(f"    ... (还有 {len(search_queries) - 5} 个查询)")

        optimized = []

        # 数据源语言映射
        english_sources = ['openalex', 'crossref', 'datacite']
        chinese_sources = ['aminer', 'semantic_scholar', 'chinese_doi']

        # 为每个原始查询生成基本优化版本
        for query_item in search_queries:
            query = query_item.get('query', '')

            # 判断查询是否是英文
            if self._is_english(query):
                # 英文查询：添加到英文数据源
                for source in english_sources:
                    optimized.append({
                        'query': query,
                        'lang': 'en',
                        'source': source,
                        'original_query': query
                    })
            else:
                # 中文查询：添加到中文数据源
                for source in chinese_sources:
                    optimized.append({
                        'query': query,
                        'lang': 'zh',
                        'source': source,
                        'original_query': query
                    })

        # 去重
        seen = set()
        unique_optimized = []
        for item in optimized:
            key = (item['query'], item['source'])
            if key not in seen:
                seen.add(key)
                unique_optimized.append(item)

        # === 阶段2 输出 ===
        print(f"[阶段2] 输出:")
        print(f"  - 优化查询数: {len(unique_optimized)}")
        print(f"  - 英文查询: {sum(1 for q in unique_optimized if q.get('lang') == 'en')} 个")
        print(f"  - 中文查询: {sum(1 for q in unique_optimized if q.get('lang') == 'zh')} 个")
        print("=" * 80)

        return unique_optimized

    def _generate_synonym_queries(
        self,
        keywords: list,
        current_papers: list,
        seen_ids: set
    ) -> list:
        """
        生成同义词扩展查询（当原始关键词搜索结果不足时使用）

        Args:
            keywords: 原始关键词列表
            current_papers: 当前已找到的文献
            seen_ids: 已看到的文献ID集合

        Returns:
            同义词查询列表
        """
        synonym_queries = []

        # 尝试从学术用语库获取同义词
        try:
            from services.academic_term_service import AcademicTermService
            term_service = AcademicTermService()

            # 为每个关键词查找同义词
            for keyword in keywords:
                # 使用术语库搜索
                all_terms = term_service.search_keywords_from_topic(keyword)

                # 找出同义词
                for term in all_terms:
                    if term.lower() != keyword.lower():
                        # 检查这个同义词是否已经搜过
                        term_key = (term, 'synonym')
                        if term_key not in seen_ids:
                            synonym_queries.append({
                                'query': term,
                                'lang': 'zh' if self._contains_chinese(term) else 'en',
                                'source': 'all',
                                'is_synonym': True,
                                'original_query': keyword
                            })

            print(f"[同义词扩展] 为 {len(keywords)} 个关键词生成 {len(synonym_queries)} 个同义词查询")

        except Exception as e:
            print(f"[同义词扩展] 术语库查询失败: {e}")

        return synonym_queries

    def _generate_simplified_queries(
        self,
        keywords: list,
        current_papers: list,
        seen_ids: set
    ) -> list:
        """
        生成简化查询（当同义词扩展后结果仍不足时使用）

        Args:
            keywords: 原始关键词列表
            current_papers: 当前已找到的文献
            seen_ids: 已看到的文献ID集合

        Returns:
            简化查询列表
        """
        simplified_queries = []

        for keyword in keywords:
            # 策略1: 只使用关键词的前半部分
            if len(keyword) > 4:
                simplified = keyword[:len(keyword)//2]
                simplified_queries.append({
                    'query': simplified,
                    'lang': 'mixed',
                    'source': 'all',
                    'is_simplified': True,
                    'original_query': keyword
                })

            # 策略2: 对于组合关键词，拆分后单独搜索
            if '+' in keyword or ' ' in keyword:
                parts = keyword.replace('+', ' ').split()
                if len(parts) > 1:
                    # 只用第一个词
                    simplified_queries.append({
                        'query': parts[0],
                        'lang': 'mixed',
                        'source': 'all',
                        'is_simplified': True,
                        'original_query': keyword
                    })

        print(f"[简化查询] 生成 {len(simplified_queries)} 个简化查询")

        return simplified_queries

    async def _optimize_search_queries(
        self,
        search_queries: list,
        topic: str,
        section_keywords: dict
    ) -> list:
        """
        ⚠️ 已废弃 - 请使用 _optimize_search_queries_basic

        此方法不再被调用，保留仅为向后兼容。

        优化搜索查询（旧版）

        优化策略：
        1. 根据数据源类型使用不同语言：
           - OPENALEX、CROSSREF、DATACITE：用英文搜索
           - AMINER、SEMANTIC_SCHOLAR、CHINESE_DOI：用中文搜索
        2. 根据学术用语库扩展同义词、近义词

        Args:
            search_queries: 原始搜索查询列表
            topic: 论文主题
            section_keywords: 按章节分组的关键词

        Returns:
            优化后的搜索查询列表
        """
        warnings.warn(
            "_optimize_search_queries 已废弃，请使用 _optimize_search_queries_basic",
            DeprecationWarning,
            stacklevel=2
        )

        optimized = []

        # 数据源语言映射
        english_sources = ['openalex', 'crossref', 'datacite']
        chinese_sources = ['aminer', 'semantic_scholar', 'chinese_doi']

        # 获取学术用语库的同义词
        synonym_keywords = await self._get_synonyms_from_term_library(topic)

        print(f"[搜索词优化] 从术语库获取到 {len(synonym_keywords)} 个同义词/近义词")

        # 为每个原始查询生成优化版本
        for query_item in search_queries:
            query = query_item.get('query', '')

            # 为英文数据源生成英文查询
            for source in english_sources:
                # 尝试英文查询
                english_query = self._to_english_query(query)
                if english_query:
                    optimized.append({
                        'query': english_query,
                        'lang': 'en',
                        'source': source,
                        'original_query': query
                    })

            # 为中文数据源生成中文查询
            for source in chinese_sources:
                # 尝试中文查询
                chinese_query = self._to_chinese_query(query)
                if chinese_query:
                    optimized.append({
                        'query': chinese_query,
                        'lang': 'zh',
                        'source': source,
                        'original_query': query
                    })

        # 添加术语库扩展的查询
        for synonym in synonym_keywords:
            for source in english_sources:
                optimized.append({
                    'query': synonym,
                    'lang': 'en',
                    'source': source,
                    'is_synonym': True
                })

            # 对于中文同义词，也要添加到中文数据源
            if self._contains_chinese(synonym):
                for source in chinese_sources:
                    optimized.append({
                        'query': synonym,
                        'lang': 'zh',
                        'source': source,
                        'is_synonym': True
                    })

        # 去重
        seen = set()
        unique_optimized = []
        for item in optimized:
            key = (item['query'], item['source'])
            if key not in seen:
                seen.add(key)
                unique_optimized.append(item)

        print(f"[搜索词优化] 生成 {len(unique_optimized)} 个优化查询")
        print(f"[搜索词优化] 英文数据源查询: {sum(1 for q in unique_optimized if q.get('lang') == 'en')} 个")
        print(f"[搜索词优化] 中文数据源查询: {sum(1 for q in unique_optimized if q.get('lang') == 'zh')} 个")
        print(f"[搜索词优化] 术语库扩展查询: {sum(1 for q in unique_optimized if q.get('is_synonym'))} 个")

        return unique_optimized

    async def _get_synonyms_from_term_library(self, topic: str) -> list:
        """从学术用语库获取同义词和近义词"""
        try:
            from services.academic_term_service import AcademicTermService
            term_service = AcademicTermService()

            # 使用术语库搜索关键词
            keywords = term_service.search_keywords_from_topic(topic)

            # 扩展：获取相关术语的同义词
            all_synonyms = set(keywords)

            # 为每个关键词查找相关的术语
            for keyword in keywords:
                # 如果关键词在术语库中，获取其同义词
                # 这里简化处理，直接返回术语库找到的所有关键词
                pass

            return list(all_synonyms)

        except Exception as e:
            print(f"[搜索词优化] 术语库查询失败: {e}")
            return []

    def _to_english_query(self, query: str) -> str:
        """将查询转换为英文"""
        # 如果已经是英文，直接返回
        if self._is_english(query):
            return query

        # 尝试从主题中提取英文术语
        english_words = self._extract_english_words(query)
        if english_words:
            return ' '.join(english_words)

        # 如果没有英文，返回空
        return ''

    def _to_chinese_query(self, query: str) -> str:
        """将查询转换为中文"""
        # 如果已经是中文，直接返回
        if self._contains_chinese(query):
            return query

        # 对于英文查询，尝试从术语库获取中文翻译
        # 这里简化处理，直接返回原查询
        return query

    def _is_english(self, text: str) -> bool:
        """判断文本是否主要是英文"""
        import re
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        return english_chars > len(text) * 0.5

    def _contains_chinese(self, text: str) -> bool:
        """判断文本是否包含中文"""
        import re
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _extract_english_words(self, text: str) -> list:
        """从文本中提取英文单词"""
        import re
        return re.findall(r'[a-zA-Z]{2,}', text)

    async def _search_with_source(
        self,
        query: str,
        lang: str,
        source: str,
        years_ago: int,
        limit: int
    ) -> list:
        """
        根据数据源类型进行搜索

        Args:
            query: 搜索查询
            lang: 语言标识
            source: 数据源类型
            years_ago: 近N年
            limit: 返回数量

        Returns:
            论文列表
        """
        # 根据数据源类型选择搜索策略
        if source in ['openalex', 'crossref', 'datacite']:
            # 英文数据源，使用英文查询
            english_query = self._to_english_query(query)
            if not english_query:
                english_query = query

            return await self._call_search_api(english_query, source, years_ago, limit)

        elif source in ['aminer', 'semantic_scholar', 'chinese_doi']:
            # 中文数据源，使用中文查询
            chinese_query = self._to_chinese_query(query)
            if not chinese_query:
                chinese_query = query

            return await self._call_search_api(chinese_query, source, years_ago, limit)

        else:
            # 通用搜索
            return await self.search_service.search(
                query=query,
                years_ago=years_ago,
                limit=limit,
                use_all_sources=False  # 不使用所有源，避免重复
            )

    async def _call_search_api(
        self,
        query: str,
        source: str,
        years_ago: int,
        limit: int
    ) -> list:
        """
        调用特定数据源的API

        Args:
            query: 搜索查询
            source: 数据源类型
            years_ago: 近N年
            limit: 返回数量

        Returns:
            论文列表
        """
        # 这里可以扩展为调用特定数据源的API
        # 目前暂时使用通用的 search_service
        try:
            if source == 'aminer':
                # 调用AMiner API
                return await self.search_service.search(
                    query=query,
                    years_ago=years_ago,
                    limit=limit,
                    use_all_sources=False
                )
            elif source == 'semantic_scholar':
                # 调用Semantic Scholar API
                return await self.search_service.search(
                    query=query,
                    years_ago=years_ago,
                    limit=limit,
                    use_all_sources=False
                )
            else:
                # 其他数据源，使用通用搜索
                return await self.search_service.search(
                    query=query,
                    years_ago=years_ago,
                    limit=limit,
                    use_all_sources=True
                )
        except Exception as e:
            print(f"[搜索API] {source} 搜索失败: {e}")
            return []


