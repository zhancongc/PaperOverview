"""
在综述生成任务中集成积分系统

将以下代码添加到 ReviewTaskExecutor.execute_task 方法开头
"""

# 在 execute_task 方法开头添加积分检查
async def execute_task(self, task_id: str, db_session: Session):
    """
    执行综述生成任务
    """
    task = task_manager.get_task(task_id)
    if not task:
        print(f"[TaskExecutor] 任务不存在: {task_id}")
        return

    # ========== 新增：积分检查 ==========
    user_id = task.params.get('user_id')  # 从任务参数中获取用户ID

    if user_id:
        from services.credit_service import CreditService

        credit_service = CreditService(db_session)

        # 检查积分余额
        balance = credit_service.get_user_balance(user_id)
        required_credits = 10  # 生成一篇综述需要10积分

        if balance < required_credits:
            # 积分不足
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=f"积分不足，需要 {required_credits} 积分，当前余额 {balance} 积分"
            )
            print(f"[TaskExecutor] 积分不足: 用户 {user_id}, 需要 {required_credits}, 当前 {balance}")
            return

        # 扣除积分
        success, message = credit_service.consume_credits(
            user_id=user_id,
            action="generate_review",
            related_id=task_id
        )

        if not success:
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=f"积分扣除失败: {message}"
            )
            print(f"[TaskExecutor] 积分扣除失败: {message}")
            return

        print(f"[TaskExecutor] 积分扣除成功: 用户 {user_id}, 消耗 {required_credits} 积分")

        # 保存扣除的积分信息，用于失败时退还
        task.credits_consumed = required_credits
        task.credits_user_id = user_id

    # ========== 原有逻辑继续 ==========
    # 尝试获取执行槽位（并发控制）
    acquired = await task_manager.acquire_slot(task_id)
    # ... 后续代码


# 在任务失败时退还积分
def handle_task_failure(self, task_id: str, error_message: str):
    """处理任务失败，退还积分"""
    task = task_manager.get_task(task_id)

    if task and hasattr(task, 'credits_consumed'):
        user_id = getattr(task, 'credits_user_id', None)
        consumed = getattr(task, 'credits_consumed', 0)

        if user_id and consumed > 0:
            from database import db
            from services.credit_service import CreditService

            with next(db.get_session()) as session:
                credit_service = CreditService(session)

                # 退还积分
                success, message = credit_service.add_credits(
                    user_id=user_id,
                    amount=consumed,
                    transaction_type="refund",
                    description=f"综述生成失败退款：{error_message}",
                    related_id=task_id
                )

                if success:
                    print(f"[TaskExecutor] 积分退还成功: 用户 {user_id}, 退还 {consumed} 积分")
                else:
                    print(f"[TaskExecutor] 积分退还失败: {message}")


# 在前端调用时传递用户ID
async def submit_review_task(request: GenerateRequest, user_id: int):
    """
    提交综述生成任务（带用户ID）

    前端需要传递当前登录用户的ID
    """
    task = task_manager.create_task(
        topic=request.topic,
        params={
            "research_direction_id": request.research_direction_id,
            "target_count": request.target_count,
            "recent_years_ratio": request.recent_years_ratio,
            "english_ratio": request.english_ratio,
            "search_years": request.search_years,
            "max_search_queries": request.max_search_queries,
            "user_id": user_id  # 新增：用户ID
        }
    )

    # ... 后续逻辑
