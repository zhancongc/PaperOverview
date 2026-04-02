"""
综述生成任务执行器
将同步的生成逻辑包装成异步任务
"""
import os
from typing import Dict
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
                progress={"step": "analyzing", "message": "正在分析题目..."}
            )

            # 1. 智能分析题目
            from services.hybrid_classifier import FrameworkGenerator
            gen = FrameworkGenerator()
            framework = await gen.generate_framework(topic, enable_llm_validation=True)

            # 提取场景特异性指导
            specificity_guidance = framework.get('specificity_guidance', {})

            # 2. 初始文献搜索
            all_papers = []
            search_queries_results = []
            search_queries = framework.get('search_queries', [])

            # 使用LLM验证和修复搜索关键词
            if search_queries:
                try:
                    from services.hybrid_classifier import HybridTopicClassifier
                    classifier = HybridTopicClassifier()
                    print(f"[TaskExecutor] 原始搜索查询数量: {len(search_queries)}")
                    for i, q in enumerate(search_queries[:5]):
                        print(f"  [{i+1}] {q.get('query', '')[:50]}... (lang: {q.get('lang', 'N/A')})")

                    search_queries = await classifier.validate_and_fix_search_queries(
                        title=topic,
                        queries=search_queries
                    )

                    print(f"[TaskExecutor] 修复后搜索查询数量: {len(search_queries)}")
                    for i, q in enumerate(search_queries[:5]):
                        print(f"  [{i+1}] {q.get('query', '')[:50]}... (lang: {q.get('lang', 'N/A')})")
                except Exception as e:
                    print(f"[TaskExecutor] LLM关键词验证失败: {e}")
                    import traceback
                    traceback.print_exc()

            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "searching", "message": f"正在搜索文献 (0/{len(search_queries)})..."}
            )

            if search_queries:
                for i, query_info in enumerate(search_queries[:params.get('max_search_queries', 8)]):
                    query = query_info.get('query', topic)
                    section = query_info.get('section', '通用')
                    lang = query_info.get('lang', None)
                    keywords = query_info.get('keywords', None)
                    search_mode = query_info.get('search_mode', None)

                    task_manager.update_task_status(
                        task_id,
                        TaskStatus.PROCESSING,
                        progress={"step": "searching", "message": f"正在搜索文献 ({i+1}/{len(search_queries)})..."}
                    )

                    papers = await self.search_service.search(
                        query=query,
                        years_ago=params.get('search_years', 10),
                        limit=50,
                        lang=lang,
                        keywords=keywords,
                        search_mode=search_mode
                    )

                    search_queries_results.append({
                        'query': query,
                        'section': section,
                        'papers': papers,
                        'citedCount': 0
                    })
                    all_papers.extend(papers)

            # 补充搜索
            if len(all_papers) < 20:
                task_manager.update_task_status(
                    task_id,
                    TaskStatus.PROCESSING,
                    progress={"step": "searching", "message": "正在补充搜索文献..."}
                )
                additional_papers = await self.search_service.search(
                    query=topic,
                    years_ago=15,
                    limit=100,
                    use_all_sources=True
                )
                all_papers.extend(additional_papers)

            # 去重
            seen_ids = set()
            unique_papers = []
            for paper in all_papers:
                paper_id = paper.get("id")
                if paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    unique_papers.append(paper)
            all_papers = unique_papers

            # 宽泛搜索
            if not all_papers:
                topic_words = topic.replace('基于', '').replace('的研究', '').replace('研究', '')
                topic_words = ' '.join([w for w in topic_words.split() if len(w) > 1])

                if topic_words:
                    last_attempt_papers = await self.search_service.search(
                        query=topic_words,
                        years_ago=20,
                        limit=50,
                        use_all_sources=True
                    )
                    for paper in last_attempt_papers:
                        paper_id = paper.get("id")
                        if paper_id not in seen_ids:
                            seen_ids.add(paper_id)
                            all_papers.append(paper)

            if not all_papers:
                raise Exception(f'未找到关于「{topic}」的相关文献')

            # 3. 筛选文献
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "filtering", "message": "正在筛选文献..."}
            )

            topic_keywords = gen.extract_relevance_keywords(framework)
            search_count = max(params.get('target_count', 50) * 2, 100)
            filtered_papers = self.filter_service.filter_and_sort(
                papers=all_papers,
                target_count=search_count,
                recent_years_ratio=params.get('recent_years_ratio', 0.5),
                english_ratio=params.get('english_ratio', 0.3),
                topic_keywords=topic_keywords
            )

            if len(filtered_papers) < params.get('target_count', 50):
                filtered_papers = self.filter_service.filter_and_sort(
                    papers=all_papers,
                    target_count=search_count,
                    recent_years_ratio=0.0,
                    english_ratio=0.0,
                    topic_keywords=[]
                )

            if len(filtered_papers) < 10:
                filtered_papers = all_papers[:max(params.get('target_count', 50), 50)]

            # 4. 生成综述
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "generating", "message": "正在生成综述..."}
            )

            api_key = os.getenv("DEEPSEEK_API_KEY")
            aminer_token = os.getenv("AMINER_API_TOKEN")

            if not api_key:
                raise Exception("DEEPSEEK_API_KEY not configured")

            generator = ReviewGeneratorService(api_key=api_key, aminer_token=aminer_token)

            review, cited_papers = await generator.generate_review(
                topic=topic,
                papers=filtered_papers,
                specificity_guidance=specificity_guidance
            )

            # 5. 验证和修复
            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "validating", "message": "正在验证和修复引用..."}
            )

            validator = ReferenceValidator()
            citation_checker = CitationOrderChecker()

            content, references_section = validator._split_review_and_references(review)

            # 5.1 首先去除超出范围的引用
            citation_check_result = citation_checker.check_order(content, papers_count=len(cited_papers))
            if citation_check_result.get('exceeds_range', False):
                max_citation = citation_check_result.get('max_citation', 0)
                papers_count = citation_check_result.get('papers_count', 0)
                print(f"[TaskExecutor] 检测到超出范围的引用（最大: {max_citation}，文献数: {papers_count}），正在去除...")
                content = citation_checker.remove_out_of_range_citations(content, papers_count)

            # 5.2 修复引用顺序
            citations = citation_checker.extract_citations(content)
            if citations:
                fixed_content, number_mapping = citation_checker.fix_citation_order(content, citations)

                # 5.3 根据新的引用顺序重新构建文献列表
                new_to_old = {}
                for item in number_mapping:
                    new_to_old[item['new']] = item['old']

                new_cited_papers = []
                for new_index in sorted(new_to_old.keys()):
                    old_index = new_to_old[new_index]
                    # 确保旧索引在有效范围内
                    if 1 <= old_index <= len(cited_papers):
                        new_cited_papers.append(cited_papers[old_index - 1])

                cited_papers = new_cited_papers
                content = fixed_content

            # 5.4 最终检查：确保没有超出范围的引用
            final_check = citation_checker.check_order(content, papers_count=len(cited_papers))
            if final_check.get('exceeds_range', False):
                print(f"[TaskExecutor] 警告：修复后仍有超出范围的引用，再次去除...")
                content = citation_checker.remove_out_of_range_citations(content, len(cited_papers))

            # 5.5 重新生成参考文献
            references = generator._format_references(cited_papers)
            review = f"{content}\n\n## 参考文献\n\n{references}"

            # 6. 计算统计信息
            stats = self.filter_service.get_statistics(cited_papers)

            cited_paper_ids = {p.get('id') for p in cited_papers}
            for query_result in search_queries_results:
                cited_count = sum(1 for p in query_result['papers'] if p.get('id') in cited_paper_ids)
                query_result['citedCount'] = cited_count
                for paper in query_result['papers']:
                    paper['cited'] = paper.get('id') in cited_paper_ids
                    if 'relevance_score' not in paper:
                        paper['relevance_score'] = 0

            for paper in filtered_papers:
                if 'relevance_score' not in paper:
                    paper['relevance_score'] = 0
                paper['cited'] = paper.get('id') in cited_paper_ids

            # 7. 最终验证
            final_validation = validator.validate_review(review=review, papers=cited_papers)

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
                    "candidate_pool": filtered_papers,
                    "statistics": stats,
                    "analysis": framework,
                    "search_queries_results": search_queries_results,
                    "cited_papers_count": len(cited_papers),
                    "validation": final_validation,
                    "created_at": record.created_at.isoformat()
                }
            )

        except Exception as e:
            import traceback
            traceback.print_exc()

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
