"""
FastAPI 主应用
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import quote

from database import db, get_db
from models import ReviewRecord
from services.scholarflux_wrapper import ScholarFlux
from services.smart_paper_search import SmartPaperSearchService
from services.paper_filter import PaperFilterService
from services.review_generator import ReviewGeneratorService
from services.topic_analyzer import ThreeCirclesReviewGenerator
from services.hybrid_classifier import FrameworkGenerator
from services.docx_generator import DocxGenerator
from services.reference_validator import ReferenceValidator
from services.review_record_service import ReviewRecordService
from services.task_manager import TaskManager, TaskStatus, task_manager
from services.review_task_executor import ReviewTaskExecutor
from config import Config, UserConfig

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    db.connect()
    # 创建数据库表
    from models import Base
    db.create_tables()
    print("[Startup] 数据库表已创建/更新")
    yield
    # 关闭时执行
    print("[Shutdown] 应用关闭")

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

# 请求模型
class TopicRequest(BaseModel):
    topic: str = Field(..., description="论文题目", min_length=1)

class GenerateRequest(BaseModel):
    # 必填参数
    topic: str = Field(..., description="论文主题", min_length=1)

    # 基本配置（有默认值）
    target_count: int = Field(50, description="目标文献数量", ge=10, le=100)
    recent_years_ratio: float = Field(0.5, description="近5年占比", ge=0.1, le=1.0)
    english_ratio: float = Field(0.3, description="英文文献占比", ge=0.1, le=1.0)

    # 高级配置（可选，有默认值）
    search_years: int = Field(10, description="搜索年份范围", ge=5, le=30)
    max_search_queries: int = Field(8, description="最多搜索查询数", ge=1, le=20)

class GenerateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

class ExportRequest(BaseModel):
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
    db_session: Session = Depends(get_db)
):
    """获取生成记录列表"""
    records = record_service.list_records(db_session, skip, limit)

    return {
        "success": True,
        "count": len(records),
        "records": [record_service.record_to_dict(r) for r in records]
    }

@app.get("/api/records/{record_id}")
async def get_record(
    record_id: int,
    db_session: Session = Depends(get_db)
):
    """获取单条记录详情"""
    record = record_service.get_record(db_session, record_id)

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return {
        "success": True,
        "record": record_service.record_to_dict(record)
    }

@app.delete("/api/records/{record_id}")
async def delete_record(
    record_id: int,
    db_session: Session = Depends(get_db)
):
    """删除记录"""
    deleted = record_service.delete_record(db_session, record_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")

    return {"success": True, "message": "删除成功"}

@app.post("/api/records/export")
async def export_review_docx(
    request: ExportRequest,
    db_session: Session = Depends(get_db)
):
    """
    导出文献综述为 Word 文档

    接收 record_id，从数据库获取数据并返回 .docx 文件
    """
    record = record_service.get_record(db_session, request.record_id)

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    try:
        generator = DocxGenerator()
        docx_bytes = generator.generate_review_docx(
            topic=record.topic,
            review=record.review,
            papers=record.papers,
            statistics=record.statistics
        )

        from fastapi.responses import Response

        # 生成文件名：文献综述-论文标题-yymmdd-HHMMSS.docx
        from datetime import datetime
        now = datetime.now()
        timestamp = now.strftime("%y%m%d-%H%M%S")

        # 清理主题中的特殊字符
        safe_topic = record.topic.replace('/', '-').replace('\\', '-').replace(':', '-')
        safe_topic = safe_topic.replace('（', '-').replace('）', '-')
        safe_topic = safe_topic.replace('<', '-').replace('>', '-').replace('|', '-')
        safe_topic = safe_topic.replace('"', '-').replace('*', '-').replace('?', '-')
        # 限制主题长度，避免文件名过长
        safe_topic = safe_topic[:50]

        filename = f"文献综述-{safe_topic}-{timestamp}.docx"

        # 使用 URL 编码处理中文文件名
        encoded_filename = quote(filename, safe='')
        content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}"

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": content_disposition
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    return {
        "status": "ok",
        "deepseek_configured": bool(api_key)
    }


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

    print(f"[API] 收到分类请求: {request.topic}")
    start = time.time()

    try:
        from services.hybrid_classifier import FrameworkGenerator

        gen = FrameworkGenerator()
        result = await gen.generate_framework(request.topic)

        elapsed = time.time() - start
        print(f"[API] 大模型分类成功，耗时 {elapsed:.2f}秒，类型: {result['type']}")

        return {
            "success": True,
            "message": "题目分类完成",
            "data": result
        }
    except Exception as e:
        elapsed = time.time() - start
        print(f"[DEBUG] 大模型分类错误 (耗时{elapsed:.2f}秒): {e}")
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

    根据题目类型自动选择合适的分析方法
    - 应用型：三圈交集分析
    - 评价型：金字塔式分析
    - 其他：通用分析
    """
    try:
        from services.hybrid_classifier import FrameworkGenerator
        gen = FrameworkGenerator()
        framework = await gen.generate_framework(request.topic, enable_llm_validation=True)

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
                'analysis': framework,  # 使用正确的分类数据结构
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
    db_session: Session = Depends(get_db)
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

    try:
        # 创建任务
        task = task_manager.create_task(
            topic=request.topic,
            params={
                "target_count": request.target_count,
                "recent_years_ratio": request.recent_years_ratio,
                "english_ratio": request.english_ratio,
                "search_years": request.search_years,
                "max_search_queries": request.max_search_queries,
            }
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
async def get_task_status(task_id: str):
    """
    获取任务状态和结果

    前端轮询此接口获取任务进度和结果
    """
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    response_data = task.to_dict()

    # 如果任务完成，添加结果数据
    if task.status == TaskStatus.COMPLETED and task.result:
        response_data["result"] = task.result

    return {
        "success": True,
        "data": response_data
    }


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
    # access_log=False 禁用 HTTP 请求日志，减少日志噪音
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, access_log=False)

@app.get("/api/tasks/status")
async def get_tasks_status():
    """
    获取任务系统状态

    返回当前运行中的任务数量、最大并发数等信息
    """
    try:
        running_count = task_manager.get_running_count()
        max_concurrent = task_manager.max_concurrent_tasks

        return {
            "success": True,
            "data": {
                "running_tasks": running_count,
                "max_concurrent_tasks": max_concurrent,
                "available_slots": max_concurrent - running_count,
                "total_tasks": len(task_manager._tasks)
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
