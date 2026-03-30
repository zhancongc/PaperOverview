"""
FastAPI 主应用
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from datetime import datetime

from database import db, get_db
from models import ReviewRecord
from services.paper_search import PaperSearchService
from services.paper_filter import PaperFilterService
from services.review_generator import ReviewGeneratorService

load_dotenv()

app = FastAPI(title="论文综述生成器 API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求模型
class GenerateRequest(BaseModel):
    topic: str = Field(..., description="论文主题", min_length=1)
    target_count: int = Field(50, description="目标文献数量", ge=10, le=100)
    recent_years_ratio: float = Field(0.5, description="近5年占比", ge=0.1, le=1.0)
    english_ratio: float = Field(0.3, description="英文文献占比", ge=0.1, le=1.0)


class GenerateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


# 全局服务实例
search_service = PaperSearchService()
filter_service = PaperFilterService()


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库连接"""
    db.connect()


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


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_review(
    request: GenerateRequest,
    db_session: Session = Depends(get_db)
):
    """生成文献综述接口"""
    record = ReviewRecord(
        topic=request.topic,
        review="",
        papers=[],
        statistics={},
        target_count=request.target_count,
        recent_years_ratio=request.recent_years_ratio,
        english_ratio=request.english_ratio,
        status="processing"
    )
    db_session.add(record)
    db_session.commit()

    try:
        # 1. 搜索文献
        papers = await search_service.search_papers(
            query=request.topic,
            years_ago=10,
            limit=200
        )

        if not papers:
            record.status = "failed"
            record.error_message = f'未找到关于「{request.topic}」的相关文献'
            db_session.commit()
            return GenerateResponse(
                success=False,
                message=record.error_message
            )

        # 2. 筛选文献
        filtered_papers = filter_service.filter_and_sort(
            papers=papers,
            target_count=request.target_count,
            recent_years_ratio=request.recent_years_ratio,
            english_ratio=request.english_ratio
        )

        # 3. 获取统计信息
        stats = filter_service.get_statistics(filtered_papers)

        # 4. 生成综述
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")

        generator = ReviewGeneratorService(api_key=api_key)
        review = await generator.generate_review(
            topic=request.topic,
            papers=filtered_papers
        )

        # 5. 保存记录
        record.review = review
        record.papers = filtered_papers
        record.statistics = stats
        record.status = "success"
        db_session.commit()

        return GenerateResponse(
            success=True,
            message="文献综述生成成功",
            data={
                "id": record.id,
                "topic": request.topic,
                "review": review,
                "papers": filtered_papers,
                "statistics": stats,
                "created_at": record.created_at.isoformat()
            }
        )

    except Exception as e:
        record.status = "failed"
        record.error_message = str(e)
        db_session.commit()
        return GenerateResponse(
            success=False,
            message=f"生成失败: {str(e)}"
        )


@app.get("/api/records")
async def get_records(
    skip: int = 0,
    limit: int = 20,
    db_session: Session = Depends(get_db)
):
    """获取生成记录列表"""
    records = db_session.query(ReviewRecord).order_by(
        ReviewRecord.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "success": True,
        "count": len(records),
        "records": [r.to_dict() for r in records]
    }


@app.get("/api/records/{record_id}")
async def get_record(
    record_id: int,
    db_session: Session = Depends(get_db)
):
    """获取单条记录详情"""
    record = db_session.query(ReviewRecord).filter(
        ReviewRecord.id == record_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return {
        "success": True,
        "record": record.to_dict()
    }


@app.delete("/api/records/{record_id}")
async def delete_record(
    record_id: int,
    db_session: Session = Depends(get_db)
):
    """删除记录"""
    record = db_session.query(ReviewRecord).filter(
        ReviewRecord.id == record_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    db_session.delete(record)
    db_session.commit()

    return {"success": True, "message": "删除成功"}


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    return {
        "status": "ok",
        "deepseek_configured": bool(api_key)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
