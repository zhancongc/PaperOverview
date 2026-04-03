"""
文献质量过滤服务
过滤掉低质量文献（如会议通知、工作报告、内部资料等）
"""
import re
from typing import List, Dict, Optional


class PaperQualityFilter:
    """文献质量过滤器"""

    # 低质量文献模式
    LOW_QUALITY_PATTERNS = [
        # 会议通知/记录
        r'会议通知|会议记录|会议纪要|工作会议|年会|研讨会',
        r'召开.*会议|举办.*会议|.*会议召开|.*会议举行',

        # 内部资料/工作报告
        r'内部资料|内部刊物|工作简报|工作动态|工作通讯',
        r'年度报告|工作总结|工作计划|工作报告|进展报告',

        # 新闻/通知
        r'启事|通知|公告|声明|辟谣',
        r'新闻发布会|答记者问',

        # 非学术内容
        r'征稿启事|征文通知|稿约|征订|停刊通知|休刊公告',
        r'更正启事|撤稿声明|致歉',

        # 机构库/仓储低质量内容
        r'Institutional Repository.*of.*',
        r'机构知识库|机构库|成果库',

        # 无意义标题
        r'^[a-zA-Z]\s*\)|^\[\d+\]|\(未标注\)|\(标注缺失\)',
    ]

    # 低质量期刊/来源模式
    LOW_QUALITY_VENUE_PATTERNS = [
        r'Institutional Repository',
        r'机构知识库',
        r'内部刊物',
        r'工作简报',
        r'内部资料',
    ]

    # 无意义作者
    LOW_QUALITY_AUTHORS = [
        '佚名',
        '匿名',
        '未标注',
        '不详',
        '综合办公室',
        '编辑部',
        '委员会',
        '未知作者',
        'Author Unknown',  # 英文未知作者
    ]

    def __init__(self):
        """编译正则表达式"""
        self.title_patterns = [re.compile(p, re.IGNORECASE) for p in self.LOW_QUALITY_PATTERNS]
        self.venue_patterns = [re.compile(p, re.IGNORECASE) for p in self.LOW_QUALITY_VENUE_PATTERNS]

    def is_low_quality_paper(self, paper: Dict) -> tuple:
        """
        判断文献是否为低质量文献

        Args:
            paper: 论文信息

        Returns:
            (是否低质量, 原因)
        """
        title = paper.get('title', '')

        # 安全获取 venue
        venue = paper.get('journal', '') or paper.get('venue', '')
        if not venue:
            primary_location = paper.get('primary_location')
            if primary_location and isinstance(primary_location, dict):
                source = primary_location.get('source')
                if source and isinstance(source, dict):
                    venue = source.get('display_name', '')

        authors = paper.get('authors', [])
        year = paper.get('year', 0)
        cited = paper.get('cited_by_count', 0)

        # 1. 检查标题模式
        for pattern in self.title_patterns:
            if pattern.search(title):
                return True, f"标题匹配低质量模式: {pattern.pattern}"

        # 2. 检查来源/期刊
        for pattern in self.venue_patterns:
            if pattern.search(venue):
                return True, f"来源为低质量: {pattern.pattern}"

        # 3. 检查作者
        if authors:
            first_author = authors[0]
            if first_author in self.LOW_QUALITY_AUTHORS:
                return True, f"作者为低质量: {first_author}"

        # 4. 检查是否为机构仓储内容（通常是内部资料）
        # 注意：被引为0不代表低质量，可能只是新论文
        if 'Institutional Repository' in venue or '机构知识库' in venue:
            # 机构仓储内容通常是低质量的，无论是否有被引
            return True, "机构仓储内容"

        # 5. 检查标题是否过短或无意义
        # 去除空格和标点后，如果少于5个字符，可能是无意义标题
        clean_title = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
        if len(clean_title) < 5:
            return True, "标题过短"

        # 6. 检查是否为年份过新且来源不明的文献（可能是低质量）
        current_year = 2026
        if year is not None and year >= current_year - 2:
            # 近2年发表的新文献，需要更严格检查来源
            # 不再以被引为0作为判断标准
            if not venue or len(venue) < 5:
                return True, "新文献且来源不明"

        return False, None

    def filter_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        过滤掉低质量文献

        Args:
            papers: 论文列表

        Returns:
            过滤后的论文列表
        """
        filtered = []
        removed_count = 0

        for paper in papers:
            is_low, _ = self.is_low_quality_paper(paper)

            if is_low:
                removed_count += 1
            else:
                filtered.append(paper)

        return filtered

    def get_paper_quality_score(self, paper: Dict) -> float:
        """
        计算文献质量得分（0-100）

        Args:
            paper: 论文信息

        Returns:
            质量得分
        """
        score = 50.0  # 基础分

        title = paper.get('title', '')
        venue = paper.get('journal', '') or paper.get('venue', '')
        year = paper.get('year')
        cited = paper.get('cited_by_count', 0)
        authors = paper.get('authors', [])

        # 被引量加分（最高30分）
        if cited > 0:
            score += min(cited / 5, 30)

        # 年份加分（近10年加分，最高10分）
        if year is not None and year >= 2015:
            score += 10

        # 作者数量加分（有作者加分，最高5分）
        if authors and len(authors) > 0:
            score += min(len(authors), 5)

        # 来源质量（有来源加分，最高5分）
        if venue and len(venue) > 10:
            score += 5

        # 标题长度（适中长度加分，最高5分）
        title_len = len(title)
        if 10 <= title_len <= 100:
            score += 5
        elif title_len > 5:
            score += 2

        # 低质量模式扣分
        is_low, _ = self.is_low_quality_paper(paper)
        if is_low:
            score = 0  # 低质量文献直接0分

        return min(score, 100)


# 全局实例
quality_filter = PaperQualityFilter()


def filter_low_quality_papers(papers: List[Dict]) -> List[Dict]:
    """
    过滤掉低质量文献（便捷函数）

    Args:
        papers: 论文列表

    Returns:
        过滤后的论文列表
    """
    return quality_filter.filter_papers(papers)
