"""
PubScholar 中文文献搜索服务 - 直接调用 API
API: https://pubscholar.cn/hky/open/resources/api/v1/articles
"""
import asyncio
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote
import aiohttp


class PubScholarAPIService:
    """PubScholar API 搜索服务"""

    BASE_URL = "https://pubscholar.cn"
    API_URL = f"{BASE_URL}/hky/open/resources/api/v1/articles"
    EXPLORE_URL = f"{BASE_URL}/explore"

    def __init__(self):
        """初始化服务"""
        self.session = None
        self.user_id = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def initialize(self):
        """初始化 HTTP 会话并获取用户ID"""
        import ssl
        connector = aiohttp.TCPConnector(ssl=False)

        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        )

        # 先访问页面获取 cookies 和用户ID
        await self._get_session_info()

    async def _get_session_info(self):
        """访问页面获取 cookies 和用户ID"""
        try:
            async with self.session.get(
                self.EXPLORE_URL,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    html = await response.text()

                    # 尝试从 HTML 中提取 user_id
                    user_id_match = re.search(r'user_id["\']?\s*[:=]\s*["\']?([a-f0-9]+)', html)
                    if user_id_match:
                        self.user_id = user_id_match.group(1)
                        print(f"[PubScholar API] 获取到用户ID: {self.user_id}")
                    else:
                        # 使用默认值
                        self.user_id = "9a6d71ef0caa608a5f29e827645d3d2f"
                        print(f"[PubScholar API] 使用默认用户ID")
                else:
                    print(f"[PubScholar API] 访问页面失败: {response.status}")
                    self.user_id = "9a6d71ef0caa608a5f29e827645d3d2f"
        except Exception as e:
            print(f"[PubScholar API] 获取会话信息失败: {e}")
            self.user_id = "9a6d71ef0caa608a5f29e827645d3d2f"

    async def close(self):
        """关闭 HTTP 会话"""
        if self.session:
            await self.session.close()

    def build_search_query(
        self,
        title_keywords: Optional[List[str]] = None,
        keyword_keywords: Optional[List[str]] = None,
        author_exclude: Optional[str] = None,
        author_include: Optional[str] = None,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        abstract_keywords: Optional[List[str]] = None,
    ) -> str:
        """
        构建专业检索式

        Args:
            title_keywords: 标题关键词列表（AND关系）
            keyword_keywords: 关键词列表（AND关系）
            author_exclude: 排除的作者（支持通配符，如"张*"）
            author_include: 包含的作者
            year_start: 起始年份
            year_end: 结束年份
            abstract_keywords: 摘要关键词列表（AND关系）

        Returns:
            专业检索式字符串

        示例:
            build_search_query(
                title_keywords=["大数据", "人工智能"],
                keyword_keywords=["经济"],
                year_start=2015,
                year_end=2023
            )
            返回: 'TI="大数据" "人工智能" AND KY=经济 AND PY=[2015 TO 2023]'
        """
        parts = []

        # 标题条件 - 多个关键词用空格表示AND
        if title_keywords:
            title_terms = ' '.join([f'"{kw}"' for kw in title_keywords])
            parts.append(f'TI={title_terms}')

        # 关键词条件
        if keyword_keywords:
            keyword_terms = ' '.join([f'"{kw}"' for kw in keyword_keywords])
            parts.append(f'KY={keyword_terms}')

        # 摘要条件
        if abstract_keywords:
            abstract_terms = ' '.join([f'"{kw}"' for kw in abstract_keywords])
            parts.append(f'AB={abstract_terms}')

        # 包含作者条件
        if author_include:
            parts.append(f'AU={author_include}')

        # 排除作者条件
        if author_exclude:
            parts.append(f'NOT AU={author_exclude}')

        # 年份范围条件
        if year_start or year_end:
            start_year = year_start if year_start else 1900
            end_year = year_end if year_end else datetime.now().year
            parts.append(f'PY=[{start_year} TO {end_year}]')

        # 用 AND 连接所有条件
        query = ' AND '.join(parts)
        return query

    async def search_by_query(
        self,
        query: str,
        page: int = 1,
        size: int = 20,
        max_pages: int = 5
    ) -> List[Dict]:
        """
        使用专业检索式搜索文献

        Args:
            query: 专业检索式
            page: 起始页码
            size: 每页数量
            max_pages: 最大页数

        Returns:
            文献列表
        """
        if not self.session:
            await self.initialize()

        print(f"[PubScholar API] 检索式: {query}")

        all_papers = []
        seen_titles = set()

        for current_page in range(page, page + max_pages):
            try:
                # 构建请求体
                payload = {
                    "page": current_page,
                    "size": size,
                    "order_field": "default",
                    "order_direction": "desc",
                    "user_id": self.user_id,
                    "lang": "zh",
                    "strategy": quote(query, safe=''),
                    "extendParams": {
                        "strategyType": "professional"
                    }
                }

                print(f"[PubScholar API] 请求第 {current_page} 页...")

                async with self.session.post(
                    self.API_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        papers = self._parse_api_response(data)

                        # 去重并添加
                        new_papers = []
                        for paper in papers:
                            title = paper.get('title', '')
                            if title and title not in seen_titles:
                                seen_titles.add(title)
                                new_papers.append(paper)

                        if not new_papers:
                            print(f"[PubScholar API] 第 {current_page} 页没有新结果，停止")
                            break

                        all_papers.extend(new_papers)
                        print(f"[PubScholar API] 第 {current_page} 页获取 {len(new_papers)} 篇")

                        # 如果返回的论文数少于请求的数量，说明没有更多结果了
                        if len(papers) < size:
                            break
                    else:
                        print(f"[PubScholar API] 请求失败: {response.status}")
                        break

                # 避免请求过快
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"[PubScholar API] 第 {current_page} 页请求失败: {e}")
                continue

        print(f"[PubScholar API] 总共找到 {len(all_papers)} 篇文献")
        return all_papers

    def _parse_api_response(self, response: dict) -> List[Dict]:
        """解析 API 响应"""
        papers = []

        # API 返回的数据结构
        content = response.get('content', []) or response.get('data', []) or response.get('list', [])

        if not isinstance(content, list):
            # 尝试从其他可能的字段获取
            for key in ['articles', 'items', 'records']:
                if key in response:
                    content = response[key]
                    if isinstance(content, list):
                        break
            if not isinstance(content, list):
                print(f"[PubScholar API] 未知响应格式: {list(response.keys())}")
                return papers

        for item in content:
            try:
                # 提取作者
                authors = []
                author_list = item.get('authors', item.get('author', []))
                if isinstance(author_list, list):
                    for author in author_list:
                        if isinstance(author, dict):
                            authors.append(author.get('name', ''))
                        elif isinstance(author, str):
                            authors.append(author)
                elif isinstance(author_list, str):
                    authors = [a.strip() for a in author_list.split(',')]

                # 提取年份
                year = item.get('year')
                if not year:
                    date = item.get('date', '') or item.get('publishDate', '')
                    if isinstance(date, str) and len(date) >= 4:
                        try:
                            year = int(date[:4])
                        except:
                            pass

                # 构建期刊信息
                source = item.get('source', '') or item.get('journal', '') or item.get('publication', '')
                volume = item.get('volume', '')
                issue = item.get('issue', '')
                journal_info = source
                if volume:
                    journal_info += f', {volume}'
                if issue:
                    journal_info += f'({issue})'

                # 提取摘要
                abstract = item.get('abstract', '') or item.get('abstracts', '') or item.get('summary', '')
                if isinstance(abstract, str):
                    abstract = abstract[:500]

                # 提取关键词
                keywords = item.get('keywords', [])
                if isinstance(keywords, str):
                    keywords = [k.strip() for k in keywords.split(',')]
                elif not isinstance(keywords, list):
                    keywords = []

                papers.append({
                    'id': item.get('id', '') or item.get('articleId', ''),
                    'title': item.get('title', ''),
                    'authors': authors,
                    'year': year,
                    'cited_by_count': item.get('citedByCount', 0) or item.get('citation_count', 0),
                    'is_english': False,
                    'abstract': abstract,
                    'type': item.get('type', 'article') or item.get('articleType', 'article'),
                    'doi': item.get('doi', ''),
                    'journal': source,
                    'journal_info': journal_info,
                    'keywords': keywords,
                    'data_source': 'PubScholar',
                    'url': item.get('url', '') or f"{self.BASE_URL}/article/{item.get('id', '')}"
                })
            except Exception as e:
                print(f"[PubScholar API] 解析单条记录失败: {e}")
                continue

        return papers

    async def search_dual_keywords(
        self,
        keyword1: str,
        keyword2: Optional[str] = None,
        years_ago: int = 10,
        max_results: int = 50
    ) -> List[Dict]:
        """
        双关键词搜索

        Args:
            keyword1: 第一个关键词（标题）
            keyword2: 第二个关键词（标题，AND关系）
            years_ago: 近N年
            max_results: 最大结果数

        Returns:
            文献列表
        """
        current_year = datetime.now().year
        start_year = current_year - years_ago

        # 构建检索式: TI="关键词1" "关键词2" AND PY=[年份]
        title_parts = [f'"{keyword1}"']
        if keyword2:
            title_parts.append(f'"{keyword2}"')

        title_condition = ' '.join(title_parts)
        query = f'TI={title_condition} AND PY=[{start_year} TO {current_year}]'

        return await self.search_by_query(query, size=min(20, max_results), max_pages=(max_results // 20) + 1)

    async def search_by_keywords(
        self,
        keywords: List[str],
        search_in: str = "title",  # title, keyword, abstract
        years_ago: int = 10,
        max_results: int = 50
    ) -> List[Dict]:
        """
        多关键词搜索

        Args:
            keywords: 关键词列表（AND关系）
            search_in: 搜索字段 (title/keyword/abstract)
            years_ago: 近N年
            max_results: 最大结果数

        Returns:
            文献列表
        """
        current_year = datetime.now().year
        start_year = current_year - years_ago

        # 字段映射
        field_map = {
            'title': 'TI',
            'keyword': 'KY',
            'abstract': 'AB',
            'subject': 'TS',
            'author': 'AU',
        }
        field_code = field_map.get(search_in, 'TI')

        # 构建检索式: TI="关键词1" "关键词2" AND PY=[年份]
        keywords_part = ' '.join([f'"{kw}"' for kw in keywords])
        query = f'{field_code}={keywords_part} AND PY=[{start_year} TO {current_year}]'

        return await self.search_by_query(query, size=min(20, max_results), max_pages=(max_results // 20) + 1)


# 测试代码
async def test_api_search():
    """测试 API 搜索"""

    print("=" * 80)
    print("测试 PubScholar API 搜索")
    print("=" * 80)

    async with PubScholarAPIService() as service:
        # 测试1: 双关键词搜索
        print("\n" + "=" * 60)
        print("测试双关键词搜索: 标题包含[大数据]和[并行计算]")
        print("=" * 60)

        papers = await service.search_dual_keywords(
            keyword1="大数据",
            keyword2="并行计算",
            years_ago=5,
            max_results=30
        )

        print(f"\n找到 {len(papers)} 篇文献:")
        for i, paper in enumerate(papers[:5], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            authors = paper.get('authors', [])[:3]
            author_str = '、'.join(authors) if authors else 'N/A'
            source = paper.get('journal', 'N/A')

            print(f"\n{i}. [{year}] {title}")
            if author_str != 'N/A':
                print(f"   作者: {author_str}")
            if source != 'N/A':
                print(f"   来源: {source}")

        # 测试2: 使用自定义检索式
        print("\n" + "=" * 60)
        print("测试自定义检索式")
        print("=" * 60)

        custom_query = 'TI="投资者情绪" AND KY="分析师预测" AND PY=[2020 TO 2024]'
        print(f"检索式: {custom_query}")

        papers2 = await service.search_by_query(
            query=custom_query,
            size=20,
            max_pages=2
        )

        print(f"\n找到 {len(papers2)} 篇文献:")
        for i, paper in enumerate(papers2[:3], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            print(f"\n{i}. [{year}] {title}")

        # 测试3: 使用 build_search_query 构建检索式
        print("\n" + "=" * 60)
        print("测试使用 build_search_query 构建检索式")
        print("=" * 60)

        query = service.build_search_query(
            title_keywords=["机器学习", "深度学习"],
            keyword_keywords=["金融"],
            year_start=2022,
            year_end=2024
        )
        print(f"构建的检索式: {query}")

        papers3 = await service.search_by_query(
            query=query,
            size=20,
            max_pages=2
        )

        print(f"\n找到 {len(papers3)} 篇文献:")
        for i, paper in enumerate(papers3[:3], 1):
            title = paper.get('title', 'N/A')
            print(f"\n{i}. {title}")

        # 统计
        all_papers = papers + papers2 + papers3
        seen = set()
        unique = []
        for p in all_papers:
            t = p.get('title', '')
            if t and t not in seen:
                seen.add(t)
                unique.append(p)

        print("\n" + "=" * 80)
        print(f"总计: {len(unique)} 篇不重复文献")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_api_search())
