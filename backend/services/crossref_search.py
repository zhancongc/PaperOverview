"""
Crossref 文献检索服务
覆盖期刊、会议论文、书籍等学术文献
API 文档: https://api.crossref.org/
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class CrossrefSearchService:
    """Crossref 搜索服务 - 主要用于期刊和会议论文"""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self):
        # Crossref 要求提供 User-Agent
        # 格式: YourProductName/Version (mailto:your-email@example.com)
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'PaperOverview/1.0 (+https://github.com/paperciting/PaperOverview; mailto:paperciting@example.com)',
                'Accept': 'application/json'
            }
        )

    async def search_papers(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0
    ) -> List[Dict]:
        """
        搜索论文

        Args:
            query: 搜索关键词
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量

        Returns:
            论文列表
        """
        # 计算年份范围
        current_year = datetime.now().year
        from_year = current_year - years_ago

        # 简化参数，避免 400 错误
        params = {
            "query": query,
            "rows": min(limit, 100)
        }

        try:
            response = await self.client.get(
                self.BASE_URL,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            papers = []
            for item in data.get("message", {}).get("items", []):
                # 提取标题
                titles = item.get("title", [])
                title = titles[0] if titles else ""

                # 提取年份
                year = None
                for date_key in ["published-print", "published-online"]:
                    date_info = item.get(date_key, {})
                    if date_info and "date-parts" in date_info:
                        date_parts = date_info["date-parts"]
                        if date_parts and len(date_parts[0]) > 0:
                            year = date_parts[0][0]
                            break

                # 过滤年份
                if year and year < from_year:
                    continue

                # 过滤被引量
                ref_count = item.get("is-referenced-by-count", 0)
                if ref_count < min_citations:
                    continue

                # 提取作者
                authors = []
                for author in item.get("author", [])[:10]:
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)

                # 判断语言
                is_english = self._is_english(title)

                # 构建期刊信息
                container = item.get("container-title", [])
                journal = container[0] if container else ""
                volume = item.get("volume", "")
                issue = item.get("issue", "")
                page = item.get("page", "")

                journal_info = journal
                if volume:
                    journal_info += f", {volume}"
                if issue:
                    journal_info += f"({issue})"
                if page:
                    journal_info += f", {page}"
                if year:
                    journal_info += f", {year}"

                # 获取PDF链接
                pdf_url = ""
                for link in item.get("link", []):
                    if link.get("content-type", "") == "application/pdf":
                        pdf_url = link.get("URL", "")
                        break

                papers.append({
                    "id": item.get("DOI", ""),
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "cited_by_count": ref_count,
                    "is_english": is_english,
                    "abstract": "",  # Crossref 不提供摘要
                    "type": item.get("type", ""),
                    "doi": item.get("DOI", ""),
                    "journal": journal,
                    "journal_info": journal_info,
                    "keywords": item.get("subject", [])[:10],
                    "data_source": "crossref",
                    "url": f"https://doi.org/{item.get('DOI', '')}",
                    "pdf_url": pdf_url
                })

            return papers

        except httpx.HTTPError as e:
            print(f"[Crossref] API error: {e}")
            return []
        except Exception as e:
            print(f"[Crossref] 搜索失败: {e}")
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


# 测试代码
async def test_crossref_search():
    """测试 Crossref 搜索"""
    print("=" * 80)
    print("测试 Crossref 搜索")
    print("=" * 80)

    service = CrossrefSearchService()

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
            print(f"   引用: {paper.get('cited_by_count', 0)}")
            print(f"   期刊: {paper.get('journal', 'N/A')}")
            print(f"   DOI: {paper.get('doi', 'N/A')}")

    finally:
        await service.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_crossref_search())
