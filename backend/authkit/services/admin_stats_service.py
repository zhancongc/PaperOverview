"""
管理员统计服务 - 汇总所有用户数据
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)


class AdminStatsService:
    """管理员统计服务"""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis_client = redis_client

    def get_overview_stats(self) -> dict:
        """获取统计概览（总数据）"""
        from ..models.stats import SiteStats
        from models import ReviewRecord
        from authkit.models.payment import Subscription
        from authkit.models import User

        # 1. 总访问量（从 Redis 或数据库）
        total_visits = self._get_total_visits()

        # 2. 总注册量
        total_registers = self.db.query(func.count(User.id)).scalar() or 0

        # 3. 总生成数（含免费）
        total_generations = self.db.query(func.count(ReviewRecord.id)).filter(
            ReviewRecord.status == "success"
        ).scalar() or 0

        # 免费生成数
        free_generations = self.db.query(func.count(ReviewRecord.id)).filter(
            and_(
                ReviewRecord.status == "success",
                ReviewRecord.is_paid == False
            )
        ).scalar() or 0

        # 付费生成数
        paid_generations = total_generations - free_generations

        # 4. 付费统计（按套餐类型）
        payment_stats = self._get_payment_stats()

        # 5. 今日数据
        today_stats = self._get_today_stats()

        return {
            "visits": {
                "total": total_visits,
                "today": today_stats.get("today_visits", 0)
            },
            "registers": {
                "total": total_registers,
                "today": today_stats.get("today_registers", 0)
            },
            "generations": {
                "total": total_generations,
                "free": free_generations,
                "paid": paid_generations
            },
            "payments": payment_stats,
            "today": today_stats
        }

    def get_daily_stats(self, days: int = 30) -> list:
        """获取每日统计数据（最近 N 天）"""
        from ..models.stats import SiteStats
        from models import ReviewRecord
        from authkit.models import User
        from authkit.models.payment import Subscription

        result = []
        today = date.today()

        for i in range(days):
            stat_date = (today - timedelta(days=days - 1 - i)).isoformat()
            date_obj = date.fromisoformat(stat_date)

            # 访问量（从 Redis 或数据库）
            visits = self._get_visits_by_date(stat_date)

            # 注册量
            registers = self.db.query(func.count(User.id)).filter(
                func.date(User.created_at) == date_obj
            ).scalar() or 0

            # 生成数
            generations = self.db.query(func.count(ReviewRecord.id)).filter(
                and_(
                    ReviewRecord.status == "success",
                    func.date(ReviewRecord.created_at) == date_obj
                )
            ).scalar() or 0

            # 付费数
            payments = self.db.query(func.count(Subscription.id)).filter(
                and_(
                    Subscription.status == "paid",
                    func.date(Subscription.payment_time) == date_obj
                )
            ).scalar() or 0

            # 收入
            revenue = self.db.query(func.sum(Subscription.amount)).filter(
                and_(
                    Subscription.status == "paid",
                    func.date(Subscription.payment_time) == date_obj
                )
            ).scalar() or 0

            result.append({
                "date": stat_date,
                "visits": visits,
                "registers": registers,
                "generations": generations,
                "payments": payments,
                "revenue": float(revenue)
            })

        return result

    def _get_total_visits(self) -> int:
        """获取总访问量"""
        if self.redis_client:
            # 从 Redis 获取最近 7 天的访问量
            total = 0
            for i in range(7):
                date_str = (date.today() - timedelta(days=i)).isoformat()
                visit_key = f"stats:visits:{date_str}"
                visits = self.redis_client.get(visit_key)
                if visits:
                    total += int(visits)

            # 加上数据库中的历史数据
            from ..models.stats import SiteStats
            db_visits = self.db.query(func.sum(SiteStats.visit_count)).scalar() or 0
            total += db_visits
            return total
        else:
            # 从数据库获取
            from ..models.stats import SiteStats
            return self.db.query(func.sum(SiteStats.visit_count)).scalar() or 0

    def _get_visits_by_date(self, stat_date: str) -> int:
        """获取指定日期的访问量"""
        if self.redis_client:
            visit_key = f"stats:visits:{stat_date}"
            visits = self.redis_client.get(visit_key)
            if visits:
                return int(visits)

        # 降级到数据库
        from ..models.stats import SiteStats
        stats = self.db.query(SiteStats).filter_by(stat_date=stat_date).first()
        return stats.visit_count if stats else 0

    def _get_payment_stats(self) -> dict:
        """获取付费统计（按套餐类型）"""
        from authkit.models.payment import Subscription

        # 总付费订单数
        total_payments = self.db.query(func.count(Subscription.id)).filter(
            Subscription.status == "paid"
        ).scalar() or 0

        # 总收入
        total_revenue = self.db.query(func.sum(Subscription.amount)).filter(
            Subscription.status == "paid"
        ).scalar() or 0

        # 按套餐类型统计
        plan_stats = self.db.query(
            Subscription.plan_type,
            func.count(Subscription.id).label('count'),
            func.sum(Subscription.amount).label('revenue')
        ).filter(
            Subscription.status == "paid"
        ).group_by(Subscription.plan_type).all()

        plans = {}
        for plan_type, count, revenue in plan_stats:
            plans[plan_type] = {
                "count": count,
                "revenue": float(revenue)
            }

        # 套餐名称映射
        plan_names = {
            "single": "体验包",
            "semester": "标准包",
            "yearly": "进阶包",
            "unlock": "单次解锁"
        }

        for plan_type, name in plan_names.items():
            if plan_type not in plans:
                plans[plan_type] = {"count": 0, "revenue": 0.0}
            plans[plan_type]["name"] = name

        return {
            "total_orders": total_payments,
            "total_revenue": float(total_revenue),
            "by_plan": plans
        }

    def _get_today_stats(self) -> dict:
        """获取今日统计"""
        from ..models.stats import SiteStats
        from models import ReviewRecord
        from authkit.models import User
        from authkit.models.payment import Subscription

        today = date.today()

        # 今日访问量
        today_visits = self._get_visits_by_date(today.isoformat())

        # 今日注册量
        today_registers = self.db.query(func.count(User.id)).filter(
            func.date(User.created_at) == today
        ).scalar() or 0

        # 今日生成数
        today_generations = self.db.query(func.count(ReviewRecord.id)).filter(
            and_(
                ReviewRecord.status == "success",
                func.date(ReviewRecord.created_at) == today
            )
        ).scalar() or 0

        # 今日付费数
        today_payments = self.db.query(func.count(Subscription.id)).filter(
            and_(
                Subscription.status == "paid",
                func.date(Subscription.payment_time) == today
            )
        ).scalar() or 0

        # 今日收入
        today_revenue = self.db.query(func.sum(Subscription.amount)).filter(
            and_(
                Subscription.status == "paid",
                func.date(Subscription.payment_time) == today
            )
        ).scalar() or 0

        return {
            "today_visits": today_visits,
            "today_registers": today_registers,
            "today_generations": today_generations,
            "today_payments": today_payments,
            "today_revenue": float(today_revenue)
        }
