"""
AMiner 论文搜索服务
使用 AMiner Open Platform API 搜索论文

Token 获取地址: https://www.aminer.cn/open/board?tab=control
注意: Token 有效期为 100 天，过期后需要重新获取
"""
import asyncio
import base64
import json
from typing import List, Dict, Optional
from urllib.parse import quote
from datetime import datetime

import httpx


class AMinerSearchService:
    """AMiner 论文搜索服务"""

    BASE_URL = "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search"
    PRO_URL = "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search/pro"

    def __init__(self, api_token: str = None):
        """
        初始化服务

        Args:
            api_token: AMiner API Token（必需）
                      获取地址: https://www.aminer.cn/open/board?tab=control
        """
        if not api_token:
            raise ValueError("AMiner API Token 是必需的。请在 AMiner 开放平台获取：https://www.aminer.cn/open/board?tab=control")
        self.api_token = api_token
        self.client = None
        self._check_token_expiry()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _check_token_expiry(self):
        """检查 Token 过期时间并提示"""
        try:
            # JWT token 格式: header.payload.signature
            parts = self.api_token.split('.')
            if len(parts) >= 2:
                # 解码 payload (base64url)
                payload = parts[1]
                # 添加 padding 如果需要
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                data = json.loads(decoded)

                exp_timestamp = data.get('exp')
                if exp_timestamp:
                    exp_date = datetime.fromtimestamp(exp_timestamp)
                    now = datetime.now()
                    days_left = (exp_date - now).days

                    if days_left < 0:
                        print(f"[AMiner] ⚠️  Token 已过期！请重新获取: https://www.aminer.cn/open/board?tab=control")
                    elif days_left <= 10:
                        print(f"[AMiner] ⚠️  Token 即将过期（剩余 {days_left} 天），请尽快重新获取: https://www.aminer.cn/open/board?tab=control")
                    else:
                        print(f"[AMiner] Token 有效期至 {exp_date.strftime('%Y-%m-%d')} (剩余 {days_left} 天)")
        except Exception as e:
            print(f"[AMiner] 无法解析 Token 过期时间: {e}")
            print(f"[AMiner] 获取新 Token: https://www.aminer.cn/open/board?tab=control")

    async def initialize(self):
        """初始化 HTTP 客户端"""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=False,
            headers={
                'Authorization': self.api_token,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

    async def verify_token(self) -> bool:
        """验证 Token 是否有效"""
        try:
            response = await self.client.get(
                self.BASE_URL,
                params={'page': 1, 'size': 1, 'title': 'test'}
            )
            data = response.json()

            if data.get('success', False):
                return True
            else:
                return False
        except Exception as e:
            return False

    async def search_by_title(
        self,
        title: str,
        page: int = 1,
        size: int = 20
    ) -> Dict:
        """
        根据论文标题搜索论文

        Args:
            title: 论文标题（空格用+代替）
            page: 页码（从1开始）
            size: 每页数量（最大20）

        Returns:
            搜索结果字典
        """
        if not self.client:
            await self.initialize()

        # 处理标题：空格替换为+
        search_title = title.replace(' ', '+')

        params = {
            'page': page,
            'size': min(size, 20),  # 最大20
            'title': search_title
        }

        print(f"[AMiner] 搜索: {title}")

        try:
            response = await self.client.get(
                self.BASE_URL,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            total = data.get('total', 0)
            items = data.get('data', [])
            print(f"[AMiner] ✓ 找到 {total} 篇，本页返回 {len(items)} 篇")

            return {
                'success': True,
                'total': total,
                'items': items,
                'page': page,
                'size': size
            }

        except httpx.HTTPStatusError as e:
            print(f"[AMiner] HTTP错误: {e.response.status_code}")
            try:
                error_data = e.response.json()
                print(f"[AMiner] 错误信息: {error_data}")
            except:
                print(f"[AMiner] 错误内容: {e.response.text[:200]}")
            return {
                'success': False,
                'error': f"HTTP {e.response.status_code}",
                'items': []
            }
        except Exception as e:
            print(f"[AMiner] 请求失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'items': []
            }

    async def search_by_keyword_and_title(
        self,
        keyword: str,
        title: str,
        page: int = 0,
        size: int = 50
    ) -> Dict:
        """
        使用 Pro 接口同时使用 keyword 和 title 搜索论文（高相关度）

        策略：将两个关键词组合，分别放在 title 和 keyword 中

        Args:
            keyword: 关键词（通常是方法论，如 QFD）
            title: 标题关键词（通常是研究对象，如 铝合金轮毂）
            page: 页码（从0开始）
            size: 每页数量（最大100）

        Returns:
            搜索结果字典
        """
        if not self.client:
            await self.initialize()

        # 组合关键词
        combined = f"{title} {keyword}"  # 用空格连接

        params = {
            'page': page,
            'size': min(size, 100),  # 最大100
            'title': combined,  # 标题中搜索组合
            'keyword': combined  # 关键词中也搜索组合
        }

        print(f"[AMiner Pro] 组合搜索: '{combined}'")

        try:
            response = await self.client.get(
                self.PRO_URL,
                params=params
            )
            response.raise_for_status()

            # 获取响应文本
            response_text = response.text

            # 检查是否为空响应
            if not response_text or response_text.strip() == '':
                print(f"[AMiner Pro] 空响应")
                return {
                    'success': False,
                    'error': 'Empty response',
                    'items': []
                }

            # 尝试解析 JSON
            try:
                data = response.json()
            except Exception as e:
                print(f"[AMiner Pro] JSON 解析失败: {e}")
                print(f"[AMiner Pro] 响应内容: {response_text[:500]}")
                return {
                    'success': False,
                    'error': f'JSON parse error: {e}',
                    'items': []
                }

            # 检查数据结构
            if data is None:
                print(f"[AMiner Pro] 返回数据为 None")
                return {
                    'success': False,
                    'error': 'Response data is None',
                    'items': []
                }

            # 获取 total 和 items
            total = data.get('total', 0)
            items = data.get('data', data.get('items', []))

            # 如果 items 为 None，设置为空列表
            if items is None:
                items = []

            print(f"[AMiner Pro] ✓ 找到 {total} 篇，本页返回 {len(items)} 篇")

            return {
                'success': True,
                'total': total,
                'items': items,
                'page': page,
                'size': size
            }

        except httpx.HTTPStatusError as e:
            print(f"[AMiner Pro] HTTP错误: {e.response.status_code}")
            try:
                error_data = e.response.json()
                print(f"[AMiner Pro] 错误信息: {error_data}")
            except:
                print(f"[AMiner Pro] 错误内容: {e.response.text[:200]}")
            return {
                'success': False,
                'error': f"HTTP {e.response.status_code}",
                'items': []
            }
        except Exception as e:
            print(f"[AMiner Pro] 请求失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'items': []
            }

    async def search_by_keyword(
        self,
        keyword: str,
        page: int = 0,
        size: int = 50
    ) -> Dict:
        """
        使用 Pro 接口根据关键词搜索论文

        Args:
            keyword: 搜索关键词
            page: 页码（从0开始）
            size: 每页数量（最大100）

        Returns:
            搜索结果字典
        """
        if not self.client:
            await self.initialize()

        params = {
            'page': page,
            'size': min(size, 100),  # 最大100
            'keyword': keyword
        }

        print(f"[AMiner Pro] 关键词搜索: {keyword}")

        try:
            response = await self.client.get(
                self.PRO_URL,
                params=params
            )
            response.raise_for_status()

            # 获取响应文本
            response_text = response.text

            # 检查是否为空响应
            if not response_text or response_text.strip() == '':
                print(f"[AMiner Pro] 空响应")
                return {
                    'success': False,
                    'error': 'Empty response',
                    'items': []
                }

            # 尝试解析 JSON
            try:
                data = response.json()
            except Exception as e:
                print(f"[AMiner Pro] JSON 解析失败: {e}")
                print(f"[AMiner Pro] 响应内容: {response_text[:500]}")
                return {
                    'success': False,
                    'error': f'JSON parse error: {e}',
                    'items': []
                }

            # 检查数据结构
            if data is None:
                print(f"[AMiner Pro] 返回数据为 None")
                return {
                    'success': False,
                    'error': 'Response data is None',
                    'items': []
                }

            # 获取 total 和 items
            total = data.get('total', 0)
            items = data.get('data', data.get('items', []))

            # 如果 items 为 None，设置为空列表
            if items is None:
                items = []

            print(f"[AMiner Pro] ✓ 找到 {total} 篇，本页返回 {len(items)} 篇")

            return {
                'success': True,
                'total': total,
                'items': items,
                'page': page,
                'size': size
            }

        except httpx.HTTPStatusError as e:
            print(f"[AMiner Pro] HTTP错误: {e.response.status_code}")
            try:
                error_data = e.response.json()
                print(f"[AMiner Pro] 错误信息: {error_data}")
            except:
                print(f"[AMiner Pro] 错误内容: {e.response.text[:200]}")
            return {
                'success': False,
                'error': f"HTTP {e.response.status_code}",
                'items': []
            }
        except Exception as e:
            print(f"[AMiner Pro] 请求失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'items': []
            }

    async def search_by_titles(
        self,
        titles: List[str],
        max_per_title: int = 10
    ) -> List[Dict]:
        """
        批量搜索多个标题

        Args:
            titles: 论文标题列表
            max_per_title: 每个标题最多返回结果数

        Returns:
            论文列表
        """
        all_papers = []
        seen_ids = set()

        for title in titles:
            result = await self.search_by_title(title, size=max_per_title)

            if result['success']:
                for item in result['items']:
                    paper_id = item.get('id')
                    if paper_id and paper_id not in seen_ids:
                        seen_ids.add(paper_id)
                        all_papers.append(self._parse_paper(item))

            # 避免请求过快
            await asyncio.sleep(1)

        print(f"[AMiner] 总共获取 {len(all_papers)} 篇不重复论文")
        return all_papers

    def _parse_paper(self, item: Dict) -> Dict:
        """解析单条论文记录"""
        # 提取作者
        authors = []
        if 'authors' in item:
            author_list = item['authors']
            if isinstance(author_list, list):
                authors = [a.get('name', str(a)) if isinstance(a, dict) else str(a) for a in author_list]
        elif 'first_author' in item:
            authors = [item['first_author']]

        # 构建期刊信息
        venue = item.get('venue_name', '')
        year = item.get('year')
        journal_info = venue
        if year and venue:
            journal_info = f"{venue}, {int(year)}" if isinstance(year, (int, float)) else venue

        # 判断是否为英文文献（改进版）
        title = item.get('title', '') or item.get('title_zh', '')
        title_zh = item.get('title_zh', '')

        # 优先使用 title_zh 字段判断
        if title_zh:
            # 有中文标题，认为是中文文献
            is_english = False
        elif title:
            # 检查标题中是否包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in title)
            is_english = not has_chinese
        else:
            # 没有标题，默认为英文
            is_english = True

        return {
            'id': item.get('id', ''),
            'title': title,
            'authors': authors,
            'year': int(year) if year and isinstance(year, (int, float)) else None,
            'cited_by_count': self._parse_citation_count(item.get('n_citation_bucket', '')),
            'is_english': is_english,
            'abstract': '',
            'type': 'article',
            'doi': item.get('doi', ''),
            'journal': venue,
            'journal_info': journal_info,
            'keywords': [],
            'data_source': 'AMiner',
            'url': f"https://www.aminer.cn/paper/{item.get('id', '')}"
        }

    def _parse_citation_count(self, bucket: str) -> int:
        """解析被引档位为数字"""
        if not bucket:
            return 0

        bucket_map = {
            '0': 0,
            '1-10': 5,
            '11-50': 30,
            '51-200': 125,
            '200-1000': 600,
            '1000-5000': 3000,
            '5000+': 5000
        }

        return bucket_map.get(bucket, 0)

    async def search_papers(
        self,
        keywords: List[str],
        year_start: int = 2016,
        year_end: int = 2026,
        max_results: int = 50
    ) -> List[Dict]:
        """
        使用关键词搜索论文

        搜索策略：
        1. 如果只有1个关键词：使用 Pro 接口搜索
        2. 如果有2个关键词：组合使用 title + keyword 搜索（高相关度）
        3. 如果有更多关键词：分别搜索每个关键词

        Args:
            keywords: 关键词列表
            year_start: 开始年份
            year_end: 结束年份
            max_results: 最大结果数

        Returns:
            论文列表
        """
        all_papers = []
        seen_ids = set()

        if len(keywords) == 1:
            # 单个关键词：使用 Pro 接口搜索
            search_keyword = keywords[0]

            page = 0
            size = 50

            while len(all_papers) < max_results:
                result = await self.search_by_keyword(
                    keyword=search_keyword,
                    page=page,
                    size=min(size, max_results - len(all_papers))
                )

                if not result['success']:
                    break

                items = result['items']
                if not items:
                    break

                # 解析并去重
                for item in items:
                    paper_id = item.get('id')
                    if paper_id and paper_id not in seen_ids:
                        seen_ids.add(paper_id)
                        paper = self._parse_paper(item)

                        # 按年份过滤
                        if paper['year']:
                            if year_start <= paper['year'] <= year_end:
                                all_papers.append(paper)
                        else:
                            all_papers.append(paper)

                        if len(all_papers) >= max_results:
                            break

                # 检查是否还有更多结果
                total = result.get('total', 0)
                if total == 0 or (page + 1) * size >= total:
                    break

                page += 1
                await asyncio.sleep(1)

        elif len(keywords) == 2:
            # 两个关键词：分别用 title 和 keyword 搜索，然后合并（提升相关度）
            keyword1, keyword2 = keywords[0], keywords[1]

            print(f"[AMiner Pro] 双关键词搜索: '{keyword1}' + '{keyword2}'")

            # 策略：分别搜索并合并
            # 搜索1：用 title 搜索第一个关键词
            result1 = await self.search_by_title(
                title=keyword1,
                page=0,
                size=max_results // 2
            )

            # 搜索2：用 keyword 搜索第二个关键词
            result2 = await self.search_by_keyword(
                keyword=keyword2,
                page=0,
                size=max_results // 2
            )

            # 合并结果
            all_items = []
            if result1['success']:
                all_items.extend(result1.get('items', []))
            if result2['success']:
                all_items.extend(result2.get('items', []))

            # 去重
            item_seen_ids = set()
            unique_items = []
            for item in all_items:
                pid = item.get('id')
                if pid and pid not in item_seen_ids:
                    item_seen_ids.add(pid)
                    unique_items.append(item)

            print(f"[AMiner Pro] 合并后: {len(unique_items)} 篇不重复文献")

            # 解析论文
            for item in unique_items:
                paper = self._parse_paper(item)
                paper_id = paper.get('id')

                # 按年份过滤
                if paper['year']:
                    if year_start <= paper['year'] <= year_end:
                        all_papers.append(paper)
                else:
                    all_papers.append(paper)

                if len(all_papers) >= max_results:
                    break

        else:
            # 多个关键词：分别搜索每个关键词
            per_keyword_limit = max(max_results // len(keywords), 10)

            for keyword in keywords:
                keyword_papers = []
                page = 0
                size = 50

                while len(keyword_papers) < per_keyword_limit:
                    result = await self.search_by_keyword(
                        keyword=keyword,
                        page=page,
                        size=min(size, per_keyword_limit - len(keyword_papers))
                    )

                    if not result['success']:
                        break

                    items = result['items']
                    if not items:
                        break

                    # 解析并去重
                    for item in items:
                        paper_id = item.get('id')
                        if paper_id and paper_id not in seen_ids:
                            seen_ids.add(paper_id)
                            paper = self._parse_paper(item)

                            # 按年份过滤
                            if paper['year']:
                                if year_start <= paper['year'] <= year_end:
                                    keyword_papers.append(paper)
                            else:
                                keyword_papers.append(paper)

                            if len(keyword_papers) >= per_keyword_limit:
                                break

                    # 检查是否还有更多结果
                    total = result.get('total', 0)
                    if total == 0 or (page + 1) * size >= total:
                        break

                    page += 1
                    await asyncio.sleep(1)

                all_papers.extend(keyword_papers)

        # 按被引量排序，返回最相关的
        all_papers.sort(key=lambda x: x.get('cited_by_count', 0), reverse=True)
        return all_papers[:max_results]

    async def _search_with_pagination(
        self,
        search_title: str,
        year_start: int,
        year_end: int,
        max_results: int,
        seen_ids: set
    ) -> List[Dict]:
        """
        分页搜索论文（使用旧的标题搜索接口，保留用于兼容）

        Args:
            search_title: 搜索标题
            year_start: 开始年份
            year_end: 结束年份
            max_results: 最大结果数
            seen_ids: 已见过的论文ID集合（用于去重）

        Returns:
            论文列表
        """
        all_papers = []
        page = 1
        size = 20

        while len(all_papers) < max_results:
            result = await self.search_by_title(
                title=search_title,
                page=page,
                size=size
            )

            if not result['success']:
                break

            items = result['items']
            if not items:
                break

            # 解析并去重
            for item in items:
                paper_id = item.get('id')
                if paper_id and paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    paper = self._parse_paper(item)

                    # 按年份过滤
                    if paper['year']:
                        if year_start <= paper['year'] <= year_end:
                            all_papers.append(paper)
                    else:
                        all_papers.append(paper)

                    if len(all_papers) >= max_results:
                        break

            # 检查是否还有更多结果
            total = result.get('total', 0)
            if page * size >= total:
                break

            page += 1
            await asyncio.sleep(1)

        return all_papers

    async def close(self):
        """关闭客户端"""
        if self.client:
            await self.client.aclose()


# 测试代码
async def test_aminer_search():
    """测试 AMiner 搜索"""
    print("=" * 80)
    print("测试 AMiner 论文搜索")
    print("=" * 80)

    # 从环境变量或用户输入获取 Token
    import os
    api_token = os.getenv('AMINER_API_TOKEN')

    if not api_token:
        print("\n请提供 AMiner API Token：")
        print("1. 访问 https://www.aminer.cn/ 注册并获取 Token")
        print("2. 设置环境变量: export AMINER_API_TOKEN='your_token_here'")
        print("3. 或直接在此输入 Token:")

        user_input = input("Token (或按回车跳过): ").strip()
        if not user_input:
            print("跳过测试")
            return
        api_token = user_input

    async with AMinerSearchService(api_token=api_token) as service:
        # 验证 Token
        print("\n正在验证 Token...")
        if not await service.verify_token():
            print("\n✗ Token 无效，请检查后重试")
            return
        print()
        # 测试1: 单个标题搜索
        print("\n" + "=" * 60)
        print("测试1: 按标题搜索")
        print("=" * 60)

        result = await service.search_by_title(
            title="Looking at CTR Prediction Again: Is Attention All You Need",
            size=10
        )

        if result['success']:
            print(f"总数: {result['total']}")
            for i, item in enumerate(result['items'][:3], 1):
                print(f"\n{i}. {item.get('title', 'N/A')}")
                print(f"   作者: {item.get('first_author', 'N/A')}")
                print(f"   年份: {item.get('year', 'N/A')}")
                print(f"   期刊: {item.get('venue_name', 'N/A')}")

        # 测试2: 关键词搜索
        print("\n" + "=" * 60)
        print("测试2: 关键词搜索")
        print("=" * 60)

        papers = await service.search_papers(
            keywords=['machine learning', 'deep learning'],
            year_start=2020,
            year_end=2024,
            max_results=20
        )

        print(f"\n找到 {len(papers)} 篇论文:")
        for i, paper in enumerate(papers[:5], 1):
            title = paper.get('title', 'N/A')
            year = paper.get('year', 'N/A')
            authors = paper.get('authors', [])[:3]
            author_str = ', '.join(authors) if authors else 'N/A'

            print(f"\n{i}. [{year}] {title}")
            if author_str != 'N/A':
                print(f"   作者: {author_str}")

        print("\n" + "=" * 80)
        print(f"总计: {len(papers)} 篇论文")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_aminer_search())
