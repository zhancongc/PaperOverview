"""
PubScholar 中文文献搜索服务 - 从页面直接抓取
"""
import asyncio
import re
from typing import List, Dict
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PubScholarPageScraper:
    """PubScholar 页面抓取服务 - 直接从页面提取中文文献"""

    BASE_URL = "https://pubscholar.cn"

    def __init__(self, headless: bool = True):
        self.headless = headless

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
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
        self.page = await self.context.new_page()

        await self.page.goto(f"{self.BASE_URL}/explore", wait_until="networkidle")

    async def search_papers(
        self,
        query: str,
        years_ago: int = 10,
        max_results: int = 20
    ) -> List[Dict]:
        """搜索中文文献"""
        if not self.page:
            await self.initialize()

        print(f"[PubScholar] 搜索: {query}")

        try:
            # 清空并输入搜索关键词
            search_box = await self.page.wait_for_selector(
                'input[placeholder*="发现你感兴趣的内容"]',
                timeout=10000
            )

            await search_box.fill('')
            await search_box.fill(query)
            await asyncio.sleep(0.5)
            await search_box.press('Enter')

            # 等待结果加载
            await asyncio.sleep(3)

            # 滚动加载更多
            for _ in range(3):
                await self.page.evaluate('window.scrollBy(0, 500)')
                await asyncio.sleep(0.5)

            # 从页面抓取结果
            papers = await self._scrape_from_page(max_results)

            print(f"[PubScholar] 找到 {len(papers)} 篇中文文献")
            return papers

        except Exception as e:
            print(f"[PubScholar] 搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _scrape_from_page(self, max_results: int) -> List[Dict]:
        """从页面直接抓取文献信息"""
        # 使用 JavaScript 从页面提取信息
        papers_data = await self.page.evaluate('''() => {
            const papers = [];

            // 尝试多种选择器
            const selectors = [
                '.paper-item',
                '.article-item',
                '[class*="result-item"]',
                '[class*="search-result"]'
            ];

            let items = [];
            for (const selector of selectors) {
                items = document.querySelectorAll(selector);
                if (items.length > 0) break;
            }

            // 如果没有找到结构化结果，尝试从整个页面中提取
            if (items.length === 0) {
                // 查找所有可能包含文献信息的元素
                const allElements = document.querySelectorAll('*');
                const potentialPapers = new Set();

                for (const elem of allElements) {
                    const text = elem.textContent || '';
                    // 查找包含中文标题的元素
                    if (text.length > 10 && text.length < 200 &&
                        /[\u4e00-\u9fff]{3,}/.test(text)) {
                        potentialPapers.add(elem);
                    }
                }

                items = Array.from(potentialPapers).slice(0, 20);
            }

            for (const item of items) {
                try {
                    // 提取标题
                    const titleElem = item.querySelector('[class*="title"]') ||
                                     item.querySelector('h3, h4, h5');
                    const title = titleElem ? titleElem.textContent.trim() : item.textContent.trim().slice(0, 100);

                    // 过滤：只保留包含中文的标题
                    if (!/[\u4e00-\u9fff]/.test(title)) continue;

                    // 提取作者
                    const authorElem = item.querySelector('[class*="author"]');
                    const authors = authorElem ?
                        authorElem.textContent.split(/[,，、]/).map(a => a.trim()) : [];

                    // 提取来源
                    const sourceElem = item.querySelector('[class*="journal"], [class*="source"]');
                    const source = sourceElem ? sourceElem.textContent.trim() : '';

                    // 提取年份
                    const yearMatch = title.match(/(20\d{2})/) ||
                                     item.textContent.match(/(20\d{2})/);
                    const year = yearMatch ? parseInt(yearMatch[1]) : null;

                    papers.push({
                        title: title,
                        authors: authors,
                        year: year,
                        source: source,
                        hasChinese: true
                    });
                } catch (e) {
                    // 忽略错误
                }
            }

            return papers;
        }''')

        # 转换为统一格式
        papers = []
        seen_titles = set()

        for paper_data in papers_data:
            title = paper_data.get('title', '')
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            # 清理标题
            title = re.sub(r'<[^>]+>', '', title)
            title = re.sub(r'\s+', ' ', title).strip()

            papers.append({
                'id': '',
                'title': title,
                'authors': paper_data.get('authors', []),
                'year': paper_data.get('year'),
                'cited_by_count': 0,
                'is_english': False,
                'abstract': '',
                'type': 'article',
                'doi': '',
                'journal': paper_data.get('source', ''),
                'journal_info': paper_data.get('source', ''),
                'keywords': [],
                'data_source': 'PubScholar'
            })

        return papers[:max_results]

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
async def test_pubscholar_scraper():
    """测试 PubScholar 页面抓取"""
    print("=" * 80)
    print("测试 PubScholar 页面抓取服务")
    print("=" * 80)

    async with PubScholarPageScraper(headless=True) as service:
        # 测试搜索
        test_queries = [
            "投资者情绪",
            "分析师预测",
            "媒体关注度",
        ]

        all_papers = []

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
                author_str = '、'.join(authors[:3]) if authors else 'N/A'
                source = paper.get('journal', 'N/A')

                print(f"\n{i}. [{year}] {title}")
                if author_str != 'N/A':
                    print(f"   作者: {author_str}")
                if source != 'N/A':
                    print(f"   来源: {source}")

            all_papers.extend(papers)

        # 去重统计
        seen = set()
        unique = []
        for p in all_papers:
            t = p.get('title', '')
            if t and t not in seen:
                seen.add(t)
                unique.append(p)

        print("\n" + "=" * 80)
        print(f"总计: {len(unique)} 篇不重复中文文献")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_pubscholar_scraper())
