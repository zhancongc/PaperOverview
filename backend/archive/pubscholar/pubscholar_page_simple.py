"""
PubScholar 页面搜索服务 - 直接操作页面进行搜索
避免API频率限制
"""
import asyncio
import json
from typing import List, Dict
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PubScholarPageSearchService:
    """PubScholar 页面搜索服务 - 直接操作页面"""

    BASE_URL = "https://pubscholar.cn"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._initialized = False

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")

        if self._initialized:
            return

        print("[PubScholar] 正在初始化浏览器...")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )

        self.page = await self.context.new_page()

        # 访问首页
        await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        self._initialized = True
        print("[PubScholar] ✓ 浏览器初始化完成")

    async def search_papers(
        self,
        keywords: List[str],
        year_start: int = 2016,
        year_end: int = 2026,
        max_results: int = 50
    ) -> List[Dict]:
        """
        在页面上进行搜索

        Args:
            keywords: 关键词列表
            year_start: 开始年份
            year_end: 结束年份
            max_results: 最大结果数

        Returns:
            文献列表
        """
        if not self._initialized:
            await self.initialize()

        # 构建搜索查询
        query = ' '.join(keywords)
        print(f"[PubScholar] 搜索查询: {query}")

        try:
            # 使用JavaScript设置搜索框的值
            result = await self.page.evaluate(f'''(query) => {{
                const searchBox = document.querySelector('input[placeholder*="发现你感兴趣的内容"]');
                if (searchBox) {{
                    searchBox.value = query;
                    searchBox.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    searchBox.dispatchEvent(new Event('change', {{ bubbles: true }}'));
                    return {{ success: true }};
                }}
                return {{ success: false }};
            }}''', query)

            if result.get('success'):
                await asyncio.sleep(0.5)
                print("[PubScholar] 已输入搜索词")

                # 点击搜索按钮
                search_result = await self.page.evaluate('''() => {
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        if (btn.textContent.includes('搜索') || btn.getAttribute('class').includes('search')) {
                            btn.click();
                            return { success: true };
                        }
                    }
                    return { success: false };
                }''')

                if search_result.get('success'):
                    print("[PubScholar] 已点击搜索按钮")
                else:
                    # 尝试按回车
                    await self.page.keyboard.press('Enter')
                    print("[PubScholar] 已按回车")

                await asyncio.sleep(3)
                await self.page.wait_for_load_state('networkidle', timeout=15000)

                # 检查当前URL
                current_url = self.page.url
                print(f"[PubScholar] 当前URL: {current_url}")

                # 保存截图
                await self.page.screenshot(path="pubscholar_page_search_result.png", full_page=True)
                print("[PubScholar] 已保存截图")

                # 滚动加载更多结果
                for _ in range(5):
                    await self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
                    await asyncio.sleep(0.8)

                # 抓取结果
                papers = await self._scrape_results(max_results)
                print(f"[PubScholar] ✓ 找到 {len(papers)} 篇文献")
                return papers

        except Exception as e:
            print(f"[PubScholar] 搜索失败: {e}")

            # 方法2: 尝试直接导航到搜索结果页面
            try:
                from urllib.parse import quote
                search_url = f"{self.BASE_URL}/explore?keywords={quote(query)}"
                await self.page.goto(search_url, wait_until="networkidle", timeout=15000)
                await asyncio.sleep(3)

                # 滚动加载更多结果
                for _ in range(5):
                    await self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
                    await asyncio.sleep(0.8)

                papers = await self._scrape_results(max_results)
                print(f"[PubScholar] ✓ 找到 {len(papers)} 篇文献（方法2）")
                return papers
            except Exception as e2:
                print(f"[PubScholar] 方法2也失败: {e2}")
                return []

    async def _scrape_results(self, max_results: int) -> List[Dict]:
        """从页面抓取结果"""
        papers = []
        seen_titles = set()

        # 使用 JavaScript 从页面提取信息
        papers_data = await self.page.evaluate(r'''() => {
            const papers = [];

            // 尝试多种选择器
            const selectors = [
                '.paper-item',
                '.article-item',
                '.result-item',
                '[class*="paper-item"]',
                '[class*="article-item"]',
                '[class*="result-item"]',
                'article',
                '[class*="card"]'
            ];

            let items = [];
            for (const selector of selectors) {
                items = Array.from(document.querySelectorAll(selector));
                if (items.length > 0) {
                    console.log(`Found ${items.length} items with: ${selector}`);
                    break;
                }
            }

            // 如果还是找不到，尝试查找包含中文标题的链接
            if (items.length === 0) {
                const links = Array.from(document.querySelectorAll('a[href]'));
                items = links.filter(a => {
                    const text = a.textContent || '';
                    return text.length > 10 && text.length < 200 && /[\u4e00-\u9fff]{5,}/.test(text);
                });
                console.log(`Found ${items.length} items with Chinese title links`);
            }

            for (const item of items) {
                try {
                    const titleElem = item.querySelector('[class*="title"]') ||
                                     item.querySelector('h1, h2, h3, h4, h5, h6');
                    let title = titleElem ? titleElem.textContent.trim() : '';
                    if (!title) {
                        title = item.textContent || '';
                    }
                    title = title.replace(/\s+/g, ' ').trim();

                    if (!title || !/[\u4e00-\u9fff]/.test(title) || title.length < 5) continue;

                    const authorElem = item.querySelector('[class*="author"]');
                    let authors = [];
                    if (authorElem) {
                        authors = authorElem.textContent.split(/[,，、\n]/).map(a => a.trim()).filter(a => a);
                    }

                    const sourceElem = item.querySelector('[class*="journal"], [class*="source"], [class*="publisher"]');
                    const source = sourceElem ? sourceElem.textContent.trim() : '';

                    let year = null;
                    const yearMatch = item.textContent.match(/(20\d{2})/);
                    if (yearMatch) year = parseInt(yearMatch[1]);

                    const abstractElem = item.querySelector('[class*="abstract"]');
                    const abstract = abstractElem ? abstractElem.textContent.trim().slice(0, 500) : '';

                    const linkElem = item.tagName === 'A' ? item : item.querySelector('a[href]');
                    const url = linkElem ? linkElem.getAttribute('href') : '';

                    papers.push({ title, authors, year, source, abstract, url });
                } catch (e) {}
            }

            return papers;
        }''')

        # 转换为统一格式
        for paper_data in papers_data:
            title = paper_data.get('title', '')
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            import re
            title = re.sub(r'<[^>]+>', '', title)
            title = re.sub(r'\s+', ' ', title).strip()

            source = paper_data.get('source', '')
            year = paper_data.get('year')
            journal_info = f"{source}, {year}" if year and source else source

            papers.append({
                'id': paper_data.get('url', ''),
                'title': title,
                'authors': paper_data.get('authors', []),
                'year': year,
                'cited_by_count': 0,
                'is_english': False,
                'abstract': paper_data.get('abstract', ''),
                'type': 'article',
                'doi': '',
                'journal': source,
                'journal_info': journal_info,
                'keywords': [],
                'data_source': 'PubScholar',
                'url': paper_data.get('url', '')
            })

            if len(papers) >= max_results:
                break

        return papers

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
async def test_pubscholar_page_search():
    """测试 PubScholar 页面搜索"""
    print("=" * 80)
    print("测试 PubScholar 页面搜索")
    print("=" * 80)

    async with PubScholarPageSearchService(headless=False) as service:
        # 测试1: 双关键词搜索
        print("\n" + "=" * 60)
        print("测试1: 大数据 并行计算")
        print("=" * 60)

        papers = await service.search_papers(
            keywords=["大数据", "并行计算"],
            max_results=20
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

        # 测试2: 投资者情绪相关
        print("\n" + "=" * 60)
        print("测试2: 投资者情绪 分析师预测")
        print("=" * 60)

        await asyncio.sleep(3)  # 等待避免频率限制

        papers2 = await service.search_papers(
            keywords=["投资者情绪", "分析师预测"],
            max_results=20
        )

        print(f"\n找到 {len(papers2)} 篇文献:")
        for i, paper in enumerate(papers2[:3], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            print(f"\n{i}. [{year}] {title}")

        # 统计
        all_papers = papers + papers2
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
    asyncio.run(test_pubscholar_page_search())
