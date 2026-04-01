"""
PubScholar API 请求服务 - 使用 Playwright 在浏览器内发起请求
"""
import asyncio
import json
from typing import List, Dict
from datetime import datetime
from urllib.parse import quote

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PubScholarBrowserRequest:
    """PubScholar 浏览器请求类 - 在浏览器内发起 API 请求"""

    BASE_URL = "https://pubscholar.cn"
    API_URL = f"{BASE_URL}/hky/open/resources/api/v1/articles"

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
            user_agent='Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )

        self.page = await self.context.new_page()

        # 访问 explore 页面建立会话
        await self.page.goto(f"{self.BASE_URL}/explore", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # 增加等待时间确保会话完全建立

        self._initialized = True
        print("[PubScholar] ✓ 浏览器初始化完成")

    def build_search_query(
        self,
        keywords: List[str],
        year_start: int = 2016,
        year_end: int = 2026
    ) -> str:
        """构建专业检索式"""
        keyword_parts = [f'TI="{kw}"' for kw in keywords]
        query = ' AND '.join(keyword_parts)
        query += f' AND PY=[{year_start} TO {year_end}]'
        return quote(query, safe='')

    async def search_papers(
        self,
        keywords: List[str],
        year_start: int = 2016,
        year_end: int = 2026,
        page: int = 1,
        size: int = 50
    ) -> List[Dict]:
        """
        在浏览器内发起 API 请求搜索文献

        Args:
            keywords: 关键词列表
            year_start: 开始年份
            year_end: 结束年份
            page: 页码
            size: 每页数量

        Returns:
            文献列表
        """
        if not self._initialized:
            await self.initialize()

        # 构建检索式
        strategy = self.build_search_query(keywords, year_start, year_end)

        print(f"[PubScholar] 检索式: {strategy}")
        print(f"[PubScholar] 请求第 {page} 页，每页 {size} 篇")

        # 在浏览器内发起 XMLHttpRequest 请求
        result = await self.page.evaluate('''async (args) => {
            const { apiUrl, strategy, page, size, baseUrl } = args;

            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();

                xhr.open('POST', apiUrl, true);
                xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
                xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');

                // 获取页面的所有 cookies
                const cookies = document.cookie;

                // 尝试获取 XSRF-TOKEN
                const xsrfMatch = document.cookie.match(/XSRF-TOKEN=([^;]+)/);
                if (xsrfMatch) {
                    xhr.setRequestHeader('X-XSRF-TOKEN', xsrfMatch[1]);
                }

                const payload = {
                    page: page,
                    size: size,
                    order_field: "default",
                    order_direction: "desc",
                    user_id: "9a6d71ef0caa608a5f29e827645d3d2f",
                    lang: "zh",
                    strategy: strategy,
                    extendParams: {
                        strategyType: "professional"
                    }
                };

                xhr.onload = function() {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        resolve({
                            success: xhr.status === 200,
                            status: xhr.status,
                            data: data
                        });
                    } catch (e) {
                        resolve({
                            success: false,
                            status: xhr.status,
                            error: 'Parse error: ' + e.message
                        });
                    }
                };

                xhr.onerror = function() {
                    resolve({
                        success: false,
                        status: xhr.status,
                        error: 'Network error'
                    });
                };

                xhr.send(JSON.stringify(payload));
            });
        }''', {
            'apiUrl': self.API_URL,
            'strategy': strategy,
            'page': page,
            'size': size,
            'baseUrl': self.BASE_URL
        })

        print(f"[PubScholar] 响应: success={result.get('success')}, status={result.get('status')}")

        if result.get('success'):
            data = result.get('data', {})

            # 打印完整响应用于调试
            print(f"[PubScholar] 完整响应: {json.dumps(data, ensure_ascii=False)[:500]}")

            # 打印原始数据结构
            print(f"[PubScholar] 响应数据keys: {list(data.keys())}")

            # 如果有错误信息
            if 'error' in data:
                print(f"[PubScholar] 错误: {data.get('error')}")
            if 'error_message' in data:
                print(f"[PubScholar] 错误信息: {data.get('error_message')}")

            papers = self._parse_response(data)
            print(f"[PubScholar] ✓ 找到 {len(papers)} 篇文献")
            return papers
        else:
            error = result.get('error', 'Unknown error')
            print(f"[PubScholar] 请求失败: {error}")
            return []

    def _parse_response(self, data: dict) -> List[Dict]:
        """解析 API 响应"""
        papers = []

        # 尝试从不同的字段获取数据
        content = data.get('content', []) or data.get('data', []) or data.get('list', [])

        if not isinstance(content, list):
            for key in ['articles', 'items', 'records']:
                if key in data:
                    content = data[key]
                    if isinstance(content, list):
                        break

        if not isinstance(content, list):
            print(f"[PubScholar] 未知响应格式，keys: {list(data.keys())}")
            # 打印原始数据帮助调试
            print(f"[PubScholar] 原始数据: {str(data)[:500]}")
            return []

        print(f"[PubScholar] 解析 {len(content)} 条记录")

        for item in content:
            try:
                # 提取作者
                authors = []
                author_list = item.get('authors', item.get('author', []))
                if isinstance(author_list, list):
                    for author in author_list:
                        if isinstance(author, dict):
                            name = author.get('name', '') or author.get('zhName', '')
                            if name:
                                authors.append(name)
                        elif isinstance(author, str):
                            authors.append(author)
                elif isinstance(author_list, str):
                    authors = [a.strip() for a in author_list.split(',')]

                # 提取年份
                year = item.get('year')
                if not year:
                    date_val = item.get('date', '') or item.get('publishDate', '')
                    if isinstance(date_val, str) and len(date_val) >= 4:
                        try:
                            year = int(date_val[:4])
                        except:
                            pass

                # 构建期刊信息
                source = item.get('source', '') or item.get('journal', '') or item.get('publication', '') or item.get('journalName', '')
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

                # 提取标题
                title = item.get('title', '') or item.get('zhTitle', '') or item.get('enTitle', '')

                # 提取被引数
                cited_by = item.get('citedByCount', 0) or item.get('citationCount', 0) or item.get('cite_num', 0) or 0

                papers.append({
                    'id': item.get('id', '') or item.get('articleId', '') or item.get('paperId', ''),
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'cited_by_count': cited_by,
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
                print(f"[PubScholar] 解析单条记录失败: {e}")
                continue

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
async def test_pubscholar_browser_request():
    """测试 PubScholar 浏览器请求"""
    print("=" * 80)
    print("测试 PubScholar 浏览器请求")
    print("=" * 80)

    async with PubScholarBrowserRequest(headless=True) as service:
        # 测试1: 双关键词搜索
        print("\n" + "=" * 60)
        print("测试1: 大数据 + 并行计算")
        print("=" * 60)

        papers = await service.search_papers(
            keywords=["大数据", "并行计算"],
            year_start=2021,
            year_end=2026,
            page=1,
            size=10
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
        print("测试2: 投资者情绪 + 分析师预测")
        print("=" * 60)

        papers2 = await service.search_papers(
            keywords=["投资者情绪", "分析师预测"],
            year_start=2020,
            year_end=2024,
            page=1,
            size=10
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
    asyncio.run(test_pubscholar_browser_request())
