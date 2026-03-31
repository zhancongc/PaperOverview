"""
综述记录服务

处理综述记录的数据库操作：
- 创建记录
- 更新记录
- 查询记录
- 删除记录
"""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models import ReviewRecord


class ReviewRecordService:
    """综述记录服务"""

    def create_record(
        self,
        db_session: Session,
        topic: str,
        target_count: int = 50,
        recent_years_ratio: float = 0.5,
        english_ratio: float = 0.3
    ) -> ReviewRecord:
        """
        创建新的综述记录

        Args:
            db_session: 数据库会话
            topic: 论文主题
            target_count: 目标文献数量
            recent_years_ratio: 近5年占比
            english_ratio: 英文文献占比

        Returns:
            创建的记录对象
        """
        record = ReviewRecord(
            topic=topic,
            review="",
            papers=[],
            statistics={},
            target_count=target_count,
            recent_years_ratio=recent_years_ratio,
            english_ratio=english_ratio,
            status="processing"
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record

    def update_success(
        self,
        db_session: Session,
        record: ReviewRecord,
        review: str,
        papers: List[Dict],
        statistics: Dict
    ) -> ReviewRecord:
        """
        更新记录为成功状态

        Args:
            db_session: 数据库会话
            record: 记录对象
            review: 综述内容
            papers: 被引用的文献列表
            statistics: 统计信息

        Returns:
            更新后的记录对象
        """
        record.review = review
        record.papers = papers
        record.statistics = statistics
        record.status = "success"
        record.error_message = None
        db_session.commit()
        db_session.refresh(record)
        return record

    def update_failure(
        self,
        db_session: Session,
        record: ReviewRecord,
        error_message: str
    ) -> ReviewRecord:
        """
        更新记录为失败状态

        Args:
            db_session: 数据库会话
            record: 记录对象
            error_message: 错误信息

        Returns:
            更新后的记录对象
        """
        record.status = "failed"
        record.error_message = error_message
        db_session.commit()
        db_session.refresh(record)
        return record

    def get_record(
        self,
        db_session: Session,
        record_id: int
    ) -> Optional[ReviewRecord]:
        """
        获取单条记录

        Args:
            db_session: 数据库会话
            record_id: 记录ID

        Returns:
            记录对象，不存在则返回 None
        """
        return db_session.query(ReviewRecord).filter(
            ReviewRecord.id == record_id
        ).first()

    def list_records(
        self,
        db_session: Session,
        skip: int = 0,
        limit: int = 20
    ) -> List[ReviewRecord]:
        """
        获取记录列表

        Args:
            db_session: 数据库会话
            skip: 跳过条数
            limit: 返回条数

        Returns:
            记录列表
        """
        return db_session.query(ReviewRecord).order_by(
            ReviewRecord.created_at.desc()
        ).offset(skip).limit(limit).all()

    def delete_record(
        self,
        db_session: Session,
        record_id: int
    ) -> bool:
        """
        删除记录

        Args:
            db_session: 数据库会话
            record_id: 记录ID

        Returns:
            是否删除成功
        """
        record = self.get_record(db_session, record_id)
        if not record:
            return False

        db_session.delete(record)
        db_session.commit()
        return True

    def record_to_dict(self, record: ReviewRecord) -> Dict:
        """
        将记录对象转换为字典

        Args:
            record: 记录对象

        Returns:
            字典格式的记录数据
        """
        return record.to_dict()
