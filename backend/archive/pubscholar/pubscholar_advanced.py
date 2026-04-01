"""
PubScholar 中文文献搜索服务 - 使用首页高级筛选功能
通过 https://pubscholar.cn/ 首页的高级筛选实现多关键词检索
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


class PubScholarAdvancedSearch:
    """PubScholar 高级筛选搜索服务"""

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

    async def search_dual_keywords(
        self,
        keyword1: str,
        keyword2: Optional[str] = None,
        years_ago: int = 10,
        max_results: int = 20
    ) -> List[Dict]:
        """
        使用高级筛选进行双关键词搜索

        高级筛选面板有两个固定输入框：
        - 第一个是"标题"输入框
        - 第二个是"关键词"输入框

        Args:
            keyword1: 标题关键词
            keyword2: 额外的关键词（可选）
            years_ago: 近N年
            max_results: 最大结果数

        Returns:
            文献列表
        """
        if not self.page:
            await self.initialize()

        print(f"[PubScholar] 高级搜索: 标题[{keyword1}]" + (f" + 关键词[{keyword2}]" if keyword2 else ""))

        try:
            # 1. 点击高级筛选按钮
            print("[PubScholar] 正在打开高级筛选...")
            await self._open_advanced_filter()

            # 2. 设置标题关键词（第一个输入框）
            await self._set_title_keyword(keyword1)

            # 3. 设置额外关键词（第二个输入框，如果提供）
            if keyword2:
                await self._set_extra_keyword(keyword2)

            # 4. 设置年份范围（如果支持）
            if years_ago:
                await self._set_year_range(years_ago)

            # 5. 点击搜索
            await self._click_search()

            # 6. 等待结果加载
            await asyncio.sleep(3)
            await self.page.wait_for_load_state('networkidle', timeout=15000)

            # 7. 滚动加载更多结果
            await self._scroll_to_load_more()

            # 8. 保存截图用于调试
            await self.page.screenshot(path="pubscholar_result_debug.png", full_page=True)

            # 9. 抓取结果
            papers = await self._scrape_results(max_results)

            print(f"[PubScholar] 找到 {len(papers)} 篇文献")
            return papers

        except Exception as e:
            print(f"[PubScholar] 搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _open_advanced_filter(self):
        """打开高级筛选面板"""
        # 尝试多种可能的选择器
        selectors = [
            'button:has-text("高级筛选")',
            'button:has-text("高级")',
            'a:has-text("高级筛选")',
            '.advanced-filter',
            '#advancedFilter',
            '[class*="advanced"]',
            '[class*="filter"]'
        ]

        for selector in selectors:
            try:
                elem = await self.page.wait_for_selector(selector, timeout=5000)
                if elem:
                    await elem.click()
                    await asyncio.sleep(1)
                    print("[PubScholar] 高级筛选面板已打开")
                    return
            except:
                continue

        # 如果找不到按钮，尝试截图查看页面状态
        await self.page.screenshot(path="pubscholar_debug.png")
        print("[PubScholar] 未找到高级筛选按钮，已保存截图到 pubscholar_debug.png")

        # 尝试直接导航到高级筛选页面
        await self.page.goto(f"{self.BASE_URL}/explore", wait_until="networkidle")
        await asyncio.sleep(2)

    async def _set_title_keyword(self, keyword: str):
        """在标题输入框中设置关键词（第一个输入框）"""
        print(f"[PubScholar] 设置标题关键词: {keyword}")

        # 使用 JavaScript 查找并设置标题输入框
        result = await self.page.evaluate('''(keyword) => {
            // 查找所有输入框
            const inputs = document.querySelectorAll('input[type="text"]');

            for (const input of inputs) {
                // 检查输入框前面的标签或父元素
                let parent = input.parentElement;
                let label = parent ? parent.querySelector('label') : null;
                let labelText = label ? label.textContent : '';

                // 检查父级的父级
                if (!labelText) {
                    let grandParent = parent ? parent.parentElement : null;
                    if (grandParent) {
                        label = grandParent.querySelector('label');
                        labelText = label ? label.textContent : '';
                    }
                }

                // 如果找到标题输入框
                if (labelText.includes('标题') || labelText.includes('Title')) {
                    input.value = keyword;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    return { success: true, message: 'Found title input' };
                }
            }

            return { success: false };
        }''', keyword)

        if result.get('success'):
            await asyncio.sleep(0.5)
            print(f"[PubScholar] ✓ 标题关键词已设置: {keyword}")
        else:
            print(f"[PubScholar] 未找到标题输入框")

    async def _add_keyword_condition(self):
        """点击添加按钮添加新的搜索条件"""
        print("[PubScholar] 添加新的搜索条件...")

        # 查找添加按钮
        selectors = [
            'button:has-text("+")',
            '.add-condition',
            '.add-filter',
            '[class*="add"] button',
            'button[class*="plus"]',
        ]

        for selector in selectors:
            try:
                buttons = await self.page.query_selector_all(selector)
                for btn in buttons:
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                        print("[PubScholar] ✓ 已添加新条件")
                        return
            except:
                continue

        # 使用 JavaScript 查找并点击添加按钮
        result = await self.page.evaluate('''() => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.textContent.includes('+') || btn.textContent.includes('添加')) {
                    btn.click();
                    return { success: true };
                }
            }
            return { success: false };
        }''')

        if result.get('success'):
            await asyncio.sleep(0.5)
            print("[PubScholar] ✓ 已添加新条件（通过JS）")

    async def _set_extra_keyword(self, keyword: str):
        """添加第二个条件并设置为关键词类型，然后输入关键词"""
        print(f"[PubScholar] 设置关键词条件: {keyword}")

        # 1. 先添加新条件
        await self._add_keyword_condition()

        # 2. 找到新添加的条件并切换类型到"关键词"
        await self._switch_condition_type(2, "关键词")

        # 3. 在第二个条件的输入框中输入关键词
        result = await self.page.evaluate('''(keyword) => {
            // 查找所有输入框
            const inputs = Array.from(document.querySelectorAll('input[type="text"]'));

            // 如果有多个输入框，使用第二个
            if (inputs.length >= 2) {
                const input = inputs[1];
                input.value = keyword;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                return { success: true, message: 'Set second input' };
            }

            return { success: false };
        }''', keyword)

        if result.get('success'):
            await asyncio.sleep(0.5)
            print(f"[PubScholar] ✓ 关键词已设置: {keyword}")
        else:
            print(f"[PubScholar] 设置关键词失败")

    async def _switch_condition_type(self, condition_index: int, target_type: str):
        """切换指定条件的类型"""
        print(f"[PubScholar] 切换条件 {condition_index} 类型到: {target_type}")

        # 使用 JavaScript 查找并切换下拉框
        result = await self.page.evaluate('''(args) => {
            const index = args.index;
            const targetType = args.targetType;

            // 查找所有下拉框
            const selects = document.querySelectorAll('select');

            if (selects.length >= index) {
                const select = selects[index - 1];
                // 查找目标选项
                for (const option of select.options) {
                    if (option.textContent.includes(targetType)) {
                        option.selected = true;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        return { success: true, message: 'Switched to ' + targetType };
                    }
                }
            }

            return { success: false };
        }''', {'index': condition_index, 'target_type': target_type})

        if result.get('success'):
            await asyncio.sleep(0.3)
            print(f"[PubScholar] ✓ 类型已切换")
        else:
            print(f"[PubScholar] 类型切换失败")

    async def _set_year_range(self, years_ago: int):
        """设置年份范围"""
        current_year = datetime.now().year
        start_year = current_year - years_ago

        # 尝试查找年份输入框或选择器
        selectors = [
            'input[name="startYear"]',
            'input[placeholder*="开始年份"]',
            'input[placeholder*="年份"]',
            '.year-input input',
            'select[name="year"]'
        ]

        for selector in selectors:
            try:
                year_input = await self.page.wait_for_selector(selector, timeout=2000)
                if year_input:
                    tag_name = await year_input.evaluate('el => el.tagName')
                    if tag_name == 'SELECT':
                        # 下拉框选择
                        await year_input.select_option(f"{start_year}-")
                    else:
                        # 输入框输入
                        await year_input.fill(str(start_year))
                    await asyncio.sleep(0.3)
                    return
            except:
                continue

    async def _click_search(self):
        """点击搜索按钮"""
        selectors = [
            'button:has-text("搜索")',
            'button[type="submit"]',
            '.search-button',
            '#searchBtn',
            'input[type="submit"]'
        ]

        for selector in selectors:
            try:
                btn = await self.page.wait_for_selector(selector, timeout=3000)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    print("[PubScholar] 已执行搜索")
                    return
            except:
                continue

        # 如果找不到按钮，尝试按回车
        try:
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(1)
        except:
            pass

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
                '.search-result-item'
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
                // 查找所有可能包含文献信息的容器
                const containers = document.querySelectorAll('[class*="item"], [class*="card"], [class*="result"]');
                for (const container of containers) {
                    const text = container.textContent || '';
                    // 查找包含中文标题的元素
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

                    // 清理标题
                    title = title.replace(/\s+/g, ' ').trim();

                    // 过滤：只保留包含中文的标题
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

    async def search_by_keywords(
        self,
        keywords: List[str],
        years_ago: int = 10,
        max_per_keyword: int = 20
    ) -> List[Dict]:
        """
        使用多个关键词搜索

        如果提供两个关键词，使用高级筛选的双关键词搜索
        如果提供更多关键词，分别搜索后合并结果
        """
        all_papers = []
        seen_titles = set()

        if len(keywords) == 2:
            # 使用双关键词高级搜索
            papers = await self.search_dual_keywords(
                keyword1=keywords[0],
                keyword2=keywords[1],
                years_ago=years_ago,
                max_results=max_per_keyword * 2
            )
            all_papers.extend(papers)
        else:
            # 分别搜索每个关键词
            for keyword in keywords:
                papers = await self.search_dual_keywords(
                    keyword1=keyword,
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
async def test_advanced_search():
    """测试高级筛选搜索"""

    print("=" * 80)
    print("测试 PubScholar 高级筛选搜索")
    print("=" * 80)

    async with PubScholarAdvancedSearch(headless=False) as service:  # headless=False 可以看到浏览器操作
        # 测试双关键词搜索
        print("\n" + "=" * 60)
        print("测试双关键词搜索: 投资者情绪 + 分析师预测")
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

        # 测试多关键词搜索
        print("\n" + "=" * 60)
        print("测试多关键词搜索")
        print("=" * 60)

        keywords = ["投资者情绪", "分析师预测", "媒体关注度"]
        all_papers = await service.search_by_keywords(
            keywords=keywords,
            years_ago=10,
            max_per_keyword=10
        )

        # 去重统计
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
    asyncio.run(test_advanced_search())
