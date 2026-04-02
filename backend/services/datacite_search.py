"""
DataCite 文献检索服务
专注于研究数据集的元数据检索
API 文档: https://api.datacite.org/
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class DataCiteSearchService:
    """DataCite 搜索服务 - 主要用于研究数据集"""

    BASE_URL = "https://api.datacite.org"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, headers={
            'Accept': 'application/vnd.api+json',
            'User-Agent': 'PaperOverview/1.0'
        })

    async def search_papers(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0
    ) -> List[Dict]:
        """
        搜索论文/数据集

        Args:
            query: 搜索关键词
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量

        Returns:
            论文列表
        """
        # 计算截止日期
        cutoff_date = (datetime.now() - timedelta(days=years_ago * 365)).strftime("%Y-%m-%d")

        params = {
            "query": query,
            "resource-type-id": "dataset",  # DataCite 主要覆盖数据集
            "page[size]": min(limit, 100),  # DataCite 默认每页最大100
            "page[number]": 1,
            "sort": "published",  # 按发布时间排序
            "filter": f"published:{cutoff_date},"
        }

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/dois",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            papers = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})

                # 提取作者
                authors = []
                for creator in attrs.get("creators", [])[:10]:
                    name = creator.get("name", "")
                    if name:
                        authors.append(name)

                # 提取标题
                titles = attrs.get("titles", [])
                title = titles[0].get("title", "") if titles else ""

                # 提取年份
                published = attrs.get("published", "")
                year = None
                if published:
                    try:
                        year = datetime.fromisoformat(published.replace('Z', '+00:00')).year
                    except:
                        pass

                # 判断语言
                is_english = self._is_english(title)

                # 构建期刊信息
                publisher = attrs.get("publisher", "")
                publication_year = attrs.get("publicationYear", "")
                journal_info = f"{publisher} ({publication_year})" if publisher and publication_year else publisher

                papers.append({
                    "id": item.get("id", ""),
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "cited_by_count": 0,  # DataCite 不提供引用计数
                    "is_english": is_english,
                    "abstract": self._extract_description(attrs),
                    "type": attrs.get("types", {}).get("resourceType", "dataset"),
                    "doi": attrs.get("doi", ""),
                    "journal": publisher,
                    "journal_info": journal_info,
                    "keywords": attrs.get("subjects", [])[:10],
                    "data_source": "datacite",
                    "url": attrs.get("url", "")
                })

            return papers

        except httpx.HTTPError as e:
            print(f"[DataCite] API error: {e}")
            return []
        except Exception as e:
            print(f"[DataCite] 搜索失败: {e}")
            return []

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    def _is_english(self, text: str) -> bool:
        """判断文本是否为英文"""
        if not text:
            return False
        # 计算非ASCII字符比例
        non_ascii = sum(1 for c in text if ord(c) > 127)
        return non_ascii / len(text) < 0.3

    def _extract_description(self, attrs: Dict) -> str:
        """提取描述信息"""
        descriptions = attrs.get("descriptions", [])
        if descriptions:
            desc = descriptions[0].get("description", "")
            # 移除HTML标签
            import re
            desc = re.sub(r'<[^>]+>', '', desc)
            return desc[:2000]  # 限制长度
        return ""


# 测试代码
async def test_datacite_search():
    """测试 DataCite 搜索"""
    print("=" * 80)
    print("测试 DataCite 搜索")
    print("=" * 80)

    service = DataCiteSearchService()

    try:
        papers = await service.search_papers(
            query="machine learning",
            years_ago=5,
            limit=5
        )

        print(f"\n找到 {len(papers)} 篇:")
        for i, paper in enumerate(papers, 1):
            print(f"\n{i}. {paper.get('title', 'N/A')}")
            print(f"   作者: {', '.join(paper.get('authors', [])[:3])}")
            print(f"   年份: {paper.get('year', 'N/A')}")
            print(f"   类型: {paper.get('type', 'N/A')}")
            print(f"   DOI: {paper.get('doi', 'N/A')}")

    finally:
        await service.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_datacite_search())
