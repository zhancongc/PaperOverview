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
        topic_keywords: List[str] | None = None
    ) -> List[Dict]:
        """
        筛选并排序论文

        筛选原则：
        1. 主题不相关 → 一票否决
        2. 主题相关 → 按优先级排序：年份 > 被引量

        Args:
            papers: 原始论文列表
            target_count: 目标数量（默认50篇）
            recent_years_ratio: 近5年占比要求（默认50%）
            topic_keywords: 题目关键词，用于相关性评分

        Returns:
            筛选后的论文列表
        """
        if not papers:
            return []

        # ========== 第一步：主题相关性一票否决 ==========
        relevant_papers = []
        for paper in papers:
            if self._is_topic_relevant(paper, topic_keywords):
                relevant_papers.append(paper)

        print(f"[筛选] 原始论文: {len(papers)} 篇，主题相关: {len(relevant_papers)} 篇")

        if not relevant_papers:
            return []

        # ========== 第二步：对主题相关的论文评分 ==========
        scored_papers = []
        for paper in relevant_papers:
            score = self._calculate_relevance_score(paper, topic_keywords)
            scored_papers.append({**paper, '_relevance_score': score})

        # 按相关性评分排序
        scored_papers.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)

        current_year = datetime.now().year
        recent_threshold = current_year - 5

        # 分类（基于评分排序后的论文）
        recent_papers = [p for p in scored_papers if p.get("year") is not None and p.get("year") >= recent_threshold]
        old_papers = [p for p in scored_papers if p.get("year") is not None and p.get("year") < recent_threshold]

        # 计算需要的数量
        recent_needed = int(target_count * recent_years_ratio)

        selected = set()
        result = []

        # 优先选择：近5年（高相关性）
        for paper in recent_papers:
            if len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 补充：5年前
        for paper in old_papers:
            if len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 如果不足目标数量，从所有相关论文中补充
        if len(result) < target_count:
            for paper in scored_papers:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)
                    if len(result) >= target_count:
                        break

        # 将 _relevance_score 转换为 relevance_score（返回给前端）
        for paper in result:
            if '_relevance_score' in paper:
                paper['relevance_score'] = paper.pop('_relevance_score')

        return result[:target_count]

    def _is_topic_relevant(self, paper: Dict, topic_keywords: List[str] | None) -> bool:
        """
        判断论文是否与主题相关（一票否决制）

        Args:
            paper: 论文信息
            topic_keywords: 主题关键词列表

        Returns:
            True 如果主题相关，False 如果不相关
        """
        # 如果没有关键词，默认都相关
        if not topic_keywords:
            return True

        title_lower = (paper.get("title") or "").lower()
        abstract_lower = (paper.get("abstract") or "").lower()

        # 检查标题中是否有关键词匹配
        for kw in topic_keywords:
            if kw is None:
                continue
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                return True

        # 检查摘要中是否有关键词匹配（至少2个）
        matched_abstract = 0
        for kw in topic_keywords:
            if kw is None:
                continue
            kw_lower = kw.lower()
            if kw_lower in abstract_lower:
                matched_abstract += 1
                if matched_abstract >= 2:
                    return True

        # 检查概念标签中是否有关键词匹配
        concepts = paper.get("concepts", [])
        for concept in concepts:
            if concept is None:
                continue
            concept_lower = concept.lower()
            for kw in topic_keywords:
                if kw is not None and kw.lower() in concept_lower:
                    return True

        # 没有任何匹配，一票否决
        return False

    def _calculate_relevance_score(self, paper: Dict, topic_keywords: List[str] | None) -> float:
        """
        计算论文与主题的相关性评分

        评分原则（优先级从高到低）：
        1. 主题相关性（最优先，0-50分）
        2. 时间新近度（次优先，0-35分）
        3. 被引量（最后，0-15分）

        Args:
            paper: 论文信息
            topic_keywords: 主题关键词列表

        Returns:
            相关性评分（0-100）
        """
        score = 0.0

        # ========== 1. 主题相关性（最优先，0-50分）==========
        if topic_keywords:
            title_lower = (paper.get("title") or "").lower()
            abstract_lower = (paper.get("abstract") or "").lower()

            # 标题中的关键词匹配（每匹配一个加 18 分，最多 36 分）
            matched_title = 0
            for kw in topic_keywords:
                if kw is None:
                    continue  # 跳过 None 值
                kw_lower = kw.lower()
                if kw_lower in title_lower:
                    score += 18
                    matched_title += 1
                    if matched_title >= 2:  # 最多2个标题关键词匹配
                        break

            # 摘要中的关键词匹配（每匹配一个加 5 分，最多 10 分）
            matched_abstract = 0
            for kw in topic_keywords:
                if kw is None:
                    continue
                kw_lower = kw.lower()
                if kw_lower not in title_lower and kw_lower in abstract_lower:
                    score += 5
                    matched_abstract += 1
                    if matched_abstract >= 2:
                        break

            # 检查概念标签（额外加分，最多 4 分）
            concepts = paper.get("concepts", [])
            matched_concepts = 0
            for concept in concepts:
                if concept is None:
                    continue
                concept_lower = concept.lower()
                for kw in topic_keywords:
                    if kw is not None and kw.lower() in concept_lower:
                        score += 2
                        matched_concepts += 1
                        break
                if matched_concepts >= 2:
                    break

        # ========== 2. 时间新近度（次优先，0-35分）==========
        current_year = datetime.now().year
        paper_year = paper.get("year")
        if paper_year is not None and paper_year >= current_year - 5:
            score += 35  # 近5年加 35 分（高优先级）
        elif paper_year is not None and paper_year >= current_year - 8:
            score += 20  # 5-8年前加 20 分
        elif paper_year is not None and paper_year >= current_year - 10:
            score += 10  # 8-10年前加 10 分

        # ========== 3. 被引量（最后考虑，0-15分）==========
        # 在主题相关且时间合适的基础上，高被引论文加分
        citations = paper.get("cited_by_count", 0)
        score += min(citations / 10, 15)

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
