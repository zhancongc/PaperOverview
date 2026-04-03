"""
OpenAlex 文献检索服务
无需 API key，完全免费
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class PaperSearchService:
    BASE_URL = "https://api.openalex.org"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

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
        # 计算截止日期
        cutoff_date = (datetime.now() - timedelta(days=years_ago * 365)).strftime("%Y-%m-%d")

        papers = []
        try:
            # 策略1: 先使用严格的领域限定搜索（计算机科学）
            # 使用 concepts.id 而不是 concepts.name（Computer Science ID: C41008148）
            print(f"[OpenAlex] 搜索: {query} (限定: Computer Science)")

            params_strict = {
                "search": query,
                "filter": f"from_publication_date:{cutoff_date},has_abstract:true,concepts.id:C41008148",
                "sort": "cited_by_count:desc",
                "per_page": min(limit, 200)
            }

            response = await self.client.get(f"{self.BASE_URL}/works", params=params_strict)
            response.raise_for_status()
            data = response.json()

            results_count = len(data.get("results", []))
            print(f"[OpenAlex] 搜索返回: {results_count} 篇")

            # 如果结果太少，放宽限制（只限定有摘要和年份）
            if results_count < 10:
                print(f"[OpenAlex] 结果不足，放宽限制（只限定年份和摘要）")
                params_relaxed = {
                    "search": query,
                    "filter": f"from_publication_date:{cutoff_date},has_abstract:true",
                    "sort": "cited_by_count:desc",
                    "per_page": min(limit, 200)
                }
                response = await self.client.get(f"{self.BASE_URL}/works", params=params_relaxed)
                response.raise_for_status()
                data = response.json()
                print(f"[OpenAlex] 放宽搜索返回: {len(data.get('results', []))} 篇")

            # 处理搜索结果
            for item in data.get("results", []):
                # 额外的相关性过滤：检查主题是否相关
                concepts = [c.get("display_name", "").lower() for c in item.get("concepts", [])]

                # 相关领域关键词（计算机科学相关）
                relevant_fields = [
                    'computer science', 'programming', 'software', 'algorithm',
                    'artificial intelligence', 'machine learning', 'deep learning',
                    'natural language processing', 'nlp', 'language model',
                    'code', 'coding', 'programming language', 'software engineering',
                    'data', 'database', 'information', 'computing'
                ]

                # 不相关领域关键词
                irrelevant_fields = [
                    'medicine', 'medical', 'clinical', 'healthcare', 'health',
                    'biology', 'biological', 'genetics', 'dna', 'gene', 'genomic',
                    'chemistry', 'chemical', 'physics', 'quantum',
                    'geology', 'environmental', 'climate', 'ecology',
                    'political science', 'sociology', 'psychology'
                ]

                # 检查是否包含相关领域的概念
                has_relevant = any(any(field in c for field in relevant_fields) for c in concepts)
                # 检查是否包含太多不相关领域的概念
                irrelevant_count = sum(1 for c in concepts if any(field in c for field in irrelevant_fields))

                # 如果没有相关概念，或者有太多不相关概念，跳过
                if not has_relevant or irrelevant_count >= 2:
                    continue

                # 过滤被引量
                cited_by_count = item.get("cited_by_count", 0)
                if cited_by_count < min_citations:
                    continue

                # 提取作者信息
                authors = []
                for authorship in item.get("authorships", []):
                    author = authorship.get("author", {})
                    if author:
                        authors.append(author.get("display_name", ""))

                # 判断语言（简单判断：标题含非ASCII字符可能是中文）
                title = item.get("title", "")
                is_english = self._is_english(title)

                papers.append({
                    "id": item.get("id", ""),
                    "title": title,
                    "authors": authors,
                    "year": item.get("publication_year"),
                    "cited_by_count": cited_by_count,
                    "is_english": is_english,
                    "abstract": self._clean_abstract(item.get("abstract", "")),
                    "type": item.get("type", ""),
                    "doi": item.get("doi", ""),
                    "primary_location": item.get("primary_location", {}),
                    "concepts": [c.get("display_name") for c in item.get("concepts", "")[:5]]
                })

            return papers

        except httpx.HTTPError as e:
            print(f"OpenAlex API error: {e}")
            return []

    def _is_english(self, text: str) -> bool:
        """简单判断文本是否为英文"""
        if not text:
            return False
        # 计算非ASCII字符比例
        non_ascii = sum(1 for c in text if ord(c) > 127)
        return non_ascii / len(text) < 0.3

    def _clean_abstract(self, abstract: str) -> str:
        """清理摘要文本（OpenAlex 的摘要有特殊标记）"""
        if not abstract:
            return ""
        # 移除 XML 标签
        import re
        abstract = re.sub(r'<[^>]+>', '', abstract)
        return abstract.strip()

    async def close(self):
        await self.client.aclose()
