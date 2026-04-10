"""
订阅管理 API 路由
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..models.payment import (
    Subscription, PaymentLog, Plan, get_plans_from_db, PLAN_DURATION, PLAN_CREDITS,
    SubscriptionCreate, PaymentCreateResponse, MembershipInfo,
)
from ..models.schemas import UserResponse
from ..services.payment_config import get_payment_service, get_payment_config
from ..core.security import decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/subscription", tags=["订阅管理"])

security = HTTPBearer()

# 数据库依赖（需要在主应用中提供）
_default_get_db = None


def get_db():
    global _default_get_db
    if _default_get_db is not None:
        yield from _default_get_db()
        return
    raise NotImplementedError("请在主应用中实现 set_get_db_sub() 函数")


def set_get_db(get_db_func):
    global _default_get_db
    _default_get_db = get_db_func


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    from ..models import User
    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return UserResponse.from_user(user)


def _get_user_model(user_id: int, db: Session):
    """获取 User ORM 对象"""
    from ..models import User
    return db.query(User).filter(User.id == user_id).first()


def _add_credits(user_id: int, plan_type: str, db: Session):
    """支付成功后为用户增加综述额度"""
    user = _get_user_model(user_id, db)
    if not user:
        return
    credits_to_add = PLAN_CREDITS.get(plan_type, 1)
    current_credits = user.get_meta("review_credits", 0)
    user.set_meta("review_credits", current_credits + credits_to_add)
    user.set_meta("has_purchased", True)
    db.commit()
    logger.info(f"用户 {user_id} 获得 {credits_to_add} 篇付费额度，当前付费 {current_credits + credits_to_add}")


@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    """获取套餐列表"""
    plans = get_plans_from_db(db)
    return {"plans": plans}


@router.post("/create", response_model=PaymentCreateResponse)
def create_subscription(
    data: SubscriptionCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建订阅订单并生成支付链接"""
    user_id = current_user.id

    # 从数据库获取套餐列表
    plans = get_plans_from_db(db)
    plan = next((p for p in plans if p["type"] == data.plan_type), None)
    if not plan:
        raise HTTPException(status_code=400, detail="套餐不存在")

    # 生成订单号
    order_no = f"AO{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

    # 创建订阅记录
    subscription = Subscription(
        user_id=user_id,
        order_no=order_no,
        plan_type=data.plan_type,
        amount=plan["price"],
        status="pending",
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    # 记录日志
    log = PaymentLog(
        subscription_id=subscription.id,
        user_id=user_id,
        action="create",
        request_data=f"plan_type={data.plan_type}, amount={plan['price']}",
    )
    db.add(log)
    db.commit()

    try:
        config = get_payment_config()
        alipay = get_payment_service()
        subject = f"AutoOverview-{plan['name']}"

        pay_url = alipay.create_order(
            out_trade_no=order_no,
            total_amount=plan["price"],
            subject=subject,
            return_url=f"{config['backend_url']}/api/payment/return",
            notify_url=f"{config['backend_url']}/api/payment/webhook/notify",
        )

        if not pay_url:
            raise HTTPException(status_code=500, detail="创建支付订单失败")

        # 记录成功日志
        log = PaymentLog(
            subscription_id=subscription.id,
            user_id=user_id,
            action="create_success",
            response_data=f"pay_url={pay_url[:100]}...",
        )
        db.add(log)
        db.commit()

        return PaymentCreateResponse(
            order_no=order_no,
            pay_url=pay_url,
            amount=plan["price"],
        )

    except RuntimeError as e:
        logger.error(f"支付服务未初始化: {str(e)}")
        raise HTTPException(status_code=500, detail="支付服务暂时不可用")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建支付订单失败: {str(e)}")
        log = PaymentLog(
            subscription_id=subscription.id,
            user_id=user_id,
            action="create_failed",
            response_data=str(e),
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=500, detail="创建支付订单失败，请稍后重试或联系客服")


@router.get("/query/{order_no}")
def query_subscription(
    order_no: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询订单支付状态"""
    subscription = db.query(Subscription).filter(
        Subscription.order_no == order_no,
        Subscription.user_id == current_user.id,
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="订单不存在")

    if subscription.status == "paid":
        return {
            "status": "paid",
            "payment_time": subscription.payment_time.isoformat() if subscription.payment_time else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        }

    # 主动查询支付状态
    try:
        alipay = get_payment_service()
        result = alipay.query_order(order_no)

        if result and result.get("trade_status") == "TRADE_SUCCESS":
            subscription.status = "paid"
            subscription.payment_method = "alipay"
            subscription.payment_time = datetime.now()
            subscription.trade_no = result.get("trade_no", "")

            # 增加综述额度
            _add_credits(current_user.id, subscription.plan_type, db)

            db.commit()

            return {
                "status": "paid",
                "payment_time": subscription.payment_time.isoformat() if subscription.payment_time else None,
            }

        return {"status": subscription.status}

    except Exception as e:
        logger.error(f"查询订单状态失败: {str(e)}")
        return {"status": subscription.status}


@router.get("/membership", response_model=MembershipInfo)
def get_membership_info(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户会员信息"""
    user = _get_user_model(current_user.id, db)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    membership_type = user.get_meta("membership_type", "free")
    expires_at_str = user.get_meta("membership_expires_at")

    days_remaining = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at < datetime.now():
                membership_type = "free"
                user.set_meta("membership_type", "free")
                user.set_meta("membership_expires_at", None)
                db.commit()
                expires_at_str = None
            else:
                days_remaining = max(0, (expires_at - datetime.now()).days)
        except Exception as e:
            logger.error("Failed to parse membership expires_at '%s': %s", expires_at_str, e)

    return MembershipInfo(
        membership_type=membership_type,
        expires_at=expires_at_str,
        days_remaining=days_remaining,
    )
