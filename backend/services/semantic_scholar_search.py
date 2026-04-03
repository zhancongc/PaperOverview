"""
Semantic Scholar 文献检索服务
免费API，对中文文献有一定支持
"""
import httpx
import asyncio
from typing import List, Dict
from datetime import datetime, timedelta


class SemanticScholarService:
    """Semantic Scholar API 客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: str = None):
        self.client = httpx.AsyncClient(timeout=30.0)
        # Semantic Scholar API key is optional but increases rate limits
        self.api_key = api_key
        # 速率限制：有API Key时每秒1次，无API Key时每10秒1次
        self.request_delay = 1.0 if api_key else 10.0  # 秒
        self.last_request_time = None
        # 重试配置
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 5  # 重试延迟（秒）
        self.backoff_factor = 2  # 退避因子

    async def search_papers(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0
    ) -> List[Dict]:
        """
        搜索论文

        Args:
            query: 搜索关键词
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量

        Returns:
            论文列表
        """
        # 速率限制：等待足够时间再发送请求
        import asyncio
        if self.last_request_time:
            elapsed = datetime.now().timestamp() - self.last_request_time
            if elapsed < self.request_delay:
                wait_time = self.request_delay - elapsed
                await asyncio.sleep(wait_time)

        # 计算截止年份
        current_year = datetime.now().year
        start_year = current_year - years_ago

        # Semantic Scholar 使用年份范围过滤
        year_range = f"{start_year}-{current_year}"

        params = {
            "query": query,
            "fields": "paperId,title,authors,year,citationCount,externalIds,publicationDate,journal,abstract",
            "limit": min(limit, 100),  # Semantic Scholar 默认最大100
            "year": year_range
        }

        # 如果有 API key，添加到请求头
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 速率限制：等待足够时间再发送请求
                if self.last_request_time:
                    elapsed = datetime.now().timestamp() - self.last_request_time
                    if elapsed < self.request_delay:
                        wait_time = self.request_delay - elapsed
                        print(f"[Semantic Scholar] 速率限制等待 {wait_time:.1f} 秒...")
                        await asyncio.sleep(wait_time)

                self.last_request_time = datetime.now().timestamp()
                response = await self.client.get(
                    f"{self.BASE_URL}/paper/search",
                    params=params,
                    headers=headers
                )

                # 检查是否是429错误（速率限制）
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # 计算退避时间
                        backoff_delay = self.retry_delay * (self.backoff_factor ** attempt)
                        print(f"[Semantic Scholar] 遇到429限流，{backoff_delay}秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(backoff_delay)
                        continue
                    else:
                        print(f"[Semantic Scholar] 达到最大重试次数，放弃请求")
                        return []

                response.raise_for_status()
                data = response.json()

                papers = []
                for item in data.get("data", []):
                    # 过滤被引量
                    citation_count = item.get("citationCount", 0)
                    if citation_count < min_citations:
                        continue

                    # 提取作者信息
                    authors = []
                    for author in item.get("authors", [])[:10]:  # 最多10个作者
                        name = author.get("name", "")
                        if name:
                            authors.append(name)

                    # 判断语言（简单判断：标题含非ASCII字符可能是中文）
                    title = item.get("title", "")
                    is_english = self._is_english(title)

                    # 获取 DOI
                    doi = None
                    external_ids = item.get("externalIds", {})
                    if external_ids and "DOI" in external_ids:
                        doi = external_ids["DOI"]

                    # 获取期刊/会议信息（更全面的提取）
                    venue_name = ""

                    # 尝试从 journal 字段获取
                    journal = item.get("journal", {})
                    if journal:
                        venue_name = journal.get("name", "")

                    # 如果没有期刊信息，尝试从 venue 字段获取
                    if not venue_name:
                        venue = item.get("venue", "")
                        if venue:
                            venue_name = venue

                    # 如果仍然没有，尝试从 publicationVenueId 推断
                    if not venue_name:
                        venue_id = item.get("publicationVenueId", "")
                        if venue_id:
                            venue_name = venue_id

                    # 从 DOI 解析出版社信息（作为补充）
                    if not venue_name and doi:
                        if "10.1145/" in doi:
                            venue_name = "ACM"
                        elif "10.1109/" in doi:
                            venue_name = "IEEE"
                        elif "10.48550/arXiv" in doi:
                            venue_name = "arXiv"
                        elif "10.1038/" in doi:
                            venue_name = "Nature"
                        elif "10.1126/" in doi:
                            venue_name = "Science"

                    papers.append({
                        "id": item.get("paperId", ""),
                        "title": title,
                        "authors": authors,
                        "year": item.get("year"),
                        "cited_by_count": citation_count,
                        "is_english": is_english,
                        "abstract": item.get("abstract", ""),
                        "type": "article",
                        "doi": doi,
                        "venue": venue_name,  # 添加 venue 字段
                        "journal": venue_name,  # 添加 journal 字段
                        "venue_name": venue_name,  # 添加 venue_name 字段（用于数据库存储）
                        "primary_location": {
                            "source": {
                                "display_name": venue_name
                            } if venue_name else {}
                        },
                        "concepts": [],  # Semantic Scholar 没有直接的 concepts 字段
                        "source": "semantic_scholar"  # 标记数据来源
                    })

                print(f"[Semantic Scholar] 成功获取 {len(papers)} 篇论文")
                return papers

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # 429错误在上面已经处理
                    continue
                else:
                    print(f"[Semantic Scholar] HTTP错误: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        return []
            except Exception as e:
                print(f"[Semantic Scholar] 请求失败: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return []

        return []

    def _is_english(self, text: str) -> bool:
        """简单判断文本是否为英文"""
        if not text:
            return False
        # 计算非ASCII字符比例
        non_ascii = sum(1 for c in text if ord(c) > 127)
        return non_ascii / len(text) < 0.3

    async def close(self):
        await self.client.aclose()
