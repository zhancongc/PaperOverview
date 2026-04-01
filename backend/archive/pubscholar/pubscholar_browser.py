"""
PubScholar 中文文献搜索服务 - 基于 Playwright 无头浏览器
API: https://pubscholar.cn/explore
"""
import asyncio
import json
import time
from typing import List, Dict, Optional
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[PubScholar] Playwright 未安装，请运行: pip install playwright && python -m playwright install chromium")


class PubScholarBrowserService:
    """PubScholar 无头浏览器搜索服务"""

    BASE_URL = "https://pubscholar.cn"

    def __init__(self, headless: bool = True):
        """
        初始化服务

        Args:
            headless: 是否使用无头模式（默认 True）
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装，请先安装: pip install playwright")

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
        self.playwright = await async_playwright().start()

        # 启动 Chromium 浏览器
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )

        # 创建上下文（设置用户代理）
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )

        # 创建新页面
        self.page = await self.context.new_page()

        # 访问 PubScholar 首页以建立会话
        print("[PubScholar] 正在初始化浏览器会话...")
        await self.page.goto(f"{self.BASE_URL}/explore", wait_until="networkidle", timeout=30000)
        print("[PubScholar] 会话建立成功")

    async def search_papers(
        self,
        query: str,
        field: str = "title",
        years_ago: int = 10,
        max_results: int = 20
    ) -> List[Dict]:
        """
        搜索中文文献

        Args:
            query: 搜索关键词
            field: 搜索字段 (title/author/keyword/abstract/all)
            years_ago: 近N年
            max_results: 最大结果数

        Returns:
            文献列表
        """
        if not self.page:
            await self.initialize()

        print(f"[PubScholar] 搜索: {query}")

        try:
            # 等待搜索框加载（使用实际的选择器）
            search_box = await self.page.wait_for_selector(
                'input.placeholder*="发现你感兴趣的内容"',
                timeout=10000
            )

            # 输入搜索关键词
            await search_box.fill(query)
            await asyncio.sleep(0.5)

            # 点击搜索按钮或按回车
            await search_box.press('Enter')
            await asyncio.sleep(2)

            # 等待结果加载 - 尝试多种可能的选择器
            await self.page.wait_for_load_state('networkidle', timeout=15000)

            # 滚动加载更多结果
            papers = await self._scrape_results(max_results)

            print(f"[PubScholar] 找到 {len(papers)} 篇文献")
            return papers

        except Exception as e:
            print(f"[PubScholar] 搜索失败: {e}")
            # 尝试从 API 获取结果
            return await self._get_api_results()

    async def _scrape_results(self, max_results: int) -> List[Dict]:
        """从页面抓取结果"""
        papers = []
        seen_titles = set()

        # 滚动加载更多结果
        for _ in range(3):  # 滚动3次
            await self.page.evaluate('window.scrollBy(0, window.innerHeight)')
            await asyncio.sleep(1)

        # 尝试多种选择器来抓取结果
        selectors = [
            '.paper-item',
            '.article-item',
            '.result-item',
            '[class*="article"]',
            '[class*="paper"]'
        ]

        all_items = []
        for selector in selectors:
            items = await self.page.query_selector_all(selector)
            if items:
                all_items = items
                break

        # 如果找不到结构化结果，尝试从 API 响应中获取
        if not all_items:
            papers = await self._get_api_results()
        else:
            for item in all_items[:max_results]:
                try:
                    paper = await self._parse_item(item)
                    if paper and paper.get('title') not in seen_titles:
                        seen_titles.add(paper['title'])
                        papers.append(paper)
                except Exception as e:
                    continue

        return papers

    async def _get_api_results(self) -> List[Dict]:
        """从网络请求中获取 API 结果"""
        papers = []

        # 设置请求监听器
        async def handle_response(response):
            try:
                if 'articles' in response.url and response.status == 200:
                    data = await response.json()
                    parsed = self._parse_api_response(data)
                    papers.extend(parsed)
            except:
                pass

        self.page.on('response', handle_response)

        # 等待一下让响应处理完成
        await asyncio.sleep(2)

        return papers

    async def _parse_item(self, item) -> Optional[Dict]:
        """解析单个结果项"""
        try:
            # 尝试提取标题
            title_elem = await item.query_selector('.title, h3, h4, a[class*="title"]')
            title = await title_elem.inner_text() if title_elem else ""

            # 尝试提取作者
            author_elem = await item.query_selector('.author, [class*="author"]')
            authors = []
            if author_elem:
                author_text = await author_elem.inner_text()
                authors = [a.strip() for a in author_text.split(',')]

            # 尝试提取摘要
            abstract_elem = await item.query_selector('.abstract, [class*="abstract"]')
            abstract = await abstract_elem.inner_text() if abstract_elem else ""

            # 尝试提取年份
            year_elem = await item.query_selector('.year, [class*="year"], .date')
            year = None
            if year_elem:
                year_text = await year_elem.inner_text()
                match = re.search(r'\d{4}', year_text)
                if match:
                    year = int(match.group())

            # 尝试提取来源
            source_elem = await item.query_selector('.journal, .source, [class*="journal"]')
            source = await source_elem.inner_text() if source_elem else ""

            return {
                'title': title.strip(),
                'authors': authors,
                'year': year,
                'abstract': abstract.strip()[:500],
                'journal': source.strip(),
                'data_source': 'PubScholar'
            }
        except:
            return None

    def _parse_api_response(self, response: dict) -> List[Dict]:
        """解析 API 响应"""
        papers = []

        content = response.get('content', [])

        for item in content:
            # 提取作者
            authors = []
            author_list = item.get('authors', item.get('author', []))
            if isinstance(author_list, list):
                for author in author_list:
                    if isinstance(author, dict):
                        authors.append(author.get('name', ''))
                    elif isinstance(author, str):
                        authors.append(author)

            # 提取年份
            year = item.get('year')
            if not year:
                date = item.get('date', '')
                if isinstance(date, str) and len(date) >= 4:
                    try:
                        year = int(date[:4])
                    except:
                        pass

            # 构建期刊信息
            source = item.get('source', '')
            volume = item.get('volume', '')
            issue = item.get('issue', '')
            journal_info = source
            if volume:
                journal_info += f', {volume}'
            if issue:
                journal_info += f'({issue})'

            papers.append({
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'authors': authors,
                'year': year,
                'cited_by_count': 0,
                'is_english': False,
                'abstract': item.get('abstracts', ''),
                'type': item.get('article_type', 'article'),
                'doi': item.get('doi', ''),
                'journal': source,
                'journal_info': journal_info,
                'keywords': item.get('keywords', []),
                'data_source': 'PubScholar'
            })

        return papers

    async def search_by_keywords(
        self,
        keywords: List[str],
        years_ago: int = 10,
        max_per_keyword: int = 20
    ) -> List[Dict]:
        """使用多个关键词搜索"""
        all_papers = []
        seen_titles = set()

        for keyword in keywords:
            papers = await self.search_papers(
                query=keyword,
                years_ago=years_ago,
                max_results=max_per_keyword
            )

            # 去重
            for paper in papers:
                title = paper.get('title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_papers.append(paper)

            await asyncio.sleep(1)

        return all_papers

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


import re


# 测试代码
async def test_pubscholar_browser():
    """测试 PubScholar 浏览器搜索服务"""

    print("=" * 80)
    print("测试 PubScholar 无头浏览器搜索")
    print("=" * 80)

    async with PubScholarBrowserService(headless=True) as service:
        # 测试搜索
        test_queries = [
            "投资者情绪",
            "分析师预测",
        ]

        all_papers = []

        for query in test_queries:
            print(f"\n搜索: {query}")
            print("-" * 80)

            papers = await service.search_papers(
                query=query,
                years_ago=10,
                max_results=5
            )

            for i, paper in enumerate(papers[:3], 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                authors = paper.get('authors', [])[:2]
                author_str = ', '.join(authors) if authors else 'N/A'
                abstract = paper.get('abstract', '')[:80]

                print(f"{i}. [{year}]")
                print(f"   标题: {title}")
                print(f"   作者: {author_str}")
                if abstract:
                    print(f"   摘要: {abstract}...")
                print()

            all_papers.extend(papers)

        # 去重统计
        seen = set()
        unique = []
        for p in all_papers:
            t = p.get('title', '')
            if t and t not in seen:
                seen.add(t)
                unique.append(p)

        print("=" * 80)
        print(f"总计: {len(unique)} 篇不重复文献")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_pubscholar_browser())
