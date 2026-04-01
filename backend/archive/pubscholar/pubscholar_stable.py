"""
PubScholar 中文文献搜索服务 - 稳定版本
使用专业检索功能，支持双关键词
"""
import asyncio
import re
from typing import List, Dict, Optional
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PubScholarStable:
    """PubScholar 稳定搜索服务"""

    BASE_URL = "https://pubscholar.cn"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")

        print("[PubScholar] 正在初始化...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )

        self.page = await self.context.new_page()
        await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)
        print("[PubScholar] 初始化完成")

    async def open_advanced_dialog(self):
        """打开高级检索弹窗"""
        print("[PubScholar] 打开高级检索...")

        # 使用文本选择器查找高级检索按钮
        try:
            btn = await self.page.wait_for_selector('button:has-text("高级检索")', timeout=10000)
            await btn.click()
            await asyncio.sleep(1)
            print("[PubScholar] ✓ 弹窗已打开")
            return True
        except Exception as e:
            print(f"[PubScholar] 打开弹窗失败: {e}")
            return False

    async def switch_to_professional(self):
        """切换到专业检索tab"""
        print("[PubScholar] 切换到专业检索...")

        # 等待弹窗加载
        await asyncio.sleep(1)

        # 使用 JavaScript 查找并点击专业检索tab
        result = await self.page.evaluate('''() => {
            // 查找所有包含"专业检索"的元素
            const elements = document.querySelectorAll('*');
            for (const elem of elements) {
                const text = elem.textContent || '';
                if (text === '专业检索' || text.trim() === '专业检索') {
                    // 点击元素
                    elem.click();
                    return { success: true, found: true };
                }
            }
            return { success: false, found: false };
        }''')

        if result.get('success'):
            await asyncio.sleep(1)  # 等待tab切换
            print("[PubScholar] ✓ 已切换到专业检索")

            # 验证切换成功
            has_textarea = await self.page.evaluate('''() => {
                const ta = document.querySelector('textarea');
                return ta && ta.offsetParent !== null;
            }''')

            if has_textarea:
                print("[PubScholar] ✓ 输入框已显示")
            else:
                print("[PubScholar] 输入框未显示")

            return True
        else:
            print("[PubScholar] 未找到专业检索tab")
            return False

    async def input_query(self, query: str):
        """输入检索式"""
        print(f"[PubScholar] 输入检索式: {query}")

        # 先清空，再输入
        try:
            # 查找 textarea
            textarea = await self.page.wait_for_selector('textarea', timeout=5000)
            await textarea.click()
            await asyncio.sleep(0.2)

            # 清空
            await textarea.fill('')
            await asyncio.sleep(0.2)

            # 输入
            await textarea.type(query, delay=50)
            await asyncio.sleep(0.5)

            # 验证输入
            value = await textarea.input_value()
            if query in value:
                print("[PubScholar] ✓ 检索式已输入")
                return True
            else:
                # 使用 JS 直接设置
                await self.page.evaluate(f'''(query) => {{
                    const ta = document.querySelector('textarea');
                    if (ta) {{
                        ta.value = query;
                        ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}''', query)
                await asyncio.sleep(0.3)
                print("[PubScholar] ✓ 检索式已输入(JS)")
                return True
        except Exception as e:
            print(f"[PubScholar] 输入失败: {e}")
            return False

    async def click_search(self):
        """点击检索按钮"""
        print("[PubScholar] 点击检索按钮...")

        try:
            # 查找检索按钮
            btn = await self.page.wait_for_selector('button:has-text("检索")', timeout=5000)
            await btn.click()
            await asyncio.sleep(1)
            print("[PubScholar] ✓ 已点击检索")
            return True
        except:
            # 备用方案：使用 JS
            result = await self.page.evaluate('''() => {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = btn.textContent || '';
                    if (text === '检索' || text.trim() === '检索') {
                        btn.click();
                        return { success: true };
                    }
                }
                return { success: false };
            }''')

            if result.get('success'):
                await asyncio.sleep(1)
                print("[PubScholar] ✓ 已点击检索(JS)")
                return True
            else:
                print("[PubScholar] 点击失败")
                return False

    async def search_by_query(
        self,
        query: str,
        max_results: int = 50
    ) -> List[Dict]:
        """使用检索式搜索"""
        if not self.page:
            await self.initialize()

        try:
            # 打开弹窗
            if not await self.open_advanced_dialog():
                return []

            # 切换到专业检索
            if not await self.switch_to_professional():
                return []

            # 输入检索式
            if not await self.input_query(query):
                return []

            # 点击检索
            if not await self.click_search():
                return []

            # 等待结果
            print("[PubScholar] 等待结果...")
            await asyncio.sleep(5)
            await self.page.wait_for_load_state('networkidle', timeout=20000)

            # 保存调试截图
            await self.page.screenshot(path="pubscholar_stable_result.png", full_page=True)
            print("[PubScholar] 已保存截图: pubscholar_stable_result.png")

            # 滚动加载更多
            for _ in range(5):
                await self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
                await asyncio.sleep(0.5)

            # 抓取结果
            papers = await self._scrape_results(max_results)
            print(f"[PubScholar] 找到 {len(papers)} 篇文献")
            return papers

        except Exception as e:
            print(f"[PubScholar] 搜索失败: {e}")
            return []

    async def _scrape_results(self, max_results: int) -> List[Dict]:
        """从页面抓取结果"""
        papers = []
        seen_titles = set()

        # 先尝试检查页面结构
        page_info = await self.page.evaluate('''() => {
            return {
                bodyText: document.body.textContent.substring(0, 500),
                allClasses: Array.from(document.querySelectorAll('[class*="item"], [class*="paper"], [class*="article"], [class*="result"]'))
                    .map(el => el.className)
                    .slice(0, 20),
                linkCount: document.querySelectorAll('a').length,
                hasResults: document.body.textContent.includes('篇') || document.body.textContent.includes('结果')
            };
        }''')

        print(f"[PubScholar] 页面信息: hasResults={page_info.get('hasResults')}, links={page_info.get('linkCount')}")
        print(f"[PubScholar] 页面文本预览: {page_info.get('bodyText', '')[:200]}")

        papers_data = await self.page.evaluate(r'''() => {
            const papers = [];

            // 尝试更多选择器
            const selectors = [
                '.paper-item',
                '.article-item',
                '.result-item',
                '.list-item',
                '[class*="paper-item"]',
                '[class*="article-item"]',
                '[class*="result-item"]',
                '[class*="list-item"]',
                'article',
                '.item',
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

            // 如果还是找不到，尝试包含中文标题的链接
            if (items.length === 0) {
                const links = Array.from(document.querySelectorAll('a'));
                items = links.filter(a => {
                    const text = a.textContent || '';
                    return text.length > 10 && text.length < 200 && /[\u4e00-\u9fff]{5,}/.test(text);
                });
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

                    const sourceElem = item.querySelector('[class*="journal"], [class*="source"]');
                    const source = sourceElem ? sourceElem.textContent.trim() : '';

                    let year = null;
                    const yearMatch = item.textContent.match(/(20\d{2})/);
                    if (yearMatch) year = parseInt(yearMatch[1]);

                    const abstractElem = item.querySelector('[class*="abstract"]');
                    const abstract = abstractElem ? abstractElem.textContent.trim().slice(0, 500) : '';

                    const linkElem = item.tagName === 'A' ? item : item.querySelector('a[href*="article"]');
                    const url = linkElem ? linkElem.getAttribute('href') : '';

                    papers.push({ title, authors, year, source, abstract, url });
                } catch (e) {}
            }

            return papers;
        }''')

        for paper_data in papers_data:
            title = paper_data.get('title', '')
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

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

    def build_query(
        self,
        title_keywords: List[str] = None,
        keyword_keywords: List[str] = None,
        year_start: int = None,
        year_end: int = None
    ) -> str:
        """构建检索式"""
        parts = []

        if title_keywords:
            parts.append('TI=' + ' '.join([f'"{kw}"' for kw in title_keywords]))

        if keyword_keywords:
            parts.append('KY=' + ' '.join([f'"{kw}"' for kw in keyword_keywords]))

        if year_start or year_end:
            start = year_start if year_start else 1900
            end = year_end if year_end else datetime.now().year
            parts.append(f'PY=[{start} TO {end}]')

        return ' AND '.join(parts)

    async def search_dual_keywords(
        self,
        keyword1: str,
        keyword2: str = None,
        years_ago: int = 10,
        max_results: int = 50
    ) -> List[Dict]:
        """双关键词搜索"""
        current_year = datetime.now().year
        start_year = current_year - years_ago

        title_parts = [f'"{keyword1}"']
        if keyword2:
            title_parts.append(f'"{keyword2}"')

        query = f'TI={" ".join(title_parts)} AND PY=[{start_year} TO {current_year}]'
        return await self.search_by_query(query, max_results)

    async def close(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()


# 测试
async def test():
    print("="*60)
    print("测试 PubScholar 稳定服务")
    print("="*60)

    async with PubScholarStable(headless=False) as service:
        # 测试双关键词
        papers = await service.search_dual_keywords(
            keyword1="大数据",
            keyword2="并行计算",
            years_ago=5,
            max_results=20
        )

        print(f"\n找到 {len(papers)} 篇:")
        for i, p in enumerate(papers[:5], 1):
            print(f"{i}. [{p.get('year')}] {p.get('title')}")


if __name__ == "__main__":
    asyncio.run(test())
