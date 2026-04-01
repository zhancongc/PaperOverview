"""
自然统计数据嵌入服务
将统计数据自然地融入叙述，避免AI痕迹
"""
import re
import os
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class NaturalStatisticsIntegrator:
    """自然统计数据集成器"""

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    def should_use_statistics(
        self,
        paper: Dict,
        context: str = ""
    ) -> Tuple[bool, str]:
        """
        判断是否应该使用统计数据

        策略：
        1. 只有"突破性发现"才用数据
        2. 样本量大、效应显著的研究才用数据
        3. 负面发现或边界条件也用数据（增加可信度）
        4. 简单重复的研究不用数据（避免冗余）

        Args:
            paper: 论文信息
            context: 上下文信息

        Returns:
            (是否使用数据, 原因说明)
        """
        stats = paper.get("statistics", {})

        # 没有统计数据
        if not stats:
            return False, "无统计数据"

        # 1. 检查是否有显著/突破性发现
        is_breakthrough = self._is_breakthrough_finding(paper, stats)
        if is_breakthrough:
            return True, "突破性发现"

        # 2. 检查样本量（大样本研究用数据更有说服力）
        n = stats.get("n") or stats.get("sample_size")
        if n and n >= 1000:
            return True, "大样本研究"

        # 3. 检查效应显著性
        p = stats.get("p")
        if p and p < 0.001:  # 高度显著
            return True, "高度显著"

        # 4. 检查是否是边界条件/负面发现
        abstract = paper.get("abstract", "").lower()
        boundary_keywords = [
            "边界", "局限", "限制", "衰减", "相反", "负面", "负面效应",
            "boundary", "limit", "constraint", "attenuate", "opposite"
        ]
        if any(kw in abstract for kw in boundary_keywords):
            return True, "边界条件/负面发现"

        # 5. 默认情况：不用数据（避免过度堆砌）
        return False, "常规发现，无需强调"

    def _is_breakthrough_finding(self, paper: Dict, stats: Dict) -> bool:
        """判断是否是突破性发现"""
        # 检查OR值（强效应）
        or_val = stats.get("or")
        if or_val:
            if or_val < 0.5 or or_val > 2.0:  # 强保护或强风险
                return True

        # 检查相关系数
        r = stats.get("r")
        if r and abs(r) >= 0.7:  # 强相关
            return True

        # 检查效应量
        d = stats.get("cohens_d")
        if d and abs(d) >= 0.8:  # 大效应
            return True

        return False

    def format_natural_citation(
        self,
        paper: Dict,
        citation_number: int,
        finding_description: str = None
    ) -> str:
        """
        生成自然的引用格式（数据融入叙述）

        Args:
            paper: 论文信息
            citation_number: 引用编号
            finding_description: 研究发现描述（可选）

        Returns:
            自然的引用字符串
        """
        # 判断是否使用数据
        should_use, reason = self.should_use_statistics(paper)

        if not should_use:
            # 不使用数据，只返回引用
            if finding_description:
                return f"{finding_description}[{citation_number}]"
            else:
                return f"[{citation_number}]"

        # 使用数据，但要自然融入
        stats = paper.get("statistics", {})
        authors = paper.get("authors", ["Unknown"])[0]
        year = paper.get("year", "")

        # 选择最相关的统计数据
        key_stat = self._select_key_statistic(stats, paper)

        # 生成自然表述
        if finding_description:
            return self._embed_data_in_statement(
                finding_description,
                key_stat,
                citation_number
            )
        else:
            return self._generate_data_statement(authors, year, key_stat, citation_number)

    def _select_key_statistic(self, stats: Dict, paper: Dict) -> Dict:
        """选择最关键的统计数据"""
        # 优先级：OR值 > 发生率/百分比 > 相关系数 > P值
        priority = ["or", "rr", "hr", "percentage", "r", "cohens_d", "p"]

        for key in priority:
            if key in stats:
                return {key: stats[key]}

        # 如果没有优先级数据，返回第一个可用的
        for key, value in stats.items():
            if key not in ["paper_id", "paper_title"]:
                return {key: value}

        return {}

    def _embed_data_in_statement(
        self,
        statement: str,
        stat: Dict,
        citation_number: int
    ) -> str:
        """将数据嵌入到陈述中"""
        # 根据数据类型选择嵌入方式
        if "or" in stat:
            or_val = stat["or"]
            if or_val < 1:
                return f"{statement}，风险降低{((1-or_val)*100):.0f}%[{citation_number}]"
            else:
                return f"{statement}，风险增加{((or_val-1)*100):.0f}%[{citation_number}]"

        elif "percentage" in stat:
            pct = stat["percentage"]
            if "下降" in statement or "降低" in statement or "减少" in statement:
                return f"{statement}，下降幅度达{pct:.1f}%[{citation_number}]"
            elif "上升" in statement or "增加" in statement or "提高" in statement:
                return f"{statement}，提升幅度达{pct:.1f}%[{citation_number}]"
            else:
                return f"{statement}，比例为{pct:.1f}%[{citation_number}]"

        elif "p" in stat:
            p_val = stat["p"]
            if p_val < 0.001:
                return f"{statement}，效应高度显著[{citation_number}]"
            elif p_val < 0.01:
                return f"{statement}，效应显著[{citation_number}]"
            else:
                return f"{statement}，具有统计学意义[{citation_number}]"

        # 默认：不添加数据
        return f"{statement}[{citation_number}]"

    def _generate_data_statement(
        self,
        author: str,
        year: int,
        stat: Dict,
        citation_number: int
    ) -> str:
        """生成数据陈述"""
        if "or" in stat:
            or_val = stat["or"]
            if or_val < 1:
                return f"{author}等({year})发现风险降低{((1-or_val)*100):.0f}%[{citation_number}]"
            else:
                return f"{author}等({year})发现风险增加{((or_val-1)*100):.0f}%[{citation_number}]"

        elif "percentage" in stat:
            pct = stat["percentage"]
            return f"{author}等({year})报告的比例为{pct:.1f}%[{citation_number}]"

        elif "r" in stat:
            r_val = stat["r"]
            if abs(r_val) >= 0.7:
                return f"{author}等({year})发现强相关（r={r_val:.2f}）[{citation_number}]"

        return f"[{citation_number}]"

    async def generate_natural_summary(
        self,
        papers: List[Dict],
        topic: str,
        context: str = ""
    ) -> str:
        """
        生成自然的综述摘要（数据融入叙述）

        Args:
            papers: 论文列表
            topic: 研究主题
            context: 上下文

        Returns:
            自然的综述摘要
        """
        # 按重要性对论文排序
        prioritized_papers = self._prioritize_papers(papers)

        # 选择性使用数据（只对重要论文）
        content_parts = []

        for i, paper in enumerate(prioritized_papers[:8], 1):  # 最多8篇
            should_use, reason = self.should_use_statistics(paper, context)

            # 提取核心发现
            abstract = paper.get("abstract", "")
            if abstract:
                # 提取第一句作为核心发现
                first_sentence = abstract.split("。")[0][:100]

                if should_use:
                    # 选择性嵌入数据
                    stat = paper.get("statistics", {})
                    if stat:
                        key_stat = self._select_key_statistic(stat, paper)
                        integrated = self._embed_data_in_statement(
                            f"{first_sentence}。",
                            key_stat,
                            i
                        )
                        content_parts.append(integrated)
                    else:
                        content_parts.append(f"{first_sentence}[{i}]")
                else:
                    content_parts.append(f"{first_sentence}[{i}]")

        # 生成综述段落
        if content_parts:
            summary = " ".join(content_parts[:5])  # 最多5句话
            summary = re.sub(r'\[。\s+', "[", summary)  # 清理可能的格式错误
            return summary + "。"
        else:
            return f"现有研究为{topic}提供了支持。"

    def _prioritize_papers(self, papers: List[Dict]) -> List[Dict]:
        """按重要性排序论文"""
        def calculate_priority(paper):
            score = 0

            # 被引量
            citations = paper.get("cited_by_count", 0)
            score += min(citations / 10, 30)

            # 年份（近5年加分）
            year = paper.get("year", 0)
            if year >= 2019:
                score += 10

            # 是否有突破性数据
            stats = paper.get("statistics", {})
            if stats.get("or"):
                or_val = stats["or"]
                if or_val < 0.5 or or_val > 2:
                    score += 20

            if stats.get("p", 1) < 0.01:
                score += 15

            return score

        return sorted(papers, key=calculate_priority, reverse=True)


class NaturalReviewGenerator:
    """自然综述生成器（避免AI痕迹）"""

    def __init__(self):
        self.integrator = NaturalStatisticsIntegrator()

    async def generate_natural_review(
        self,
        topic: str,
        papers: List[Dict],
        style: str = "natural"
    ) -> str:
        """
        生成自然的综述内容

        Args:
            topic: 研究主题
            papers: 论文列表
            style: 风格（natural, balanced, data-rich）

        Returns:
            生成的综述内容
        """
        # 按主题分组论文
        grouped_papers = self._group_papers_by_theme(papers)

        content_parts = []

        for theme, theme_papers in grouped_papers.items():
            if len(theme_papers) == 1:
                paper = theme_papers[0]
                should_use, reason = self.integrator.should_use_statistics(paper)
                if should_use:
                    content_parts.append(self._generate_single_with_data(paper, theme))
                else:
                    content_parts.append(self._generate_simple_citation(paper, theme))
            else:
                content_parts.append(await self._generate_group_comparison(theme_papers, theme))

        return "\n\n".join(content_parts)

    def _generate_single_with_data(
        self,
        paper: Dict,
        theme: str
    ) -> str:
        """生成单篇论文的引用（带数据）"""
        abstract = paper.get("abstract", "")
        first_sentence = abstract.split("。")[0][:100] if abstract else ""

        # 提取并嵌入关键数据
        stats = paper.get("statistics", {})
        if stats:
            key_stat = self.integrator._select_key_statistic(stats, paper)
            return f"{first_sentence}，{self.integrator._embed_data_in_statement('', key_stat, 1)}"
        else:
            return f"{first_sentence}[1]"

    def _generate_simple_citation(self, paper: Dict, theme: str) -> str:
        """生成简单引用（不带数据）"""
        abstract = paper.get("abstract", "")
        first_sentence = abstract.split("。")[0][:100] if abstract else ""
        return f"{first_sentence}[1]"

    async def _generate_group_comparison(
        self,
        papers: List[Dict],
        theme: str
    ) -> str:
        """生成群体对比（自然融入数据）"""
        # 找出有强数据的论文
        papers_with_data = [
            p for p in papers
            if p.get("statistics") and self.integrator.should_use_statistics(p)[0]
        ]

        if not papers_with_data:
            # 都没有数据，用简单引用
            return f"关于{theme}，多项研究提供了支持。"

        # 选择最有说服力的数据
        content_parts = []

        for paper in papers_with_data[:3]:
            abstract = paper.get("abstract", "")
            first_sentence = abstract.split("。")[0][:80]

            # 融入数据
            stats = paper.get("statistics", {})
            key_stat = self.integrator._select_key_statistic(stats, paper)

            # 生成长句式引用
            if "or" in key_stat:
                or_val = key_stat["or"]
                if or_val < 1:
                    content_parts.append(f"{first_sentence}，风险降低{((1-or_val)*100):.0f}%")
                else:
                    content_parts.append(f"{first_sentence}，风险增加{((or_val-1)*100):.0f}%")
            else:
                content_parts.append(first_sentence)

        # 生成段落
        if len(content_parts) >= 2:
            # 找出对立观点
            first = content_parts[0]
            if "降低" in first:
                second_template = "然而，也有研究指出效果有限"
            else:
                second_template = "进一步的研究证实了"

            if len(content_parts) > 1:
                return f"{content_parts[0]}；{content_parts[1]}{second_template}。"

        return "相关研究提供了支持。"

    def _group_papers_by_theme(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """按主题分组论文"""
        groups = {
            "正面发现": [],
            "负面发现": [],
            "边界条件": [],
            "方法论": []
        }

        for paper in papers:
            abstract = paper.get("abstract", "").lower()
            title = paper.get("title", "").lower()

            if any(kw in abstract or kw in title for kw in ["支持", "积极", "有效", "提升", "改善"]):
                groups["正面发现"].append(paper)
            elif any(kw in abstract or kw in title for kw in ["限制", "局限", "负面", "衰减", "抑制"]):
                groups["负面发现"].append(paper)
            elif any(kw in abstract or kw in title for kw in ["边界", "条件", "情境", "调节"]):
                groups["边界条件"].append(paper)
            else:
                groups["方法论"].append(paper)

        # 移除空组
        return {k: v for k, v in groups.items() if v}


# 便捷导出函数
async def generate_natural_review_summary(
    papers: List[Dict],
    topic: str
) -> str:
    """
    生成自然的综述摘要

    Args:
        papers: 论文列表
        topic: 研究主题

    Returns:
        自然的综述摘要
    """
    integrator = NaturalStatisticsIntegrator()
    return await integrator.generate_natural_summary(papers, topic)


def format_natural_citation(
    paper: Dict,
    citation_number: int,
    finding_description: str = None
) -> str:
    """
    生成自然的引用格式

    Args:
        paper: 论文信息
        citation_number: 引用编号
        finding_description: 研究发现描述

    Returns:
        自然的引用字符串
    """
    integrator = NaturalStatisticsIntegrator()
    return integrator.format_natural_citation(paper, citation_number, finding_description)


# 演示用的示例对比
EXAMPLES = {
    "ai_style": {
        "description": "AI痕迹明显的堆砌式引用",
        "example": """Zhang等[1](OR=0.65, p<0.001)发现显著效应；Li等[2](OR=1.2, p<0.01)也支持这一结论；Wang等[3](p=0.05)的研究证实了这一点。"""
    },
    "natural_style": {
        "description": "自然融入数据的引用",
        "example": """关于QFD的实际效果，学界尚未形成完全一致的结论。多数制造业实证研究支持其积极价值，如Zhang等[1]发现实施QFD后产品缺陷率下降了35%。然而，Wang等[2]基于服务企业的研究指出，在组织流程标准化程度较低的情境下，QFD的效果存在明显衰减。"""
    }
}
