"""
PubScholar 中文文献搜索服务 - 使用 Playwright 在浏览器内发起 API 请求
"""
import asyncio
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PubScholarBrowserAPI:
    """PubScholar API 搜索服务 - 在浏览器内发起请求"""

    BASE_URL = "https://pubscholar.cn"
    API_URL = f"{BASE_URL}/hky/open/resources/api/v1/articles"
    EXPLORE_URL = f"{BASE_URL}/explore"

    def __init__(self, headless: bool = True):
        """初始化服务"""
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def initialize(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")

        print("[PubScholar] 正在初始化浏览器...")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )

        self.page = await self.context.new_page()

        # 访问 explore 页面建立会话
        await self.page.goto(self.EXPLORE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)

        print("[PubScholar] 初始化完成")

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
        """构建专业检索式"""
        parts = []

        if title_keywords:
            title_terms = ' '.join([f'"{kw}"' for kw in title_keywords])
            parts.append(f'TI={title_terms}')

        if keyword_keywords:
            keyword_terms = ' '.join([f'"{kw}"' for kw in keyword_keywords])
            parts.append(f'KY={keyword_terms}')

        if abstract_keywords:
            abstract_terms = ' '.join([f'"{kw}"' for kw in abstract_keywords])
            parts.append(f'AB={abstract_terms}')

        if author_include:
            parts.append(f'AU={author_include}')

        if author_exclude:
            parts.append(f'NOT AU={author_exclude}')

        if year_start or year_end:
            start_year = year_start if year_start else 1900
            end_year = year_end if year_end else datetime.now().year
            parts.append(f'PY=[{start_year} TO {end_year}]')

        return ' AND '.join(parts)

    async def search_by_query(
        self,
        query: str,
        page: int = 1,
        size: int = 20,
        max_pages: int = 5
    ) -> List[Dict]:
        """使用专业检索式搜索文献 - 在浏览器内发起请求"""
        if not self.page:
            await self.initialize()

        print(f"[PubScholar] 检索式: {query}")

        all_papers = []
        seen_titles = set()

        for current_page in range(page, page + max_pages):
            try:
                # 在浏览器内发起 API 请求
                result = await self.page.evaluate('''async (args) => {
                    const { apiUrl, query, page, size } = args;

                    const payload = {
                        page: page,
                        size: size,
                        order_field: "default",
                        order_direction: "desc",
                        lang: "zh",
                        strategy: query,
                        extendParams: {
                            strategyType: "professional"
                        }
                    };

                    try {
                        const response = await fetch(apiUrl, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            },
                            body: JSON.stringify(payload)
                        });

                        const data = await response.json();
                        return { success: response.ok, status: response.status, data: data };
                    } catch (error) {
                        return { success: false, error: error.message };
                    }
                }''', {
                    'apiUrl': self.API_URL,
                    'query': query,
                    'page': current_page,
                    'size': size
                })

                if result.get('success'):
                    data = result.get('data', {})
                    papers = self._parse_api_response(data)

                    new_papers = []
                    for paper in papers:
                        title = paper.get('title', '')
                        if title and title not in seen_titles:
                            seen_titles.add(title)
                            new_papers.append(paper)

                    if not new_papers:
                        print(f"[PubScholar] 第 {current_page} 页没有新结果，停止")
                        break

                    all_papers.extend(new_papers)
                    print(f"[PubScholar] 第 {current_page} 页获取 {len(new_papers)} 篇")

                    if len(papers) < size:
                        break
                else:
                    error = result.get('error', 'Unknown error')
                    status = result.get('status', 'N/A')
                    print(f"[PubScholar] 请求失败: {status}, {error}")
                    break

                await asyncio.sleep(0.3)

            except Exception as e:
                print(f"[PubScholar] 第 {current_page} 页请求失败: {e}")
                continue

        print(f"[PubScholar] 总共找到 {len(all_papers)} 篇文献")
        return all_papers

    def _parse_api_response(self, response: dict) -> List[Dict]:
        """解析 API 响应"""
        papers = []
        content = response.get('content', []) or response.get('data', []) or response.get('list', [])

        if not isinstance(content, list):
            for key in ['articles', 'items', 'records']:
                if key in response:
                    content = response[key]
                    if isinstance(content, list):
                        break
            if not isinstance(content, list):
                return papers

        for item in content:
            try:
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

                year = item.get('year')
                if not year:
                    date = item.get('date', '') or item.get('publishDate', '')
                    if isinstance(date, str) and len(date) >= 4:
                        try:
                            year = int(date[:4])
                        except:
                            pass

                source = item.get('source', '') or item.get('journal', '') or item.get('publication', '')
                volume = item.get('volume', '')
                issue = item.get('issue', '')
                journal_info = source
                if volume:
                    journal_info += f', {volume}'
                if issue:
                    journal_info += f'({issue})'

                abstract = item.get('abstract', '') or item.get('abstracts', '') or item.get('summary', '')
                if isinstance(abstract, str):
                    abstract = abstract[:500]

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
                continue

        return papers

    async def search_dual_keywords(
        self,
        keyword1: str,
        keyword2: Optional[str] = None,
        years_ago: int = 10,
        max_results: int = 50
    ) -> List[Dict]:
        """双关键词搜索"""
        current_year = datetime.now().year
        start_year = current_year - years_ago

        title_parts = [f'"{keyword1}"']
        if keyword2:
            title_parts.append(f'"{keyword2}"')

        title_condition = ' '.join(title_parts)
        query = f'TI={title_condition} AND PY=[{start_year} TO {current_year}]'

        return await self.search_by_query(query, size=min(20, max_results), max_pages=(max_results // 20) + 1)

    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()


# 测试代码
async def test_browser_api():
    """测试浏览器内 API 搜索"""

    print("=" * 80)
    print("测试 PubScholar 浏览器内 API 搜索")
    print("=" * 80)

    async with PubScholarBrowserAPI(headless=True) as service:
        # 测试双关键词搜索
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

        # 测试自定义检索式
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

        # 测试使用 build_search_query
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
    asyncio.run(test_browser_api())
