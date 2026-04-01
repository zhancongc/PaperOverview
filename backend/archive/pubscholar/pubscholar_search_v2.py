"""
PubScholar 中文文献搜索服务 - 基于 Playwright 监听 API 请求
API: https://pubscholar.cn/explore
"""
import asyncio
import json
import re
from typing import List, Dict
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PubScholarService:
    """PubScholar 搜索服务 - 监听 API 响应"""

    BASE_URL = "https://pubscholar.cn"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.api_results = []

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',  # 设置为中文
            timezone_id='Asia/Shanghai'
        )
        self.page = await self.context.new_page()

        # 监听所有响应
        self.page.on('response', self._handle_response)

        # 禁用自动翻译
        await self.page.add_init_script("""
            // 禁用浏览器自动翻译
            Object.defineProperty(navigator, 'language', {
                get: function() { return 'zh-CN'; }
            });
            Object.defineProperty(navigator, 'languages', {
                get: function() { return ['zh-CN', 'zh']; }
            });
        """)

        await self.page.goto(f"{self.BASE_URL}/explore", wait_until="networkidle")

    async def _handle_response(self, response):
        """处理响应，捕获 API 数据"""
        url = response.url
        if 'articles' in url and response.status == 200:
            try:
                data = await response.json()
                self.api_results.append(data)
                print(f"[PubScholar] 捕获到 API 响应，内容数: {len(data.get('content', []))}")
            except:
                pass

    async def search_papers(
        self,
        query: str,
        years_ago: int = 10,
        max_results: int = 20
    ) -> List[Dict]:
        """搜索中文文献"""
        if not self.page:
            await self.initialize()

        # 使用中文关键词映射（针对 PubScholar 优化）
        cn_keywords = self._get_chinese_keywords(query)
        print(f"[PubScholar] 搜索: {query} -> {cn_keywords}")

        all_papers = []
        seen_titles = set()

        for keyword in cn_keywords:
            self.api_results = []

            try:
                search_box = await self.page.wait_for_selector(
                    'input[placeholder*="发现你感兴趣的内容"]',
                    timeout=10000
                )

                await search_box.fill('')
                await search_box.fill(keyword)
                await asyncio.sleep(0.5)
                await search_box.press('Enter')
                await asyncio.sleep(4)

                # 解析结果
                for response_data in self.api_results:
                    papers = self._parse_response(response_data)
                    for paper in papers:
                        title = paper.get('title', '')
                        if title and title not in seen_titles:
                            seen_titles.add(title)
                            all_papers.append(paper)

                if len(all_papers) >= max_results:
                    break

            except Exception as e:
                print(f"[PubScholar] 搜索 '{keyword}' 失败: {e}")

        # 去重并限制数量
        unique_papers = []
        seen = set()
        for paper in all_papers:
            title = paper.get('title', '')
            if title and title not in seen:
                seen.add(title)
                unique_papers.append(paper)

        print(f"[PubScholar] 找到 {len(unique_papers)} 篇文献")
        return unique_papers[:max_results]

    def _get_chinese_keywords(self, query: str) -> List[str]:
        """
        获取中文搜索关键词（针对 PubScholar 优化）

        某些关键词在 PubScholar 上需要使用特定词汇才能找到中文文献
        """
        keyword_mapping = {
            '投资者情绪': ['投资者情绪', '投资者情绪指数', '市场情绪', '股市情绪'],
            '分析师预测': ['分析师预测', '盈利预测', '证券分析师', '分析师评级'],
            '分析师盈利预测准确性': ['盈利预测', '预测准确性', '分析师预测准确性'],
            '媒体关注度': ['媒体关注', '媒体报道', '新闻关注', '舆情'],
            'QFD': ['质量功能展开', 'QFD', '质量屋'],
            '质量管理': ['质量管理', '质量控制', '质量改进'],
        }

        # 检查是否有映射
        for key, values in keyword_mapping.items():
            if key in query:
                return values

        # 没有映射，返回原查询
        return [query]

    def _parse_response(self, response: dict) -> List[Dict]:
        """解析 API 响应"""
        papers = []
        content = response.get('content', [])

        for item in content:
            # 清理标题中的 HTML 标签
            title = item.get('title', '')
            title = re.sub(r'<[^>]+>', '', title)

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
            first_page = item.get('first_page', '')
            last_page = item.get('last_page', '')

            journal_info = source
            if volume:
                journal_info += f', {volume}'
            if issue:
                journal_info += f'({issue})'
            if first_page:
                journal_info += f':{first_page}'
                if last_page:
                    journal_info += f'-{last_page}'

            papers.append({
                'id': item.get('id', ''),
                'title': title,
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

            for paper in papers:
                title = paper.get('title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_papers.append(paper)

            await asyncio.sleep(2)

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


# 测试代码
async def test_pubscholar():
    """测试 PubScholar 搜索"""
    print("=" * 80)
    print("测试 PubScholar 搜索服务")
    print("=" * 80)

    async with PubScholarService(headless=True) as service:
        # 测试搜索
        test_queries = [
            "投资者情绪",
            "分析师预测",
        ]

        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"搜索: {query}")
            print('='*60)

            papers = await service.search_papers(
                query=query,
                years_ago=10,
                max_results=5
            )

            for i, paper in enumerate(papers, 1):
                title = paper.get('title', 'N/A')
                year = paper.get('year', 'N/A')
                authors = paper.get('authors', [])
                author_str = ', '.join(authors[:3]) if authors else 'N/A'
                journal = paper.get('journal_info', 'N/A')
                abstract = paper.get('abstract', '')[:100]

                print(f"\n{i}. [{year}] {title}")
                print(f"   作者: {author_str}")
                print(f"   期刊: {journal}")
                if abstract:
                    print(f"   摘要: {abstract}...")


if __name__ == "__main__":
    asyncio.run(test_pubscholar())
