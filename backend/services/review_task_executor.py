"""
综述生成任务执行器
将同步的生成逻辑包装成异步任务
"""
import os
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session

from services.task_manager import TaskManager, TaskStatus, task_manager
from services.smart_paper_search import SmartPaperSearchService
from services.paper_filter import PaperFilterService
from services.review_generator import ReviewGeneratorService
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
                progress={"step": "generating_outline", "message": "正在生成大纲..."}
            )

            # === 阶段1: 生成大纲 ===
            print("\n" + "=" * 80)
            print("[阶段1] 生成综述大纲")
            print("=" * 80)

            outline = await self._generate_review_outline(topic)
            framework = {'outline': outline}

            print(f"[阶段1] 大纲生成完成:")
            print(f"  - 引言: {outline.get('introduction', {}).get('focus', '')[:50]}...")
            print(f"  - 主体章节: {len(outline.get('body_sections', []))} 个")
            for section in outline.get('body_sections', []):
                if isinstance(section, dict):
                    title = section.get('title', '')
                    print(f"    - {title}")
            print(f"  - 结论: 待定（根据文献内容生成）")

            # === 阶段2: 题目分析（生成搜索关键词） ===
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "analyzing", "message": "正在分析题目生成搜索关键词..."}
            )

            print("\n" + "=" * 80)
            print("[阶段2] 题目分析（生成搜索关键词）")
            print("=" * 80)

            from services.hybrid_classifier import FrameworkGenerator
            gen = FrameworkGenerator()
            analysis_result = await gen.generate_framework(topic, enable_llm_validation=True)

            # 提取场景特异性指导
            specificity_guidance = analysis_result.get('specificity_guidance', {})

            # 获取搜索查询
            search_queries = analysis_result.get('search_queries', [])

            # 根据大纲为每个章节生成专属关键词
            section_keywords = self._generate_section_keywords_from_outline(
                outline=outline,
                base_queries=search_queries,
                topic=topic
            )

            print(f"[阶段2] 关键词生成完成:")
            for section_title, keywords in section_keywords.items():
                print(f"  - {section_title}: {len(keywords)} 个关键词")

            # 使用LLM验证和修复搜索关键词
            all_keywords = []
            for keywords in section_keywords.values():
                all_keywords.extend(keywords)

            if all_keywords:
                try:
                    from services.hybrid_classifier import HybridTopicClassifier
                    classifier = HybridTopicClassifier()

                    # 将关键词转换为查询格式
                    search_queries_formatted = [
                        {'query': kw, 'lang': 'mixed'} for kw in all_keywords
                    ]

                    print(f"[阶段2] 原始搜索查询数量: {len(search_queries_formatted)}")
                    for i, q in enumerate(search_queries_formatted[:5]):
                        print(f"  [{i+1}] {q.get('query', '')[:50]}...")

                    search_queries = await classifier.validate_and_fix_search_queries(
                        title=topic,
                        queries=search_queries_formatted
                    )

                    print(f"[阶段2] 修复后搜索查询数量: {len(search_queries)}")
                except Exception as e:
                    print(f"[阶段2] LLM关键词验证失败: {e}")
                    import traceback
                    traceback.print_exc()

            # 将大纲和关键词整合到 framework
            framework['section_keywords'] = section_keywords
            framework['specificity_guidance'] = specificity_guidance

            # === 阶段3: 按小节搜索文献 ===
            search_result = await self._search_literature_by_sections(
                topic=topic,
                search_queries=search_queries,
                params=params,
                framework=framework,
                task_id=task_id
            )

            if not search_result['all_papers']:
                raise Exception(f'未找到关于「{topic}」的相关文献')

            # === 阶段4: 精简文献到N篇 ===
            filter_result = await self._filter_papers_to_target(
                search_result=search_result,
                topic=topic,
                framework=framework,
                params=params,
                task_id=task_id
            )

            if not filter_result['all_papers']:
                raise Exception(f'筛选后没有足够的文献')

            papers_by_section = filter_result['sections']
            all_papers = filter_result['all_papers']
            N = filter_result['total_count']

            print(f"\n[阶段4] 输出结果:")
            print(f"  - 总文献数: {N}")
            print(f"  - 小节分布:")
            for section_title, papers in papers_by_section.items():
                print(f"    - {section_title}: {len(papers)} 篇")

            # === 阶段5: 分小节生成综述 ===
            api_key = os.getenv("DEEPSEEK_API_KEY")
            aminer_token = os.getenv("AMINER_API_TOKEN")

            if not api_key:
                raise Exception("DEEPSEEK_API_KEY not configured")

            print(f"\n[阶段5] 分小节生成综述")
            print(f"[阶段5] 文献数量: {N} 篇")

            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "generating", "message": f"正在生成综述 ({N}篇文献)..."}
            )

            generator = ReviewGeneratorService(api_key=api_key, aminer_token=aminer_token)

            # 传递按小节分组的文献
            review, cited_papers = await generator.generate_review_by_sections(
                topic=topic,
                framework=framework,
                papers_by_section=papers_by_section,
                all_papers=all_papers,
                specificity_guidance=specificity_guidance
            )

            # 5. 验证和修复（增强版）
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "validating", "message": "正在验证和修复引用..."}
            )

            # 使用增强的验证方法
            content, cited_papers = await self._validate_and_fix_review(
                review=review,
                papers=all_papers,
                generator=generator,
                task_id=task_id
            )

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
        search_queries: list,
        params: dict,
        framework: dict,
        task_id: str
    ) -> dict:
        """
        按小节搜索文献（新流程阶段3）

        流程：
        1. 优先从数据库搜索
        2. 数据库不足时使用API补充
        3. 小节内部去重
        4. 小节间去重，保留文献数量少的小节的文献

        Args:
            topic: 论文主题
            search_queries: 搜索查询列表
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
        print("=" * 80)
        print("[阶段3] 按小节搜索文献（优先数据库）")
        print("=" * 80)

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

                section_papers = []
                section_seen_ids = set()  # 小节内部去重

                # 为每个关键词搜索
                for keyword in keywords[:5]:  # 每个小节最多5个关键词
                    task_manager.update_task_status(
                        task_id,
                        TaskStatus.PROCESSING,
                        progress={"step": "searching", "message": f"正在搜索 {section_title}: {keyword}..."}
                    )

                    # === 步骤1: 优先从数据库搜索 ===
                    from services.paper_metadata_dao import PaperMetadataDAO
                    dao = PaperMetadataDAO(db_session)

                    db_papers = dao.search_papers(
                        keyword=keyword,
                        min_year=datetime.now().year - params.get('search_years', 10),
                        limit=50
                    )

                    # 转换为字典格式
                    db_papers_dict = [p.to_paper_dict() for p in db_papers]

                    print(f"[阶段3] 数据库搜索 '{keyword}': 找到 {len(db_papers_dict)} 篇")

                    # 添加数据库搜索结果
                    for paper in db_papers_dict:
                        paper_id = paper.get("id")
                        if paper_id and paper_id not in section_seen_ids:
                            section_seen_ids.add(paper_id)
                            section_papers.append(paper)

                    # === 步骤2: 如果数据库搜索结果不足，使用API补充 ===
                    if len(db_papers_dict) < 20:  # 如果数据库搜索结果少于20篇
                        print(f"[阶段3] 数据库结果不足，使用API补充搜索...")

                        api_papers = await self.search_service.search(
                            query=keyword,
                            years_ago=params.get('search_years', 10),
                            limit=30,
                            use_all_sources=True
                        )

                        # 添加API搜索结果（去重）
                        for paper in api_papers:
                            paper_id = paper.get("id")
                            if paper_id and paper_id not in section_seen_ids:
                                section_seen_ids.add(paper_id)
                                section_papers.append(paper)

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
        min_target_papers = 100  # 目标至少100篇
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
        精简文献到目标数量（新流程阶段4）

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
        section_keywords = framework.get('section_keywords', {})
        for keywords in section_keywords.values():
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

            # 使用筛选服务筛选该小节的专属文献
            filtered_papers = self.filter_service.filter_and_sort(
                papers=section_papers,
                target_count=target_count,
                recent_years_ratio=recent_years_ratio,
                english_ratio=english_ratio,
                topic_keywords=topic_keywords
            )

            # 截取到目标数量
            filtered_papers = filtered_papers[:target_count]
            filtered_by_section[section_title] = filtered_papers
            print(f"[阶段4] 小节 '{section_title}': 筛选到 {len(filtered_papers)} 篇专属文献")

        # 统计最终分配的文献总数
        final_total = sum(len(papers) for papers in filtered_by_section.values())
        stats = self.filter_service.get_statistics(
            [p for papers in filtered_by_section.values() for p in papers]
        )

        print(f"\n[阶段4] 专属文献分配完成:")
        print(f"  - 总文献数: {final_total} (目标: {N})")
        print(f"  - 英文文献: {stats['english_count']}")
        print(f"  - 近5年文献: {stats['recent_count']} ({stats['recent_ratio']:.1%})")
        print(f"  - 小节分布:")
        for section_title, papers in filtered_by_section.items():
            print(f"    - {section_title}: {len(papers)} 篇")

        return {
            'sections': filtered_by_section,
            'all_papers': [p for papers in filtered_by_section.values() for p in papers],
            'total_count': final_total
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
        import os
        from openai import AsyncOpenAI

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DEEPSEEK_API_KEY not configured")

        client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        system_prompt = """你是学术综述大纲设计专家。

你的任务是根据研究主题，设计一个高质量的文献综述大纲。

要求：
1. **结构清晰**：包含引言、主体（2-5个主题章节）
2. **主题划分**：主体部分按研究主题或方法论划分
3. **逻辑连贯**：各主题之间要有逻辑关系
4. **结论待定**：结论部分需要根据实际文献内容来定，大纲中只需说明

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
            "comparison_points": ["对比点1", "对比点2"]
        }
    ],
    "conclusion": {
        "focus": "结论部分将根据实际文献内容总结研究现状、指出不足和未来方向"
    }
}

注意：
- body_sections 应该包含 2-5 个章节
- 每个章节的 key_points 应该有 3-5 个要点
- 每个章节的 comparison_points 应该有 2-3 个对比点"""

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
                        "comparison_points": ["方法差异", "理论分歧"]
                    },
                    {
                        "title": "主要研究进展",
                        "focus": "总结当前研究的主要成果",
                        "key_points": ["技术进展", "应用案例", "效果评估"],
                        "comparison_points": ["研究结论对比", "应用效果"]
                    }
                ],
                "conclusion": {
                    "focus": "结论部分将根据实际文献内容总结研究现状、指出不足和未来方向"
                }
            }

    def _generate_section_keywords_from_outline(
        self,
        outline: dict,
        base_queries: list,
        topic: str
    ) -> dict:
        """
        根据大纲为每个章节生成专属关键词

        Args:
            outline: 大纲
            base_queries: 基础搜索查询
            topic: 论文主题

        Returns:
            {章节标题: [关键词列表]}
        """
        section_keywords = {}

        # 提取主题关键词
        topic_keywords = self._extract_topic_keywords(topic)

        # 为每个章节生成关键词
        body_sections = outline.get('body_sections', [])
        for section in body_sections:
            if isinstance(section, dict):
                title = section.get('title', '')
                focus = section.get('focus', '')
                key_points = section.get('key_points', [])

                # 章节关键词 = 主题关键词 + 章节标题 + focus + key_points
                keywords = set(topic_keywords)

                # 添加标题中的关键词
                title_words = self._extract_chinese_words(title)
                keywords.update(title_words)

                # 添加 focus 中的关键词
                focus_words = self._extract_chinese_words(focus)
                keywords.update(focus_words)

                # 添加 key_points 中的关键词
                for point in key_points:
                    point_words = self._extract_chinese_words(point)
                    keywords.update(point_words)

                # 添加相关的 base_queries
                for query in base_queries:
                    query_text = query.get('query', '') if isinstance(query, dict) else query
                    # 如果查询与章节相关（包含章节关键词），则添加
                    if any(kw in query_text for kw in keywords):
                        keywords.add(query_text)

                section_keywords[title] = list(keywords)

        return section_keywords

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


