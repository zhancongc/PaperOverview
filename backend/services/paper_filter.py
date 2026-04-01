"""
文献筛选与排序服务
"""
from typing import List, Dict
from datetime import datetime, timedelta


class PaperFilterService:
    def __init__(self):
        pass

    def filter_and_sort(
        self,
        papers: List[Dict],
        target_count: int = 50,
        recent_years_ratio: float = 0.5,
        english_ratio: float = 0.3,
        topic_keywords: List[str] | None = None
    ) -> List[Dict]:
        """
        筛选并排序论文

        Args:
            papers: 原始论文列表
            target_count: 目标数量（默认50篇）
            recent_years_ratio: 近5年占比要求（默认50%）
            english_ratio: 英文文献占比要求（默认30%）
            topic_keywords: 题目关键词，用于相关性评分

        Returns:
            筛选后的论文列表
        """
        if not papers:
            return []

        # 计算每篇论文的相关性评分
        scored_papers = []
        for paper in papers:
            score = self._calculate_relevance_score(paper, topic_keywords)
            scored_papers.append({**paper, '_relevance_score': score})

        # 按相关性评分排序
        scored_papers.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)

        current_year = datetime.now().year
        recent_threshold = current_year - 5

        # 分类（基于评分排序后的论文）
        recent_papers = [p for p in scored_papers if p.get("year") is not None and p.get("year") >= recent_threshold]
        old_papers = [p for p in scored_papers if p.get("year") is not None and p.get("year") < recent_threshold]

        english_papers = [p for p in scored_papers if p.get("is_english", False)]
        non_english_papers = [p for p in scored_papers if not p.get("is_english", False)]

        # 计算需要的数量
        recent_needed = int(target_count * recent_years_ratio)
        english_needed = int(target_count * english_ratio)

        selected = set()
        result = []

        # 优先选择：近5年 + 英文（高相关性）
        for paper in recent_papers:
            if paper.get("is_english") and len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 补充：近5年 + 非英文
        for paper in recent_papers:
            if not paper.get("is_english") and len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 补充：5年前 + 英文
        for paper in old_papers:
            if paper.get("is_english") and len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 补充：5年前 + 非英文
        for paper in old_papers:
            if not paper.get("is_english") and len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 如果不足目标数量，从所有论文中补充
        if len(result) < target_count:
            for paper in scored_papers:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)
                    if len(result) >= target_count:
                        break

        # 移除临时评分字段
        for paper in result:
            paper.pop('_relevance_score', None)

        return result[:target_count]

    def _calculate_relevance_score(self, paper: Dict, topic_keywords: List[str] | None) -> float:
        """
        计算论文与主题的相关性评分

        Args:
            paper: 论文信息
            topic_keywords: 主题关键词列表

        Returns:
            相关性评分（0-100）
        """
        score = 0.0

        # 基础分：被引量（归一化到 0-30 分）
        citations = paper.get("cited_by_count", 0)
        score += min(citations / 10, 30)

        # 如果有主题关键词，计算关键词匹配度
        if topic_keywords:
            title_lower = paper.get("title", "").lower()
            abstract_lower = paper.get("abstract", "").lower()
            keywords = " ".join(topic_keywords).lower()

            # 标题中的关键词匹配（每匹配一个加 10 分）
            for kw in topic_keywords:
                if kw.lower() in title_lower:
                    score += 15  # 标题匹配权重更高
                elif kw.lower() in abstract_lower:
                    score += 5   # 摘要匹配权重较低

            # 检查概念标签
            concepts = paper.get("concepts", [])
            for concept in concepts:
                if any(kw.lower() in concept.lower() for kw in topic_keywords):
                    score += 3
                    break  # 每个概念只计算一次

        # 新近论文加分
        current_year = datetime.now().year
        paper_year = paper.get("year")
        if paper_year is not None and paper_year >= current_year - 5:
            score += 10  # 近5年加 10 分
        elif paper_year is not None and paper_year >= current_year - 10:
            score += 5   # 5-10年前加 5 分

        # 英文论文加分（因为通常质量更好）
        if paper.get("is_english", False):
            score += 5

        return min(score, 100)  # 最高 100 分

    def get_statistics(self, papers: List[Dict]) -> Dict:
        """获取论文统计信息"""
        if not papers:
            return {}

        current_year = datetime.now().year
        recent_threshold = current_year - 5

        recent_count = sum(1 for p in papers if p.get("year") is not None and p.get("year") >= recent_threshold)
        english_count = sum(1 for p in papers if p.get("is_english", False))
        total_citations = sum(p.get("cited_by_count", 0) for p in papers)

        return {
            "total": len(papers),
            "recent_count": recent_count,
            "recent_ratio": recent_count / len(papers) if papers else 0,
            "english_count": english_count,
            "english_ratio": english_count / len(papers) if papers else 0,
            "total_citations": total_citations,
            "avg_citations": total_citations / len(papers) if papers else 0
        }
