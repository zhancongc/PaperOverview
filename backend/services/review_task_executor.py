"""
综述生成任务执行器
将同步的生成逻辑包装成异步任务
"""
import logging
import os
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from services.task_manager import TaskManager, TaskStatus, task_manager
from services.paper_filter import PaperFilterService
from services.smart_review_generator_final import SmartReviewGeneratorFinal
from services.semantic_scholar_search import SemanticScholarService, get_semantic_scholar_service
from services.paper_search_agent import PaperSearchAgent
from services.citation_validator_v2 import CitationValidatorV2
from services.review_record_service import ReviewRecordService
from services.stage_recorder import stage_recorder


class ReviewTaskExecutor:
    """综述生成任务执行器"""

    def __init__(self):
        self.filter_service = PaperFilterService()
        self.record_service = ReviewRecordService()

    async def execute_task(self, task_id: str, db_session: Session):
        """
        执行综述生成任务（3步流程）

        步骤1: PaperSearchAgent 搜索文献
        步骤2: SmartReviewGeneratorFinal 生成综述
        步骤3: CitationValidatorV2 引用校验修复

        Args:
            task_id: 任务ID
            db_session: 数据库会话
        """
        task = task_manager.get_task(task_id)
        if not task:
            logger.debug(f"[TaskExecutor] 任务不存在: {task_id}")
            return

        # 尝试获取执行槽位（并发控制，支持排队提示和超时）
        acquired = await task_manager.acquire_slot(task_id, timeout=1800)  # 30分钟超时
        if not acquired:
            logger.debug(f"[TaskExecutor] 任务 {task_id} 排队超时")
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error="系统繁忙，排队超时（超过30分钟），请稍后重试"
            )
            return

        params = task.params
        topic = task.topic

        # 创建任务记录
        stage_recorder.create_task(task_id, topic, params)
        task_manager.update_task_status(task_id, TaskStatus.PROCESSING)

        try:
            # 创建数据库记录
            record = self.record_service.create_record(
                db_session=db_session,
                topic=topic,
                target_count=params.get('target_count', 50),
                recent_years_ratio=params.get('recent_years_ratio', 0.5),
                english_ratio=params.get('english_ratio', 0.3),
                is_paid=getattr(task, 'is_paid', False),
                user_id=getattr(task, 'user_id', None)
            )

            # =====================================================
            # 步骤1: PaperSearchAgent 搜索文献
            # =====================================================
            logger.debug("\n" + "=" * 80)
            logger.debug(f"[步骤1] 搜索文献: {topic}")
            logger.debug("=" * 80)

            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "searching", "message": "正在搜索文献..."}
            )

            semantic_scholar_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
            ss_service = get_semantic_scholar_service()

            # 使用 LLM + Function Calling 驱动检索
            search_agent = PaperSearchAgent(ss_service=ss_service)
            all_papers = await search_agent.search(
                topic=topic,
                search_years=params.get('search_years', 10),
                target_count=params.get('target_count', 50)
            )

            logger.debug(f"[步骤1] 搜索完成: 共 {len(all_papers)} 篇文献")

            if not all_papers:
                raise Exception(f'未找到关于「{topic}」的相关文献')

            MIN_PAPERS_THRESHOLD = 20
            if len(all_papers) < MIN_PAPERS_THRESHOLD:
                raise Exception(f'搜索到的文献数量不足，只有 {len(all_papers)} 篇，至少需要 {MIN_PAPERS_THRESHOLD} 篇')

            # 记录步骤1完成
            stage_recorder.record_paper_search(
                task_id=task_id,
                outline={'topic': topic},
                search_queries_count=1,
                papers_count=len(all_papers),
                papers_summary=self.filter_service.get_statistics(all_papers),
                papers_sample=all_papers[:20]
            )
            stage_recorder.update_task_status(task_id, status="processing", current_stage="文献搜索完成")

            # =====================================================
            # 步骤2: SmartReviewGeneratorFinal 生成综述
            # =====================================================
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise Exception("DEEPSEEK_API_KEY not configured")

            logger.debug("\n" + "=" * 80)
            logger.debug(f"[步骤2] 生成综述（最终版）")
            logger.debug(f"[步骤2] 候选文献: {len(all_papers)} 篇")
            logger.debug("=" * 80)

            task_manager.update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress={"step": "generating", "message": "正在生成综述..."}
            )

            final_generator = SmartReviewGeneratorFinal(
                deepseek_api_key=api_key,
                deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            )

            # 构建搜索参数，用于生成文献检索方法论说明
            search_params = {
                "search_years": params.get('search_years', 10),
                "target_count": params.get('target_count', 50),
                "recent_years_ratio": params.get('recent_years_ratio', 0.5),
                "english_ratio": params.get('english_ratio', 0.3),
                "search_platform": "Semantic Scholar",
                "sort_by": "被引量降序"
            }

            result = await final_generator.generate_review_from_papers(
                topic=topic,
                papers=all_papers,
                model=params.get('review_model', 'deepseek-reasoner'),
                search_params=search_params,
                language=params.get('language', 'zh')
            )

            review = result["review"]
            cited_papers = result["cited_papers"]
            final_validation = result.get("validation", {"valid": True, "issues": []})

            # =====================================================
            # 步骤3: CitationValidatorV2 引用校验修复
            # =====================================================
            logger.debug("\n[步骤3] 使用 CitationValidatorV2 进行额外引用校验...")
            validator_v2 = CitationValidatorV2()
            validation_result = validator_v2.validate_and_fix(review, cited_papers)

            if not validation_result.valid:
                logger.debug(f"[步骤3] 发现问题: {validation_result.issues}")
                if validation_result.fixed_content:
                    logger.debug("[步骤3] 使用修复后的综述内容")
                    review = validation_result.fixed_content
                if validation_result.fixed_references:
                    logger.debug(f"[步骤3] 使用修复后的参考文献 ({len(validation_result.fixed_references)} 篇)")
                    cited_papers = validation_result.fixed_references
                final_validation = {
                    "valid": validation_result.valid,
                    "issues": validation_result.issues
                }
            else:
                logger.debug("[步骤3] ✓ 引用规范校验通过")
                # 使用 v2 改进版格式化参考文献（处理 arXiv ID、Unicode 等）
                improved_refs = validator_v2.format_references_ieee_improved(cited_papers)
                if "## References" in review:
                    review = review[:review.index("## References")] + "## References\n\n" + improved_refs
                    logger.debug("[步骤3] 使用改进版 IEEE 格式化参考文献")
            # 统计信息
            stats = self.filter_service.get_statistics(cited_papers)

            # 标记文献是否被引用
            cited_paper_ids = {p.get('id') for p in cited_papers}
            for paper in all_papers:
                if 'relevance_score' not in paper:
                    paper['relevance_score'] = 0
                paper['cited'] = paper.get('id') in cited_paper_ids

            # 记录步骤2完成
            stage_recorder.update_task_status(task_id, status="processing", current_stage="生成综述")

            papers_summary = []
            for p in cited_papers:
                url = p.get('url') or ''
                papers_summary.append({
                    'id': p.get('id'),
                    'title': p.get('title', '')[:200],
                    'authors': p.get('authors', [])[:5],
                    'year': p.get('year'),
                    'venue': (p.get('journal', '') or p.get('venue', ''))[:100],
                    'cited_by_count': p.get('cited_by_count', 0),
                    'url': url[:500] if url else ''
                })

            candidate_pool_summary = []
            for p in all_papers:
                url = p.get('url') or ''
                candidate_pool_summary.append({
                    'id': p.get('id'),
                    'title': p.get('title', '')[:200],
                    'authors': p.get('authors', [])[:5],
                    'year': p.get('year'),
                    'venue': (p.get('journal', '') or p.get('venue', ''))[:100],
                    'cited_by_count': p.get('cited_by_count', 0),
                    'url': url[:500] if url else ''
                })

            stage_recorder.record_review_generation(
                task_id=task_id,
                papers_count=len(all_papers),
                review_length=len(review),
                citation_count=review.count('['),
                cited_papers_count=len(cited_papers),
                validation_result=final_validation,
                review=review,
                papers_summary=papers_summary,
                candidate_pool_summary=candidate_pool_summary
            )

            # 保存数据库记录
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
                    "cited_papers_count": len(cited_papers),
                    "validation": final_validation,
                    "created_at": record.created_at.isoformat()
                }
            )

            stage_recorder.update_task_status(
                task_id,
                status="completed",
                current_stage="完成",
                completed_at=datetime.now(),
                review_record_id=record.id
            )

        except Exception as e:
            logger.error("综述生成任务失败: task_id=%s, error=%s", task_id, e, exc_info=True)

            if task_id in task_manager._running_tasks:
                task_manager.release_slot(task_id)

            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

            stage_recorder.update_task_status(
                task_id,
                status="failed",
                current_stage="失败",
                error_message=str(e),
                completed_at=datetime.now()
            )

            try:
                if 'record' in locals():
                    self.record_service.update_failure(
                        db_session=db_session,
                        record=record,
                        error_message=str(e)
                    )
            except Exception as e:
                logger.error("任务失败后更新状态异常: task_id=%s, error=%s", task_id, e)

            # 退还用户额度
            task_user_id = getattr(task, 'user_id', None)
            if task_user_id:
                try:
                    from main import refund_credit
                    from authkit.database import SessionLocal as AuthSessionLocal
                    if AuthSessionLocal:
                        auth_db = AuthSessionLocal()
                        try:
                            refund_credit(task_user_id, auth_db)
                            logger.info("已退还用户 %s 的综述额度", task_user_id)
                        finally:
                            auth_db.close()
                except Exception as refund_err:
                    logger.error("额度退还失败: user_id=%s, error=%s", task_user_id, refund_err)

    async def search_papers_only(
        self,
        topic: str,
        params: dict,
    ) -> dict:
        """
        只查找文献，不生成综述（使用 PaperSearchAgent）

        Args:
            topic: 论文主题
            params: 参数配置

        Returns:
            {
                'all_papers': 所有搜索到的文献,
                'statistics': 统计信息,
            }
        """
        ss_service = get_semantic_scholar_service()
        search_agent = PaperSearchAgent(ss_service=ss_service)
        all_papers = await search_agent.search(
            topic=topic,
            search_years=params.get('search_years', 10),
            target_count=params.get('target_count', 50)
        )

        stats = self.filter_service.get_statistics(all_papers)

        logger.debug(f"[search_papers_only] 搜索完成: {len(all_papers)} 篇文献")

        return {
            'all_papers': all_papers,
            'statistics': stats,
        }
