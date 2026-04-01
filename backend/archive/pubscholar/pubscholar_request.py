"""
PubScholar API 请求服务
使用专业检索 API 搜索中文文献
"""
import asyncio
import hashlib
import json
import re
import time
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote
from urllib import parse

import httpx


class PubScholarRequest:
    """PubScholar API 请求类"""

    BASE_URL = "https://pubscholar.cn"
    API_URL = f"{BASE_URL}/hky/open/resources/api/v1/articles"

    # 默认用户ID
    DEFAULT_USER_ID = "9a6d71ef0caa608a5f29e827645d3d2f"

    def __init__(self):
        self.client = None
        self.cookies = {}
        self.xsrf_token = None
        self.user_id = self.DEFAULT_USER_ID
        self._initialized = False

    async def initialize(self):
        """初始化会话，获取必要的 token 和 cookies"""
        if self._initialized:
            return

        print("[PubScholar] 正在初始化会话...")

        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=False,  # 禁用 SSL 验证
            headers={
                'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Origin': self.BASE_URL,
                'Referer': f"{self.BASE_URL}/explore",
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
        )

        # 访问 explore 页面获取 XSRF-TOKEN
        try:
            response = await self.client.get(f"{self.BASE_URL}/explore")

            # 从 cookies 中提取 XSRF-TOKEN
            for cookie_name, cookie_value in response.cookies.items():
                if 'xsrf' in cookie_name.lower():
                    self.xsrf_token = cookie_value
                    self.cookies[cookie_name] = cookie_value
                    print(f"[PubScholar] 获取到 {cookie_name}: {cookie_value[:20]}...")

            # 尝试从 HTML 中提取 XSRF-TOKEN
            if not self.xsrf_token:
                html = response.text
                xsrf_match = re.search(r'XSRF-TOKEN["\']?\s*[:=]\s*["\']?([a-f0-9\-]+)', html)
                if xsrf_match:
                    self.xsrf_token = xsrf_match.group(1)
                    self.cookies['XSRF-TOKEN'] = self.xsrf_token
                    print(f"[PubScholar] 从 HTML 获取 XSRF-TOKEN: {self.xsrf_token[:20]}...")

            # 尝试从 meta 标签获取
            if not self.xsrf_token:
                meta_match = re.search(r'<meta[^>]*name=["\']_csrf["\'][^>]*content=["\']([^"\']+)["\']', response.text)
                if meta_match:
                    self.xsrf_token = meta_match.group(1)
                    print(f"[PubScholar] 从 meta 获取 XSRF-TOKEN: {self.xsrf_token[:20]}...")

            if self.xsrf_token:
                self._initialized = True
                print("[PubScholar] ✓ 会话初始化成功")
            else:
                print("[PubScholar] ⚠ 未获取到 XSRF-TOKEN，将使用默认值")
                self.xsrf_token = "default-token"
                self._initialized = True

        except Exception as e:
            print(f"[PubScholar] 初始化失败: {e}")
            # 即使失败也标记为已初始化，尝试使用默认值
            self.xsrf_token = "default-token"
            self._initialized = True

    def _generate_nonce(self, length: int = 6) -> str:
        """生成随机 nonce"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def _generate_signature(self, data: dict, timestamp: str, nonce: str) -> str:
        """
        生成签名

        根据观察，签名可能是对特定参数的哈希
        尝试多种可能的签名方式
        """
        # 方式1: 对整个请求体签名
        body_str = json.dumps(data, separators=(',', ':'), sort_keys=True)
        sign_str = f"{body_str}{timestamp}{nonce}{self.xsrf_token}"

        # 尝试 MD5
        signature = hashlib.md5(sign_str.encode()).hexdigest()

        return signature

    def build_search_query(
        self,
        keywords: List[str],
        year_start: int = 2016,
        year_end: int = 2026
    ) -> str:
        """
        构建专业检索式

        Args:
            keywords: 关键词列表
            year_start: 开始年份
            year_end: 结束年份

        Returns:
            URL 编码的检索式
        """
        # TI=关键词1 AND TI=关键词2 AND PY=[年份 TO 年份]
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
        搜索文献

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

        # 生成请求参数
        timestamp = str(int(time.time() * 1000))
        nonce = self._generate_nonce()

        payload = {
            "page": page,
            "size": size,
            "order_field": "default",
            "order_direction": "desc",
            "user_id": self.user_id,
            "lang": "zh",
            "strategy": strategy,
            "extendParams": {
                "strategyType": "professional"
            }
        }

        # 生成签名
        signature = self._generate_signature(payload, timestamp, nonce)

        # 构建请求头
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'X-XSRF-TOKEN': self.xsrf_token,
            'nonce': nonce,
            'signature': signature,
            'timestamp': timestamp,
            'x-finger': self.user_id,
        }

        # 添加 cookies
        cookies = dict(self.cookies)

        try:
            response = await self.client.post(
                self.API_URL,
                json=payload,
                headers=headers,
                cookies=cookies
            )

            print(f"[PubScholar] 响应状态: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                papers = self._parse_response(data)
                print(f"[PubScholar] ✓ 找到 {len(papers)} 篇文献")
                return papers
            else:
                print(f"[PubScholar] 请求失败: {response.status_code}")
                print(f"[PubScholar] 响应内容: {response.text[:500]}")
                return []

        except Exception as e:
            print(f"[PubScholar] 请求异常: {e}")
            import traceback
            traceback.print_exc()
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
            print(f"[PubScholar] 未知响应格式: {list(data.keys())}")
            return []

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
                    date = item.get('date', '') or item.get('publishDate', '')
                    if isinstance(date, str) and len(date) >= 4:
                        try:
                            year = int(date[:4])
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
                title = item.get('title', '') or item.get('zhTitle', '') or ''

                papers.append({
                    'id': item.get('id', '') or item.get('articleId', '') or item.get('paperId', ''),
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'cited_by_count': item.get('citedByCount', 0) or item.get('citationCount', 0) or item.get('cite_num', 0),
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
        """关闭客户端"""
        if self.client:
            await self.client.aclose()


# 测试代码
async def test_pubscholar_request():
    """测试 PubScholar 请求"""
    print("=" * 80)
    print("测试 PubScholar API 请求")
    print("=" * 80)

    async with PubScholarRequest() as service:
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


# 添加异步上下文管理器支持
async def get_context_manager():
    """创建异步上下文管理器"""
    class PubScholarContext:
        def __init__(self):
            self.service = PubScholarRequest()

        async def __aenter__(self):
            await self.service.initialize()
            return self.service

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.service.close()

    return PubScholarContext()


# 让类支持 async with
PubScholarRequest.__aenter__ = lambda self: (lambda s: s.initialize() or (lambda: s)())(self)()
PubScholarRequest.__aexit__ = lambda self, exc_type, exc_val, exc_tb: (lambda s: s.close() or (lambda: (lambda: None)())())(self)()


if __name__ == "__main__":
    # 使用上下文管理器
    async def run_test():
        service = PubScholarRequest()
        try:
            await service.initialize()
            # 测试搜索
            papers = await service.search_papers(
                keywords=["大数据", "并行计算"],
                year_start=2021,
                year_end=2026,
                page=1,
                size=10
            )
            print(f"\n找到 {len(papers)} 篇文献")
            for i, p in enumerate(papers[:3], 1):
                print(f"{i}. {p.get('title', 'N/A')}")
        finally:
            await service.close()

    asyncio.run(run_test())
