"""
支付相关数据模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional

# 使用独立的 Base，由 main.py 通过 engine 创建表
PaymentBase = declarative_base()


class Subscription(PaymentBase):
    """订阅订单模型"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    order_no = Column(String(64), unique=True, nullable=False, index=True, comment="商户订单号")
    plan_type = Column(String(32), nullable=False, comment="套餐类型: single(体验包1篇)/semester(基础包3篇)/yearly(进阶包6篇)/unlock(单次解锁)")
    amount = Column(Float, nullable=False, comment="订单金额")
    status = Column(String(20), default="pending", comment="订单状态: pending/paid/cancelled")
    payment_method = Column(String(20), nullable=True, comment="支付方式: alipay")
    payment_time = Column(DateTime(timezone=True), nullable=True, comment="支付时间")
    trade_no = Column(String(64), nullable=True, comment="支付宝交易号")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="会员到期时间")
    record_id = Column(Integer, nullable=True, comment="关联的综述记录ID（unlock类型时使用）")
    extra_data = Column(Text, nullable=True, comment="额外数据（JSON格式）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_no": self.order_no,
            "plan_type": self.plan_type,
            "amount": self.amount,
            "status": self.status,
            "payment_method": self.payment_method,
            "payment_time": self.payment_time.isoformat() if self.payment_time else None,
            "trade_no": self.trade_no,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PaymentLog(PaymentBase):
    """支付日志模型"""
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, nullable=True, comment="订阅ID")
    user_id = Column(Integer, nullable=True, comment="用户ID")
    action = Column(String(50), nullable=False, comment="操作类型")
    request_data = Column(Text, nullable=True, comment="请求数据")
    response_data = Column(Text, nullable=True, comment="响应数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


# ==================== Pydantic Schemas ====================

class SubscriptionCreate(BaseModel):
    """创建订阅请求"""
    plan_type: str  # single(体验包1篇)/semester(基础包3篇)/yearly(进阶包6篇)/unlock(单次解锁)


class PaymentCreateResponse(BaseModel):
    """创建支付响应"""
    order_no: str
    pay_url: str
    amount: float
    expires_in: int = 900  # 15分钟


class MembershipInfo(BaseModel):
    """会员信息"""
    membership_type: str = "free"  # free / premium
    expires_at: Optional[str] = None
    days_remaining: Optional[int] = None


# ==================== 套餐定义 ====================

PLANS = [
    {
        "type": "single",
        "name": "单次体验",
        "price": 29.8,
        "credits": 1,
        "recommended": False,
        "features": [
            "1 篇综述生成额度",
            "在线查看 + PDF 导出",
        ]
    },
    {
        "type": "semester",
        "name": "基础包",
        "price": 59.8,
        "credits": 3,
        "recommended": True,
        "features": [
            "3 篇综述生成额度",
            "在线查看 + PDF 导出",
            "低至 ¥19.9/篇",
        ]
    },
    {
        "type": "yearly",
        "name": "进阶包",
        "price": 99.8,
        "credits": 6,
        "recommended": False,
        "features": [
            "6 篇综述生成额度",
            "在线查看 + PDF 导出",
            "低至 ¥16.6/篇",
        ]
    },
]

PLAN_CREDITS = {p["type"]: p["credits"] for p in PLANS}
PLAN_DURATION = {p["type"]: 365 for p in PLANS}  # 额度不过期，保持兼容
