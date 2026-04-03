"""
阶段记录服务
记录综述生成过程中各个阶段的数据到数据库
"""
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import sessionmaker, Session

from database import db
from models import (
    ReviewTask,
    OutlineGenerationStage,
    PaperSearchStage,
    PaperFilterStage,
    ReviewGenerationStage,
    PaperSearchSource
)


class StageRecorder:
    """阶段记录器"""

    def __init__(self):
        # 确保数据库已连接
        if db.engine is None:
            db.connect()
        self.SessionLocal = sessionmaker(bind=db.engine)

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def create_task(self, task_id: str, topic: str, params: Dict) -> bool:
        """创建任务记录"""
        session = self.get_session()
        try:
            task = ReviewTask(
                id=task_id,
                topic=topic,
                params=params,
                status="pending",
                created_at=datetime.now()
            )
            session.add(task)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"[StageRecorder] 创建任务失败: {e}")
            return False
        finally:
            session.close()

    def update_task_status(
        self,
        task_id: str,
        status: str,
        current_stage: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        review_record_id: Optional[int] = None
    ) -> bool:
        """更新任务状态"""
        session = self.get_session()
        try:
            task = session.query(ReviewTask).filter_by(id=task_id).first()
            if not task:
                print(f"[StageRecorder] 任务不存在: {task_id}")
                return False

            task.status = status
            if current_stage:
                task.current_stage = current_stage
            if started_at:
                task.started_at = started_at
            if completed_at:
                task.completed_at = completed_at
            if error_message:
                task.error_message = error_message
            if review_record_id:
                task.review_record_id = review_record_id

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"[StageRecorder] 更新任务状态失败: {e}")
            return False
        finally:
            session.close()

    def record_outline_generation(
        self,
        task_id: str,
        topic: str,
        outline: Dict,
        framework_type: Optional[str],
        classification: Optional[Dict],
        status: str = "completed",
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None
    ) -> Optional[int]:
        """记录生成大纲阶段"""
        session = self.get_session()
        try:
            if not started_at:
                started_at = datetime.now()

            record = OutlineGenerationStage(
                task_id=task_id,
                topic=topic,
                outline=outline,
                framework_type=framework_type,
                classification=classification,
                status=status,
                error_message=error_message,
                started_at=started_at,
                completed_at=datetime.now() if status == "completed" else None
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            print(f"[StageRecorder] 记录大纲生成失败: {e}")
            traceback.print_exc()
            return None
        finally:
            session.close()

    def record_paper_search(
        self,
        task_id: str,
        outline: Dict,
        search_queries_count: int,
        papers_count: int,
        papers_summary: Optional[Dict],
        papers_sample: Optional[List[Dict]],
        status: str = "completed",
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None
    ) -> Optional[int]:
        """记录文献搜索阶段"""
        session = self.get_session()
        try:
            if not started_at:
                started_at = datetime.now()

            record = PaperSearchStage(
                task_id=task_id,
                outline=outline,
                search_queries_count=search_queries_count,
                papers_count=papers_count,
                papers_summary=papers_summary,
                papers_sample=papers_sample[:20] if papers_sample else [],  # 最多存储20篇样本
                status=status,
                error_message=error_message,
                started_at=started_at,
                completed_at=datetime.now() if status == "completed" else None
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            print(f"[StageRecorder] 记录文献搜索失败: {e}")
            traceback.print_exc()
            return None
        finally:
            session.close()

    def record_paper_filter(
        self,
        task_id: str,
        input_papers_count: int,
        quality_filtered_count: int,
        quality_filtered_details: Optional[List[Dict]],
        topic_irrelevant_count: int,
        topic_irrelevant_details: Optional[List[Dict]],
        output_papers_count: int,
        output_papers_summary: Optional[Dict],
        status: str = "completed",
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None
    ) -> Optional[int]:
        """记录文献筛选阶段"""
        session = self.get_session()
        try:
            if not started_at:
                started_at = datetime.now()

            record = PaperFilterStage(
                task_id=task_id,
                input_papers_count=input_papers_count,
                quality_filtered_count=quality_filtered_count,
                quality_filtered_details=quality_filtered_details,
                topic_irrelevant_count=topic_irrelevant_count,
                topic_irrelevant_details=topic_irrelevant_details,
                output_papers_count=output_papers_count,
                output_papers_summary=output_papers_summary,
                status=status,
                error_message=error_message,
                started_at=started_at,
                completed_at=datetime.now() if status == "completed" else None
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            print(f"[StageRecorder] 记录文献筛选失败: {e}")
            traceback.print_exc()
            return None
        finally:
            session.close()

    def record_review_generation(
        self,
        task_id: str,
        papers_count: int,
        review_length: int,
        citation_count: int,
        cited_papers_count: int,
        validation_result: Optional[Dict],
        review: Optional[str] = None,
        papers_summary: Optional[List[Dict]] = None,
        candidate_pool_summary: Optional[List[Dict]] = None,
        status: str = "completed",
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None
    ) -> Optional[int]:
        """
        记录生成综述阶段

        Args:
            task_id: 任务ID
            papers_count: 输入文献数
            review_length: 综述内容长度
            citation_count: 引用文献数
            cited_papers_count: 被引用文献数
            validation_result: 验证结果
            review: 综述内容（可选，用于版本对比）
            papers_summary: 引用文献摘要（可选，包含id、title、authors等核心字段）
            candidate_pool_summary: 候选文献池摘要（可选，筛选前的所有论文）
            status: 状态
            error_message: 错误信息
            started_at: 开始时间
        """
        session = self.get_session()
        try:
            if not started_at:
                started_at = datetime.now()

            record = ReviewGenerationStage(
                task_id=task_id,
                papers_count=papers_count,
                review_length=review_length,
                citation_count=citation_count,
                cited_papers_count=cited_papers_count,
                validation_result=validation_result,
                review=review,
                papers_summary=papers_summary,
                candidate_pool_summary=candidate_pool_summary,
                status=status,
                error_message=error_message,
                started_at=started_at,
                completed_at=datetime.now() if status == "completed" else None
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            print(f"[StageRecorder] 记录综述生成失败: {e}")
            traceback.print_exc()
            return None
        finally:
            session.close()

    def record_paper_search_sources(
        self,
        task_id: str,
        sources: List[Dict]
    ) -> int:
        """
        批量记录文献搜索来源

        Args:
            task_id: 任务ID
            sources: 搜索来源列表，每个元素格式：
                {
                    "paper_id": "论文ID",
                    "search_keyword": "搜索关键词"
                }

        Returns:
            成功插入的记录数
        """
        session = self.get_session()
        try:
            # 第一步：在内存中去重
            seen = set()
            unique_sources = []
            for source in sources:
                paper_id = source.get('paper_id')
                keyword = source.get('search_keyword')

                if not paper_id or not keyword:
                    continue

                # 使用 (task_id, paper_id, keyword) 作为唯一键
                key = (task_id, paper_id, keyword)
                if key not in seen:
                    seen.add(key)
                    unique_sources.append(source)

            # 第二步：批量插入去重后的数据（使用单条插入避免批量冲突）
            count = 0
            for source in unique_sources:
                paper_id = source.get('paper_id')
                keyword = source.get('search_keyword')

                try:
                    # 先检查是否已存在
                    existing = session.query(PaperSearchSource).filter_by(
                        task_id=task_id,
                        paper_id=paper_id,
                        search_keyword=keyword
                    ).first()

                    if not existing:
                        record = PaperSearchSource(
                            task_id=task_id,
                            paper_id=paper_id,
                            search_keyword=keyword
                        )
                        session.add(record)
                        count += 1
                except Exception as e:
                    # 单条插入失败，继续下一条
                    print(f"[StageRecorder] 跳过记录: {e}")
                    continue

            session.commit()
            print(f"[StageRecorder] 记录搜索来源: {count} 条 (去重前: {len(sources)})")
            return count
        except Exception as e:
            session.rollback()
            print(f"[StageRecorder] 记录搜索来源失败: {e}")
            traceback.print_exc()
            return 0
        finally:
            session.close()

    def get_paper_search_sources(self, task_id: str) -> Dict:
        """
        获取任务的搜索来源统计

        Args:
            task_id: 任务ID

        Returns:
            {
                "task_id": "xxx",
                "total_records": 总记录数,
                "keyword_stats": [
                    {
                        "keyword": "搜索关键词",
                        "matched_papers_count": 匹配文献数,
                        "paper_ids": [...]
                    }
                ]
            }
        """
        session = self.get_session()
        try:
            from sqlalchemy import func

            # 按关键词分组统计
            stats = session.query(
                PaperSearchSource.search_keyword,
                func.count(PaperSearchSource.paper_id).label('count')
            ).filter(
                PaperSearchSource.task_id == task_id
            ).group_by(
                PaperSearchSource.search_keyword
            ).order_by(
                func.count(PaperSearchSource.paper_id).desc()
            ).all()

            # 获取每个关键词匹配的文献ID
            keyword_stats = []
            for keyword, count in stats:
                papers = session.query(PaperSearchSource.paper_id).filter(
                    PaperSearchSource.task_id == task_id,
                    PaperSearchSource.search_keyword == keyword
                ).all()
                paper_ids = [p.paper_id for p in papers]

                keyword_stats.append({
                    "keyword": keyword,
                    "matched_papers_count": count,
                    "paper_ids": paper_ids[:10]  # 最多返回10个示例
                })

            return {
                "task_id": task_id,
                "total_records": session.query(PaperSearchSource).filter(
                    PaperSearchSource.task_id == task_id
                ).count(),
                "keyword_stats": keyword_stats
            }
        except Exception as e:
            print(f"[StageRecorder] 获取搜索来源统计失败: {e}")
            traceback.print_exc()
            return {
                "task_id": task_id,
                "total_records": 0,
                "keyword_stats": []
            }
        finally:
            session.close()


# 全局实例
stage_recorder = StageRecorder()
