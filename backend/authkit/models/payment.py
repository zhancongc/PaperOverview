"""
支付相关数据模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional, List

# 使用独立的 Base，由 main.py 通过 engine 创建表
PaymentBase = declarative_base()


class Plan(PaymentBase):
    """套餐价格模型"""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(32), unique=True, nullable=False, comment="套餐类型: single/semester/yearly/unlock")
    name = Column(String(50), nullable=False, comment="套餐名称")
    price = Column(Float, nullable=False, comment="价格（元）")
    credits = Column(Integer, nullable=False, comment="包含的综述额度数量")
    recommended = Column(Boolean, default=False, comment="是否推荐")
    features = Column(Text, nullable=True, comment="套餐特性（JSON格式）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="显示顺序")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "price": self.price,
            "credits": self.credits,
            "recommended": self.recommended,
            "features": self.parse_features() if self.features else [],
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def parse_features(self):
        """解析 JSON 格式的特性列表"""
        if not self.features:
            return []
        import json
        try:
            return json.loads(self.features)
        except:
            return []


class Subscription(PaymentBase):
    """订阅订单模型"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    order_no = Column(String(64), unique=True, nullable=False, index=True, comment="商户订单号")
    plan_type = Column(String(32), nullable=False, comment="套餐类型: single(体验包1篇)/semester(标准包3篇)/yearly(进阶包6篇)/unlock(单次解锁)")
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
    plan_type: str  # single(体验包1篇)/semester(标准包3篇)/yearly(进阶包6篇)/unlock(单次解锁)


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

# 默认套餐配置（用于初始化数据库）
DEFAULT_PLANS = [
    {
        "type": "single",
        "name": "体验包",
        "price": 29.8,
        "credits": 1,
        "recommended": False,
        "sort_order": 1,
        "features": [
            "1 篇综述生成额度",
            "在线查看 + PDF 导出",
        ]
    },
    {
        "type": "semester",
        "name": "标准包",
        "price": 69.8,
        "credits": 3,
        "recommended": True,
        "sort_order": 2,
        "features": [
            "3 篇综述生成额度",
            "在线查看 + PDF 导出",
            "约 ¥23.2/篇",
        ]
    },
    {
        "type": "yearly",
        "name": "进阶包",
        "price": 109.8,
        "credits": 6,
        "recommended": False,
        "sort_order": 3,
        "features": [
            "6 篇综述生成额度",
            "在线查看 + PDF 导出",
            "约 ¥18.3/篇",
        ]
    },
]

# 保持向后兼容的常量（从数据库读取）
PLANS = DEFAULT_PLANS
PLAN_CREDITS = {p["type"]: p["credits"] for p in PLANS}
PLAN_DURATION = {p["type"]: 365 for p in PLANS}  # 额度不过期，保持兼容


def get_plans_from_db(session):
    """
    从数据库获取启用的套餐列表

    Args:
        session: 数据库会话

    Returns:
        套餐列表
    """
    plans = session.query(Plan).filter_by(is_active=True).order_by(Plan.sort_order).all()
    if plans:
        return [plan.to_dict() for plan in plans]
    # 如果数据库中没有套餐，返回默认配置
    return DEFAULT_PLANS


def init_plans_in_db(session):
    """
    初始化套餐数据到数据库

    Args:
        session: 数据库会话
    """
    existing_plans = session.query(Plan).count()
    if existing_plans > 0:
        return  # 已经初始化过

    import json
    for plan_data in DEFAULT_PLANS:
        plan = Plan(
            type=plan_data["type"],
            name=plan_data["name"],
            price=plan_data["price"],
            credits=plan_data["credits"],
            recommended=plan_data["recommended"],
            features=json.dumps(plan_data["features"]),  # 存储 JSON
            sort_order=plan_data.get("sort_order", 0)
        )
        session.add(plan)
    session.commit()
    print("[Init] 已初始化套餐数据到数据库")
