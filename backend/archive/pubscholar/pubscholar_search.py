"""
PubScholar 中文文献搜索服务
API: https://pubscholar.cn/explore

注意：此服务需要用户先在浏览器访问 pubscholar.cn 获取有效的会话 cookie
"""
import httpx
import json
import time
import hashlib
from typing import List, Dict, Optional
from datetime import datetime


class PubScholarSearchService:
    """PubScholar 中文文献搜索服务"""

    BASE_URL = "https://pubscholar.cn"
    API_URL = f"{BASE_URL}/hky/open/resources/api/v1/articles"

    def __init__(self, cookie_string: str = None, xsrf_token: str = None):
        """
        初始化服务

        Args:
            cookie_string: 从浏览器复制的完整 cookie 字符串
            xsrf_token: XSRF-TOKEN 值（如果 cookie 中包含，可以不传）

        使用方法：
            1. 打开浏览器，访问 https://pubscholar.cn/explore
            2. 按 F12 打开开发者工具
            3. 在 Network 标签中找到任意请求
            4. 复制 Request Headers 中的 Cookie 值
            5. 将 Cookie 值作为参数传入
        """
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.cookie_string = cookie_string
        self.xsrf_token = xsrf_token

        # 如果提供了 cookie，解析出 XSRF-TOKEN
        if cookie_string and not xsrf_token:
            self.xsrf_token = self._extract_xsrf_from_cookie(cookie_string)

        # 生成用户标识
        self.user_id = hashlib.md5(f"papers_{int(time.time())}".encode()).hexdigest()
        self.finger = hashlib.md5(f"finger_{int(time.time())}".encode()).hexdigest()

    def _extract_xsrf_from_cookie(self, cookie_string: str) -> Optional[str]:
        """从 cookie 字符串中提取 XSRF-TOKEN"""
        for part in cookie_string.split(';'):
            part = part.strip()
            if part.startswith('XSRF-TOKEN='):
                return part.split('=', 1)[1].strip()
        return None

    def _parse_cookie_string(self, cookie_string: str) -> Dict[str, str]:
        """解析 cookie 字符串为字典"""
        cookies = {}
        for part in cookie_string.split(';'):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    def _build_search_strategy(
        self,
        query: str,
        field: str = "title",
        years_ago: int = 10
    ) -> str:
        """
        构建搜索策略（URL编码格式）

        Args:
            query: 搜索关键词
            field: 搜索字段 (title/author/keyword/abstract/all)
            years_ago: 近N年

        Returns:
            URL编码的搜索策略字符串
        """
        from urllib.parse import quote

        current_year = datetime.now().year
        start_year = current_year - years_ago

        # 构建高级搜索策略
        # 格式: (field:(query~)) AND (year:[start TO end])
        strategy = f'({field}:({query}~)) AND (year:[{start_year} TO {current_year}])'

        return quote(strategy, safe='')

    async def search_papers(
        self,
        query: str,
        field: str = "title",
        years_ago: int = 10,
        page: int = 1,
        size: int = 20
    ) -> List[Dict]:
        """
        搜索中文文献

        Args:
            query: 搜索关键词
            field: 搜索字段 (title/author/keyword/abstract/all)
            years_ago: 近N年
            page: 页码
            size: 每页数量

        Returns:
            文献列表
        """
        if not self.cookie_string:
            print("[PubScholar] 错误: 未提供 cookie，无法访问 API")
            print("[PubScholar] 请从浏览器获取 cookie 后传入：")
            print("  1. 访问 https://pubscholar.cn/explore")
            print("  2. F12 -> Network -> 复制 Cookie")
            return []

        # 生成请求参数
        timestamp = str(int(time.time() * 1000))
        nonce = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))

        # 构建请求数据
        data = {
            "page": page,
            "size": size,
            "order_field": "default",
            "order_direction": "desc",
            "user_id": self.user_id,
            "lang": "zh",
            "strategy": self._build_search_strategy(query, field, years_ago),
            "extendParams": {
                "strategyType": "advanced"
            },
            "open_access": None
        }

        # 构建请求头
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": self.BASE_URL,
            "Referer": f"{self.BASE_URL}/explore",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        # 添加认证信息
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token

        # 解析 cookie 并添加到请求中
        cookies = self._parse_cookie_string(self.cookie_string)

        try:
            response = await self.client.post(
                self.API_URL,
                headers=headers,
                cookies=cookies,
                json=data
            )

            if response.status_code == 200:
                result = response.json()
                papers = self._parse_response(result)
                print(f"[PubScholar] 搜索 '{query}': 找到 {len(papers)} 篇文献")
                return papers
            else:
                print(f"[PubScholar] API error: {response.status_code}")
                print(f"[PubScholar] Response: {response.text[:300]}")
                return []

        except Exception as e:
            print(f"[PubScholar] Request error: {e}")
            return []

    def _parse_response(self, response: dict) -> List[Dict]:
        """解析 API 响应"""
        papers = []

        try:
            # 获取文献列表（字段名是 content，不是 data）
            content = response.get("content", [])

            for item in content:
                # 提取作者信息
                authors = []
                author_list = item.get("authors", item.get("author", []))
                if isinstance(author_list, list):
                    for author in author_list:
                        if isinstance(author, dict):
                            authors.append(author.get("name", ""))
                        elif isinstance(author, str):
                            authors.append(author)

                # 提取年份
                year = item.get("year")
                if not year:
                    date = item.get("date", "")
                    if isinstance(date, str) and len(date) >= 4:
                        try:
                            year = int(date[:4])
                        except:
                            year = None

                # 提取来源期刊
                source = item.get("source", item.get("journal", ""))

                # 提取摘要
                abstract = item.get("abstracts", "")

                # 提取关键词
                keywords = item.get("keywords", [])

                # 提取卷期页
                volume = item.get("volume", "")
                issue = item.get("issue", "")
                page = f"{item.get('first_page', '')}-{item.get('last_page', '')}" if item.get('first_page') else ""

                # 构建期刊信息
                journal_info = source
                if volume:
                    journal_info += f", {volume}"
                if issue:
                    journal_info += f"({issue})"
                if page:
                    journal_info += f":{page}"

                papers.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "authors": authors,
                    "year": year,
                    "cited_by_count": 0,  # PubScholar 没有提供被引量
                    "is_english": False,
                    "abstract": abstract,
                    "type": item.get("article_type", "article"),
                    "doi": item.get("doi", ""),
                    "journal": source,
                    "journal_info": journal_info,
                    "keywords": keywords,
                    "volume": volume,
                    "issue": issue,
                    "pages": page,
                    "data_source": "PubScholar"
                })

        except Exception as e:
            print(f"[PubScholar] Parse error: {e}")

        return papers

    async def search_by_keywords(
        self,
        keywords: List[str],
        field: str = "title",
        years_ago: int = 10,
        max_per_keyword: int = 20
    ) -> List[Dict]:
        """
        使用多个关键词搜索

        Args:
            keywords: 关键词列表
            field: 搜索字段
            years_ago: 近N年
            max_per_keyword: 每个关键词最多返回数量

        Returns:
            合并去重后的文献列表
        """
        all_papers = []
        seen_titles = set()

        for keyword in keywords:
            papers = await self.search_papers(
                query=keyword,
                field=field,
                years_ago=years_ago,
                size=max_per_keyword
            )

            # 去重
            for paper in papers:
                title = paper.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_papers.append(paper)

            # 添加延迟避免请求过快
            await asyncio.sleep(1)

        return all_papers

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


import random
import asyncio


# 测试代码
async def test_pubscholar_search():
    """测试 PubScholar 搜索服务"""
    # 注意：需要用户提供真实的 cookie
    cookie_string = None  # 在这里填入从浏览器复制的 cookie

    if not cookie_string:
        print("请先设置 cookie_string 变量")
        print("使用方法：")
        print("  1. 打开浏览器，访问 https://pubscholar.cn/explore")
        print("  2. 按 F12 打开开发者工具")
        print("  3. 在 Network 标签中找到请求，复制 Cookie 值")
        print("  4. 将 Cookie 值填入 cookie_string 变量")
        return

    service = PubScholarSearchService(cookie_string=cookie_string)

    print("=" * 80)
    print("测试 PubScholar 中文文献搜索")
    print("=" * 80)

    # 测试搜索
    test_queries = [
        "投资者情绪",
        "分析师预测",
        "媒体关注度",
    ]

    for query in test_queries:
        print(f"\n搜索: {query}")
        print("-" * 80)

        papers = await service.search_papers(
            query=query,
            field="title",
            years_ago=10,
            size=5
        )

        for i, paper in enumerate(papers[:3], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            authors = paper.get('authors', [])[:2]
            author_str = ', '.join(authors) if authors else 'N/A'
            abstract = paper.get('abstract', '')[:100]

            print(f"{i}. [{year}]")
            print(f"   标题: {title}")
            print(f"   作者: {author_str}")
            print(f"   摘要: {abstract}...")
            print()

    await service.close()


if __name__ == "__main__":
    asyncio.run(test_pubscholar_search())
