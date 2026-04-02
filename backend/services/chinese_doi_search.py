"""
中文 DOI 搜索服务
通过 ISTIC/万方中文 DOI 系统搜索中文文献
注意：中文 DOI API 可能需要授权访问
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import quote


class ChineseDoiSearchService:
    """
    中文 DOI 搜索服务

    中文 DOI 是由中国科学技术信息研究所 (ISTIC) 和万方数据联合运营的
    DOI 注册机构，覆盖中文学术期刊、会议论文等。

    注意：官方 API 可能需要申请授权，当前实现使用公开搜索接口
    """

    def __init__(self, api_key: str = None):
        """
        初始化服务

        Args:
            api_key: 中文 DOI API 密钥（如果有的话）
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # 中文 DOI 的主要接口地址
        self.base_urls = [
            "https://www.chinadoi.cn/DOI/API/v1.0",  # 官方 API（需要授权）
            "https://d.wanfangdata.com.cn/doi/search",  # 万方搜索
        ]

    async def search_papers(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0
    ) -> List[Dict]:
        """
        搜索中文论文

        Args:
            query: 搜索关键词（支持中文）
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量

        Returns:
            论文列表
        """
        # 计算年份范围
        current_year = datetime.now().year
        from_year = current_year - years_ago

        # 方案1: 尝试使用万方数据的公开搜索
        papers = await self._search_wanfang(query, from_year, limit)

        # 方案2: 如果万方没有结果，尝试 CNKI 的公开搜索
        if not papers:
            papers = await self._search_cnki(query, from_year, limit)

        # 过滤被引量
        if min_citations > 0:
            papers = [p for p in papers if p.get('cited_by_count', 0) >= min_citations]

        return papers[:limit]

    async def _search_wanfang(
        self,
        query: str,
        from_year: int,
        limit: int
    ) -> List[Dict]:
        """
        通过万方数据搜索

        注意：万方数据的 API 需要授权，这里提供接口框架
        """
        if self.api_key:
            # 如果有 API 密钥，使用官方 API
            return await self._wanfang_api_search(query, from_year, limit)
        else:
            # 否则返回模拟数据（实际使用需要实现爬虫或申请 API）
            print("[ChineseDOI] 万方 API 需要授权密钥，使用模拟数据")
            return await self._get_mock_results(query, from_year, limit)

    async def _wanfang_api_search(
        self,
        query: str,
        from_year: int,
        limit: int
    ) -> List[Dict]:
        """
        使用万方官方 API 搜索

        需要申请 API 密钥: http://www.wanfangdata.com.cn/
        """
        params = {
            "q": query,
            "from_year": from_year,
            "page_size": limit,
            "api_key": self.api_key
        }

        try:
            response = await self.client.get(
                "https://api.wanfangdata.com.cn/search",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            papers = []
            for item in data.get("records", []):
                papers.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "authors": item.get("authors", []),
                    "year": item.get("year"),
                    "cited_by_count": item.get("cited_count", 0),
                    "is_english": False,  # 万方主要是中文文献
                    "abstract": item.get("abstract", ""),
                    "type": item.get("type", "article"),
                    "doi": item.get("doi", ""),
                    "journal": item.get("journal", ""),
                    "journal_info": item.get("journal_info", ""),
                    "keywords": item.get("keywords", []),
                    "data_source": "wanfang",
                    "url": item.get("url", "")
                })

            return papers

        except Exception as e:
            print(f"[ChineseDOI] 万方 API 搜索失败: {e}")
            return []

    async def _search_cnki(
        self,
        query: str,
        from_year: int,
        limit: int
    ) -> List[Dict]:
        """
        通过 CNKI 搜索

        注意：CNKI API 需要授权，这里提供接口框架
        """
        print("[ChineseDOI] CNKI API 需要授权密钥")
        return await self._get_mock_results(query, from_year, limit)

    async def _get_mock_results(
        self,
        query: str,
        from_year: int,
        limit: int
    ) -> List[Dict]:
        """
        返回模拟结果用于测试

        实际使用时应该替换为真实的 API 调用
        """
        # 检测是否为中文查询
        is_chinese = any('\u4e00' <= c <= '\u9fff' for c in query)

        if not is_chinese:
            print(f"[ChineseDOI] 非中文查询，返回空结果")
            return []

        # 模拟一些中文论文结果
        mock_papers = [
            {
                "id": f"cnki_{i}",
                "title": f"{query}相关研究{i}",
                "authors": [f"张三", f"李四", f"王五"],
                "year": 2023 - i % 3,
                "cited_by_count": 10 - i,
                "is_english": False,
                "abstract": f"关于{query}的研究...",
                "type": "journal",
                "doi": f"10.xxxx/xxxx.{i}",
                "journal": "计算机学报",
                "journal_info": f"计算机学报, {2023 - i % 3}",
                "keywords": [query, "研究", "分析"],
                "data_source": "chinese_doi_mock",
                "url": f"https://www.cnki.net/kns/detail/detail.aspx?dbcode=CJFD&dbname=CJFDAUTO&filename=TEST{i:04d}"
            }
            for i in range(min(limit, 3))
        ]

        return mock_papers

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 测试代码
async def test_chinese_doi_search():
    """测试中文 DOI 搜索"""
    print("=" * 80)
    print("测试中文 DOI 搜索")
    print("=" * 80)

    # 测试无 API 密钥的情况（使用模拟数据）
    service = ChineseDoiSearchService()

    try:
        papers = await service.search_papers(
            query="机器学习",
            years_ago=5,
            limit=5
        )

        print(f"\n找到 {len(papers)} 篇:")
        for i, paper in enumerate(papers, 1):
            print(f"\n{i}. {paper.get('title', 'N/A')}")
            print(f"   作者: {', '.join(paper.get('authors', [])[:3])}")
            print(f"   年份: {paper.get('year', 'N/A')}")
            print(f"   来源: {paper.get('data_source', 'N/A')}")
            print(f"   期刊: {paper.get('journal', 'N/A')}")

        print("\n注意：当前返回的是模拟数据。实际使用需要申请万方/CNKI API 密钥。")
        print("- 万方数据: http://www.wanfangdata.com.cn/")
        print("- CNKI: https://oversea.cnki.net/")

    finally:
        await service.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_chinese_doi_search())
