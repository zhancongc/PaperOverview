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
        english_ratio: float = 0.3
    ) -> List[Dict]:
        """
        筛选并排序论文

        Args:
            papers: 原始论文列表
            target_count: 目标数量（默认50篇）
            recent_years_ratio: 近5年占比要求（默认50%）
            english_ratio: 英文文献占比要求（默认30%）

        Returns:
            筛选后的论文列表
        """
        if not papers:
            return []

        current_year = datetime.now().year
        recent_threshold = current_year - 5

        # 分类
        recent_papers = [p for p in papers if p.get("year", 0) >= recent_threshold]
        old_papers = [p for p in papers if p.get("year", 0) < recent_threshold]

        english_papers = [p for p in papers if p.get("is_english", False)]
        non_english_papers = [p for p in papers if not p.get("is_english", False)]

        # 按被引量排序（已排序，确保顺序）
        recent_papers.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
        old_papers.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
        english_papers.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
        non_english_papers.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)

        # 计算需要的数量
        recent_needed = int(target_count * recent_years_ratio)
        english_needed = int(target_count * english_ratio)

        selected = set()
        result = []

        # 优先选择：近5年 + 英文
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

        # 如果不足50篇，从所有论文中补充
        if len(result) < target_count:
            for paper in papers:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)
                    if len(result) >= target_count:
                        break

        # 按被引量排序最终结果
        result.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)

        return result[:target_count]

    def get_statistics(self, papers: List[Dict]) -> Dict:
        """获取论文统计信息"""
        if not papers:
            return {}

        current_year = datetime.now().year
        recent_threshold = current_year - 5

        recent_count = sum(1 for p in papers if p.get("year", 0) >= recent_threshold)
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
