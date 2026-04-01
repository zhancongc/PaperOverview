"""
PubScholar 中文文献搜索服务 - 使用专业检索功能
流程：首页 -> 高级检索 -> 专业检索tab -> 输入检索式 -> 检索
"""
import asyncio
import re
from typing import List, Dict, Optional
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[PubScholar] Playwright 未安装，请运行: pip install playwright && python -m playwright install chromium")


class PubScholarProfessionalSearch:
    """PubScholar 专业检索服务"""

    BASE_URL = "https://pubscholar.cn"

    # 检索式字段代码
    FIELD_CODES = {
        'title': 'TI',      # 标题
        'keyword': 'KY',    # 关键词
        'author': 'AU',     # 作者
        'abstract': 'AB',   # 摘要
        'subject': 'TS',    # 主题
        'affiliation': 'AF', # 机构
        'source': 'SO',     # 出版物
        'year': 'PY',       # 出版年
    }

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
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )

        # 创建新页面
        self.page = await self.context.new_page()

        # 访问 PubScholar 首页
        print("[PubScholar] 正在初始化浏览器会话...")
        await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        print("[PubScholar] 会话建立成功")

    def build_search_query(
        self,
        title_keywords: Optional[List[str]] = None,
        keyword_keywords: Optional[List[str]] = None,
        author_exclude: Optional[str] = None,
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
            year_start: 起始年份
            year_end: 结束年份
            abstract_keywords: 摘要关键词列表（AND关系）

        Returns:
            专业检索式字符串

        示例:
            build_search_query(
                title_keywords=["大数据", "人工智能"],
                keyword_keywords=["经济"],
                author_exclude="张*",
                year_start=2015,
                year_end=2023
            )
            返回: 'TI="大数据" "人工智能" AND KY=经济 AND NOT AU=张* AND PY=[2015 TO 2023]'
        """
        parts = []

        # 标题条件 - 多个关键词用空格表示AND
        if title_keywords:
            # TI="关键词1" "关键词2" 表示标题同时包含多个关键词
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

    async def open_advanced_search(self):
        """打开高级检索弹窗"""
        print("[PubScholar] 正在打开高级检索弹窗...")

        # 确保在首页
        if not self.page.url or self.page.url == f"{self.BASE_URL}/":
            await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=15000)

        # 使用用户提供的 xpath 点击"高级检索"按钮
        try:
            # 等待按钮加载
            advanced_btn = await self.page.wait_for_selector(
                'xpath=//*[@id="app"]/div[2]/div[1]/div[1]/div/main/section[1]/div/div[2]/div/div[2]/span/span/div/button',
                timeout=10000
            )
            if advanced_btn:
                await advanced_btn.click()
                await asyncio.sleep(1)
                print("[PubScholar] ✓ 高级检索弹窗已打开")
                return
        except Exception as e:
            print(f"[PubScholar] 使用xpath点击失败: {e}")

        # 备用方案：使用文本选择器
        selectors = [
            'button:has-text("高级检索")',
            'span:has-text("高级检索")',
        ]

        for selector in selectors:
            try:
                elem = await self.page.wait_for_selector(selector, timeout=5000)
                if elem:
                    await elem.click()
                    await asyncio.sleep(1)
                    print("[PubScholar] ✓ 高级检索弹窗已打开（备用方案）")
                    return
            except:
                continue

    async def switch_to_professional_tab(self):
        """切换到专业检索tab"""
        print("[PubScholar] 正在切换到专业检索tab...")

        # 等待弹窗加载
        await asyncio.sleep(0.5)

        # 使用用户提供的 xpath 点击"专业检索"按钮
        try:
            # 尝试点击专业检索tab
            prof_tab = await self.page.wait_for_selector(
                'xpath=/html/body/div[7]/div/div[2]/div/div[1]/div/div/div/div/div[1]/div[2]',
                timeout=5000
            )
            if prof_tab:
                await prof_tab.click()
                await asyncio.sleep(0.5)
                print("[PubScholar] ✓ 已切换到专业检索tab")
                return
        except Exception as e:
            print(f"[PubScholar] 使用xpath点击专业检索tab失败: {e}")

        # 备用方案：使用文本选择器
        selectors = [
            'div:has-text("专业检索")',
            'button:has-text("专业检索")',
            'span:has-text("专业检索")',
        ]

        for selector in selectors:
            try:
                elem = await self.page.wait_for_selector(selector, timeout=3000)
                if elem:
                    await elem.click()
                    await asyncio.sleep(0.5)
                    print("[PubScholar] ✓ 已切换到专业检索tab（备用方案）")
                    return
            except:
                continue

        print("[PubScholar] 未找到专业检索tab")

    async def input_search_query(self, query: str):
        """在专业检索式输入框中输入检索式"""
        print(f"[PubScholar] 输入检索式: {query}")

        # 使用用户提供的 xpath 点击并输入
        try:
            # 先点击输入框获取焦点
            textarea = await self.page.wait_for_selector(
                'xpath=/html/body/div[7]/div/div[2]/div/div[1]/div/div/div/div/div[2]/div/div[2]/div/textarea',
                timeout=5000
            )
            if textarea:
                await textarea.click()
                await asyncio.sleep(0.2)
                await textarea.fill(query)
                await asyncio.sleep(0.3)
                print("[PubScholar] ✓ 检索式已输入")
                return
        except Exception as e:
            print(f"[PubScholar] 使用xpath输入失败: {e}")

        # 备用方案：查找textarea
        try:
            textareas = await self.page.query_selector_all('textarea')
            for ta in textareas:
                placeholder = await ta.get_attribute('placeholder') or ''
                if '检索' in placeholder or '式' in placeholder or '查询' in placeholder:
                    await ta.click()
                    await asyncio.sleep(0.2)
                    await ta.fill(query)
                    await asyncio.sleep(0.3)
                    print("[PubScholar] ✓ 检索式已输入（备用方案）")
                    return
        except Exception as e:
            print(f"[PubScholar] 备用方案也失败: {e}")

    async def click_search_button(self):
        """点击检索按钮"""
        print("[PubScholar] 正在点击检索按钮...")

        # 使用用户提供的 xpath 点击"检索"按钮
        try:
            search_btn = await self.page.wait_for_selector(
                'xpath=/html/body/div[7]/div/div[2]/div/div[1]/div/div/div/div/div[2]/div/div[3]/button[1]',
                timeout=5000
            )
            if search_btn:
                await search_btn.click()
                await asyncio.sleep(1)
                print("[PubScholar] ✓ 已点击检索按钮")
                return
        except Exception as e:
            print(f"[PubScholar] 使用xpath点击检索按钮失败: {e}")

        # 备用方案：使用文本选择器
        selectors = [
            'button:has-text("检索")',
            'button.btn-primary',
            'button[type="submit"]',
        ]

        for selector in selectors:
            try:
                btn = await self.page.wait_for_selector(selector, timeout=3000)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    print("[PubScholar] ✓ 已点击检索按钮（备用方案）")
                    return
            except:
                continue

        print("[PubScholar] 未找到检索按钮")

    async def search_by_query(
        self,
        query: str,
        max_results: int = 20,
        wait_time: int = 3
    ) -> List[Dict]:
        """
        使用专业检索式搜索文献

        Args:
            query: 专业检索式
            max_results: 最大结果数
            wait_time: 等待加载时间（秒）

        Returns:
            文献列表
        """
        if not self.page:
            await self.initialize()

        print(f"[PubScholar] 专业检索: {query}")

        try:
            # 1. 打开高级检索
            await self.open_advanced_search()
            await self.page.screenshot(path="pubscholar_step1_advanced.png")

            # 2. 切换到专业检索tab
            await self.switch_to_professional_tab()
            await self.page.screenshot(path="pubscholar_step2_professional_tab.png")

            # 3. 输入检索式
            await self.input_search_query(query)
            await self.page.screenshot(path="pubscholar_step3_input.png")

            # 4. 点击检索按钮
            await self.click_search_button()
            await self.page.screenshot(path="pubscholar_step4_click_search.png")

            # 5. 等待结果加载
            print(f"[PubScholar] 等待结果加载...")
            await asyncio.sleep(wait_time)
            await self.page.wait_for_load_state('networkidle', timeout=15000)

            # 6. 滚动加载更多结果
            await self._scroll_to_load_more()

            # 7. 保存最终截图
            await self.page.screenshot(path="pubscholar_professional_debug.png", full_page=True)

            # 8. 抓取结果
            papers = await self._scrape_results(max_results)

            print(f"[PubScholar] 找到 {len(papers)} 篇文献")
            return papers

        except Exception as e:
            print(f"[PubScholar] 检索失败: {e}")
            import traceback
            traceback.print_exc()
            # 保存错误截图
            try:
                await self.page.screenshot(path="pubscholar_error.png", full_page=True)
            except:
                pass
            return []

    async def search_dual_keywords(
        self,
        keyword1: str,
        keyword2: Optional[str] = None,
        years_ago: int = 10,
        max_results: int = 20
    ) -> List[Dict]:
        """
        双关键词搜索 - 使用专业检索

        Args:
            keyword1: 第一个关键词（标题）
            keyword2: 第二个关键词（关键词字段）
            years_ago: 近N年
            max_results: 最大结果数

        Returns:
            文献列表
        """
        current_year = datetime.now().year
        start_year = current_year - years_ago

        # 构建检索式: TI="关键词1" AND KY="关键词2" AND PY=[年份]
        parts = [f'TI="{keyword1}"']
        if keyword2:
            parts.append(f'KY="{keyword2}"')
        parts.append(f'PY=[{start_year} TO {current_year}]')

        query = ' AND '.join(parts)

        return await self.search_by_query(query, max_results=max_results)

    async def search_by_keywords(
        self,
        keywords: List[str],
        search_in: str = "title",  # title, keyword, abstract
        years_ago: int = 10,
        max_results: int = 20
    ) -> List[Dict]:
        """
        多关键词搜索

        Args:
            keywords: 关键词列表（OR关系，任一匹配即可）
            search_in: 搜索字段 (title/keyword/abstract)
            years_ago: 近N年
            max_results: 最大结果数

        Returns:
            文献列表
        """
        current_year = datetime.now().year
        start_year = current_year - years_ago

        # 获取字段代码
        field_code = self.FIELD_CODES.get(search_in, 'TI')

        # 构建检索式: TI=关键词1 关键词2 (空格表示OR)
        keywords_part = ' '.join(keywords)
        query = f'{field_code}={keywords_part} AND PY=[{start_year} TO {current_year}]'

        return await self.search_by_query(query, max_results=max_results)

    async def _scroll_to_load_more(self):
        """滚动加载更多结果"""
        for i in range(5):
            await self.page.evaluate('window.scrollBy(0, window.innerHeight)')
            await asyncio.sleep(0.8)

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
async def test_professional_search():
    """测试专业检索"""

    print("=" * 80)
    print("测试 PubScholar 专业检索")
    print("=" * 80)

    async with PubScholarProfessionalSearch(headless=False) as service:
        # 测试1: 使用预定义方法进行双关键词搜索
        print("\n" + "=" * 60)
        print("测试双关键词搜索: 标题[投资者情绪] + 关键词[分析师预测]")
        print("=" * 60)

        papers = await service.search_dual_keywords(
            keyword1="投资者情绪",
            keyword2="分析师预测",
            years_ago=10,
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

        # 测试2: 使用自定义检索式
        print("\n" + "=" * 60)
        print("测试自定义检索式")
        print("=" * 60)

        # TI="大数据" "人工智能" AND KY=经济 AND PY=[2018 TO 2023]
        custom_query = 'TI="大数据" "人工智能" AND KY=经济 AND PY=[2018 TO 2023]'
        print(f"检索式: {custom_query}")

        papers2 = await service.search_by_query(
            query=custom_query,
            max_results=10
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
            year_start=2020,
            year_end=2023
        )
        print(f"构建的检索式: {query}")

        papers3 = await service.search_by_query(
            query=query,
            max_results=10
        )

        print(f"\n找到 {len(papers3)} 篇文献")
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
    asyncio.run(test_professional_search())
