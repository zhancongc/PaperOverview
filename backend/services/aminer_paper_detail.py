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
            ("POST", "/paper/info", {"ids": [paper_id]}),  # paper/info 使用 POST + ids 数组
            ("GET", "/paper/get", {"id": paper_id}),
            ("GET", "/search", {"query": paper_id, "size": 1})
        ]

        for method, endpoint, payload in endpoints:
            try:
                if method == "POST":
                    # POST 请求，使用 json 参数
                    response = await self.client.post(
                        f"{self.BASE_URL}{endpoint}",
                        json=payload
                    )
                else:
                    # GET 请求，使用 params 参数
                    response = await self.client.get(
                        f"{self.BASE_URL}{endpoint}",
                        params=payload
                    )

                response.raise_for_status()
                data = response.json()

                if data.get('success', False):
                    # paper/info 返回 data 是数组
                    result_data = data.get('data', data.get('item', {}))
                    if isinstance(result_data, list) and len(result_data) > 0:
                        item = result_data[0]
                    elif isinstance(result_data, dict):
                        item = result_data
                    else:
                        continue

                    if item:
                        # 提取有用信息
                        return self._extract_detail_info(item)
                else:
                    # 尝试直接从响应中提取
                    if 'data' in data:
                        result_data = data['data']
                        if isinstance(result_data, list) and len(result_data) > 0:
                            return self._extract_detail_info(result_data[0])
                        return self._extract_detail_info(result_data)
                    elif 'item' in data:
                        return self._extract_detail_info(data['item'])

            except Exception as e:
                # 只在非404错误时打印日志（404是预期的，论文不在AMiner数据库中）
                error_str = str(e)
                if '404' not in error_str and 'Not Found' not in error_str:
                    print(f"[AMinerDetail] {method} {endpoint} 失败: {e}")
                continue

        return None

    def _extract_detail_info(self, item: Dict) -> Dict:
        """从论文数据中提取详细信息"""
        info = {}

        # 提取作者（根据API文档：authors 是数组，每个元素有 name 和 name_zh 字段）
        if 'authors' in item:
            author_list = item['authors']
            if isinstance(author_list, list) and len(author_list) > 0:
                # 优先使用 name_zh（中文名），其次使用 name
                authors = []
                for a in author_list:
                    if a and isinstance(a, dict):
                        name = a.get('name_zh') or a.get('name')
                        if name:
                            authors.append(name)
                if authors:
                    info['authors'] = authors
                    print(f"[AMinerDetail] 提取到作者: {authors}")

        # 提取 DOI
        if 'doi' in item and item['doi']:
            info['doi'] = item['doi']

        # 提取期刊信息（根据API文档：raw 字段是期刊名称）
        if 'raw' in item and item['raw']:
            info['venue_name'] = item['raw']
        elif 'venue_name' in item and item['venue_name']:
            info['venue_name'] = item['venue_name']

        if 'year' in item and item['year']:
            info['year'] = item['year']

        # 提取卷号
        if 'issue' in item and item['issue']:
            info['issue'] = item['issue']

        print(f"[AMinerDetail] 提取的论文信息: {info}")
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
                    # 只在非404错误时打印日志
                    error_str = str(e)
                    if '404' not in error_str and 'Not Found' not in error_str:
                        print(f"[AMinerDetail] 论文 {paper.get('id', 'Unknown')[:20]}... 补充失败: {e}")
                    results[index] = {}

        # 并发执行
        tasks = [fetch_detail(item) for item in needs_enrichment]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        enriched_count = 0
        not_found_count = 0

        for index, detail in results.items():
            if detail:
                papers[index].update(detail)
                enriched_count += 1
            else:
                not_found_count += 1

        print(f"[AMinerDetail] 补充完成: 成功{enriched_count}篇, 未找到{not_found_count}篇")

        return papers

    async def close(self):
        """关闭 HTTP 客户端"""
        if self.client:
            await self.client.aclose()
            self.client = None


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
