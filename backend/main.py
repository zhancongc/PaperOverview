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
from config import Config, UserConfig

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

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库连接"""
    db.connect()
    # 创建数据库表
    from models import Base
    db.create_tables()
    print("[Startup] 数据库表已创建/更新")

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

# ==================== 智能生成综述接口 ====================

@app.post("/api/smart-generate")
async def smart_generate_review(
    request: GenerateRequest,
    db_session: Session = Depends(get_db)
):
    """
    智能生成文献综述（生成后验证被引用文献质量，不达标则扩大候选池重试）
    """
    # 创建记录
    record = record_service.create_record(
        db_session=db_session,
        topic=request.topic,
        target_count=request.target_count,
        recent_years_ratio=request.recent_years_ratio,
        english_ratio=request.english_ratio
    )

    validator = ReferenceValidator()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    aminer_token = os.getenv("AMINER_API_TOKEN")
    if not api_key:
        record = record_service.update_failure(
            db_session=db_session,
            record=record,
            error_message="DEEPSEEK_API_KEY not configured"
        )
        return GenerateResponse(
            success=False,
            message="API配置错误"
        )

    try:
        # 1. 智能分析题目
        from services.hybrid_classifier import FrameworkGenerator
        gen = FrameworkGenerator()
        framework = await gen.generate_framework(request.topic, enable_llm_validation=True)

        # 2. 初始文献搜索
        all_papers = []
        search_queries_results = []

        search_queries = framework.get('search_queries', [])

        # 使用LLM验证和修复搜索关键词
        if search_queries:
            try:
                from services.hybrid_classifier import HybridTopicClassifier
                classifier = HybridTopicClassifier()
                search_queries = await classifier.validate_and_fix_search_queries(
                    title=request.topic,
                    queries=search_queries
                )
                print(f"[SmartGenerate] LLM验证后的搜索查询: {len(search_queries)} 个")
            except Exception as e:
                print(f"[SmartGenerate] LLM关键词验证失败: {e}，使用原查询")

        if search_queries:
            print(f"[SmartGenerate] 使用智能分析生成的搜索查询: {len(search_queries)} 个")
            print(f"[SmartGenerate] 用户配置: search_years={request.search_years}, max_queries={request.max_search_queries}")

            for query_info in search_queries[:request.max_search_queries]:  # 使用用户配置的查询数量
                query = query_info.get('query', request.topic)
                section = query_info.get('section', '通用')
                lang = query_info.get('lang', None)  # 获取语言标识
                keywords = query_info.get('keywords', None)  # 获取关键词列表
                search_mode = query_info.get('search_mode', None)  # 获取搜索模式

                print(f"[SmartGenerate] 执行查询: {query}, 语言={lang}, 模式={search_mode}, 关键词={keywords}")

                # 根据查询语言选择搜索方式
                papers = await search_service.search(
                    query=query,
                    years_ago=request.search_years,  # 使用用户配置的年份范围
                    limit=50,  # 每个查询50篇
                    lang=lang,  # 传递语言标识
                    keywords=keywords,  # 传递关键词列表
                    search_mode=search_mode  # 传递搜索模式
                )
                print(f"[SmartGenerate] 查询 '{query}' 找到 {len(papers)} 篇")

                search_queries_results.append({
                    'query': query,
                    'section': section,
                    'papers': papers,
                    'citedCount': 0
                })
                all_papers.extend(papers)

        # 补充搜索（确保至少有一些文献）
        if len(all_papers) < 20:
            print(f"[SmartGenerate] 文献数量不足（{len(all_papers)}篇），使用主题补充搜索")
            # 尝试更宽泛的搜索
            additional_papers = await search_service.search(
                query=request.topic,
                years_ago=15,  # 扩大年份范围
                limit=100,
                use_all_sources=True  # 使用所有数据源
            )
            print(f"[SmartGenerate] 补充搜索找到 {len(additional_papers)} 篇")
            all_papers.extend(additional_papers)

        # 去重
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            paper_id = paper.get("id")
            if paper_id not in seen_ids:
                seen_ids.add(paper_id)
                unique_papers.append(paper)
        all_papers = unique_papers
        print(f"[SmartGenerate] 去重后共 {len(all_papers)} 篇文献")

        if not all_papers:
            # 最后尝试：使用更宽泛的搜索
            print(f"[SmartGenerate] 最后尝试：使用题目关键词进行宽泛搜索")
            # 从题目中提取关键词进行搜索
            topic_words = request.topic.replace('基于', '').replace('的研究', '').replace('研究', '')
            topic_words = ' '.join([w for w in topic_words.split() if len(w) > 1])

            if topic_words:
                last_attempt_papers = await search_service.search(
                    query=topic_words,
                    years_ago=20,  # 扩大到20年
                    limit=50,
                    use_all_sources=True
                )
                # 去重后添加
                for paper in last_attempt_papers:
                    paper_id = paper.get("id")
                    if paper_id not in seen_ids:
                        seen_ids.add(paper_id)
                        all_papers.append(paper)
                print(f"[SmartGenerate] 宽泛搜索找到 {len(last_attempt_papers)} 篇（去重后新增）")

        # 如果仍然没有找到任何文献，返回错误
        if not all_papers:
            record = record_service.update_failure(
                db_session=db_session,
                record=record,
                error_message=f'未找到关于「{request.topic}」的相关文献，请尝试更通用的题目描述'
            )
            return GenerateResponse(
                success=False,
                message=record.error_message
            )

        # 3. 提取主题关键词
        topic_keywords = gen.extract_relevance_keywords(framework)

        # 4. 筛选文献（作为候选池）
        search_count = max(request.target_count * 2, 100)
        filtered_papers = filter_service.filter_and_sort(
            papers=all_papers,
            target_count=search_count,
            recent_years_ratio=request.recent_years_ratio,
            english_ratio=request.english_ratio,
            topic_keywords=topic_keywords
        )
        print(f"[SmartGenerate] 筛选后候选池: {len(filtered_papers)} 篇")

        # 如果筛选后文献太少，放宽条件重新筛选
        if len(filtered_papers) < request.target_count:
            print(f"[SmartGenerate] 筛选后文献不足（{len(filtered_papers)} < {request.target_count}），放宽条件")
            # 放宽条件：降低年份和语言比例要求
            filtered_papers = filter_service.filter_and_sort(
                papers=all_papers,
                target_count=search_count,
                recent_years_ratio=0.0,  # 不限制年份
                english_ratio=0.0,  # 不限制语言
                topic_keywords=[]  # 不限制关键词
            )
            print(f"[SmartGenerate] 放宽条件后候选池: {len(filtered_papers)} 篇")

        # 如果仍然太少，直接使用所有文献
        if len(filtered_papers) < 10:
            print(f"[SmartGenerate] 候选池仍然太少，使用所有去重后的文献")
            filtered_papers = all_papers[:max(request.target_count, 50)]

        # 5-7. 生成综述并验证被引用文献（带重试循环）
        generator = ReviewGeneratorService(api_key=api_key, aminer_token=aminer_token)
        review = None
        cited_papers = None
        validation_passed = False
        retry_count = 0
        max_retries = 1
        candidate_pool = filtered_papers

        while retry_count <= max_retries:
            print(f"[SmartGenerate] 第 {retry_count + 1} 次生成综述，候选池: {len(candidate_pool)} 篇")

            # 5. 生成综述
            review, cited_papers = await generator.generate_review(
                topic=request.topic,
                papers=candidate_pool
            )

            # 6. 验证被引用文献质量
            content, _ = validator._split_review_and_references(review)
            cited_indices = validator._extract_cited_indices(content)

            # 验证引用数量
            count_validation = validator.validate_citation_count(
                cited_indices=cited_indices,
                papers=cited_papers,
                min_count=request.target_count
            )

            # 验证近5年占比
            recent_validation = validator.validate_recent_ratio(
                papers=cited_papers,
                min_ratio=request.recent_years_ratio
            )

            # 验证英文占比（30%-70%范围）
            english_validation = validator.validate_english_ratio(
                papers=cited_papers,
                min_ratio=request.english_ratio,
                max_ratio=0.7  # 外文文献不超过70%
            )

            # 检查是否全部通过
            all_passed = (
                count_validation["passed"] and
                recent_validation["passed"] and
                english_validation["passed"]
            )

            print(f"[SmartGenerate] 引用数量: {count_validation['actual']}/{count_validation['required']}, "
                  f"近5年: {recent_validation['actual']}%/{recent_validation['required']}%, "
                  f"英文: {english_validation['actual']}%（要求{english_validation['required_min']}-{english_validation['required_max']}%）")

            if all_passed:
                validation_passed = True
                print(f"[SmartGenerate] 被引用文献验证通过")
                break
            else:
                if retry_count < max_retries:
                    print(f"[SmartGenerate] 被引用文献验证未通过，扩大候选池重试...")

                    # 根据验证失败原因，针对性扩大候选池
                    actual_english_ratio = english_validation["actual"] / 100

                    # 如果英文文献过多，专门搜索中文文献
                    if actual_english_ratio > 0.7:
                        print(f"[SmartGenerate] 英文文献过多({english_validation['actual']}%)，专门搜索中文文献...")
                        additional_papers = await search_service.search(
                            query=request.topic,
                            years_ago=15,
                            limit=150,
                            lang="zh",  # 只搜索中文文献
                            use_all_sources=True
                        )
                    # 如果英文文献过少，专门搜索英文文献
                    elif actual_english_ratio < 0.3:
                        print(f"[SmartGenerate] 英文文献过少({english_validation['actual']}%)，专门搜索英文文献...")

                        # 检查是否有英文查询可用
                        english_queries = [q for q in search_queries if q.get('lang') == 'en']
                        if english_queries:
                            print(f"[SmartGenerate] 使用框架中的英文查询 ({len(english_queries)}个)...")
                            additional_papers = []
                            for eq in english_queries[:5]:  # 最多使用5个英文查询
                                papers = await search_service.search(
                                    query=eq.get('query'),
                                    years_ago=15,
                                    limit=50,
                                    lang="en",
                                    use_all_sources=True
                                )
                                additional_papers.extend(papers)
                        else:
                            # 没有英文查询，尝试使用主题但去掉lang限制让系统自动判断
                            print(f"[SmartGenerate] 没有英文查询，使用主题搜索（自动语言检测）...")
                            additional_papers = await search_service.search(
                                query=request.topic,
                                years_ago=15,
                                limit=150,
                                use_all_sources=True  # 不指定lang，让系统自动判断
                            )
                    else:
                        # 其他情况（数量不足或年份不足），扩大搜索范围
                        print(f"[SmartGenerate] 扩大搜索范围（更多年份和数据源）...")
                        additional_papers = await search_service.search(
                            query=request.topic,
                            years_ago=15,  # 扩大年份范围
                            limit=150,
                            use_all_sources=True  # 使用所有数据源
                        )

                    # 去重并添加到候选池
                    for paper in additional_papers:
                        paper_id = paper.get("id")
                        if paper_id not in seen_ids:
                            seen_ids.add(paper_id)
                            all_papers.append(paper)

                    # 重新筛选更大的候选池
                    search_count = max(request.target_count * 3, 150)
                    candidate_pool = filter_service.filter_and_sort(
                        papers=all_papers,
                        target_count=search_count,
                        recent_years_ratio=request.recent_years_ratio,
                        english_ratio=request.english_ratio,
                        topic_keywords=topic_keywords
                    )
                    print(f"[SmartGenerate] 扩大后候选池: {len(candidate_pool)} 篇")
                else:
                    print(f"[SmartGenerate] 达到最大重试次数，标记未通过")

                retry_count += 1

        # 7. 验证并修正引用顺序（无论是否通过都要检查）
        from services.citation_order_checker import CitationOrderChecker

        print(f"[SmartGenerate] 检查引用序号顺序...")
        citation_checker = CitationOrderChecker()

        # 分离正文和参考文献
        content, references_section = validator._split_review_and_references(review)

        # 检查正文中的引用序号（传递参考文献数量以验证范围）
        citation_check_result = citation_checker.check_order(content, papers_count=len(cited_papers))

        if not citation_check_result['valid']:
            print(f"[SmartGenerate] 引用序号有问题: {citation_check_result['message']}")

            # 【特殊处理】如果引用超出范围，先去除超范围的引用
            if citation_check_result.get('exceeds_range', False):
                max_citation = citation_check_result.get('max_citation', 0)
                papers_count = citation_check_result.get('papers_count', 0)
                print(f"[SmartGenerate] 检测到引用超出范围：正文中最大引用为[{max_citation}]，但参考文献列表只有{papers_count}篇")
                print(f"[SmartGenerate] 正在去除超出范围的引用 [{papers_count + 1}-{max_citation}]...")

                # 去除超出范围的引用
                content = citation_checker.remove_out_of_range_citations(content, papers_count)

                print(f"[SmartGenerate] 超范围引用已去除")

            # 提取引用列表
            citations = citation_checker.extract_citations(content)

            if citations:
                print(f"[SmartGenerate] 正在自动修复引用序号顺序...")

                # 修复序号顺序
                fixed_content, number_mapping = citation_checker.fix_citation_order(content, citations)

                print(f"[SmartGenerate] 序号修复完成，映射: {number_mapping}")

                # 需要根据序号映射重新排列 cited_papers
                # number_mapping: [{'old': 1, 'new': 1}, {'old': 3, 'new': 2}, ...]
                # 意思是：旧序号1变成新序号1，旧序号3变成新序号2，等等。

                # 创建新序号到旧序号的反向映射
                new_to_old = {}
                for item in number_mapping:
                    new_to_old[item['new']] = item['old']

                # 重新排列 cited_papers
                new_cited_papers = []
                for new_index in sorted(new_to_old.keys()):
                    old_index = new_to_old[new_index]
                    # old_index 是 1-based，所以需要 -1
                    if old_index <= len(cited_papers):
                        new_cited_papers.append(cited_papers[old_index - 1])

                cited_papers = new_cited_papers

                # 重新生成参考文献部分
                references = generator._format_references(cited_papers)
                review = f"{fixed_content}\n\n## 参考文献\n\n{references}"

                print(f"[SmartGenerate] 引用序号和参考文献已同步更新")
        else:
            print(f"[SmartGenerate] ✓ 引用序号顺序正确: {citation_check_result['message']}")

        # 8. 计算统计信息（基于最终被引用文献）
        stats = filter_service.get_statistics(cited_papers)

        # 计算每个搜索查询的被引用论文数量
        cited_paper_ids = {p.get('id') for p in cited_papers}
        for query_result in search_queries_results:
            cited_count = sum(1 for p in query_result['papers'] if p.get('id') in cited_paper_ids)
            query_result['citedCount'] = cited_count
            for paper in query_result['papers']:
                paper['cited'] = paper.get('id') in cited_paper_ids
                # 如果没有相关性得分，添加默认值0
                if 'relevance_score' not in paper:
                    paper['relevance_score'] = 0

        # 为候选池中的论文添加相关性得分和引用状态
        for paper in candidate_pool:
            if 'relevance_score' not in paper:
                paper['relevance_score'] = 0
            paper['cited'] = paper.get('id') in cited_paper_ids

        # 9. 最终完整验证
        final_validation = validator.validate_review(
            review=review,
            papers=cited_papers
        )

        # 10. 保存记录
        record = record_service.update_success(
            db_session=db_session,
            record=record,
            review=review,
            papers=cited_papers,
            statistics=stats
        )

        return GenerateResponse(
            success=True,
            message="文献综述生成成功" if validation_passed else "文献综述生成完成（部分指标未达标）",
            data={
                "id": record.id,
                "topic": request.topic,
                "review": review,
                "papers": cited_papers,  # 返回实际被引用的论文
                "candidate_pool": candidate_pool,  # 同时返回候选池供参考
                "statistics": stats,
                "analysis": framework,
                "search_queries_results": search_queries_results,
                "cited_papers_count": len(cited_papers),
                "validation_passed": validation_passed,
                "validation": final_validation,
                "created_at": record.created_at.isoformat()
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        record = record_service.update_failure(
            db_session=db_session,
            record=record,
            error_message=str(e)
        )
        return GenerateResponse(
            success=False,
            message=f"生成失败: {str(e)}"
        )

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
