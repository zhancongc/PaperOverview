"""
积分系统 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from services.credit_service import CreditService
from authkit.routers.auth import get_current_user
from authkit.models.schemas import UserResponse
from database import get_db

router = APIRouter(prefix="/api/credits", tags=["积分系统"])


@router.get("/balance")
async def get_credit_balance(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取积分余额"""
    service = CreditService(db)
    balance = service.get_user_balance(current_user.id)

    return {
        "success": True,
        "data": {
            "balance": balance,
            "can_generate": balance >= 10  # 是否足够生成一篇综述
        }
    }


@router.get("/packages")
async def get_credit_packages(
    db: Session = Depends(get_db)
):
    """获取积分套餐列表"""
    service = CreditService(db)
    packages = service.get_packages()

    return {
        "success": True,
        "data": packages
    }


@router.post("/purchase")
async def purchase_credits(
    package_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    购买积分套餐

    - **package_id**: 套餐ID（1-5）
    """
    service = CreditService(db)
    success, message, order_no = service.create_order(current_user.id, package_id)

    if success:
        # 实际项目中这里会调用支付接口
        return {
            "success": True,
            "message": message,
            "data": {
                "order_no": order_no,
                "payment_url": f"/pay/{order_no}"  # 支付链接
            }
        }
    else:
        raise HTTPException(status_code=400, detail=message)


@router.get("/history")
async def get_transaction_history(
    limit: int = 20,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取积分交易记录"""
    service = CreditService(db)
    history = service.get_transaction_history(current_user.id, limit)

    return {
        "success": True,
        "data": history
    }


@router.get("/cost")
async def get_credit_costs():
    """获取积分消耗规则"""
    from models.credits import CREDIT_COSTS

    return {
        "success": True,
        "data": {
            "generate_review": CREDIT_COSTS.get("generate_review", 10),
            "export_review": CREDIT_COSTS.get("export_review", 0),
            "save_draft": CREDIT_COSTS.get("save_draft", 0),
            "description": {
                "generate_review": "生成一篇综述需要 10 积分",
                "export_review": "导出综述免费",
                "save_draft": "保存草稿免费"
            }
        }
    }


@router.post("/demo/add")
async def demo_add_credits(
    amount: int = 100,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    [演示] 添加测试积分

    仅用于演示环境，生产环境需要移除此接口
    """
    # 检查是否是演示环境
    import os
    if os.getenv("DEMO_MODE") != "true":
        raise HTTPException(status_code=403, detail="此接口仅在演示模式可用")

    service = CreditService(db)
    success, message = service.add_credits(
        user_id=current_user.id,
        amount=amount,
        transaction_type="reward",
        description="演示环境赠送积分"
    )

    if success:
        balance = service.get_user_balance(current_user.id)
        return {
            "success": True,
            "message": f"已添加 {amount} 积分",
            "data": {"balance": balance}
        }
    else:
        raise HTTPException(status_code=400, detail=message)
