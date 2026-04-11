"""
管理员统计 API 路由 - /david 页面数据接口
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..services.admin_stats_service import AdminStatsService

router = APIRouter(prefix="/api/admin/stats", tags=["管理员统计"])


# 数据库依赖（需要在主应用中提供）
_default_get_db = None
_shared_redis_client = None


def get_db():
    """获取数据库会话（需要在主应用中实现）"""
    global _default_get_db
    if _default_get_db is not None:
        yield from _default_get_db()
        return
    raise NotImplementedError("请在主应用中实现 set_get_db() 函数")


def set_get_db(get_db_func):
    """设置数据库依赖（由主应用调用）"""
    global _default_get_db
    _default_get_db = get_db_func


def set_redis_client(redis_client):
    """设置共享 Redis 客户端"""
    global _shared_redis_client
    _shared_redis_client = redis_client


def get_admin_stats_service(db: Session = Depends(get_db)) -> AdminStatsService:
    """获取管理员统计服务"""
    return AdminStatsService(db, redis_client=_shared_redis_client)


@router.get("/overview")
async def get_admin_stats_overview(
    stats_service: AdminStatsService = Depends(get_admin_stats_service)
):
    """
    获取管理员统计概览

    返回：
    - visits: 访问量（总数、今日）
    - registers: 注册量（总数、今日）
    - generations: 生成数（总数、免费、付费）
    - payments: 付费统计（总订单数、总收入、按套餐分组）
    - today: 今日数据汇总
    """
    stats = stats_service.get_overview_stats()
    return {
        "success": True,
        "data": stats
    }


@router.get("/daily")
async def get_admin_daily_stats(
    days: int = 30,
    stats_service: AdminStatsService = Depends(get_admin_stats_service)
):
    """
    获取每日统计数据

    参数：
    - days: 天数（默认最近 30 天）

    返回每日数据：
    - date: 日期
    - visits: 访问量
    - registers: 注册量
    - generations: 生成数
    - payments: 付费数
    - revenue: 收入
    """
    if days > 365:
        raise HTTPException(status_code=400, detail="天数不能超过 365 天")

    stats = stats_service.get_daily_stats(days)
    return {
        "success": True,
        "data": {
            "days": days,
            "stats": stats
        }
    }
