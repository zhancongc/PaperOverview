"""
支付宝异步通知 (Webhook)
"""
import logging

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..models.payment import Subscription, PaymentLog, PLAN_DURATION
from ..services.payment_config import get_payment_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payment/webhook", tags=["支付Webhook"])

# 数据库依赖
_default_get_db = None


def get_db():
    global _default_get_db
    if _default_get_db is not None:
        yield from _default_get_db()
        return
    raise NotImplementedError("请在主应用中实现 set_get_db_webhook()")


def set_get_db(get_db_func):
    global _default_get_db
    _default_get_db = get_db_func


def verify_alipay_notification(params: dict, alipay_public_key: str) -> bool:
    """验证支付宝异步通知签名"""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        sign = params.pop('sign', None)
        sign_type = params.get('sign_type', 'RSA2')

        if not sign:
            return False

        # 过滤并排序参数
        filtered = {k: v for k, v in params.items() if k != 'sign_type' and v not in [None, '']}
        sorted_params = sorted(filtered.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # 格式化公钥
        key = alipay_public_key.strip()
        if not key.startswith('-----BEGIN'):
            key = f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"

        public_key = load_pem_public_key(key.encode())
        import base64
        signature = base64.b64decode(sign)

        if sign_type == 'RSA2':
            public_key.verify(signature, query_string.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())
        else:
            public_key.verify(signature, query_string.encode('utf-8'), padding.PKCS1v15(), hashes.SHA1())

        return True
    except Exception as e:
        logger.error(f"验证签名失败: {str(e)}")
        return False


def process_payment(params: dict, db: Session) -> str:
    """处理支付通知核心逻辑"""
    try:
        trade_no = params.get('trade_no')
        out_trade_no = params.get('out_trade_no')
        trade_status = params.get('trade_status')
        total_amount = params.get('total_amount')

        logger.info(f"订单 {out_trade_no} 支付状态: {trade_status}")

        sub = db.query(Subscription).filter(Subscription.order_no == out_trade_no).first()
        if not sub:
            logger.warning(f"订单不存在: {out_trade_no}")
            return "fail"

        if sub.status == "paid":
            logger.info(f"订单 {out_trade_no} 已处理，跳过")
            return "success"

        if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            logger.warning(f"交易状态异常: {trade_status}")
            return "fail"

        if abs(float(total_amount) - sub.amount) > 0.01:
            logger.error(f"金额不匹配: 期望 {sub.amount}, 实际 {total_amount}")
            return "fail"

        # 更新订单
        sub.status = "paid"
        sub.payment_method = "alipay"
        sub.payment_time = datetime.now()
        sub.trade_no = trade_no

        # 根据订单类型处理不同的逻辑
        if sub.plan_type == "unlock":
            # 单次解锁：解锁指定的综述
            if sub.record_id:
                from models import ReviewRecord
                record = db.query(ReviewRecord).filter(ReviewRecord.id == sub.record_id).first()
                if record:
                    record.is_paid = True
                    logger.info(f"解锁综述 {sub.record_id} for user {sub.user_id}")
                else:
                    logger.warning(f"综述记录 {sub.record_id} 不存在")
        else:
            # 套餐购买：增加综述额度
            from ..models.payment import PLAN_CREDITS
            from ..models import User
            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                credits_to_add = PLAN_CREDITS.get(sub.plan_type, 1)
                current_credits = user.get_meta("review_credits", 0)
                user.set_meta("review_credits", current_credits + credits_to_add)
                user.set_meta("has_purchased", True)
                logger.info(f"用户 {user.id} 获得 {credits_to_add} 篇付费额度，当前付费 {current_credits + credits_to_add}")

        db.commit()

        log = PaymentLog(
            subscription_id=sub.id, user_id=sub.user_id,
            action="notify_success",
            request_data=f"trade_no={trade_no}, status={trade_status}, amount={total_amount}",
            response_data="订单状态更新成功",
        )
        db.add(log)
        db.commit()

        logger.info(f"✅ 订单 {out_trade_no} 处理成功")
        return "success"

    except Exception as e:
        logger.error(f"处理支付通知失败: {str(e)}")
        db.rollback()
        return "fail"


@router.post("/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    """支付宝异步通知接口"""
    try:
        form_data = await request.form()
        params = dict(form_data)

        logger.info(f"收到支付宝异步通知: order={params.get('out_trade_no')}, status={params.get('trade_status')}")

        config = get_payment_config()
        alipay_public_key = config.get("alipay_public_key", "")

        if alipay_public_key and not config.get("is_dev", True):
            params_copy = params.copy()
            if not verify_alipay_notification(params_copy, alipay_public_key):
                logger.warning("签名验证失败")
                return "fail"

        result = process_payment(params, db)
        return result

    except Exception as e:
        logger.error(f"处理支付宝通知失败: {str(e)}")
        return "fail"
