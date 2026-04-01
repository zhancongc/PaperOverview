"""
AMiner 论文详情补充服务
用于获取论文的完整信息（作者、DOI等）
"""
import asyncio
from typing import Dict, Optional
import httpx


class AMinerPaperDetailService:
    """AMiner 论文详情服务"""

    BASE_URL = "https://datacenter.aminer.cn/gateway/open_platform/api"

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.client = None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self):
        """初始化 HTTP 客户端"""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=False,
            headers={
                'Authorization': self.api_token,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

    async def get_paper_detail(self, paper_id: str) -> Optional[Dict]:
        """
        获取论文详细信息

        Args:
            paper_id: 论文ID

        Returns:
            论文详情字典，失败返回 None
        """
        if not self.client:
            await self.initialize()

        # 尝试多个可能的接口
        endpoints = [
            f"/paper/info",
            f"/paper/get",
            f"/search"
        ]

        for endpoint in endpoints:
            try:
                # 对于 search 接口，使用 ID 搜索
                if endpoint == "/search":
                    params = {'query': paper_id, 'size': 1}
                else:
                    params = {'id': paper_id}

                response = await self.client.get(
                    f"{self.BASE_URL}{endpoint}",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                if data.get('success', False):
                    item = data.get('data', data.get('item', {}))
                    if item and isinstance(item, dict):
                        # 提取有用信息
                        return self._extract_detail_info(item)
                else:
                    # 尝试直接从响应中提取
                    if 'data' in data:
                        return self._extract_detail_info(data['data'])
                    elif 'item' in data:
                        return self._extract_detail_info(data['item'])

            except Exception as e:
                print(f"[AMinerDetail] {endpoint} 失败: {e}")
                continue

        return None

    def _extract_detail_info(self, item: Dict) -> Dict:
        """从论文数据中提取详细信息"""
        info = {}

        # 提取作者
        if 'authors' in item:
            author_list = item['authors']
            if isinstance(author_list, list):
                authors = [a.get('name', str(a)) if isinstance(a, dict) else str(a) for a in author_list if a]
                if authors:
                    info['authors'] = authors

        # 提取 DOI
        if 'doi' in item and item['doi']:
            info['doi'] = item['doi']

        # 提取期刊信息
        if 'venue_name' in item and item['venue_name']:
            info['venue_name'] = item['venue_name']

        if 'year' in item and item['year']:
            info['year'] = item['year']

        return info

    async def enrich_papers(self, papers: list, max_concurrent: int = 5) -> list:
        """
        批量补充论文信息

        Args:
            papers: 论文列表
            max_concurrent: 最大并发数

        Returns:
            补充后的论文列表
        """
        if not papers:
            return papers

        # 找出需要补充的论文（没有作者或 DOI 的）
        needs_enrichment = []
        for i, paper in enumerate(papers):
            authors = paper.get('authors', [])
            if not authors or authors == ['佚名'] or not paper.get('doi'):
                needs_enrichment.append((i, paper))

        if not needs_enrichment:
            print(f"[AMinerDetail] 所有论文信息完整，无需补充")
            return papers

        print(f"[AMinerDetail] 需要补充 {len(needs_enrichment)} 篇论文的信息")

        # 并发获取详情（限制并发数）
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def fetch_detail(index_paper):
            index, paper = index_paper
            async with semaphore:
                try:
                    detail = await self.get_paper_detail(paper.get('id', ''))
                    if detail:
                        results[index] = detail
                    else:
                        results[index] = {}
                    await asyncio.sleep(0.2)  # 避免过快请求
                except Exception as e:
                    print(f"[AMinerDetail] 论文 {paper.get('id', 'Unknown')} 补充失败: {e}")
                    results[index] = {}

        # 并发执行
        tasks = [fetch_detail(item) for item in needs_enrichment]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        for index, detail in results.items():
            if detail:
                papers[index].update(detail)

        return papers


# 全局实例
detail_service = None


async def enrich_papers(papers: list, api_token: str) -> list:
    """
    补充论文信息（便捷函数）

    Args:
        papers: 论文列表
        api_token: AMiner API Token

    Returns:
        补充后的论文列表
    """
    global detail_service

    if detail_service is None:
        detail_service = AMinerPaperDetailService(api_token)

    async with detail_service:
        return await detail_service.enrich_papers(papers)
