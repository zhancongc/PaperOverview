"""
基于标题的文献相关性快速检查

在调用 LLM 之前，先用规则快速筛选明显不相关的文献
"""
import re
from typing import List, Dict, Tuple


class TitleRelevanceChecker:
    """标题相关性检查器"""

    # 明显不相关的领域关键词
    IRRELEVANT_DOMAINS = {
        "computer_algebra": {  # 计算机代数系统
            "exclude_keywords": [
                # 软件工程/程序分析
                "symbolic execution", "path exploration", "constraint solving",
                "software testing", "vulnerability detection", "program analysis",
                "static analysis", "dynamic analysis", "code coverage",
                # 安全相关
                "smart contract", "vulnerability", "security analysis",
                # 生物信息学
                "protein", "gene", "dna", "bioinformatics", "omics",
                "neural network", "deep learning",
            ],
            "include_keywords": [
                "computer algebra", "symbolic computation", "mathematica",
                "maple", "maxima", "sage", "symbolic integration",
                "equation solving", "polynomial", "algebra system",
                "mathematical software", "cas", "formula manipulation",
            ],
        },
        "symbolic_execution": {  # 符号执行
            "exclude_keywords": [
                # 数学软件
                "mathematica", "maple", "maxima", "sage", "wolfram",
                "symbolic integration" if "execution" not in "symbolic integration" else "",
                "equation solving", "algebra system",
                # 生物信息学
                "protein", "gene", "dna", "bioinformatics",
            ],
            "include_keywords": [
                "symbolic execution", "path exploration", "constraint solving",
                "klee", "angr", "symbolic", "concolic", "dynamic symbolic",
                "software verification", "program analysis", "test generation",
            ],
        },
        "machine_learning": {  # 机器学习
            "exclude_keywords": [
                # 数学软件
                "mathematica", "maple", "symbolic computation",
                # 程序分析（除非是 ML for program analysis）
                "static analysis", "symbolic execution",
            ],
            "include_keywords": [
                "machine learning", "deep learning", "neural network",
                "cnn", "rnn", "transformer", "artificial intelligence",
                "supervised learning", "unsupervised learning",
            ],
        },
    }

    @classmethod
    def check_title_relevance(
        cls,
        title: str,
        topic: str,
        domain: str = None
    ) -> Tuple[bool, str]:
        """
        检查文章标题是否与主题相关

        Args:
            title: 文章标题
            topic: 论文主题
            domain: 领域（可选）

        Returns:
            (是否相关, 原因说明)
        """
        title_lower = title.lower()

        # 如果没有指定领域，尝试自动识别
        if not domain:
            from services.contextual_keyword_translator import DomainKnowledge
            domain = DomainKnowledge.identify_domain(topic)

        # 如果无法识别领域，使用通用检查
        if not domain:
            return cls._generic_check(title, topic)

        # 获取领域规则
        domain_rules = cls.IRRELEVANT_DOMAINS.get(domain, {})

        # 第一步：检查是否包含排除关键词
        for exclude_kw in domain_rules.get("exclude_keywords", []):
            if exclude_kw and exclude_kw.lower() in title_lower:
                # 特殊处理：如果是复合词，检查是否真的是排除的
                # 例如 "symbolic integration" 在计算机代数中是相关的
                if domain == "computer_algebra" and "symbolic" in exclude_kw:
                    # 检查是否同时包含 "execution" 或 "testing"
                    if "execution" in title_lower or "testing" in title_lower:
                        return False, f"包含排除术语 '{exclude_kw}' (与符号执行相关)"
                else:
                    return False, f"包含排除术语 '{exclude_kw}'"

        # 第二步：检查是否包含相关关键词
        for include_kw in domain_rules.get("include_keywords", []):
            if include_kw and include_kw.lower() in title_lower:
                return True, f"包含相关术语 '{include_kw}'"

        # 第三步：检查主题关键词
        topic_keywords = cls._extract_topic_keywords(topic)
        title_words = set(title_lower.split())

        # 计算重叠度
        overlap = 0
        matched_words = []
        for kw in topic_keywords:
            if kw.lower() in title_lower:
                overlap += 1
                matched_words.append(kw)

        if overlap >= 2:
            return True, f"与主题关键词匹配: {', '.join(matched_words[:3])}"

        # 如果没有明确匹配，返回不确定
        return None, "无法通过标题确定相关性"

    @classmethod
    def _generic_check(cls, title: str, topic: str) -> Tuple[bool, str]:
        """
        通用相关性检查（当无法识别领域时）

        Args:
            title: 文章标题
            topic: 论文主题

        Returns:
            (是否相关, 原因说明)
        """
        title_lower = title.lower()
        topic_lower = topic.lower()

        # 提取主题关键词
        topic_keywords = cls._extract_topic_keywords(topic)

        # 检查标题是否包含主题关键词
        matched = []
        for kw in topic_keywords:
            if kw.lower() in title_lower:
                matched.append(kw)

        if len(matched) >= 2:
            return True, f"包含主题关键词: {', '.join(matched[:3])}"
        elif len(matched) == 1:
            return None, f"仅包含1个主题关键词 '{matched[0]}'，需要进一步判断"
        else:
            return False, f"不包含主题关键词"

    @classmethod
    def _extract_topic_keywords(cls, topic: str) -> List[str]:
        """
        从主题中提取关键词

        Args:
            topic: 论文主题

        Returns:
            关键词列表
        """
        keywords = []

        # 提取英文单词（3个字母以上）
        english_words = re.findall(r'[a-zA-Z]{3,}', topic)
        keywords.extend([w for w in english_words if w.lower() not in
                         ['the', 'and', 'for', 'with', 'based', 'using', 'application']])

        # 提取中文词汇（2-4个字）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', topic)
        keywords.extend(chinese_words)

        # 提取缩写（全大写）
        abbreviations = re.findall(r'[A-Z]{2,}', topic)
        keywords.extend(abbreviations)

        return list(set(keywords))

    @classmethod
    def batch_check_titles(
        cls,
        papers: List[Dict],
        topic: str,
        domain: str = None
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        批量检查论文标题的相关性

        Args:
            papers: 论文列表
            topic: 论文主题
            domain: 领域

        Returns:
            (相关论文, 不相关论文, 不确定论文)
        """
        relevant = []
        irrelevant = []
        uncertain = []

        for paper in papers:
            title = paper.get('title', '')
            if not title:
                uncertain.append(paper)
                continue

            is_relevant, reason = cls.check_title_relevance(title, topic, domain)

            # 添加检查结果到论文对象
            paper_copy = paper.copy()
            paper_copy['_title_check'] = {
                'relevant': is_relevant,
                'reason': reason
            }

            if is_relevant is True:
                relevant.append(paper_copy)
            elif is_relevant is False:
                irrelevant.append(paper_copy)
            else:
                uncertain.append(paper_copy)

        return relevant, irrelevant, uncertain


# 便捷函数
def check_title_relevance(title: str, topic: str, domain: str = None) -> Tuple[bool, str]:
    """检查单篇论文的标题相关性"""
    return TitleRelevanceChecker.check_title_relevance(title, topic, domain)


def batch_check_titles(papers: List[Dict], topic: str, domain: str = None) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """批量检查论文标题相关性"""
    return TitleRelevanceChecker.batch_check_titles(papers, topic, domain)


# 测试代码
if __name__ == "__main__":
    # 测试用例
    topic = "CAS (computer algebra system) 的算法、实现及应用"
    domain = "computer_algebra"

    test_papers = [
        {"title": "Symbolic execution for software verification"},
        {"title": "Mathematica: A system for doing mathematics by computer"},
        {"title": "Symbolic integration algorithms in Computer Algebra Systems"},
        {"title": "Accelerating array constraints in symbolic execution"},
        {"title": "Equation solving in Maple: A Computer Algebra System approach"},
        {"title": "Deep learning for protein structure prediction"},
    ]

    print("=" * 80)
    print(f"主题: {topic}")
    print(f"领域: {domain}")
    print("=" * 80)

    relevant, irrelevant, uncertain = batch_check_titles(test_papers, topic, domain)

    print(f"\n相关论文 ({len(relevant)}篇):")
    for paper in relevant:
        print(f"  ✓ {paper['title'][:60]}")
        print(f"    原因: {paper['_title_check']['reason']}")

    print(f"\n不相关论文 ({len(irrelevant)}篇):")
    for paper in irrelevant:
        print(f"  ✗ {paper['title'][:60]}")
        print(f"    原因: {paper['_title_check']['reason']}")

    print(f"\n不确定论文 ({len(uncertain)}篇):")
    for paper in uncertain:
        print(f"  ? {paper['title'][:60]}")
        print(f"    原因: {paper['_title_check']['reason']}")
