"""
ScholarFlux - 统一学术搜索API封装层
提供统一接口，自动处理限速和错误

更新日志:
- v2.1: 添加数据源开关配置（通过 .env 文件）
- v2.0: 添加 DataCite, Crossref, AMiner 支持

数据源配置：
所有数据源可通过 .env 文件中的开关控制：
- OPENALEX_ENABLED: 启用 OpenAlex（默认 true）
- CROSSREF_ENABLED: 启用 Crossref（默认 true）
- DATACITE_ENABLED: 启用 DataCite（默认 true）
- AMINER_ENABLED: 启用 AMiner（默认 true）
- SEMANTIC_SCHOLAR_ENABLED: 启用 Semantic Scholar（默认 false）
- CHINESE_DOI_ENABLED: 启用中文 DOI（默认 false）

已禁用（限流/需要密钥）：
- Semantic Scholar: 限流太严格（每10秒1次）
- 中文 DOI: 需要 API 密钥

自动处理：
- 多数据源并行搜索
- 智能去重
- 速率限制
- 错误重试
- 结果保存到数据库
"""
import asyncio
import os
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from contextlib import contextmanager

from .paper_search import PaperSearchService
from .semantic_scholar_search import SemanticScholarService
from .aminer_search import AMinerSearchService
from .datacite_search import DataCiteSearchService
from .crossref_search import CrossrefSearchService
from .chinese_doi_search import ChineseDoiSearchService
from .paper_quality_filter import filter_low_quality_papers


class RateLimiter:
    """速率限制器"""

    def __init__(self, calls_per_second: float = 1.0):
        """
        Args:
            calls_per_second: 每秒允许的调用次数
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = None
        self.lock = asyncio.Lock()

    async def acquire(self):
        """获取调用许可"""
        async with self.lock:
            now = time.time()
            if self.last_call_time:
                elapsed = now - self.last_call_time
                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    await asyncio.sleep(wait_time)
            self.last_call_time = time.time()


class ScholarAPI:
    """单个学术API的封装"""

    def __init__(self, name: str, service, rate_limit: float = 1.0, is_chinese: bool = False):
        """
        Args:
            name: API名称
            service: 服务实例
            rate_limit: 每秒调用次数限制
            is_chinese: 是否为中文文献API
        """
        self.name = name
        self.service = service
        self.rate_limiter = RateLimiter(rate_limit)
        self.is_available = True
        self.is_chinese = is_chinese

    async def search(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0
    ) -> List[Dict]:
        """搜索论文（带速率限制）"""
        if not self.is_available:
            return []

        try:
            await self.rate_limiter.acquire()

            # AMiner 使用不同的接口（需要关键词列表）
            if self.name == "aminer":
                # 将查询字符串分割成关键词列表
                keywords = [k.strip() for k in query.split() if k.strip() and len(k) > 1]

                # 如果分割后没有有效关键词，使用整个查询
                if not keywords:
                    keywords = [query]

                papers = await self.service.search_papers(
                    keywords=keywords,
                    year_start=datetime.now().year - years_ago,
                    year_end=datetime.now().year,
                    max_results=limit
                )
            else:
                # 其他 API 使用标准接口
                papers = await self.service.search_papers(
                    query=query,
                    years_ago=years_ago,
                    limit=limit,
                    min_citations=min_citations
                )

            # 添加数据源标记
            for paper in papers:
                paper.setdefault('source', self.name)
            return papers

        except Exception as e:
            print(f"[{self.name}] API error: {e}")
            # 如果是速率限制错误，暂时禁用该API
            if '429' in str(e) or 'rate limit' in str(e).lower():
                self.is_available = False
                print(f"[{self.name}] 暂时禁用（速率限制）")
            return []


class ScholarFlux:
    """
    统一学术搜索接口 v2.0

    数据源配置：
    - OpenAlex: 英文文献（主要数据源）
    - Crossref: 期刊/会议论文（引用数据准确）
    - DataCite: 研究数据集（补充）
    - AMiner: 中文文献（需要 AMINER_API_TOKEN）

    已禁用：
    - Semantic Scholar: 限流太严格（每10秒1次）
    - 中文 DOI: 需要 API 密钥

    自动处理：
    - 多数据源并行搜索
    - 智能去重
    - 速率限制
    - 错误重试
    - 结果保存到数据库
    """

    # 类级别的标志，确保初始化日志只打印一次
    _initialized = False

    def __init__(self):
        """初始化所有可用的学术API"""
        self.apis = []
        self.chinese_api = None

        # 只在首次初始化时打印日志
        if not ScholarFlux._initialized:
            print("=" * 80)
            print("ScholarFlux v2.0 - 多数据源文献搜索")
            print("=" * 80)

            # ===== 数据源 1: OpenAlex =====
            if os.getenv('OPENALEX_ENABLED', 'true').lower() == 'true':
                try:
                    openalex_service = PaperSearchService()
                    rate_limit = float(os.getenv('OPENALEX_RATE_LIMIT', '5.0'))
                    self.apis.append(ScholarAPI(
                        name="openalex",
                        service=openalex_service,
                        rate_limit=rate_limit,
                        is_chinese=False
                    ))
                    print("[ScholarFlux] ✓ OpenAlex 已加载（英文文献，主要数据源）")
                except Exception as e:
                    print(f"[ScholarFlux] ✗ OpenAlex 初始化失败: {e}")
            else:
                print("[ScholarFlux] ○ OpenAlex 已禁用（OPENALEX_ENABLED=false）")

            # ===== 数据源 2: Crossref =====
            if os.getenv('CROSSREF_ENABLED', 'true').lower() == 'true':
                try:
                    crossref_service = CrossrefSearchService()
                    self.apis.append(ScholarAPI(
                        name="crossref",
                        service=crossref_service,
                        rate_limit=5.0,
                        is_chinese=False
                    ))
                    print("[ScholarFlux] ✓ Crossref 已加载（期刊/会议论文）")
                except Exception as e:
                    print(f"[ScholarFlux] ✗ Crossref 初始化失败: {e}")
            else:
                print("[ScholarFlux] ○ Crossref 已禁用（CROSSREF_ENABLED=false）")

            # ===== 数据源 3: DataCite =====
            if os.getenv('DATACITE_ENABLED', 'true').lower() == 'true':
                try:
                    datacite_service = DataCiteSearchService()
                    self.apis.append(ScholarAPI(
                        name="datacite",
                        service=datacite_service,
                        rate_limit=5.0,
                        is_chinese=False
                    ))
                    print("[ScholarFlux] ✓ DataCite 已加载（研究数据集）")
                except Exception as e:
                    print(f"[ScholarFlux] ✗ DataCite 初始化失败: {e}")
            else:
                print("[ScholarFlux] ○ DataCite 已禁用（DATACITE_ENABLED=false）")

            # ===== 数据源 4: Semantic Scholar =====
            if os.getenv('SEMANTIC_SCHOLAR_ENABLED', 'false').lower() == 'true':
                semantic_key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
                try:
                    semantic_service = SemanticScholarService(api_key=semantic_key)
                    rate_limit = float(os.getenv('SEMANTIC_SCHOLAR_RATE_LIMIT', '1.0'))
                    self.apis.append(ScholarAPI(
                        name="semantic_scholar",
                        service=semantic_service,
                        rate_limit=rate_limit,
                        is_chinese=False
                    ))
                    if semantic_key:
                        print("[ScholarFlux] ✓ Semantic Scholar 已加载（使用 API Key，速率限制: 1 req/s）")
                    else:
                        print("[ScholarFlux] ✓ Semantic Scholar 已加载（无 API Key，速率限制: 0.1 req/s）")
                        print("          提示: 配置 SEMANTIC_SCHOLAR_API_KEY 可获得更高速率限制")
                except Exception as e:
                    print(f"[ScholarFlux] ✗ Semantic Scholar 初始化失败: {e}")
            else:
                print("[ScholarFlux] ○ Semantic Scholar 已禁用（SEMANTIC_SCHOLAR_ENABLED=false）")

            # ===== 数据源 5: 中文 DOI =====
            if os.getenv('CHINESE_DOI_ENABLED', 'false').lower() == 'true':
                chinese_doi_key = os.getenv('CHINESE_DOI_API_KEY')
                try:
                    chinese_doi_service = ChineseDoiSearchService(api_key=chinese_doi_key)
                    self.chinese_api = ScholarAPI(
                        name="chinese_doi",
                        service=chinese_doi_service,
                        rate_limit=2.0,
                        is_chinese=True
                    )
                    self.apis.append(self.chinese_api)
                    if chinese_doi_key:
                        print("[ScholarFlux] ✓ 中文 DOI 已加载（中文文献）")
                    else:
                        print("[ScholarFlux] ○ 中文 DOI 已加载（无 API 密钥，使用模拟数据）")
                        print("          获取密钥: http://www.wanfangdata.com.cn/")
                except Exception as e:
                    print(f"[ScholarFlux] ✗ 中文 DOI 初始化失败: {e}")
                self.chinese_api = None
            else:
                print("[ScholarFlux] ○ 中文 DOI 已禁用（CHINESE_DOI_ENABLED=false）")

            # ===== 数据源 6: AMiner =====
            if os.getenv('AMINER_ENABLED', 'true').lower() == 'true':
                aminer_token = os.getenv('AMINER_API_TOKEN')
                if aminer_token:
                    try:
                        rate_limit = float(os.getenv('AMINER_RATE_LIMIT', '1.0'))
                        aminer_service = AMinerSearchService(api_token=aminer_token)
                        self.aminer_api = ScholarAPI(
                            name="aminer",
                            service=aminer_service,
                            rate_limit=rate_limit,
                            is_chinese=True
                        )
                        self.apis.append(self.aminer_api)
                        print("[ScholarFlux] ✓ AMiner 已加载（中文文献）")
                    except Exception as e:
                        print(f"[ScholarFlux] ✗ AMiner 初始化失败: {e}")
                        self.aminer_api = None
                else:
                    print("[ScholarFlux] ○ AMiner 未配置（设置 AMINER_API_TOKEN 环境变量）")
                    self.aminer_api = None
            else:
                print("[ScholarFlux] ○ AMiner 已禁用（AMINER_ENABLED=false）")
                self.aminer_api = None

            print("=" * 80)
            print(f"[ScholarFlux] 初始化完成，已加载 {len(self.apis)} 个数据源")
            print("=" * 80)

            # 标记已初始化，避免重复打印日志
            ScholarFlux._initialized = True

    @contextmanager
    def _get_db_session(self):
        """获取数据库会话"""
        from database import db
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            yield session
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    def _save_papers_to_db(self, papers: List[Dict], source: str = "unknown"):
        """保存论文到数据库"""
        if not papers:
            return

        try:
            with self._get_db_session() as session:
                from services.paper_metadata_dao import PaperMetadataDAO
                dao = PaperMetadataDAO(session)
                dao.save_papers(papers, source=source)
        except Exception:
            pass

    async def search_papers(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0
    ) -> List[Dict]:
        """
        搜索论文（兼容旧接口）

        Args:
            query: 搜索关键词
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量

        Returns:
            去重后的论文列表
        """
        return await self.search(
            query=query,
            years_ago=years_ago,
            limit=limit,
            min_citations=min_citations,
            use_all_sources=True
        )

    def _contains_chinese(self, text: str) -> bool:
        """检测文本是否包含中文"""
        return bool(text and any('\u4e00' <= char <= '\u9fff' for char in text))

    async def search(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0,
        use_all_sources: bool = True,
        lang: str = None,
        keywords: List[str] = None,
        search_mode: str = None
    ) -> List[Dict]:
        """
        统一搜索接口（多数据源并行搜索）

        Args:
            query: 搜索关键词
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量
            use_all_sources: 是否使用所有数据源
            lang: 语言标识 ('zh' 中文, 'en' 英文, None 自动检测)
            keywords: 关键词列表（预留）
            search_mode: 搜索模式（预留）

        Returns:
            去重后的论文列表
        """
        if not self.apis:
            print("[ScholarFlux] 没有可用的数据源")
            return []

        # 检测查询语言
        if lang is None:
            is_chinese_query = self._contains_chinese(query)
        else:
            is_chinese_query = (lang == 'zh')

        # 选择活跃的数据源
        if use_all_sources:
            # 使用所有可用数据源
            if is_chinese_query:
                print(f"[ScholarFlux] 中文查询，使用所有数据源: {query}")
            else:
                print(f"[ScholarFlux] 英文查询，使用所有数据源: {query}")
            active_apis = self.apis
        else:
            # 只使用非中文数据源
            active_apis = [api for api in self.apis if not api.is_chinese]
            if not active_apis:
                active_apis = self.apis

        # 过滤可用的 API
        active_apis = [api for api in active_apis if api.is_available]

        if not active_apis:
            print("[ScholarFlux] 所有数据源不可用")
            return []

        # 并行搜索所有数据源
        tasks = []
        for api in active_apis:
            task = api.search(
                query=query,
                years_ago=years_ago,
                limit=limit,
                min_citations=min_citations
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集结果
        all_papers = []
        source_counts = {}  # 记录每个数据源返回的数量
        source_mapping = {}  # 记录每篇论文的来源列表

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_counts[active_apis[i].name] = 0
                continue

            source = active_apis[i].name
            source_counts[source] = len(result)

            for paper in result:
                paper_id = paper.get("id")
                if paper_id:
                    # 累积来源记录（而不是只记录第一个）
                    if paper_id not in source_mapping:
                        source_mapping[paper_id] = []
                    if source not in source_mapping[paper_id]:
                        source_mapping[paper_id].append(source)
                paper.setdefault('source', [source])  # 临时设置为列表
            all_papers.extend(result)

        # 质量过滤（移除低质量文献）
        all_papers = filter_low_quality_papers(all_papers)

        # 去重（基于标题，优先保留被引量高的）
        unique_papers = self._deduplicate_by_title(all_papers)

        # 按相关性排序（综合考虑被引量和年份）
        sorted_papers = self._sort_by_relevance(unique_papers)

        # 限制返回数量
        final_papers = sorted_papers[:limit]

        # 确保每篇论文都有完整的来源列表
        for paper in final_papers:
            paper_id = paper.get("id")
            if paper_id and paper_id in source_mapping:
                paper['source'] = source_mapping[paper_id]

        # 保存到数据库
        try:
            self._save_papers_to_db(final_papers, source="scholarflux_v2")
        except Exception as e:
            pass  # 静默处理保存失败

        print(f"[ScholarFlux] 最终返回: {len(final_papers)} 篇论文")
        return final_papers

    def _deduplicate_by_title(self, papers: List[Dict]) -> List[Dict]:
        """
        基于标题去重，保留被引量高的版本

        去重策略：
        1. 标题归一化（小写、去除特殊字符）
        2. 优先保留被引量高的
        3. 被引量相同时，优先保留有 DOI 的
        """
        seen_titles = {}
        unique_papers = []

        for paper in papers:
            title = paper.get("title", "").strip().lower()
            # 去除特殊字符和空格
            title = ''.join(c for c in title if c.isalnum() or c.isspace())

            if not title or len(title) < 10:  # 跳过过短的标题
                continue

            if title not in seen_titles:
                seen_titles[title] = len(unique_papers)
                unique_papers.append(paper)
            else:
                # 比较被引量，保留更高的
                existing_idx = seen_titles[title]
                existing_paper = unique_papers[existing_idx]
                existing_citations = existing_paper.get("cited_by_count", 0)
                current_citations = paper.get("cited_by_count", 0)

                # 如果当前论文被引量更高，替换
                if current_citations > existing_citations:
                    unique_papers[existing_idx] = paper
                # 被引量相同时，优先保留有 DOI 的
                elif current_citations == existing_citations:
                    if paper.get("doi") and not existing_paper.get("doi"):
                        unique_papers[existing_idx] = paper

        return unique_papers

    def _sort_by_relevance(self, papers: List[Dict]) -> List[Dict]:
        """
        按相关性排序

        综合考虑：
        - 被引量（归一化）
        - 新近度（近5年加分）
        - 数据源优先级
        - 完整性（有 DOI、作者等）
        """
        current_year = datetime.now().year

        # 数据源优先级评分
        source_priority = {
            "crossref": 5,      # 引用数据最准确
            "openalex": 4,      # 数据全面
            "datacite": 2,      # 主要是数据集
            # "semantic_scholar": 3,   # 已禁用
            # "chinese_doi": 4,        # 已禁用
        }

        def score_paper(paper: Dict) -> float:
            score = 0.0

            # 1. 被引量得分（归一化到 0-50）
            citations = paper.get("cited_by_count", 0)
            score += min(citations / 2, 50)

            # 2. 新近论文加分
            paper_year = paper.get("year")
            if paper_year is not None:
                if paper_year >= current_year - 2:
                    score += 30  # 近2年加分最多
                elif paper_year >= current_year - 5:
                    score += 20
                elif paper_year >= current_year - 10:
                    score += 10

            # 3. 数据源优先级加分
            source = paper.get("source", "")
            score += source_priority.get(source, 0)

            # 4. 完整性加分
            if paper.get("doi"):
                score += 5
            if paper.get("authors"):
                score += 3
            if paper.get("abstract"):
                score += 3

            # 5. 中文文献加分（针对中文查询）
            if not paper.get("is_english", True):
                score += 5

            return score

        return sorted(papers, key=score_paper, reverse=True)

    async def close(self):
        """关闭所有API连接"""
        for api in self.apis:
            if hasattr(api.service, 'close'):
                try:
                    await api.service.close()
                except Exception as e:
                    print(f"[ScholarFlux] 关闭 {api.name} 失败: {e}")

    def get_status(self) -> Dict:
        """获取所有数据源的状态"""
        return {
            api.name: {
                "available": api.is_available,
                "rate_limit": api.rate_limiter.calls_per_second,
                "is_chinese": api.is_chinese
            }
            for api in self.apis
        }


# 测试代码
async def test_scholarflux_v2():
    """测试 ScholarFlux v2.0"""
    print("\n" + "=" * 80)
    print("测试 ScholarFlux v2.0 - 多数据源搜索")
    print("=" * 80)

    flux = ScholarFlux()

    # 显示状态
    status = flux.get_status()
    print(f"\n数据源状态:")
    for name, info in status.items():
        available = "✓" if info["available"] else "✗"
        chinese = " (中文)" if info["is_chinese"] else ""
        print(f"  {available} {name}{chinese}: {info['rate_limit']} req/s")

    try:
        # 测试英文搜索
        print(f"\n" + "-" * 80)
        print("测试 1: 英文关键词搜索")
        print("-" * 80)

        papers_en = await flux.search(
            query="machine learning",
            years_ago=5,
            limit=10
        )

        print(f"\n找到 {len(papers_en)} 篇英文论文:")
        for i, paper in enumerate(papers_en[:5], 1):
            title = (paper.get('title') or 'N/A')[:60]
            source = paper.get('source', 'N/A')
            year = paper.get('year', 'N/A')
            citations = paper.get('cited_by_count', 0)
            print(f"{i}. [{year}] {title}... ({source}, {citations} 引用)")

        # 测试中文搜索
        print(f"\n" + "-" * 80)
        print("测试 2: 中文关键词搜索")
        print("-" * 80)

        papers_zh = await flux.search(
            query="机器学习",
            years_ago=5,
            limit=10
        )

        print(f"\n找到 {len(papers_zh)} 篇中文相关论文:")
        for i, paper in enumerate(papers_zh[:5], 1):
            title = (paper.get('title') or 'N/A')[:60]
            source = paper.get('source', 'N/A')
            year = paper.get('year', 'N/A')
            is_en = "英文" if paper.get('is_english', True) else "中文"
            print(f"{i}. [{year}] {title}... ({source}, {is_en})")

    finally:
        await flux.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_scholarflux_v2())
