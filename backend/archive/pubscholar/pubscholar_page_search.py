"""
PubScholar 中文文献搜索服务 - 使用专业检索页面并抓取结果
直接操作页面元素，不调用 API
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


class PubScholarPageSearch:
    """PubScholar 搜索服务 - 直接操作专业检索页面"""

    BASE_URL = "https://pubscholar.cn"

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

        # 访问首页
        await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
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

    async def open_professional_search(self):
        """打开专业检索页面"""
        print("[PubScholar] 正在打开专业检索...")

        # 点击高级检索按钮
        try:
            advanced_btn = await self.page.wait_for_selector(
                'xpath=//*[@id="app"]/div[2]/div[1]/div[1]/div/main/section[1]/div/div[2]/div/div[2]/span/span/div/button',
                timeout=10000
            )
            await advanced_btn.click()
            await asyncio.sleep(1)
            print("[PubScholar] ✓ 高级检索弹窗已打开")
        except:
            # 备用方案
            try:
                elem = await self.page.wait_for_selector('button:has-text("高级检索")', timeout=5000)
                await elem.click()
                await asyncio.sleep(1)
                print("[PubScholar] ✓ 高级检索弹窗已打开（备用）")
            except:
                print("[PubScholar] 打开高级检索失败")

        # 点击专业检索 tab
        try:
            prof_tab = await self.page.wait_for_selector(
                'xpath=/html/body/div[7]/div/div[2]/div/div[1]/div/div/div/div/div[1]/div[2]',
                timeout=5000
            )
            await prof_tab.click()
            await asyncio.sleep(0.5)
            print("[PubScholar] ✓ 已切换到专业检索")
        except:
            # 备用方案
            try:
                elem = await self.page.wait_for_selector('div:has-text("专业检索")', timeout=3000)
                await elem.click()
                await asyncio.sleep(0.5)
                print("[PubScholar] ✓ 已切换到专业检索（备用）")
            except:
                print("[PubScholar] 切换专业检索失败")

    async def input_query_and_search(self, query: str):
        """输入检索式并执行搜索"""
        print(f"[PubScholar] 输入检索式: {query}")

        # 点击输入框
        try:
            textarea = await self.page.wait_for_selector(
                'xpath=/html/body/div[7]/div/div[2]/div/div[1]/div/div/div/div/div[2]/div/div[2]/div/textarea',
                timeout=5000
            )
            await textarea.click()
            await asyncio.sleep(0.2)
            await textarea.fill(query)
            await asyncio.sleep(0.3)
            print("[PubScholar] ✓ 检索式已输入")
        except:
            # 备用方案
            try:
                ta = await self.page.wait_for_selector('textarea', timeout=3000)
                await ta.click()
                await asyncio.sleep(0.2)
                await ta.fill(query)
                await asyncio.sleep(0.3)
                print("[PubScholar] ✓ 检索式已输入（备用）")
            except:
                print("[PubScholar] 输入检索式失败")

        # 点击检索按钮
        try:
            search_btn = await self.page.wait_for_selector(
                'xpath=/html/body/div[7]/div/div[2]/div/div[1]/div/div/div/div/div[2]/div/div[3]/button[1]',
                timeout=5000
            )
            await search_btn.click()
            await asyncio.sleep(1)
            print("[PubScholar] ✓ 已点击检索按钮")
        except:
            # 备用方案
            try:
                btn = await self.page.wait_for_selector('button:has-text("检索")', timeout=3000)
                await btn.click()
                await asyncio.sleep(1)
                print("[PubScholar] ✓ 已点击检索按钮（备用）")
            except:
                print("[PubScholar] 点击检索按钮失败")

    async def search_by_query(
        self,
        query: str,
        max_results: int = 50,
        wait_time: int = 3
    ) -> List[Dict]:
        """使用专业检索式搜索文献"""
        if not self.page:
            await self.initialize()

        print(f"[PubScholar] 检索式: {query}")

        try:
            # 打开专业检索
            await self.open_professional_search()

            # 输入并执行搜索
            await self.input_query_and_search(query)

            # 等待结果加载
            print(f"[PubScholar] 等待结果加载...")
            await asyncio.sleep(wait_time)
            await self.page.wait_for_load_state('networkidle', timeout=15000)

            # 滚动加载更多
            for i in range(5):
                await self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
                await asyncio.sleep(0.5)

            # 保存截图
            await self.page.screenshot(path="pubscholar_search_result.png", full_page=True)

            # 抓取结果
            papers = await self._scrape_results(max_results)

            print(f"[PubScholar] 找到 {len(papers)} 篇文献")
            return papers

        except Exception as e:
            print(f"[PubScholar] 检索失败: {e}")
            import traceback
            traceback.print_exc()
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
                '[class*="article"]',
                '[class*="paper"]',
                '.search-result-item',
                '.list-item',
                '[class*="list-item"]'
            ];

            let items = [];
            for (const selector of selectors) {
                items = document.querySelectorAll(selector);
                if (items.length > 0) {
                    console.log(`Found ${items.length} items with selector: ${selector}`);
                    break;
                }
            }

            // 如果找不到结构化结果，尝试查找包含文献信息的元素
            if (items.length === 0) {
                const containers = document.querySelectorAll('[class*="item"], [class*="card"], [class*="result"], [class*="list"]');
                for (const container of containers) {
                    const text = container.textContent || '';
                    if (text.length > 20 && text.length < 500 &&
                        /[\u4e00-\u9fff]{5,}/.test(text)) {
                        items.push(container);
                    }
                }
            }

            for (const item of items) {
                try {
                    // 提取标题
                    const titleElem = item.querySelector('[class*="title"]') ||
                                     item.querySelector('h3, h4, h5, a[href*="article"]');
                    let title = titleElem ? titleElem.textContent.trim() : '';

                    title = title.replace(/\s+/g, ' ').trim();

                    if (!title || !/[\u4e00-\u9fff]/.test(title) || title.length < 5) {
                        continue;
                    }

                    // 提取作者
                    const authorElem = item.querySelector('[class*="author"]');
                    let authors = [];
                    if (authorElem) {
                        const authorText = authorElem.textContent;
                        authors = authorText.split(/[,，、\n]/).map(a => a.trim()).filter(a => a);
                    }

                    // 提取来源
                    const sourceElem = item.querySelector('[class*="journal"], [class*="source"], [class*="publisher"]');
                    const source = sourceElem ? sourceElem.textContent.trim() : '';

                    // 提取年份
                    let year = null;
                    const yearMatch = item.textContent.match(/(20\d{2})/);
                    if (yearMatch) {
                        year = parseInt(yearMatch[1]);
                    }

                    // 提取摘要
                    const abstractElem = item.querySelector('[class*="abstract"], [class*="summary"]');
                    const abstract = abstractElem ? abstractElem.textContent.trim().slice(0, 500) : '';

                    // 提取链接
                    const linkElem = item.querySelector('a[href*="article"]');
                    const url = linkElem ? linkElem.getAttribute('href') : '';

                    papers.push({
                        title: title,
                        authors: authors,
                        year: year,
                        source: source,
                        abstract: abstract,
                        url: url
                    });
                } catch (e) {
                    console.error('Error parsing item:', e);
                }
            }

            return papers;
        }''')

        # 转换为统一格式
        for paper_data in papers_data:
            title = paper_data.get('title', '')
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            # 清理标题
            title = re.sub(r'<[^>]+>', '', title)
            title = re.sub(r'\s+', ' ', title).strip()

            # 构建期刊信息
            source = paper_data.get('source', '')
            year = paper_data.get('year')
            journal_info = source
            if year and source:
                journal_info = f"{source}, {year}"

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

        return await self.search_by_query(query, max_results=max_results)

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
async def test_search():
    """测试搜索服务"""

    print("=" * 80)
    print("测试 PubScholar 搜索服务")
    print("=" * 80)

    async with PubScholarPageSearch(headless=False) as service:
        # 测试双关键词搜索
        print("\n" + "=" * 60)
        print("测试双关键词搜索: 标题包含[大数据]和[并行计算]")
        print("=" * 60)

        papers = await service.search_dual_keywords(
            keyword1="大数据",
            keyword2="并行计算",
            years_ago=5,
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

        # 测试自定义检索式
        print("\n" + "=" * 60)
        print("测试自定义检索式")
        print("=" * 60)

        query = service.build_search_query(
            title_keywords=["投资者情绪"],
            keyword_keywords=["分析师预测"],
            year_start=2020,
            year_end=2024
        )
        print(f"检索式: {query}")

        papers2 = await service.search_by_query(query, max_results=20)

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
    asyncio.run(test_search())
