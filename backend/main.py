"""
FastAPI 主应用
"""
import os
import logging
from dotenv import load_dotenv

# 全局日志级别设为 INFO，过滤 DEBUG 输出
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量（必须在所有导入之前）
load_dotenv()  # 加载 .env
load_dotenv('.env.auth', override=True)  # 加载 .env.auth

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime
from urllib.parse import quote

from database import db, get_db

# 集成 auth-kit - 必须先注入依赖再导入路由
from authkit.database import init_database as init_auth_database, get_db as auth_get_db
import authkit.routers.auth
authkit.routers.auth.set_get_db(auth_get_db)

from authkit.routers import router as auth_router
import authkit.routers.stats as stats_router_module
import authkit.routers.admin_stats as admin_stats_router_module
from authkit.middleware import StatsMiddleware

# 支付模块
from authkit.routers import subscription as sub_router
from authkit.routers import webhook as webhook_router
from authkit.routers import payment_callback as payment_cb_router
from authkit.models.payment import Subscription, PaymentLog, PaymentBase
from models import ReviewRecord
from services.scholarflux_wrapper import ScholarFlux
from services.smart_paper_search import SmartPaperSearchService
from services.paper_filter import PaperFilterService
from services.topic_analyzer import ThreeCirclesReviewGenerator
from services.hybrid_classifier import FrameworkGenerator
from services.docx_generator import DocxGenerator
from services.reference_validator import ReferenceValidator
from services.review_record_service import ReviewRecordService
from services.task_manager import TaskManager, TaskStatus, task_manager
from services.review_task_executor import ReviewTaskExecutor
from config import Config, UserConfig

# 认证依赖
security = HTTPBearer(auto_error=False)

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[int]:
    """从 token 中提取 user_id，未登录返回 None"""
    if not credentials:
        return None
    from authkit.core.security import decode_access_token
    payload = decode_access_token(credentials.credentials)
    if payload:
        uid = payload.get("sub")
        return int(uid) if uid else None
    return None


def check_and_deduct_credit(user_id: int, db_session: Session) -> tuple[Optional[str], bool]:
    """
    检查并扣除用户综述额度。
    返回 (错误信息, 是否扣除付费额度)。错误信息为 None 表示通过。
    优先扣除付费额度，再扣除免费额度。
    """
    from authkit.models import User
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return None, False  # 用户不存在时不拦截

    free_credits = user.get_meta("free_credits", 0)
    paid_credits = user.get_meta("review_credits", 0)
    total = free_credits + paid_credits

    if total <= 0:
        return "综述生成额度已用完，请购买套餐后继续使用", False

    # 优先扣除付费额度，再用免费额度
    used_paid = paid_credits > 0
    if used_paid:
        user.set_meta("review_credits", paid_credits - 1)
    else:
        user.set_meta("free_credits", free_credits - 1)
    db_session.commit()
    return None, used_paid


def refund_credit(user_id: int, db_session: Session) -> None:
    """
    退还用户综述额度（任务失败时调用）。
    优先退还免费额度，再退还付费额度（与扣除顺序相反）。
    """
    from authkit.models import User
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return

    free_credits = user.get_meta("free_credits", 0)
    paid_credits = user.get_meta("review_credits", 0)

    # 优先退还免费额度（与扣除时"先用付费再用免费"相反）
    if free_credits == 0:
        user.set_meta("review_credits", paid_credits + 1)
    else:
        user.set_meta("free_credits", free_credits + 1)
    db_session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    db.connect()

    # 创建数据库表
    from models import Base
    db.create_tables()

    # 创建支付相关表
    PaymentBase.metadata.create_all(bind=db.engine)
    logger.debug("[Startup] 数据库表已创建/更新（含支付表）")

    # 初始化 auth-kit 数据库（使用 PostgreSQL）
    auth_db_url = os.getenv("AUTH_DATABASE_URL", "postgresql://postgres:security@localhost/paper")
    init_auth_database(auth_db_url)
    logger.debug("[Startup] Auth 数据库已初始化 (PostgreSQL)")

    # 初始化支付模块 - 注入数据库依赖
    from authkit.database import get_db as authkit_get_db
    sub_router.set_get_db(authkit_get_db)
    webhook_router.set_get_db(authkit_get_db)
    payment_cb_router.set_get_db(authkit_get_db)
    logger.debug("[Startup] 支付模块已初始化")

    # 初始化套餐数据到数据库
    from authkit.models.payment import init_plans_in_db
    with next(authkit_get_db()) as session:
        init_plans_in_db(session)
    logger.debug("[Startup] 套餐数据已初始化")

    # 初始化统计数据库表
    from authkit.models.stats import StatsBase
    StatsBase.metadata.create_all(bind=db.engine)
    logger.debug("[Startup] 统计数据库表已创建")

    # 初始化 Redis 客户端（用于统计）
    redis_client = None
    try:
        import redis
        from authkit.core.config import config as auth_config
        redis_client = redis.Redis(
            host=auth_config.REDIS_HOST,
            port=auth_config.REDIS_PORT,
            db=auth_config.REDIS_DB,
            password=auth_config.REDIS_PASSWORD,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("[Startup] Redis 连接成功（统计功能启用）")

        # 设置共享 Redis 客户端（供中间件和路由使用）
        from authkit.middleware import StatsMiddleware
        StatsMiddleware._shared_redis_client = redis_client
        stats_router_module.set_redis_client(redis_client)
        admin_stats_router_module.set_redis_client(redis_client)

        # 启动统计批量写入任务
        from authkit.middleware.stats_middleware import StatsBatchWriter
        batch_writer = StatsBatchWriter(redis_client, auth_get_db, interval_seconds=300)
        asyncio.create_task(batch_writer.start())
        logger.info("[Startup] 统计批量写入任务已启动")

    except Exception as e:
        logger.warning(f"[Startup] Redis 不可用，统计功能降级到数据库模式: {e}")
        redis_client = None

    # 从 Redis 恢复重启前的活跃任务
    task_manager.restore_from_redis()

    yield
    # 关闭时执行
    logger.debug("[Shutdown] 应用关闭")

app = FastAPI(
    title="论文综述生成器 API",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加统计中间件（在 CORS 之后）
app.add_middleware(StatsMiddleware, get_db_func=auth_get_db)

# 集成认证路由
app.include_router(auth_router)

# 集成统计路由
stats_router_module.set_get_db(auth_get_db)
app.include_router(stats_router_module.router)

# 集成管理员统计路由
admin_stats_router_module.set_get_db(auth_get_db)
app.include_router(admin_stats_router_module.router)

# 集成支付路由
app.include_router(sub_router.router)
app.include_router(webhook_router.router)
app.include_router(payment_cb_router.router)

# 请求模型
class TopicRequest(BaseModel):
    topic: str = Field(..., description="论文题目", min_length=1)

class GenerateRequest(BaseModel):
    # 必填参数
    topic: str = Field(..., description="论文主题", min_length=1)

    # 可选参数：研究方向ID（提高搜索相关性）
    research_direction_id: str = Field(
        "",
        description="研究方向ID（可选）。可选值：computer（计算机科学）、materials（材料科学）、management（管理学）。如果不指定，系统将自动推断。",
    )

    # 基本配置（有默认值）
    target_count: int = Field(50, description="目标文献数量", ge=10, le=100)
    recent_years_ratio: float = Field(0.5, description="近5年占比", ge=0.1, le=1.0)
    english_ratio: float = Field(0.0, description="英文文献占比（已废弃，不再使用）", ge=0.0, le=1.0)

    # 高级配置（可选，有默认值）
    search_years: int = Field(10, description="搜索年份范围", ge=5, le=30)
    max_search_queries: int = Field(8, description="最多搜索查询数", ge=1, le=20)

class GenerateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

class ExportRequest(BaseModel):
    record_id: int
    format: str = "ieee"  # 引用格式 (ieee/apa/mla/gb_t_7714)


class UnlockRequest(BaseModel):
    record_id: int

# 全局服务实例
scholarflux = ScholarFlux()
search_service = SmartPaperSearchService(scholarflux, get_db)
filter_service = PaperFilterService()
three_circles_generator = ThreeCirclesReviewGenerator()
record_service = ReviewRecordService()

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "论文综述生成器 API"}


@app.get("/api/research-directions")
async def get_research_directions():
    """
    获取系统支持的研究方向列表

    返回所有可用的研究方向，包括：
    - 方向ID
    - 中文名称
    - 英文名称
    - 描述
    - 关键词列表
    - 缩写词表
    - 子方向列表
    """
    try:
        from config.research_directions import get_all_directions

        directions = get_all_directions()

        return {
            "success": True,
            "data": directions
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_papers(
    query: str,
    limit: int = 100,
    years_ago: int = 5
):
    """搜索论文接口"""
    try:
        papers = await search_service.search_papers(
            query=query,
            years_ago=years_ago,
            limit=limit
        )
        return {
            "success": True,
            "count": len(papers),
            "papers": papers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/records")
async def get_records(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = Depends(get_current_user_id),
    db_session: Session = Depends(get_db)
):
    """获取当前用户的生成记录列表"""
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    records = record_service.list_records(db_session, skip, limit, user_id=user_id)

    return {
        "success": True,
        "count": len(records),
        "records": [record_service.record_to_dict(r) for r in records]
    }

@app.get("/api/records/{record_id}")
async def get_record(
    record_id: int,
    db_session: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """获取单条记录详情"""
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    record = record_service.get_record(db_session, record_id)

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 验证所有权
    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="该综述不属于您，无法访问")

    return {
        "success": True,
        "record": record_service.record_to_dict(record)
    }

@app.delete("/api/records/{record_id}")
async def delete_record(
    record_id: int,
    db_session: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """删除记录"""
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    # 先获取记录验证所有权
    record = record_service.get_record(db_session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="该综述不属于您，无法删除")

    deleted = record_service.delete_record(db_session, record_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")

    return {"success": True, "message": "删除成功"}


@app.post("/api/records/export")
async def export_review_docx(
    request: ExportRequest,
    db_session: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    导出文献综述为 Word 文档
    - 公开文档（案例）可直接导出
    - 付费用户可导出自己的文档
    PDF 导出由前端 html2canvas + jspdf 实现
    """
    from models import ReviewTask

    # 公开文档列表（案例展示）- 从环境变量读取
    DEMO_TASK_IDS = set(os.getenv("DEMO_TASK_IDS", "").split(",")) if os.getenv("DEMO_TASK_IDS") else set()

    record = record_service.get_record(db_session, request.record_id)

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 查找对应的 task_id 判断是否为公开文档
    review_task = db_session.query(ReviewTask).filter_by(review_record_id=record.id).first()
    is_public_doc = review_task and review_task.id in DEMO_TASK_IDS

    # 如果不是公开文档，检查用户权限
    if not is_public_doc:
        # 验证用户所有权
        if not user_id:
            raise HTTPException(status_code=401, detail="请先登录")

        if record.user_id != user_id:
            raise HTTPException(status_code=403, detail="该综述不属于您，无法导出")

        # Word 导出逻辑：
        # 1. 已付费生成的文档（is_paid=True）：直接导出
        # 2. 免费生成的文档（is_paid=False）：需要单次解锁（29.8元）或用付费额度重新生成
        if not getattr(record, 'is_paid', False):
            raise HTTPException(status_code=403, detail="该综述使用免费额度生成，导出 Word 需要单次解锁（29.8元）或使用付费额度重新生成")

    try:
        generator = DocxGenerator()
        docx_bytes = generator.generate_review_docx(
            topic=record.topic,
            review=record.review,
            papers=record.papers,
            statistics=record.statistics,
            citation_format=request.format
        )

        from fastapi.responses import Response
        from datetime import datetime
        now = datetime.now()
        timestamp = now.strftime("%y%m%d-%H%M%S")

        safe_topic = record.topic.replace('/', '-').replace('\\', '-').replace(':', '-')
        safe_topic = safe_topic.replace('（', '-').replace('）', '-')
        safe_topic = safe_topic.replace('<', '-').replace('>', '-').replace('|', '-')
        safe_topic = safe_topic.replace('"', '-').replace('*', '-').replace('?', '-')
        safe_topic = safe_topic[:50]

        filename = f"文献综述-{safe_topic}-{timestamp}.docx"
        encoded_filename = quote(filename, safe='')

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@app.post("/api/records/unlock")
async def unlock_record_for_export(
    request: UnlockRequest,
    db_session: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    单次解锁综述，允许导出 Word（29.8元）
    - 将该综述标记为已付费（is_paid=True）
    - 创建支付订单（29.8元）
    - 支付成功后自动解锁
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    record = record_service.get_record(db_session, request.record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 检查是否已经是付费状态
    if getattr(record, 'is_paid', False):
        return {
            "success": True,
            "message": "该综述已解锁",
            "already_unlocked": True
        }

    # 检查是否是该用户的记录
    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="该综述不属于您，无法解锁")

    # 创建解锁订单
    from authkit.database import SessionLocal as AuthSessionLocal
    from authkit.models.payment import Subscription, PaymentLog
    import uuid

    if not AuthSessionLocal:
        raise HTTPException(status_code=500, detail="支付服务不可用")

    auth_db = AuthSessionLocal()
    try:
        # 生成订单号
        order_no = f"UL{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

        # 创建订阅记录（使用单次体验套餐的价格）
        subscription = Subscription(
            user_id=user_id,
            order_no=order_no,
            plan_type="unlock",
            amount=29.8,
            status="pending",
            record_id=request.record_id,
        )
        auth_db.add(subscription)
        auth_db.commit()
        auth_db.refresh(subscription)

        # 记录日志
        log = PaymentLog(
            subscription_id=subscription.id,
            user_id=user_id,
            action="unlock_record",
            request_data=str({"record_id": request.record_id}),
        )
        auth_db.add(log)
        auth_db.commit()

        # 统一调用支付服务（开发环境使用 DevAlipayService，生产环境使用真实支付宝）
        from authkit.services.payment_config import get_payment_config, get_payment_service

        payment_config = get_payment_config()
        alipay_service = get_payment_service()

        # 构建回调 URL
        return_url = f"{payment_config['frontend_url']}/profile"
        notify_url = f"{payment_config['backend_url']}/api/payment/notify"

        # 创建支付订单
        pay_url = alipay_service.create_order(
            out_trade_no=order_no,
            total_amount=29.8,
            subject="单次解锁综述导出",
            timeout_express="15m",
            return_url=return_url,
            notify_url=notify_url
        )

        if pay_url:
            return {
                "success": True,
                "order_no": order_no,
                "amount": 29.8,
                "pay_url": pay_url,
                "message": "解锁订单已创建，请完成支付"
            }
        else:
            return {
                "success": False,
                "message": "创建支付订单失败，请稍后重试"
            }
    finally:
        auth_db.close()


@app.post("/api/records/unlock-with-credit")
async def unlock_record_with_credit(
    request: UnlockRequest,
    db_session: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    使用额度解锁综述（扣除1个付费额度）
    - 检查用户是否有足够的付费额度
    - 扣除1个额度
    - 将综述标记为已付费（is_paid=True）
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    record = record_service.get_record(db_session, request.record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 检查是否已经是付费状态
    if getattr(record, 'is_paid', False):
        return {
            "success": True,
            "message": "该综述已解锁"
        }

    # 检查是否是该用户的记录
    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="该综述不属于您，无法解锁")

    # 检查并扣除额度
    from authkit.database import SessionLocal as AuthSessionLocal
    from authkit.models import User

    auth_db = AuthSessionLocal()
    try:
        user = auth_db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        current_credits = user.get_meta("review_credits", 0)
        if current_credits < 1:
            return {
                "success": False,
                "message": "付费额度不足，请购买套餐"
            }

        # 扣除1个额度
        user.set_meta("review_credits", current_credits - 1)

        # 标记综述为已付费
        record.is_paid = True

        db_session.commit()
        auth_db.commit()

        return {
            "success": True,
            "message": "解锁成功！已扣除1个付费额度"
        }
    finally:
        auth_db.close()


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    demo_task_ids = [s.strip() for s in os.getenv("DEMO_TASK_IDS", "").split(",") if s.strip()]
    return {
        "status": "ok",
        "deepseek_configured": bool(api_key),
        "demo_task_ids": demo_task_ids
    }


@app.get("/api/jade/access")
async def check_jade_access(user_id: Optional[int] = Depends(get_current_user_id)):
    """检查当前用户是否有 /jade 页面的访问权限"""
    if not user_id:
        return {"allowed": False}

    whitelist_str = os.getenv("JADE_WHITELIST", "")
    whitelist = {email.strip() for email in whitelist_str.split(",") if email.strip()}
    if not whitelist:
        return {"allowed": False}

    from authkit.database import SessionLocal as AuthSessionLocal
    if not AuthSessionLocal:
        return {"allowed": False}

    auth_db = AuthSessionLocal()
    try:
        from authkit.models import User
        user = auth_db.query(User).filter(User.id == user_id).first()
        if user and user.email in whitelist:
            return {"allowed": True}
    finally:
        auth_db.close()

    return {"allowed": False}


@app.get("/api/david/access")
async def check_david_access(user_id: Optional[int] = Depends(get_current_user_id)):
    """检查当前用户是否有 /david 页面的访问权限"""
    if not user_id:
        return {"allowed": False}

    whitelist_str = os.getenv("DAVID_WHITELIST", "")
    whitelist = {email.strip() for email in whitelist_str.split(",") if email.strip()}
    if not whitelist:
        return {"allowed": False}

    from authkit.database import SessionLocal as AuthSessionLocal
    if not AuthSessionLocal:
        return {"allowed": False}

    auth_db = AuthSessionLocal()
    try:
        from authkit.models import User
        user = auth_db.query(User).filter(User.id == user_id).first()
        if user and user.email in whitelist:
            return {"allowed": True}
    finally:
        auth_db.close()

    return {"allowed": False}


@app.get("/api/tasks/active")
async def get_active_task(user_id: Optional[int] = Depends(get_current_user_id)):
    """获取当前用户进行中的任务"""
    if not user_id:
        return {"active": False}

    # 先检查内存中的任务
    from services.task_manager import task_manager
    for task_id, task in task_manager._tasks.items():
        if getattr(task, 'user_id', None) == user_id and task.status in ("pending", "processing"):
            return {
                "active": True,
                "task_id": task_id,
                "topic": task.topic,
                "status": task.status,
                "progress": task.progress if hasattr(task, 'progress') else None
            }

    # 再检查数据库
    from models import ReviewTask, ReviewRecord
    db_session = next(get_db())
    try:
        # 通过 review_records 的 user_id 找到关联的进行中任务
        pending_tasks = db_session.query(ReviewTask).filter(
            ReviewTask.status.in_(["pending", "processing"])
        ).all()
        for t in pending_tasks:
            if t.review_record_id:
                record = db_session.query(ReviewRecord).filter_by(id=t.review_record_id).first()
                if record and record.user_id == user_id:
                    return {
                        "active": True,
                        "task_id": t.id,
                        "topic": t.topic,
                        "status": t.status,
                        "progress": None
                    }
    finally:
        db_session.close()

    return {"active": False}


@app.get("/api/usage/credits")
async def get_credits(user_id: Optional[int] = Depends(get_current_user_id)):
    """获取当前用户综述额度"""
    if not user_id:
        return {"credits": 0, "free_credits": 0, "has_purchased": False}

    from authkit.database import SessionLocal as AuthSessionLocal
    if not AuthSessionLocal:
        return {"credits": 0, "free_credits": 0, "has_purchased": False}

    auth_db = AuthSessionLocal()
    try:
        from authkit.models import User
        user = auth_db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"credits": 0, "free_credits": 0, "has_purchased": False}
        free = user.get_meta("free_credits", 0)
        paid = user.get_meta("review_credits", 0)
        return {
            "credits": free + paid,
            "free_credits": free,
            "has_purchased": user.get_meta("has_purchased", False),
        }
    finally:
        auth_db.close()


@app.get("/api/papers/statistics")
async def get_papers_statistics():
    """获取论文库统计信息"""
    try:
        stats = search_service.get_statistics()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/papers/recent")
async def get_recent_papers(limit: int = 50):
    """获取最近入库的论文"""
    try:
        with next(get_db()) as session:
            from services.paper_metadata_dao import PaperMetadataDAO
            dao = PaperMetadataDAO(session)
            papers = dao.get_recent_papers(limit=limit)
            return {
                "success": True,
                "count": len(papers),
                "papers": [p.to_dict() for p in papers]
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/papers/top-cited")
async def get_top_cited_papers(limit: int = 50):
    """获取被引次数最多的论文"""
    try:
        with next(get_db()) as session:
            from services.paper_metadata_dao import PaperMetadataDAO
            dao = PaperMetadataDAO(session)
            papers = dao.get_top_cited_papers(limit=limit)
            return {
                "success": True,
                "count": len(papers),
                "papers": [p.to_dict() for p in papers]
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }



# ==================== 配置接口 ====================

@app.get("/api/config/schema")
async def get_config_schema():
    """
    获取用户配置 Schema

    返回前端表单配置，用于动态生成配置界面
    """
    return {
        "success": True,
        "data": UserConfig.get_schema()
    }

@app.get("/api/config/server")
async def get_server_config():
    """
    获取服务端配置（只读）

    用于显示当前服务端配置，便于调试
    """
    return {
        "success": True,
        "data": {
            "max_retries": Config.MAX_RETRIES,
            "min_papers_threshold": Config.MIN_PAPERS_THRESHOLD,
            "candidate_pool_multiplier": Config.CANDIDATE_POOL_MULTIPLIER,
            "papers_per_page": Config.PAPERS_PER_PAGE,
            "aminer_rate_limit": Config.AMINER_RATE_LIMIT,
            "openalex_rate_limit": Config.OPENALEX_RATE_LIMIT,
            "semantic_scholar_rate_limit": Config.SEMANTIC_SCHOLAR_RATE_LIMIT,
            "citation_weight": Config.CITATION_WEIGHT,
            "recency_weight": Config.RECENCY_WEIGHT,
            "relevance_weight": Config.RELEVANCE_WEIGHT,
        }
    }

    # ==================== 题目分类接口 ====================

@app.post("/api/classify-topic")
async def classify_topic(request: TopicRequest):
    """
    题目分类接口（使用大模型）

    自动识别题目类型（应用型/评价型/理论型/实证型）
    并生成对应的综述框架
    """
    import sys
    import time

    logger.debug("[API] 收到分类请求: %s", request.topic)
    start = time.time()

    try:
        from services.hybrid_classifier import FrameworkGenerator

        gen = FrameworkGenerator()
        result = await gen.generate_framework(request.topic)

        elapsed = time.time() - start
        logger.debug(f"[API] 大模型分类成功，耗时 {elapsed:.2f}秒，类型: {result['type']}")

        return {
            "success": True,
            "message": "题目分类完成",
            "data": result
        }
    except Exception as e:
        elapsed = time.time() - start
        logger.debug(f"[DEBUG] 大模型分类错误 (耗时{elapsed:.2f}秒): {e}")
        import traceback
        traceback.print_exc()
        # 出错时使用规则引擎回退
        from services.topic_classifier import FrameworkGenerator as FallbackGenerator
        fallback = FallbackGenerator()
        result = fallback.generate_framework(request.topic)
        result['classification_reason'] += f'（大模型错误，使用规则引擎）'
        return {
            "success": True,
            "message": "题目分类完成（使用规则引擎）",
            "data": result
        }

# ==================== 智能分析接口 ====================

@app.post("/api/smart-analyze")
async def smart_analyze(request: TopicRequest):
    """
    智能分析接口（使用大模型）

    根据题目类型自动选择合适的分析方法，并生成大纲和搜索关键词
    - 应用型：三圈交集分析
    - 评价型：金字塔式分析
    - 其他：通用分析
    """
    try:
        from services.hybrid_classifier import FrameworkGenerator
        gen = FrameworkGenerator()
        framework = await gen.generate_framework(request.topic, enable_llm_validation=True)

        # === 生成大纲和搜索关键词（复用查找文献的第一步）===
        from services.review_task_executor import ReviewTaskExecutor
        executor = ReviewTaskExecutor()
        outline = await executor._generate_review_outline(request.topic)

        # 提取搜索关键词
        search_queries = []
        for section in outline.get('body_sections', []):
            if isinstance(section, dict):
                search_keywords = section.get('search_keywords', [])
                section_title = section.get('title', '')
                for kw in search_keywords:
                    search_queries.append({
                        'query': kw,
                        'section': section_title,
                        'lang': 'mixed'
                    })

        # 将大纲和搜索关键词添加到分析结果中
        framework['outline'] = outline
        framework['search_queries'] = search_queries

        # 根据类型选择分析方法
        if framework['type'] == 'application':
            # 应用型使用三圈分析
            circles_result = await three_circles_generator.generate(request.topic)

            # 清理 papers 数据，只保留摘要信息
            circles = []
            for circle in circles_result.get('circles', []):
                circles.append({
                    'circle': circle['circle'],
                    'name': circle['name'],
                    'query': circle['query'],
                    'description': circle['description'],
                    'count': circle['count']
                })

            result = {
                'analysis': framework,  # 使用正确的分类数据结构（包含大纲和搜索关键词）
                'circles': circles,
                'review_framework': framework.get('framework'),
                'framework_type': 'three-circles'
            }
        elif framework['type'] == 'evaluation':
            # 评价型使用金字塔式分析
            result = {
                'analysis': framework,
                'circles': [],
                'review_framework': framework.get('framework'),
                'framework_type': 'pyramid'
            }
        else:
            # 其他类型使用框架分析
            result = {
                'analysis': framework,
                'circles': [],
                'review_framework': framework.get('framework'),
                'framework_type': framework.get('type', 'general')
            }

        return {
            "success": True,
            "message": "智能分析完成",
            "data": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 三圈文献分析接口（保留原有功能） ====================

@app.post("/api/analyze-three-circles")
async def analyze_three_circles(request: TopicRequest):
    """
    三圈文献分析接口

    分析论文题目，构建"研究对象+优化目标+方法论"三圈文献体系
    """
    try:
        result = await three_circles_generator.generate(request.topic)

        return {
            "success": True,
            "message": "三圈分析完成",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 智能生成综述接口（异步任务模式）====================

class TaskSubmitResponse(BaseModel):
    """任务提交响应"""
    success: bool
    message: str
    data: Optional[Dict] = None

@app.post("/api/smart-generate", response_model=TaskSubmitResponse)
async def submit_review_task(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    提交综述生成任务（异步模式）

    立即返回任务ID，前端使用 /api/tasks/{task_id} 轮询结果
    """
    # 检查API配置
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return TaskSubmitResponse(
            success=False,
            message="API配置错误：DEEPSEEK_API_KEY not configured"
        )

    # 检查用户付费状态并扣除额度
    is_paid = False
    if user_id:
        from authkit.database import SessionLocal as AuthSessionLocal
        if AuthSessionLocal:
            auth_db = AuthSessionLocal()
            try:
                # 额度检查，返回是否使用了付费额度
                usage_error, used_paid = check_and_deduct_credit(user_id, auth_db)
                if usage_error:
                    return TaskSubmitResponse(success=False, message=usage_error)
                is_paid = used_paid
            finally:
                auth_db.close()

    try:
        # 创建任务
        # 获取研究方向名称
        research_direction = ""
        if request.research_direction_id:
            from config.research_directions import get_direction_by_id
            direction_info = get_direction_by_id(request.research_direction_id)
            if direction_info:
                research_direction = direction_info.get("name", "")

        task = task_manager.create_task(
            topic=request.topic,
            params={
                "research_direction_id": request.research_direction_id,
                "research_direction": research_direction,  # 实际的方向名称
                "target_count": request.target_count,
                "recent_years_ratio": request.recent_years_ratio,
                "english_ratio": request.english_ratio,
                "search_years": request.search_years,
                "max_search_queries": request.max_search_queries,
            },
            user_id=user_id,
            is_paid=is_paid
        )

        # 启动后台任务
        async def run_task():
            # 在后台任务中创建新的 session，不使用请求级别的 session
            executor = ReviewTaskExecutor()
            with next(db.get_session()) as task_session:
                await executor.execute_task(task.task_id, task_session)

        # 使用 asyncio.create_task 而不是 BackgroundTasks
        asyncio.create_task(run_task())

        return TaskSubmitResponse(
            success=True,
            message="任务已提交，请使用任务ID查询进度",
            data={
                "task_id": task.task_id,
                "topic": request.topic,
                "status": TaskStatus.PENDING.value,
                "poll_url": f"/api/tasks/{task.task_id}"
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return TaskSubmitResponse(
            success=False,
            message=f"任务提交失败: {str(e)}"
        )


@app.get("/api/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    user_id: Optional[int] = Depends(get_current_user_id),
    db_session: Session = Depends(get_db)
):
    """
    获取任务状态和结果

    前端轮询此接口获取任务进度和结果
    """
    from models import ReviewTask, ReviewRecord

    # 公开文档列表（案例展示）- 从环境变量读取
    DEMO_TASK_IDS = set(os.getenv("DEMO_TASK_IDS", "").split(",")) if os.getenv("DEMO_TASK_IDS") else set()
    is_public = task_id in DEMO_TASK_IDS

    # 首先尝试从内存中获取任务
    task = task_manager.get_task(task_id)

    if task:
        # 非公开任务需要验证所有者
        if not is_public:
            if not user_id:
                raise HTTPException(status_code=401, detail="请先登录")
            task_user_id = getattr(task, 'user_id', None)
            if task_user_id and task_user_id != user_id:
                raise HTTPException(status_code=403, detail="该任务不属于您，无法访问")

        response_data = task.to_dict()
        # 如果任务完成，添加结果数据
        if task.status == TaskStatus.COMPLETED and task.result:
            response_data["result"] = task.result
        return {
            "success": True,
            "data": response_data
        }

    # 内存中没有，从数据库查询
    review_task = db_session.query(ReviewTask).filter_by(id=task_id).first()

    if not review_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 非公开任务需要验证所有者
    if not is_public:
        if not user_id:
            raise HTTPException(status_code=401, detail="请先登录")
        if review_task.review_record_id:
            owner_record = db_session.query(ReviewRecord).filter_by(id=review_task.review_record_id).first()
            if owner_record and owner_record.user_id != user_id:
                raise HTTPException(status_code=403, detail="该任务不属于您，无法访问")

    response_data = review_task.to_dict()

    # 如果任务完成，从数据库获取综述记录并添加到结果中
    if review_task.status == "completed" and review_task.review_record_id:
        review_record = db_session.query(ReviewRecord).filter_by(id=review_task.review_record_id).first()
        if review_record:
            response_data["result"] = {
                "id": review_record.id,
                "review": review_record.review,
                "papers": review_record.papers if isinstance(review_record.papers, list) else [],
                "statistics": review_record.statistics if isinstance(review_record.statistics, dict) else {},
                "created_at": review_record.created_at.isoformat() if review_record.created_at else ""
            }

    return {
        "success": True,
        "data": response_data
    }


@app.get("/api/records/{record_id}/review")
async def get_record_review(
    record_id: int,
    format: str = "ieee",
    user_id: Optional[int] = Depends(get_current_user_id),
    db_session: Session = Depends(get_db)
):
    """
    通过 record_id 获取综述结果（支持引用格式切换）

    用于从个人中心等没有 task_id 的场景访问综述

    参数：
    - record_id: 综述记录ID
    - format: 引用格式 (ieee/apa/mla/gb_t_7714，默认 ieee)
    """
    from models import ReviewRecord, ReviewTask

    # 获取综述记录
    review_record = db_session.query(ReviewRecord).filter_by(id=record_id).first()

    if not review_record:
        raise HTTPException(status_code=404, detail="综述记录不存在")

    # 验证所有权
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    if review_record.user_id != user_id:
        raise HTTPException(status_code=403, detail="该综述不属于您，无法访问")

    # 查找关联的 task_id（如果有）
    review_task = db_session.query(ReviewTask).filter_by(review_record_id=review_record.id).first()
    task_id = review_task.id if review_task else None

    # 获取论文列表
    papers = review_record.papers if isinstance(review_record.papers, list) else []

    # 获取综述内容
    review_content = review_record.review

    # 如果指定了非 IEEE 格式，重新格式化参考文献
    if format != "ieee" and "## References" in review_content:
        from services.citation_formatter import format_references

        if papers:
            parts = review_content.split("## References", 1)
            content_part = parts[0]
            new_references = format_references(papers, format)
            review_content = content_part + "## References\n\n" + new_references

    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "topic": review_record.topic,
            "review": review_content,
            "papers": papers,
            "cited_papers_count": len(papers),
            "created_at": review_record.created_at.isoformat() if review_record.created_at else "",
            "statistics": review_record.statistics if isinstance(review_record.statistics, dict) else {},
            "record_id": review_record.id,
            "is_public": False,
            "is_paid": getattr(review_record, 'is_paid', False)
        }
    }


@app.get("/api/tasks/{task_id}/review")
async def get_task_review(
    task_id: str,
    format: str = "ieee",
    user_id: Optional[int] = Depends(get_current_user_id),
    db_session: Session = Depends(get_db)
):
    """
    通过 task_id 获取综述结果

    用于分享链接：/review/{task_id}

    参数：
    - format: 引用格式 (ieee/apa/mla/gb_t_7714，默认 ieee)
    """
    from models import ReviewTask, ReviewRecord

    # 公开文档列表（案例展示）— 从环境变量读取，与 /api/health 保持一致
    _demo_ids = [s.strip() for s in os.getenv("DEMO_TASK_IDS", "").split(",") if s.strip()]
    is_public = task_id in _demo_ids

    # 首先尝试从内存中获取任务
    task = task_manager.get_task(task_id)

    if task and task.status == TaskStatus.COMPLETED and task.result:
        # 非公开任务需要验证所有者
        if not is_public:
            if not user_id:
                raise HTTPException(status_code=401, detail="请先登录")
            task_user_id = getattr(task, 'user_id', None)
            if task_user_id and task_user_id != user_id:
                raise HTTPException(status_code=403, detail="该综述不属于您，无法访问")

        # 内存中有完整的任务数据
        result_data = {
            "task_id": task_id,
            "topic": task.topic,
            "review": task.result.get("review", ""),
            "papers": task.result.get("papers", []),
            "cited_papers_count": task.result.get("cited_papers_count", 0),
            "created_at": task.result.get("created_at", ""),
            "statistics": task.result.get("statistics", {}),
            "record_id": task.result.get("id"),
            "is_public": is_public,
            "is_paid": getattr(task, 'is_paid', False)
        }

        # 如果指定了非 IEEE 格式，重新格式化参考文献
        if format != "ieee" and "## References" in result_data["review"]:
            from services.citation_formatter import format_references

            papers = result_data["papers"]
            if papers:
                parts = result_data["review"].split("## References", 1)
                content_part = parts[0]
                new_references = format_references(papers, format)
                result_data["review"] = content_part + "## References\n\n" + new_references

        return {
            "success": True,
            "data": result_data
        }

    # 内存中没有，从数据库查询
    review_task = db_session.query(ReviewTask).filter_by(id=task_id).first()

    if not review_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if review_task.status != "completed" or not review_task.review_record_id:
        raise HTTPException(status_code=404, detail="综述尚未生成完成")

    # 从数据库获取综述记录
    review_record = db_session.query(ReviewRecord).filter_by(id=review_task.review_record_id).first()

    if not review_record:
        raise HTTPException(status_code=404, detail="综述记录不存在")

    # 非公开任务需要验证所有者
    if not is_public:
        if not user_id:
            raise HTTPException(status_code=401, detail="请先登录")
        if review_record.user_id != user_id:
            raise HTTPException(status_code=403, detail="该综述不属于您，无法访问")

    # 返回与内存任务相同格式的数据
    result_data = {
        "task_id": task_id,
        "topic": review_record.topic,
        "review": review_record.review,
        "papers": review_record.papers if isinstance(review_record.papers, list) else [],
        "cited_papers_count": len(review_record.papers) if isinstance(review_record.papers, list) else 0,
        "created_at": review_record.created_at.isoformat() if review_record.created_at else "",
        "statistics": review_record.statistics if isinstance(review_record.statistics, dict) else {},
        "record_id": review_record.id,
        "is_public": is_public,
        "is_paid": getattr(review_record, 'is_paid', False)
    }

    # 如果指定了非 IEEE 格式，重新格式化参考文献
    if format != "ieee" and "## References" in result_data["review"]:
        from services.citation_formatter import format_references

        papers = result_data["papers"]
        if papers:
            parts = result_data["review"].split("## References", 1)
            content_part = parts[0]
            new_references = format_references(papers, format)
            result_data["review"] = content_part + "## References\n\n" + new_references

    return {
        "success": True,
        "data": result_data
    }


# ==================== 查找文献接口（不生成综述）====================

class SearchPapersOnlyRequest(BaseModel):
    """查找文献请求"""
    topic: str = Field(..., description="论文主题", min_length=1)
    target_count: int = Field(50, description="目标文献数量", ge=10, le=100)
    search_years: int = Field(10, description="搜索年份范围", ge=5, le=30)


@app.post("/api/search-papers-only")
async def search_papers_only(request: SearchPapersOnlyRequest):
    """
    查找文献（不生成综述）

    使用 PaperSearchAgent 搜索文献并返回结果。
    """
    try:
        executor = ReviewTaskExecutor()

        params = {
            'target_count': request.target_count,
            'search_years': request.search_years,
        }

        result = await executor.search_papers_only(
            topic=request.topic,
            params=params
        )

        return {
            "success": True,
            "message": "文献查找完成",
            "data": result
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 参考文献验证接口 ====================

class ValidateRequest(BaseModel):
    review: str = Field(..., description="综述内容")
    papers: List[Dict] = Field(..., description="参考文献列表")

@app.post("/api/validate-review")
async def validate_review(request: ValidateRequest):
    """
    验证参考文献质量

    检查：
    1. 引用数量是否>=50篇
    2. 近5年文献占比是否>=50%
    3. 英文文献占比是否>=30%
    4. 引用顺序是否正确（连续编号）
    """
    try:
        validator = ReferenceValidator()
        result = validator.validate_review(
            review=request.review,
            papers=request.papers
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class CheckCitationOrderRequest(BaseModel):
    text: str = Field(..., description="待检查的文本内容")


@app.post("/api/check-citation-order")
async def check_citation_order(request: CheckCitationOrderRequest):
    """
    检查正文中的引用序号顺序

    检查：
    1. 序号是否按顺序出现（不倒退）
    2. 是否有缺失的序号
    3. 是否有重复的序号
    4. 序号格式是否正确

    不使用大模型，纯正则表达式检查
    """
    try:
        from services.citation_order_checker import CitationOrderChecker

        checker = CitationOrderChecker()
        result = checker.check_order(request.text)

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # 启用热重载，修改代码后自动重启服务
    # reload=True 时必须使用字符串格式的应用路径
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        access_log=True,
        reload_excludes=[".venv", "*.pyc", "__pycache__"]
    )

@app.get("/api/tasks/status")
async def get_tasks_status():
    """
    获取任务系统状态

    返回当前运行中的任务数量、最大并发数等信息
    """
    try:
        running_count = task_manager.get_running_count()
        waiting_count = task_manager.get_waiting_count()
        max_concurrent = task_manager.max_concurrent_tasks

        return {
            "success": True,
            "data": {
                "running_tasks": running_count,
                "waiting_tasks": waiting_count,
                "max_concurrent_tasks": max_concurrent,
                "available_slots": max_concurrent - running_count,
                "total_tasks": len(task_manager._tasks)
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 查找文献历史记录接口 ====================

@app.get("/api/search-history")
async def get_search_history(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    获取查找文献历史记录

    参数：
    - limit: 返回数量限制（默认20）
    - offset: 偏移量（默认0）
    - status: 状态筛选（可选：completed/failed/processing）

    返回：
    - 任务列表，包含各个阶段的数据
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    try:
        from models import ReviewTask
        from models import OutlineGenerationStage, PaperSearchStage, PaperFilterStage
        from database import db

        session_gen = db.get_session()
        session = next(session_gen)
        try:
            # 构建查询 - 只返回当前用户的任务
            query = session.query(ReviewTask)

            # 通过关联的 review_record 筛选当前用户的任务
            from models import ReviewRecord
            query = query.join(ReviewRecord, ReviewTask.review_record_id == ReviewRecord.id).filter(
                ReviewRecord.user_id == user_id
            )

            if status:
                query = query.filter(ReviewTask.status == status)

            # 按创建时间倒序排列
            query = query.order_by(ReviewTask.created_at.desc())

            # 分页
            total = query.count()
            tasks = query.offset(offset).limit(limit).all()

            # 构建结果
            results = []
            for task in tasks:
                task_dict = task.to_dict()

                # 获取各个阶段的数据
                outline_stage = session.query(OutlineGenerationStage).filter_by(
                    task_id=task.id
                ).first()
                search_stage = session.query(PaperSearchStage).filter_by(
                    task_id=task.id
                ).first()
                filter_stage = session.query(PaperFilterStage).filter_by(
                    task_id=task.id
                ).first()

                task_dict['stages'] = {
                    'outline': outline_stage.to_dict() if outline_stage else None,
                    'search': search_stage.to_dict() if search_stage else None,
                    'filter': filter_stage.to_dict() if filter_stage else None
                }

                results.append(task_dict)

            return {
                "success": True,
                "data": {
                    "total": total,
                    "offset": offset,
                    "limit": limit,
                    "tasks": results
                }
            }
        finally:
            session.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search-history/{task_id}")
async def get_search_history_detail(
    task_id: str,
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    获取单个查找文献任务的详细记录

    参数：
    - task_id: 任务ID

    返回：
    - 任务的完整信息，包括所有阶段的数据
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    try:
        from models import ReviewTask
        from models import OutlineGenerationStage, PaperSearchStage, PaperFilterStage
        from database import db

        session_gen = db.get_session()
        session = next(session_gen)
        try:
            # 获取任务
            task = session.query(ReviewTask).filter_by(id=task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

            # 验证所有权
            if hasattr(task, 'user_id') and task.user_id and task.user_id != user_id:
                raise HTTPException(status_code=403, detail="该任务不属于您，无法访问")

            # 如果任务有关联的记录，也需要验证
            if task.review_record_id:
                from models import ReviewRecord
                record = session.query(ReviewRecord).filter_by(id=task.review_record_id).first()
                if record and record.user_id and record.user_id != user_id:
                    raise HTTPException(status_code=403, detail="该任务不属于您，无法访问")

            task_dict = task.to_dict()

            # 获取各个阶段的数据
            outline_stage = session.query(OutlineGenerationStage).filter_by(
                task_id=task_id
            ).first()
            search_stage = session.query(PaperSearchStage).filter_by(
                task_id=task_id
            ).first()
            filter_stage = session.query(PaperFilterStage).filter_by(
                task_id=task_id
            ).first()

            task_dict['stages'] = {
                'outline': outline_stage.to_dict() if outline_stage else None,
                'search': search_stage.to_dict() if search_stage else None,
                'filter': filter_stage.to_dict() if filter_stage else None
            }

            return {
                "success": True,
                "data": task_dict
            }
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}/search-sources")
async def get_task_search_sources(
    task_id: str,
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    获取任务的搜索来源统计（关键词-文献对应关系）

    参数：
    - task_id: 任务ID

    返回：
    - 搜索来源统计信息
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    # 验证任务所有权
    from models import ReviewTask, ReviewRecord
    db_session = next(get_db())
    try:
        task = db_session.query(ReviewTask).filter_by(id=task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 验证所有权
        if task.review_record_id:
            record = db_session.query(ReviewRecord).filter_by(id=task.review_record_id).first()
            if record and record.user_id and record.user_id != user_id:
                raise HTTPException(status_code=403, detail="该任务不属于您，无法访问")
    finally:
        db_session.close()

    try:
        from services.stage_recorder import stage_recorder
        result = stage_recorder.get_paper_search_sources(task_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search-history/{task_id}/search-sources")
async def get_search_history_search_sources(
    task_id: str,
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    获取查找文献历史记录的搜索来源统计

    参数：
    - task_id: 任务ID

    返回：
    - 搜索来源统计信息
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    # 验证任务所有权
    from models import ReviewTask, ReviewRecord
    db_session = next(get_db())
    try:
        task = db_session.query(ReviewTask).filter_by(id=task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 验证所有权
        if task.review_record_id:
            record = db_session.query(ReviewRecord).filter_by(id=task.review_record_id).first()
            if record and record.user_id and record.user_id != user_id:
                raise HTTPException(status_code=403, detail="该任务不属于您，无法访问")
    finally:
        db_session.close()

    try:
        from services.stage_recorder import stage_recorder
        result = stage_recorder.get_paper_search_sources(task_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
