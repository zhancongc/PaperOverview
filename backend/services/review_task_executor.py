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
from services.stage_recorder import stage_recorder
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

        # 创建任务记录（使用stage_recorder）
        stage_recorder.create_task(task_id, topic, params)

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

            # === 执行阶段1-4：文献搜索和筛选（共同逻辑）===
            search_result = await self._search_and_filter_papers(
                topic=topic,
                params=params,
                task_id=task_id
            )

            framework = search_result['framework']
            all_papers = search_result['all_papers']
            filtered_papers = search_result['filtered_papers']
            stats = search_result['stats']
            specificity_guidance = search_result['specificity_guidance']
            total_count = len(filtered_papers)

            # === 阶段5: 生成综述（Function Calling 统一版本） ===
            api_key = os.getenv("DEEPSEEK_API_KEY")

            if not api_key:
                raise Exception("DEEPSEEK_API_KEY not configured")

            # 计算目标引用数
            target_citation_count = params.get('target_count', 50)

            # === 智能调整目标引用数 ===
            # 如果候选文献数量不足，按比例调整目标引用数
            available_papers = len(filtered_papers)
            if available_papers < target_citation_count:
                # 至少引用 70% 的候选文献，但不超过目标引用数
                # 使用 round() 四舍五入而不是 int() 向下取整
                adjusted_target = max(
                    round(available_papers * 0.7),  # 至少引用 70%
                    min(20, available_papers)  # 至少引用 20 篇
                )
                print(f"\n[阶段5] ⚠️  候选文献数 ({available_papers}) < 目标引用数 ({target_citation_count})")
                print(f"[阶段5] 调整目标引用数为: {adjusted_target} 篇")
                target_citation_count = adjusted_target

            print(f"\n[阶段5] 生成综述（Function Calling 统一版本）")
            print(f"[阶段5] 候选文献数: {total_count} 篇")
            print(f"[阶段5] 目标引用数: {target_citation_count} 篇")
            print(f"[阶段5] 使用渐进式信息披露，LLM按需选择最相关的文献")

            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "generating", "message": f"正在生成综述（从{total_count}篇候选中选择）..."}
            )

            # 检查参考文献数量
            MIN_PAPERS_THRESHOLD = 20
            if len(filtered_papers) < MIN_PAPERS_THRESHOLD:
                error_msg = f"参考文献数量不足，筛选后只有 {len(filtered_papers)} 篇，至少需要 {MIN_PAPERS_THRESHOLD} 篇才能生成综述"
                print(f"[错误] {error_msg}")

                task_manager.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error=error_msg
                )

                # 记录失败状态
                stage_recorder.record_review_generation(
                    task_id=task_id,
                    papers_count=len(filtered_papers),
                    review_length=0,
                    citation_count=0,
                    cited_papers_count=0,
                    validation_result=None,
                    review=None,
                    papers_summary=None,
                    status="failed",
                    error_message=error_msg
                )

                raise ValueError(error_msg)

            # 使用 Function Calling 统一版本生成器
            fc_generator = ReviewGeneratorFCUnified(api_key=api_key)

            # 确保最小引用数不超过可用文献数
            min_citation_count = min(
                params.get('target_count', 50),
                len(filtered_papers)
            )

            # 一次性生成完整综述
            review, cited_papers = await fc_generator.generate_review(
                topic=topic,
                papers=filtered_papers,
                framework=framework,
                target_citation_count=target_citation_count,
                min_citation_count=min_citation_count,
                recent_years_ratio=params.get('recent_years_ratio', 0.5),
                english_ratio=params.get('english_ratio', 0.3),
                specificity_guidance=specificity_guidance,
                model=params.get('review_model', 'deepseek-reasoner'),  # 默认使用 reasoner 支持长综述生成，思考模式已关闭
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

            # === 记录阶段5完成 ===
            stage_recorder.update_task_status(task_id, status="processing", current_stage="生成综述")

            # 准备文献摘要（只包含核心字段，避免存储过多数据）
            papers_summary = []
            for p in cited_papers:
                url = p.get('url') or ''
                papers_summary.append({
                    'id': p.get('id'),
                    'title': p.get('title', '')[:200],  # 限制标题长度
                    'authors': p.get('authors', [])[:5],  # 限制作者数量
                    'year': p.get('year'),
                    'venue': (p.get('journal', '') or p.get('venue', ''))[:100],  # 限制来源长度
                    'cited_by_count': p.get('cited_by_count', 0),
                    'url': url[:500] if url else ''  # 限制URL长度
                })

            # 准备候选文献池摘要（筛选前的所有论文）
            candidate_pool_summary = []
            for p in all_papers:
                url = p.get('url') or ''
                candidate_pool_summary.append({
                    'id': p.get('id'),
                    'title': p.get('title', '')[:200],  # 限制标题长度
                    'authors': p.get('authors', [])[:5],  # 限制作者数量
                    'year': p.get('year'),
                    'venue': (p.get('journal', '') or p.get('venue', ''))[:100],  # 限制来源长度
                    'cited_by_count': p.get('cited_by_count', 0),
                    'url': url[:500] if url else ''  # 限制URL长度
                })

            stage_recorder.record_review_generation(
                task_id=task_id,
                papers_count=len(all_papers),
                review_length=len(review),
                citation_count=review.count('['),  # 粗略估计引用次数
                cited_papers_count=len(cited_papers),
                validation_result=final_validation,
                review=review,  # 存储完整综述内容
                papers_summary=papers_summary,  # 存储文献摘要
                candidate_pool_summary=candidate_pool_summary  # 存储候选文献池摘要
            )

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

            # 更新阶段记录器中的任务状态
            stage_recorder.update_task_status(
                task_id,
                status="completed",
                current_stage="完成",
                completed_at=datetime.now(),
                review_record_id=record.id
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

            # 更新阶段记录器中的任务状态
            stage_recorder.update_task_status(
                task_id,
                status="failed",
                current_stage="失败",
                error_message=str(e),
                completed_at=datetime.now()
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

        # 收集搜索来源记录（paper_id -> [search_keywords]）
        paper_search_sources = []  # [{"paper_id": "...", "search_keyword": "..."}, ...]
        paper_source_seen = set()  # 用于去重 (paper_id, search_keyword)

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

                # 优先使用英文查询（将英文查询移到前面）
                en_queries = [q for q in unique_optimized_queries if q.get('lang') == 'en']
                zh_queries = [q for q in unique_optimized_queries if q.get('lang') != 'en']
                unique_optimized_queries = en_queries + zh_queries

                print(f"[阶段3] 优化查询顺序调整:")
                print(f"  - 英文查询: {len(en_queries)} 个（优先）")
                print(f"  - 其他查询: {len(zh_queries)} 个")

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
                            source_key = (paper_id, query)
                            if paper_id and paper_id not in section_seen_ids:
                                section_seen_ids.add(paper_id)
                                section_papers.append(paper)
                                # 记录搜索来源（去重）
                                if source_key not in paper_source_seen:
                                    paper_source_seen.add(source_key)
                                    paper_search_sources.append({
                                        "paper_id": paper_id,
                                        "search_keyword": query
                                    })
                            elif paper_id and paper_id in section_seen_ids:
                                # 文献已存在，但通过不同关键词搜到，也记录来源（去重）
                                if source_key not in paper_source_seen:
                                    paper_source_seen.add(source_key)
                                    paper_search_sources.append({
                                        "paper_id": paper_id,
                                        "search_keyword": query
                                    })

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
                                source_key = (paper_id, query)
                                if paper_id and paper_id not in section_seen_ids:
                                    section_seen_ids.add(paper_id)
                                    section_papers.append(paper)
                                    # 记录搜索来源（去重）
                                    if source_key not in paper_source_seen:
                                        paper_source_seen.add(source_key)
                                        paper_search_sources.append({
                                            "paper_id": paper_id,
                                            "search_keyword": query
                                        })
                                elif paper_id and paper_id in section_seen_ids:
                                    # 文献已存在，但通过不同关键词搜到，也记录来源（去重）
                                    if source_key not in paper_source_seen:
                                        paper_source_seen.add(source_key)
                                        paper_search_sources.append({
                                            "paper_id": paper_id,
                                            "search_keyword": query
                                        })

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
                            source_key = (paper_id, keyword)
                            if paper_id and paper_id not in existing_ids:
                                section_papers.append(paper)
                                existing_ids.add(paper_id)
                                # 记录搜索来源（去重）
                                if source_key not in paper_source_seen:
                                    paper_source_seen.add(source_key)
                                    paper_search_sources.append({
                                        "paper_id": paper_id,
                                        "search_keyword": keyword
                                    })
                            elif paper_id and paper_id in existing_ids:
                                # 文献已存在，但通过不同关键词搜到，也记录来源（去重）
                                if source_key not in paper_source_seen:
                                    paper_source_seen.add(source_key)
                                    paper_search_sources.append({
                                        "paper_id": paper_id,
                                        "search_keyword": keyword
                                    })

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
                                source_key = (paper_id, keyword)
                                if paper_id and paper_id not in existing_ids:
                                    section_papers.append(paper)
                                    existing_ids.add(paper_id)
                                    # 记录搜索来源（去重）
                                    if source_key not in paper_source_seen:
                                        paper_source_seen.add(source_key)
                                        paper_search_sources.append({
                                            "paper_id": paper_id,
                                            "search_keyword": keyword
                                        })
                                elif paper_id and paper_id in existing_ids:
                                    # 文献已存在，但通过不同关键词搜到，也记录来源（去重）
                                    if source_key not in paper_source_seen:
                                        paper_source_seen.add(source_key)
                                        paper_search_sources.append({
                                            "paper_id": paper_id,
                                            "search_keyword": keyword
                                        })

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

        # === 验证搜索结果与题目主题一致性 ===
        print(f"\n[阶段3] 验证搜索结果与题目主题一致性...")
        try:
            relevance_score = self._validate_search_relevance(topic, all_papers)
            print(f"[阶段3] 主题相关性得分: {relevance_score:.1%}")

            if relevance_score < 0.3:
                print(f"[阶段3] ⚠️  警告: 搜索结果与题目相关性过低（{relevance_score:.1%} < 30%）")
                print(f"[阶段3] 可能原因:")
                print(f"[阶段3]   1. 关键词翻译不准确")
                print(f"[阶段3]   2. 题目与搜索结果不匹配")
                print(f"[阶段3]   3. 需要重新定义搜索策略")
                print(f"[阶段3] 建议: 请检查题目和关键词是否一致")
                # 不中断流程，但给出警告
        except Exception as e:
            print(f"[阶段3] 主题相关性验证失败: {e}")

        # AMiner论文详情补充
        all_papers = await self._enrich_aminer_papers(all_papers)

        # === 保存搜索来源记录 ===
        print(f"[阶段3] 保存搜索来源记录: {len(paper_search_sources)} 条")
        from services.stage_recorder import stage_recorder
        stage_recorder.record_paper_search_sources(task_id, paper_search_sources)

        # === 为每篇论文添加 search_keywords 字段 ===
        # 按 paper_id 聚合关键词
        paper_id_to_keywords = {}
        for source in paper_search_sources:
            paper_id = source['paper_id']
            keyword = source['search_keyword']
            if paper_id not in paper_id_to_keywords:
                paper_id_to_keywords[paper_id] = set()
            paper_id_to_keywords[paper_id].add(keyword)

        # 添加到论文对象
        for paper in all_papers:
            paper_id = paper.get('id')
            if paper_id in paper_id_to_keywords:
                paper['search_keywords'] = list(paper_id_to_keywords[paper_id])

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

        # 打印筛选前的参考文献列表（前100篇）
        print(f"\n[阶段4] 筛选前的参考文献列表（前100篇）:")
        print(f"{'序号':<6}{'标题':<60}{'年份':<8}{'被引':<8}{'语言':<6}{'来源'}")
        print("-" * 120)
        for i, paper in enumerate(all_papers[:100], 1):
            title = paper.get('title', '')[:57] + '...' if len(paper.get('title', '')) > 57 else paper.get('title', '')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            # 根据标题内容判断语言（更可靠）
            title_full = paper.get('title', '')
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in title_full)
            lang = '英文' if not has_chinese else '中文'
            venue = (paper.get('journal', '') or paper.get('venue', ''))[:20]
            print(f"{i:<6}{title:<60}{year:<8}{cited:<8}{lang:<6}{venue}")
        if len(all_papers) > 100:
            print(f"... 共 {len(all_papers)} 篇文献")

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
        removed_details = []

        for paper in unique_papers:
            # 计算质量得分
            quality_score = quality_filter.get_paper_quality_score(paper)

            # 过滤低质量文献
            if quality_score >= 10:  # 质量得分阈值降低到10，更宽松
                paper['quality_score'] = quality_score
                filtered_papers.append(paper)
            else:
                removed_count += 1
                removed_details.append({
                    'title': paper.get('title', '')[:50],
                    'score': quality_score,
                    'year': paper.get('year'),
                    'cited': paper.get('cited_by_count', 0),
                    'venue': (paper.get('journal', '') or paper.get('venue', ''))[:30]
                })

        print(f"[阶段4] 质量过滤: 移除 {removed_count} 篇低质量文献")
        print(f"[阶段4] 保留文献数: {len(filtered_papers)} 篇")

        # 打印被过滤文献的详细信息（前20篇）
        if removed_details:
            print(f"\n[阶段4] 被过滤文献列表（前20篇）:")
            print(f"{'得分':<8}{'年份':<8}{'被引':<8}{'标题':<45}{'来源'}")
            print("-" * 100)
            for detail in removed_details[:20]:
                print(f"{detail['score']:<8.1f}{detail['year']:<8}{detail['cited']:<8}{detail['title']:<45}{detail['venue']}")
            if len(removed_details) > 20:
                print(f"... 共 {len(removed_details)} 篇被过滤")

        # 3. 主题相关性检查（按小节分别判断）
        print(f"\n[阶段4] 开始主题相关性检查（按小节分别判断）...")
        task_manager.update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress={"step": "topic_relevance_check", "message": f"按小节检查文献主题相关性..."}
        )

        # 获取按小节分组的论文
        papers_by_section = search_result.get('sections', {})
        section_keywords = framework.get('section_keywords', {})

        # 为每个小节创建论文到小节的映射（一篇论文可能属于多个小节）
        paper_to_sections = {}
        for section_title, papers in papers_by_section.items():
            for paper in papers:
                paper_id = paper.get('id')
                if paper_id:
                    if paper_id not in paper_to_sections:
                        paper_to_sections[paper_id] = []
                    paper_to_sections[paper_id].append(section_title)

        # 为当前filtered_papers添加section信息
        for paper in filtered_papers:
            paper_id = paper.get('id')
            paper['sections'] = paper_to_sections.get(paper_id, ['未知小节'])

        # 按小节分组进行相关性判断
        relevant_papers = []
        topic_irrelevant_count = 0
        topic_irrelevant_details = []
        seen_paper_ids = set()  # 用于去重（一篇论文可能在多个小节中被判断）

        try:
            import httpx
            api_key = os.getenv("DEEPSEEK_API_KEY")
            client = httpx.AsyncClient(timeout=120.0)

            # 对每个小节分别处理
            for section_title, section_papers in papers_by_section.items():
                if section_title in ['引言', '结论']:
                    continue

                # 获取该小节的质量过滤后的论文
                section_filtered_papers = []
                for paper in filtered_papers:
                    paper_id = paper.get('id')
                    # 检查这篇论文是否属于当前小节
                    for sp in section_papers:
                        if sp.get('id') == paper_id:
                            section_filtered_papers.append(paper)
                            break

                if not section_filtered_papers:
                    continue

                print(f"\n[阶段4] 判断小节 '{section_title}' 的文献相关性...")

                # 获取该小节的关键词
                keywords_for_section = section_keywords.get(section_title, [])
                keywords_str = ", ".join(keywords_for_section) if keywords_for_section else "无"

                # === 第一步：基于标题的快速筛选 ===
                print(f"[阶段4] 步骤1: 基于标题快速筛选...")
                from services.title_relevance_checker import batch_check_titles
                from services.contextual_keyword_translator import DomainKnowledge

                # 识别领域
                domain = DomainKnowledge.identify_domain(topic)

                # 批量检查标题相关性
                title_relevant, title_irrelevant, title_uncertain = batch_check_titles(
                    section_filtered_papers,
                    topic,
                    domain
                )

                print(f"[阶段4] 标题检查结果:")
                print(f"  - 明显相关: {len(title_relevant)} 篇")
                print(f"  - 明显不相关: {len(title_irrelevant)} 篇")
                print(f"  - 需要进一步判断: {len(title_uncertain)} 篇")

                # 显示明显不相关的文献样本
                if title_irrelevant:
                    print(f"[阶段4] 明显不相关的文献样本（前3篇）:")
                    for paper in title_irrelevant[:3]:
                        reason = paper.get('_title_check', {}).get('reason', '')
                        title = paper.get('title', '')[:60]
                        print(f"  - {title}")
                        print(f"    原因: {reason}")

                # 第二步：只对不确定的文献使用 LLM 判断
                llm_papers = title_uncertain.copy()

                # 明确相关的文献直接保留
                for paper in title_relevant:
                    paper_id = paper.get('id')
                    if paper_id and paper_id not in seen_paper_ids:
                        seen_paper_ids.add(paper_id)
                        relevant_papers.append(paper)

                if not llm_papers:
                    print(f"[阶段4] 所有文献通过标题检查完成，跳过 LLM 判断")
                    continue

                print(f"[阶段4] 步骤2: 对 {len(llm_papers)} 篇文献使用 LLM 判断...")

                # 构建该小节的文献列表
                papers_text = ""
                for i, paper in enumerate(llm_papers, 1):
                    title = paper.get('title', '')
                    venue = paper.get('journal', '') or paper.get('venue', '')
                    papers_text += f"{i}. 标题: {title}\n   来源: {venue}\n\n"

                prompt = f"""请判断以下文献是否适合用于撰写以下小节的内容。

**重要提示**: 首先检查文献标题是否与小节主题相关。标题是最重要的判断依据。

研究总主题: {topic}
当前小节: {section_title}
小节关键词: {keywords_str}

文献列表:
{papers_text}

请对每篇文献进行判断，返回格式如下（严格按格式，不要有多余文字）：
相关: [序号列表，用逗号分隔]
不相关: [序号列表，用逗号分隔]

例如：
相关: 1,2,4,7,10
不相关: 3,5,6,8,9

判断标准：
1. **标题匹配度**：文献标题是否包含与小节主题相关的关键词
2. **主题一致性**：文献的研究内容是否能支持本小节的论述
3. **领域适配性**：
   - 如果小节讨论的是通用方法，其他行业的应用文献也可以保留
   - 如果小节讨论的是特定领域，则优先保留该领域的文献
4. **无关性判断**：只有在文献明显**无法为本小节提供任何有价值的信息**时，才判定为不相关
   - 例如：小节讨论"数学软件"，而文献是"烹饪食谱"或"电影评论"
   - **重要**：不要仅仅因为文献属于某个特定领域（如物理、化学、生物）就判定为不相关
   - **跨学科研究**：如果题目本身涉及多个领域，应该保留相关领域的文献

研究总主题: {topic}

当前小节: {section_title}
小节关键词: {keywords_str}

文献列表:
{papers_text}

请对每篇文献进行判断，返回格式如下（严格按格式，不要有多余文字）：
相关: [序号列表，用逗号分隔]
不相关: [序号列表，用逗号分隔]

例如：
相关: 1,2,4,7,10
不相关: 3,5,6,8,9

判断标准：
1. **标题匹配度**：文献标题是否包含与小节主题相关的关键词
2. **主题一致性**：文献的研究内容是否能支持本小节的论述
3. **领域适配性**：
   - 如果小节讨论的是通用方法，其他行业的应用文献也可以保留
   - 如果小节讨论的是特定领域，则优先保留该领域的文献
4. **无关性判断**：只有在文献明显**无法为本小节提供任何有价值的信息**时，才判定为不相关
   - 例如：小节讨论"数学软件"，而文献是"烹饪食谱"或"电影评论"
   - **重要**：不要仅仅因为文献属于某个特定领域（如物理、化学、生物）就判定为不相关
   - **跨学科研究**：如果题目本身涉及多个领域，应该保留相关领域的文献
"""

                # 调用LLM判断
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                )

                result = response.json()
                content = result['choices'][0]['message']['content'].strip()

                # 解析结果
                relevant_indices = []
                irrelevant_indices = []

                for line in content.split('\n'):
                    if line.startswith('相关:'):
                        indices_str = line.replace('相关:', '').strip()
                        relevant_indices = [int(x.strip()) for x in indices_str.split(',') if x.strip().isdigit()]
                    elif line.startswith('不相关:'):
                        indices_str = line.replace('不相关:', '').strip()
                        irrelevant_indices = [int(x.strip()) for x in indices_str.split(',') if x.strip().isdigit()]

                # 收集结果（注意：这里使用 llm_papers，因为只有不确定的论文被送到了 LLM）
                for idx, paper in enumerate(llm_papers, 1):
                    paper_id = paper.get('id')
                    if idx in relevant_indices:
                        if paper_id not in seen_paper_ids:
                            seen_paper_ids.add(paper_id)
                            relevant_papers.append(paper)
                    # 不相关的论文不需要处理，因为它们已经被标记为不相关了

            # 现在，找出那些在所有小节中都没被选中的论文
            all_filtered_ids = set(p.get('id') for p in filtered_papers)
            relevant_ids = set(p.get('id') for p in relevant_papers)
            always_irrelevant_ids = all_filtered_ids - relevant_ids

            for paper in filtered_papers:
                paper_id = paper.get('id')
                if paper_id in always_irrelevant_ids:
                    topic_irrelevant_count += 1
                    topic_irrelevant_details.append({
                        'title': paper.get('title', '')[:50],
                        'year': paper.get('year'),
                        'cited': paper.get('cited_by_count', 0),
                        'venue': (paper.get('journal', '') or paper.get('venue', ''))[:30],
                        'sections': paper.get('sections', [])
                    })

            await client.aclose()

        except Exception as e:
            print(f"[阶段4] LLM检查出错，保留所有文献: {e}")
            import traceback
            traceback.print_exc()
            relevant_papers = filtered_papers[:]

        filtered_papers = relevant_papers

        print(f"\n[阶段4] 主题相关性检查完成:")
        print(f"  - 移除 {topic_irrelevant_count} 篇主题不相关的文献")
        print(f"  - 保留 {len(filtered_papers)} 篇文献")

        # 打印主题不相关的文献
        if topic_irrelevant_details:
            print(f"\n[阶段4] 主题不相关文献列表（前20篇）:")
            print(f"{'年份':<8}{'被引':<8}{'标题':<45}{'来源':<25}{'所属小节'}")
            print("-" * 120)
            for detail in topic_irrelevant_details[:20]:
                sections_str = ", ".join(detail.get('sections', []))[:30]
                print(f"{detail['year']:<8}{detail['cited']:<8}{detail['title']:<45}{detail['venue']:<25}{sections_str}")
            if len(topic_irrelevant_details) > 20:
                print(f"... 共 {len(topic_irrelevant_details)} 篇被移除")

        # 5. 增强相关性评分（添加到论文中）
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

        # 6. 按相关性评分排序
        filtered_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        print(f"[阶段4] 已添加相关性评分并排序")

        # 7. 统计信息
        try:
            stats = self.filter_service.get_statistics(filtered_papers)

            print(f"\n[阶段4] 质量过滤完成:")
            print(f"  - 总文献数: {len(filtered_papers)}")
            print(f"  - 英文文献: {stats.get('english_count', 0)}")
            print(f"  - 近5年文献: {stats.get('recent_count', 0)} ({stats.get('recent_ratio', 0):.1%})")
            print(f"  - 平均被引: {stats.get('avg_citations', 0):.1f}")
        except Exception as e:
            print(f"\n[阶段4] 质量过滤完成:")
            print(f"  - 总文献数: {len(filtered_papers)}")
            print(f"  - 统计信息获取失败: {e}")

        # 打印筛选后的参考文献列表（前50篇）
        print(f"\n[阶段4] 筛选后的参考文献列表（前50篇）:")
        print(f"{'序号':<6}{'标题':<60}{'年份':<8}{'被引':<8}{'语言'}")
        print("-" * 100)
        for i, paper in enumerate(filtered_papers[:50], 1):
            title = paper.get('title', '')[:57] + '...' if len(paper.get('title', '')) > 57 else paper.get('title', '')
            year = paper.get('year', 'N/A')
            cited = paper.get('cited_by_count', 0)
            # 根据标题内容判断语言（更可靠）
            title_full = paper.get('title', '')
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in title_full)
            lang = '英文' if not has_chinese else '中文'
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
            'total_count': len(filtered_papers),
            'quality_filtered_count': removed_count,
            'quality_filtered_details': removed_details,
            'topic_irrelevant_count': topic_irrelevant_count,
            'topic_irrelevant_details': topic_irrelevant_details
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

    async def _generate_review_outline(self, topic: str, research_direction: str = "") -> dict:
        """
        生成综述大纲

        Args:
            topic: 论文主题
            research_direction: 研究方向（可选，用于提高搜索相关性）

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
        if research_direction:
            print(f"  - 研究方向: {research_direction}")

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

**搜索关键词生成规则**（非常重要）：
- 从论文主题和章节标题中提取关键词
- 关键词应该是可以在文献数据库（如知网、Web of Science）中搜索的术语
- 关键词应该在论文的"标题"或"关键词"字段中出现
- **根据章节性质决定是否加特定领域限定**：
  * 如果章节讨论的是**通用方法论**（如"DMAIC在质量管理领域的研究进展"），关键词不要加特定行业限定，这样可以搜到其他行业的相关文献
    - 正确示例（通用方法章节）：["DMAIC质量管理", "质量改进方法", "质量管理框架"]
  * 如果章节讨论的是**特定领域应用**（如"芯片行业的质量管理进展"），关键词必须加领域限定
    - 正确示例（特定领域章节）：["芯片质量管理", "高通芯片质量控制", "芯片制造质量改进"]
- 避免使用单个通用词汇（如"LLM"、"evaluation"、"质量"等单独使用）
- 每个搜索关键词都应该是一个完整的短语

例如：
- 主题："Enhancing LLM-based Evaluation of Low-Resource Code via Code Translation"
- 搜索关键词应该是：
  ["LLM-based code evaluation", "low-resource programming languages", "code translation for LLM evaluation"]

再例如：
- 主题："基于DMAIC的高通芯片质量管理研究"
- 章节1："DMAIC在质量管理领域的研究进展"（通用方法）
- 搜索关键词：["DMAIC质量管理", "质量改进方法", "质量管理框架"]
- 章节2："芯片行业的质量管理实践"（特定领域）
- 搜索关键词：["芯片质量管理", "高通芯片质量控制", "芯片制造质量改进"]

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

**主题**：{topic}"""

        if research_direction:
            user_prompt += f"""

**研究方向**：{research_direction}
（重要：生成的大纲和搜索关键词应该围绕这个研究方向展开）"""

        user_prompt += """

请输出JSON格式的大纲："""

        try:
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # 生成大纲需要结构化输出
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

    def _is_generic_methodology_section(self, section_title: str) -> bool:
        """
        判断章节是否讨论通用方法论（不需要加特定领域限定）

        Returns:
            True 如果是通用方法论章节，False 如果是特定领域章节
        """
        generic_indicators = [
            # 中文通用方法论标识
            "研究进展", "综述", "方法", "方法论", "理论基础", "基本概念",
            "技术进展", "应用案例", "效果评估", "挑战与展望", "未来方向",
            "研究现状", "理论框架", "研究方法", "关键技术",
            # 英文通用方法论标识
            "research progress", "review", "methodology", "theoretical basis",
            "basic concepts", "technical progress", "application", "case study",
            "evaluation", "challenges", "future directions", "state of the art",
            "theoretical framework", "research method", "key technology"
        ]

        specific_indicators = [
            # 中文特定领域标识（通常出现在标题中）
            "在", "应用于", "用于", "行业", "领域", "场景", "环境",
            # 英文特定领域标识
            "in", "for", "applied to", "industry", "domain", "scenario", "environment"
        ]

        section_lower = section_title.lower()

        # 检查是否有特定领域标识
        for indicator in specific_indicators:
            if indicator in section_lower:
                return False

        # 检查是否有通用方法论标识
        for indicator in generic_indicators:
            if indicator.lower() in section_lower:
                return True

        # 默认：如果标题比较短且抽象，认为是通用的
        if len(section_title) < 10 and not any(c in section_title for c in "的之在用于"):
            return True

        return False

    def _auto_generate_keywords(self, topic: str, section_title: str) -> list:
        """
        自动生成搜索关键词（当LLM没有生成时使用）

        根据章节性质决定是否加领域限定：
        - 通用方法论章节：只使用章节关键词，不加特定领域限定
        - 特定领域章节：加上领域限定

        Args:
            topic: 论文主题
            section_title: 章节标题

        Returns:
            2-3个关键词列表
        """
        keywords = []

        # 判断主题语言
        is_english_topic = self._is_english(topic)

        # 判断是否是通用方法论章节
        is_generic = self._is_generic_methodology_section(section_title)

        # 从主题中提取核心关键词
        topic_keywords = self._extract_topic_keywords(topic)

        # 从章节标题中提取关键词
        section_keywords = self._extract_chinese_words(section_title)
        if is_english_topic:
            section_keywords = self._extract_topic_keywords(section_title)

        if is_generic:
            # 通用方法论章节：优先使用章节关键词
            print(f"[自动生成关键词] 章节 '{section_title}' 是通用方法论，不加领域限定")

            if is_english_topic:
                # 英文：使用章节关键词
                if section_keywords:
                    # 直接使用章节关键词组合
                    if len(section_keywords) >= 2:
                        keywords.append(" ".join(section_keywords[:3]))
                    keywords.extend(section_keywords[:3])
                else:
                    keywords.append(section_title)
            else:
                # 中文：使用章节关键词
                if section_keywords:
                    if len(section_keywords) >= 2:
                        keywords.append("".join(section_keywords[:3]))
                    keywords.extend(section_keywords[:3])
                else:
                    keywords.append(section_title)
        else:
            # 特定领域章节：加上领域限定
            print(f"[自动生成关键词] 章节 '{section_title}' 是特定领域，加领域限定")

            if is_english_topic:
                # 英文主题：生成组合短语
                if topic_keywords:
                    # 用主题的前2-3个词作为基础
                    base_topic = " ".join(topic_keywords[:3]) if len(topic_keywords) >= 2 else topic

                    # 生成带章节限定的关键词
                    if section_keywords:
                        for sec_kw in section_keywords[:2]:
                            keywords.append(f"{sec_kw} {base_topic}")

                    # 添加主题本身作为关键词
                    keywords.append(base_topic)

                    # 添加更具体的组合
                    if len(topic_keywords) >= 2:
                        keywords.append(f"{topic_keywords[0]} {topic_keywords[1]}")
            else:
                # 中文主题：生成组合短语
                if topic_keywords:
                    # 用主题的前2-3个词作为基础
                    base_topic = "".join(topic_keywords[:3]) if len(topic_keywords) >= 2 else topic

                    # 生成带章节限定的关键词
                    if section_keywords:
                        for sec_kw in section_keywords[:2]:
                            keywords.append(f"{sec_kw}{base_topic}")

                    # 添加主题本身作为关键词
                    keywords.append(base_topic)

                    # 添加更具体的组合
                    if len(topic_keywords) >= 2:
                        keywords.append(f"{topic_keywords[0]}{topic_keywords[1]}")

        # 如果关键词太少，添加章节标题
        if len(keywords) < 2:
            keywords.append(section_title)
            if section_title != topic:
                keywords.append(topic)

        # 去重并限制数量
        keywords = list(set(keywords))[:3]

        # 确保至少有2个关键词
        result = keywords[:3]
        while len(result) < 2:
            result.append(section_title if section_title else topic)

        print(f"[自动生成关键词] 主题: {topic}, 章节: {section_title}")
        print(f"[自动生成关键词] 生成: {result}")

        return result

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

    def _validate_search_relevance(self, topic: str, papers: list) -> float:
        """
        验证搜索结果与题目主题的一致性

        Args:
            topic: 论文题目
            papers: 搜索到的文献列表

        Returns:
            相关性得分 (0-1)
        """
        from services.contextual_keyword_translator import DomainKnowledge

        # 第一步：识别题目领域
        domain = DomainKnowledge.identify_domain(topic)

        if not domain:
            # 无法识别领域，使用通用验证
            return self._generic_relevance_check(topic, papers)

        # 第二步：获取领域约束
        domain_info = DomainKnowledge.DOMAINS.get(domain, {})
        related_terms = domain_info.get("related_concepts", [])
        exclude_terms = domain_info.get("exclude_terms", [])

        print(f"[相关性验证] 识别领域: {domain_info.get('name', domain)}")
        print(f"[相关性验证] 相关术语: {related_terms[:5]}...")
        print(f"[相关性验证] 排除术语: {exclude_terms[:5]}...")

        # 第三步：检查前20篇文献
        sample_papers = papers[:20] if len(papers) >= 20 else papers

        relevant_count = 0
        exclude_count = 0
        total_count = len(sample_papers)

        for paper in sample_papers:
            title = paper.get('title', '').lower()

            # 检查是否包含相关术语
            is_relevant = False
            for term in related_terms:
                if term.lower() in title:
                    is_relevant = True
                    relevant_count += 1
                    break

            # 检查是否包含排除术语
            for term in exclude_terms:
                if term.lower() in title:
                    exclude_count += 1
                    break

        # 计算相关性得分
        if total_count > 0:
            relevance_score = relevant_count / total_count
        else:
            relevance_score = 0.0

        print(f"[相关性验证] 相关文献: {relevant_count}/{total_count}")
        print(f"[相关性验证] 排除文献: {exclude_count} 篇")

        # 如果排除文献太多，降低得分
        if exclude_count > total_count * 0.5:
            relevance_score *= 0.5
            print(f"[相关性验证] 排除文献过多，得分减半")

        return relevance_score

    def _generic_relevance_check(self, topic: str, papers: list) -> float:
        """
        通用相关性检查（当无法识别领域时）

        Args:
            topic: 论文题目
            papers: 搜索到的文献列表

        Returns:
            相关性得分 (0-1)
        """
        # 提取题目中的关键词
        topic_words = set()
        # 英文单词
        import re
        english_words = re.findall(r'[a-zA-Z]{3,}', topic)
        topic_words.update([w.lower() for w in english_words])
        # 中文词汇
        chinese_words = self._extract_chinese_words(topic)
        topic_words.update(chinese_words)

        # 检查前20篇文献
        sample_papers = papers[:20] if len(papers) >= 20 else papers

        relevant_count = 0
        total_count = len(sample_papers)

        for paper in sample_papers:
            title = paper.get('title', '').lower()
            # 检查是否包含题目中的关键词
            for word in topic_words:
                if word in title:
                    relevant_count += 1
                    break

        if total_count > 0:
            return relevant_count / total_count
        return 0.0

    async def _optimize_search_queries_basic(
        self,
        search_queries: list,
        topic: str,
        research_direction: str = ""
    ) -> list:
        """
        基本搜索词优化（语言优化 + 翻译扩展）

        Args:
            search_queries: 原始搜索查询列表
            topic: 论文主题
            research_direction: 研究方向（可选，用于提高翻译相关性）

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
        # Semantic Scholar 主要是英文数据库（虽然也有一定中文支持）
        english_sources = ['openalex', 'crossref', 'datacite', 'semantic_scholar']
        chinese_sources = ['aminer', 'chinese_doi']

        # === 关键词组合逻辑 ===
        # 将原始查询按章节分组，然后生成组合查询
        section_queries = {}  # {章节标题: [查询1, 查询2, ...]}

        for query_item in search_queries:
            query = query_item.get('query', '')
            section = query_item.get('section', 'default')

            if section not in section_queries:
                section_queries[section] = []
            section_queries[section].append(query)

        print(f"[阶段2] 关键词组合:")
        print(f"  章节: {len(section_queries)} 个")

        # 为每个章节生成组合查询
        combination_count = 0
        for section, queries in section_queries.items():
            print(f"  - {section}: {len(queries)} 个关键词")

            if len(queries) == 1:
                # 单个关键词：直接使用
                query = queries[0]
                lang = 'en' if self._is_english(query) else 'zh'

                # 根据语言分配数据源
                sources = english_sources if lang == 'en' else chinese_sources
                for source in sources:
                    optimized.append({
                        'query': query,
                        'lang': lang,
                        'source': source,
                        'original_query': query,
                        'is_combination': False
                    })

            elif len(queries) >= 2:
                # 多个关键词：生成 AND 组合查询
                print(f"    生成 AND 组合查询...")

                # 提取核心关键词（通常是前2个）
                primary_kw = queries[0]
                secondary_kw = queries[1]

                # 生成 AND 查询
                combined_query = f'{primary_kw} AND {secondary_kw}'

                lang = 'en' if self._is_english(combined_query) else 'zh'
                sources = english_sources if lang == 'en' else chinese_sources

                for source in sources:
                    optimized.append({
                        'query': combined_query,
                        'lang': lang,
                        'source': source,
                        'original_query': f'{primary_kw} + {secondary_kw}',
                        'is_combination': True
                    })

                combination_count += 1
                print(f"      {combined_query}")

                # 如果有第3个关键词，生成三词组合
                if len(queries) >= 3:
                    tertiary_kw = queries[2]
                    combined_query_3 = f'{primary_kw} AND {secondary_kw} AND {tertiary_kw}'

                    for source in sources:
                        optimized.append({
                            'query': combined_query_3,
                            'lang': lang,
                            'source': source,
                            'original_query': f'{primary_kw} + {secondary_kw} + {tertiary_kw}',
                            'is_combination': True
                        })

                    print(f"      {combined_query_3}")
                    combination_count += 1

        print(f"  总组合查询数: {combination_count}")
        print(f"  总优化查询数: {len(optimized)}")

        # 去重
        seen = set()
        unique_optimized = []
        for item in optimized:
            key = (item['query'], item['source'])
            if key not in seen:
                seen.add(key)
                unique_optimized.append(item)

        # === 翻译扩展（使用上下文感知翻译）===
        print(f"[阶段2] 翻译扩展（上下文感知）:")
        try:
            from services.contextual_keyword_translator import translate_keywords_contextual

            # 收集需要翻译的中文关键词（包括 'zh' 和 'mixed' 语言标记）
            # 注意：'mixed' 语言的关键词可能是中英混合（如 "CAS核心算法"），需要翻译处理
            zh_keywords = [q['query'] for q in unique_optimized if q.get('lang') in ('zh', 'mixed')]

            if zh_keywords:
                # 使用上下文感知翻译（传入研究方向以提高相关性）
                translations = await translate_keywords_contextual(
                    keywords=zh_keywords,
                    topic=topic,
                    target_lang='en',
                    research_direction_id=research_direction
                )

                # 为每个翻译生成查询
                translated_queries = []
                for original_query, translated_query in translations.items():
                    # 找到原始查询的配置
                    original_config = None
                    for q in unique_optimized:
                        if q['query'] == original_query:
                            original_config = q
                            break

                    if original_config:
                        # 后处理：提取英文部分（去除中文字符）
                        import re
                        # 提取英文单词和常见符号（AND, OR等）
                        english_parts = re.findall(r'[a-zA-Z]{2,}|\bAND\b|\bOR\b', translated_query)
                        if english_parts:
                            # 重构为纯英文查询
                            cleaned_query = ' '.join(english_parts)
                            # 清理多余的空格
                            cleaned_query = ' '.join(cleaned_query.split())
                        else:
                            # 如果没有英文部分，跳过
                            continue

                        # 为每个英文数据源添加翻译后的查询
                        for source in english_sources:
                            translated_queries.append({
                                'query': cleaned_query,
                                'lang': 'en',
                                'source': source,
                                'original_query': original_query,
                                'is_translation': True,
                                'context_aware': True  # 标记为上下文感知翻译
                            })

                # 合并原文和翻译后的查询
                unique_optimized.extend(translated_queries)

                print(f"[阶段2] 上下文翻译完成: {len(translations)} 个关键词")
            else:
                print(f"[阶段2] 没有中文关键词需要翻译")

        except Exception as e:
            print(f"[阶段2] 上下文翻译失败: {e}")
            print(f"[阶段2] 回退到原文查询")

        # === 阶段2 输出 ===
        print(f"[阶段2] 输出:")
        print(f"  - 优化查询数: {len(unique_optimized)}")
        print(f"  - 英文查询: {sum(1 for q in unique_optimized if q.get('lang') == 'en')} 个")
        print(f"  - 中文查询: {sum(1 for q in unique_optimized if q.get('lang') == 'zh')} 个")

        # 统计翻译查询数
        translation_count = sum(1 for q in unique_optimized if q.get('is_translation', False))
        if translation_count > 0:
            print(f"  - 翻译查询: {translation_count} 个")
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
        # Semantic Scholar 主要是英文数据库（虽然也有一定中文支持）
        english_sources = ['openalex', 'crossref', 'datacite', 'semantic_scholar']
        chinese_sources = ['aminer', 'chinese_doi']

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
        """将查询转换为英文

        注意：此方法已被弃用，翻译应该在阶段2（关键词优化）时完成。
        这里只保留基本功能作为后备方案。
        """
        # 如果已经是英文，直接返回
        if self._is_english(query):
            return query

        # 尝试从主题中提取英文术语
        english_words = self._extract_english_words(query)
        if english_words:
            return ' '.join(english_words)

        # 如果没有英文，返回空（不应该到达这里，因为翻译应该在阶段2完成）
        print(f"[警告] 查询 '{query}' 在阶段2没有被翻译，搜索可能失败")
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

    # ==================== 共同方法：文献搜索和筛选 ====================

    async def _search_and_filter_papers(
        self,
        topic: str,
        params: dict,
        task_id: str,
        progress_callback=None
    ) -> dict:
        """
        共同方法：执行阶段1-4（文献搜索和筛选）

        这个方法被 execute_task 和 search_papers_only 共同使用

        Args:
            topic: 论文主题
            params: 参数配置
            task_id: 任务ID
            progress_callback: 进度回调函数（可选）

        Returns:
            {
                'framework': 综述框架,
                'all_papers': 搜索到的所有文献,
                'filtered_papers': 筛选后的文献,
                'stats': 统计信息,
                'search_result': 搜索结果（包含按小节分组）
            }
        """
        def add_log(message):
            """添加日志"""
            print(message)
            if progress_callback:
                progress_callback(message)

        # === 阶段1: 生成大纲和搜索关键词 ===
        task_manager.update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress={"step": "generating_outline", "message": "正在生成大纲和搜索关键词..."}
        )

        print("\n" + "=" * 80)
        print("[阶段1] 生成综述大纲和搜索关键词")
        print("=" * 80)

        # 获取研究方向参数
        research_direction = params.get('research_direction', '')
        if research_direction:
            print(f"[阶段1] 使用研究方向: {research_direction}")
        else:
            print(f"[阶段1] 未指定研究方向，将由LLM自动推断")

        outline = await self._generate_review_outline(topic, research_direction)
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

        # 1. 添加大纲中的中文关键词
        for keywords in section_keywords.values():
            for kw in keywords:
                search_queries.append({'query': kw, 'lang': 'mixed'})

        # 2. 添加英文关键词（直接调用 LLM 生成）
        # 从主题中提取研究对象
        research_object = topic.split('的')[0] if '的' in topic else topic
        optimization_goal = '算法实现及应用' if '算法实现及应用' in topic or 'algorithm implementation' in topic.lower() else ''
        methodology = 'symbolic computation' if 'symbolic' in topic.lower() or '符号' in topic else ''

        keywords_data = await gen._generate_dynamic_keywords(
            title=topic,
            research_object=research_object,
            optimization_goal=optimization_goal,
            methodology=methodology
        )

        # 提取英文关键词
        object_keywords = keywords_data.get('object_keywords', [])
        method_keywords = keywords_data.get('method_keywords', [])
        goal_keywords = keywords_data.get('goal_keywords', [])

        all_english_keywords = object_keywords + method_keywords + goal_keywords

        # 过滤掉过于通用的单个词和包含未扩展 CAS 的关键词
        generic_single_words = {'algorithm', 'method', 'system', 'approach', 'technique', 'model'}
        filtered_english_keywords = []
        for kw in all_english_keywords:
            # 过滤条件：
            # 1. 不是单个通用词
            # 2. 长度大于3
            # 3. 如果包含 CAS，必须同时包含 Computer Algebra（已扩展）
            is_generic = kw.lower() in generic_single_words
            is_too_short = len(kw) <= 3
            has_unexpanded_cas = 'CAS' in kw and 'Computer Algebra' not in kw

            if not is_generic and not is_too_short and not has_unexpanded_cas:
                filtered_english_keywords.append(kw)

        print(f"[阶段1] LLM 生成的英文关键词: {len(filtered_english_keywords)} 个")
        for kw in filtered_english_keywords[:8]:
            print(f"  - {kw}")

        # 添加英文关键词到搜索查询
        for kw in filtered_english_keywords:
            search_queries.append({'query': kw, 'lang': 'en'})

        # 记录阶段1完成
        stage_recorder.record_outline_generation(
            task_id=task_id,
            topic=topic,
            outline=outline,
            framework_type=framework.get('outline', {}).get('structure', ''),
            classification={
                'type': framework.get('outline', {}).get('type_name', ''),
                'key_elements': framework.get('outline', {}).get('key_elements', {}),
                'search_queries_count': len(search_queries)
            }
        )

        # === 阶段2: 搜索词优化（基本语言优化） ===
        task_manager.update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress={"step": "optimizing_keywords", "message": "正在优化搜索关键词..."}
        )

        print("\n" + "=" * 80)
        print("[阶段2] 搜索词优化（基本语言优化 + 翻译扩展）")
        print("=" * 80)

        optimized_queries = await self._optimize_search_queries_basic(
            search_queries=search_queries,
            topic=topic,
            research_direction=research_direction
        )

        print(f"[阶段2] 搜索词优化完成:")
        print(f"  - 原始搜索词: {len(search_queries)} 个")
        print(f"  - 优化后搜索词: {len(optimized_queries)} 个")

        # === 阶段3: 按小节搜索文献 ===
        print("\n" + "=" * 80)
        print("[阶段3] 按小节搜索文献")
        print("=" * 80)

        search_result = await self._search_literature_by_sections(
            topic=topic,
            optimized_queries=optimized_queries,
            params=params,
            framework=framework,
            task_id=task_id
        )

        all_papers = search_result['all_papers']

        if not all_papers:
            raise Exception(f'未找到关于「{topic}」的相关文献')

        print(f"[阶段3] 搜索完成:")
        print(f"  - 总文献数: {len(all_papers)}")
        print(f"  - 小节数: {len(search_result['sections'])}")

        # === 记录阶段3完成 ===
        stage_recorder.update_task_status(task_id, status="processing", current_stage="文献搜索")
        # 计算文献摘要统计
        papers_summary = search_result.get('stats', {})
        papers_summary['sections'] = {
            title: len(papers) for title, papers in search_result['sections'].items()
        }
        # 收集文献样本（前20篇）
        papers_sample = all_papers[:20] if all_papers else []
        stage_recorder.record_paper_search(
            task_id=task_id,
            outline=framework,
            search_queries_count=len(optimized_queries),
            papers_count=len(all_papers),
            papers_summary=papers_summary,
            papers_sample=papers_sample
        )

        # === 阶段4: 质量过滤 ===
        task_manager.update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress={"step": "filtering", "message": "正在进行质量过滤..."}
        )

        print("\n" + "=" * 80)
        print("[阶段4] 质量过滤")
        print("=" * 80)

        filter_result = await self._filter_papers_by_quality(
            search_result=search_result,
            topic=topic,
            framework=framework,
            params=params,
            task_id=task_id
        )

        filtered_papers = filter_result['all_papers']

        if not filtered_papers:
            raise Exception(f'筛选后没有足够的文献')

        print(f"[阶段4] 质量过滤完成:")
        print(f"  - 筛选后文献数: {len(filtered_papers)}")

        # === 记录阶段4完成 ===
        stage_recorder.update_task_status(task_id, status="processing", current_stage="文献筛选")
        # 获取筛选详情（从filter_result中）
        quality_filtered_count = filter_result.get('quality_filtered_count', 0)
        quality_filtered_details = filter_result.get('quality_filtered_details', [])
        topic_irrelevant_count = filter_result.get('topic_irrelevant_count', 0)
        topic_irrelevant_details = filter_result.get('topic_irrelevant_details', [])

        # 计算筛选后的统计信息
        filter_stats = self.filter_service.get_statistics(filtered_papers)

        stage_recorder.record_paper_filter(
            task_id=task_id,
            input_papers_count=len(all_papers),
            quality_filtered_count=quality_filtered_count,
            quality_filtered_details=quality_filtered_details[:50],  # 限制存储数量
            topic_irrelevant_count=topic_irrelevant_count,
            topic_irrelevant_details=topic_irrelevant_details[:50],  # 限制存储数量
            output_papers_count=len(filtered_papers),
            output_papers_summary=filter_stats
        )

        # 计算最终统计信息
        stats = filter_stats

        print(f"\n[阶段1-4] 完成:")
        print(f"  - 搜索到文献: {len(all_papers)} 篇")
        print(f"  - 筛选后文献: {len(filtered_papers)} 篇")

        return {
            'framework': framework,
            'all_papers': all_papers,
            'filtered_papers': filtered_papers,
            'stats': stats,
            'search_result': search_result,
            'specificity_guidance': specificity_guidance
        }

    # ==================== 查找文献（不生成综述）====================

    async def search_papers_only(
        self,
        topic: str,
        params: dict,
        progress_callback=None
    ) -> dict:
        """
        只查找文献，不生成综述

        执行流程：
        1. 生成综述框架和搜索关键词
        2. 优化搜索关键词
        3. 按小节搜索文献
        4. 质量过滤

        Args:
            topic: 论文主题
            params: 参数配置
            progress_callback: 进度回调函数

        Returns:
            {
                'framework': 综述框架,
                'all_papers': 所有搜索到的文献,
                'filtered_papers': 筛选后的文献,
                'statistics': 统计信息,
                'search_queries_results': 搜索查询结果,
                'logs': 过程日志,
                'task_id': 任务ID
            }
        """
        import uuid
        logs = []
        framework = None
        all_papers = []
        filtered_papers = []

        # 生成任务ID
        task_id = str(uuid.uuid4())[:8]

        def add_log(message):
            """添加日志"""
            logs.append(message)
            print(message)
            if progress_callback:
                progress_callback(message)

        # 创建任务记录
        stage_recorder.create_task(task_id, topic, params)
        stage_recorder.update_task_status(task_id, status="processing", current_stage="初始化")

        try:
            # === 执行阶段1-4：文献搜索和筛选（共同逻辑）===
            search_result = await self._search_and_filter_papers(
                topic=topic,
                params=params,
                task_id=task_id,
                progress_callback=progress_callback
            )

            framework = search_result['framework']
            all_papers = search_result['all_papers']
            filtered_papers = search_result['filtered_papers']
            stats = search_result['stats']
            search_result_data = search_result['search_result']

            # 准备搜索查询结果（用于前端展示）
            search_queries_results = []
            for section_title, papers in search_result_data['sections'].items():
                search_queries_results.append({
                    'section': section_title,
                    'query': section_title,  # 使用小节标题作为查询
                    'papers_count': len(papers),
                    'papers': papers
                })

            add_log("\n" + "=" * 80)
            add_log("[查找文献完成]")
            add_log("=" * 80)
            add_log(f"  - 搜索到文献: {len(all_papers)} 篇")
            add_log(f"  - 筛选后文献: {len(filtered_papers)} 篇")
            add_log(f"  - 目标引用数: {params.get('target_count', 50)} 篇")

            # === 任务完成 ===
            stage_recorder.update_task_status(
                task_id,
                status="completed",
                current_stage="完成",
                completed_at=datetime.now()
            )

            return {
                'framework': framework,
                'all_papers': all_papers,
                'filtered_papers': filtered_papers,
                'statistics': stats,
                'search_queries_results': search_queries_results,
                'logs': logs,
                'task_id': task_id  # 返回任务ID
            }

        except Exception as e:
            import traceback
            error_msg = f"[错误] {str(e)}"
            add_log(error_msg)
            traceback.print_exc()

            # === 任务失败 ===
            stage_recorder.update_task_status(
                task_id,
                status="failed",
                current_stage="失败",
                error_message=str(e),
                completed_at=datetime.now()
            )

            raise


