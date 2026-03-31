"""
ScholarFlux - 统一学术搜索API封装层
提供统一接口，自动处理限速和错误
"""
import asyncio
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .paper_search import PaperSearchService
from .semantic_scholar_search import SemanticScholarService


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

    def __init__(self, name: str, service, rate_limit: float = 1.0):
        """
        Args:
            name: API名称
            service: 服务实例
            rate_limit: 每秒调用次数限制
        """
        self.name = name
        self.service = service
        self.rate_limiter = RateLimiter(rate_limit)
        self.is_available = True

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
    统一学术搜索接口

    自动处理：
    - 多数据源聚合
    - 速率限制
    - 错误重试
    - 结果去重
    """

    def __init__(self):
        """初始化所有可用的学术API"""
        self.apis = []

        # OpenAlex - 主要数据源
        try:
            openalex_service = PaperSearchService()
            self.apis.append(ScholarAPI(
                name="openalex",
                service=openalex_service,
                rate_limit=5.0  # OpenAlex 允许每秒5次
            ))
        except Exception as e:
            print(f"[ScholarFlux] OpenAlex 初始化失败: {e}")

        # Semantic Scholar - 补充数据源
        try:
            semantic_service = SemanticScholarService()
            self.apis.append(ScholarAPI(
                name="semantic_scholar",
                service=semantic_service,
                rate_limit=0.1  # 免费版限制严格，每10秒1次
            ))
        except Exception as e:
            print(f"[ScholarFlux] Semantic Scholar 初始化失败: {e}")

        print(f"[ScholarFlux] 初始化完成，已加载 {len(self.apis)} 个数据源")

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

    async def search(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0,
        use_all_sources: bool = True
    ) -> List[Dict]:
        """
        统一搜索接口

        Args:
            query: 搜索关键词
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量
            use_all_sources: 是否使用所有数据源（False则只用主数据源）

        Returns:
            去重后的论文列表
        """
        if not self.apis:
            print("[ScholarFlux] 没有可用的数据源")
            return []

        # 选择要使用的API
        if use_all_sources:
            active_apis = [api for api in self.apis if api.is_available]
        else:
            active_apis = [self.apis[0]] if self.apis and self.apis[0].is_available else []

        if not active_apis:
            print("[ScholarFlux] 所有数据源不可用")
            return []

        # 并行搜索所有可用数据源
        tasks = [
            api.search(
                query=query,
                years_ago=years_ago,
                limit=limit,
                min_citations=min_citations
            )
            for api in active_apis
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集结果
        all_papers = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[ScholarFlux] {active_apis[i].name} 搜索失败: {result}")
                continue
            all_papers.extend(result)

        # 去重（优先保留被引量高的）
        unique_papers = self._deduplicate_by_title(all_papers)

        # 按相关性排序（综合考虑被引量和年份）
        sorted_papers = self._sort_by_relevance(unique_papers)

        return sorted_papers[:limit]

    def _deduplicate_by_title(self, papers: List[Dict]) -> List[Dict]:
        """基于标题去重，保留被引量高的版本"""
        seen_titles = {}
        unique_papers = []

        for paper in papers:
            title = paper.get("title", "").strip().lower()
            if not title:
                continue

            if title not in seen_titles:
                seen_titles[title] = len(unique_papers)
                unique_papers.append(paper)
            else:
                # 比较被引量，保留更高的
                existing_idx = seen_titles[title]
                existing_citations = unique_papers[existing_idx].get("cited_by_count", 0)
                current_citations = paper.get("cited_by_count", 0)

                if current_citations > existing_citations:
                    unique_papers[existing_idx] = paper

        return unique_papers

    def _sort_by_relevance(self, papers: List[Dict]) -> List[Dict]:
        """
        按相关性排序

        综合考虑：
        - 被引量（归一化）
        - 新近度（近5年加分）
        - 数据源优先级
        """
        current_year = datetime.now().year

        def score_paper(paper: Dict) -> float:
            score = 0.0

            # 被引量得分（归一化到 0-50）
            citations = paper.get("cited_by_count", 0)
            score += min(citations / 2, 50)

            # 新近论文加分
            paper_year = paper.get("year", 0)
            if paper_year >= current_year - 5:
                score += 20
            elif paper_year >= current_year - 10:
                score += 10

            # 英文论文加分
            if paper.get("is_english", False):
                score += 5

            # 数据源优先级
            source = paper.get("source", "")
            if source == "openalex":
                score += 2  # OpenAlex 数据质量更高

            return score

        return sorted(papers, key=score_paper, reverse=True)

    async def close(self):
        """关闭所有API连接"""
        for api in self.apis:
            if hasattr(api.service, 'close'):
                await api.service.close()

    def get_status(self) -> Dict:
        """获取所有数据源的状态"""
        return {
            api.name: {
                "available": api.is_available,
                "rate_limit": api.rate_limiter.calls_per_second
            }
            for api in self.apis
        }
