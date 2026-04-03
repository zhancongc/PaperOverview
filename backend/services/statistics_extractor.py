"""
统计数据提取服务
从论文中提取OR值、发生率、P值、样本量等具体数据
让综述引用更加"实"起来
"""
import re
import os
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class StatisticsExtractor:
    """统计数据提取器"""

    # 统计数据的正则表达式模式
    PATTERNS = {
        # OR值 (Odds Ratio)
        "or_value": r'(?:OR|odds\s*ratio)[\s:=]+(\d+\.?\d*)\s*(?:\(?\s*95\s*%\s*CI\s*[:\s]([\d.\-]+)\s*\)?)?',
        "or_ci": r'95\s*%\s*CI\s*[:\s]\s*([\d.]+)\s*[-—–]\s*([\d.]+)',

        # RR值 (Relative Risk)
        "rr_value": r'(?:RR|relative\s*risk)[\s:=]+(\d+\.?\d*)',
        "rr_ci": r'95\s*%\s*CI\s*[:\s]\s*([\d\.]+)\s*[-—–]\s*([\d\.]+)',

        # HR值 (Hazard Ratio)
        "hr_value": r'(?:HR|hazard\s*ratio)[\s:=]+(\d+\.?\d*)',

        # P值
        "p_value": r'(?:p\s*[<≤≥=]*\s*([0-9.]+)|(?:P\s*[<≤≥=]*\s*([0-9.e-]+)))',
        "p_value_simple": r'p\s*[<≤=]\s*0\.05',
        "p_value_exact": r'p\s*[=]\s*([0-9.]+)',

        # 发生率/百分比
        "percentage": r'(\d+\.?\d*)%\s*(?:\[(\d+\.?\d*)%[-~](\d+\.?\d*)%\])?',
        "incidence_rate": r'(?:incidence|prevalence|rate)[\s:]+(\d+\.?\d*)\s*%',

        # 均值和标准差
        "mean_sd": r'(?:mean|average|μ)[\s:=]+(\d+\.?\d*)\s*(?:±|SD\s*[:=]\s*|±\s*)(\d+\.?\d*)',

        # 样本量
        "sample_size": r'(?:n|N|sample)\s*[=]\s*(\d+)',
        "sample_size_range": r'(?:n|N)\s*[=]\s*(\d+)[-~](\d+)',

        # 相关系数
        "correlation": r'[rR][\s:=]+(\d+\.?\d*)\s*(?:\[?\s*95\s*%\s*CI\s*[:\s]\s*([\d\.]+)\s*[-—–]\s*([\d\.]+)\s*\]?)?',
        "correlation_p": r'[rR][\s:=]+(\d+\.?\d*)\s*,\s*p\s*[<≤=]\s*([0-9.]+)',

        # 回归系数
        "beta": r'β?\s*[=]\s*([-+]?\d+\.?\d*)\s*(?:\(SE\s*[:=]\s*([-+]?\d+\.?\d*)\))?',
        "beta_ci": r'β?\s*[=]\s*([-+]?\d+\.?\d*)\s*(?:\[?\s*95\s*%\s*CI\s*[:\s]\s*([-+]?\d+\.?\d*)\s*[-—–]\s*([-+]?\d+\.?\d*)\s*\]?)?',

        # 效应量 (Cohen's d)
        "effect_size": r'(?:d|cohens?\s*d)\s*[=]\s*([-+]?\d+\.?\d*)',

        # t值
        "t_value": r't\s*(?:\((\d+)\)\s*)?[=]\s*([-+]?\d+\.?\d*)',

        # F值
        "f_value": r'F\s*(?:\((\d+),\s*(\d+)\)\s*)?[=]\s*([\d.]+)',
    }

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    def extract_statistics_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取统计数据

        Args:
            text: 论文摘要或正文

        Returns:
            提取的统计数据字典
        """
        if not text:
            return {}

        stats = {}

        # 提取OR值
        or_match = re.search(self.PATTERNS["or_value"], text, re.IGNORECASE)
        if or_match:
            stats["or"] = float(or_match.group(1))
            # 尝试提取置信区间
            ci_match = re.search(self.PATTERNS["or_ci"], text, re.IGNORECASE)
            if ci_match:
                stats["or_ci_lower"] = float(ci_match.group(1))
                stats["or_ci_upper"] = float(ci_match.group(2))

        # 提取RR值
        rr_match = re.search(self.PATTERNS["rr_value"], text, re.IGNORECASE)
        if rr_match:
            stats["rr"] = float(rr_match.group(1))

        # 提取HR值
        hr_match = re.search(self.PATTERNS["hr_value"], text, re.IGNORECASE)
        if hr_match:
            stats["hr"] = float(hr_match.group(1))

        # 提取P值
        p_match = re.search(self.PATTERNS["p_value"], text, re.IGNORECASE)
        if p_match:
            p_val = p_match.group(1) or p_match.group(2)
            try:
                stats["p"] = float(p_val) if p_val else 0.05
            except:
                stats["p_significant"] = True  # 标记为显著但无具体值

        # 检查是否p < 0.05
        if re.search(self.PATTERNS["p_value_simple"], text, re.IGNORECASE):
            stats["p_significant"] = True

        # 提取百分比
        pct_match = re.search(self.PATTERNS["percentage"], text)
        if pct_match:
            stats["percentage"] = float(pct_match.group(1))
            if pct_match.group(2):  # 有范围
                stats["percentage_range"] = [float(pct_match.group(2)), float(pct_match.group(3))]

        # 提取均值和标准差
        mean_sd_match = re.search(self.PATTERNS["mean_sd"], text, re.IGNORECASE)
        if mean_sd_match:
            stats["mean"] = float(mean_sd_match.group(1))
            stats["sd"] = float(mean_sd_match.group(2))

        # 提取样本量
        sample_match = re.search(self.PATTERNS["sample_size"], text, re.IGNORECASE)
        if sample_match:
            stats["n"] = int(sample_match.group(1))

        # 提取相关系数
        corr_match = re.search(self.PATTERNS["correlation"], text, re.IGNORECASE)
        if corr_match:
            stats["r"] = float(corr_match.group(1))

        # 提取回归系数
        beta_match = re.search(self.PATTERNS["beta"], text, re.IGNORECASE)
        if beta_match:
            stats["beta"] = float(beta_match.group(1))

        # 提取效应量
        es_match = re.search(self.PATTERNS["effect_size"], text, re.IGNORECASE)
        if es_match:
            stats["cohens_d"] = float(es_match.group(1))

        return stats

    async def extract_statistics_with_llm(self, paper: Dict) -> Dict[str, Any]:
        """
        使用LLM提取统计数据（更准确）

        Args:
            paper: 论文信息

        Returns:
            提取的统计数据
        """
        if not self.client:
            return self.extract_statistics_from_text(
                paper.get("abstract", "") + " " + paper.get("title", "")
            )

        title = paper.get("title", "")
        abstract = paper.get("abstract", "")

        prompt = f"""请从以下论文中提取关键的统计数据。

论文标题：{title}
摘要：{abstract}

请提取以下统计数据（如果有的话）：
1. OR值（Odds Ratio）及其95%置信区间
2. RR值（Relative Risk）
3. HR值（Hazard Ratio）
4. P值
5. 发生率/百分比
6. 样本量（N）
7. 均值±标准差
8. 相关系数（r）
9. 回归系数（β）
10. 效应量（Cohen's d）

请按以下JSON格式返回（只返回有值的字段）：
```json
{{
  "or": 1.5,
  "or_ci_lower": 1.2,
  "or_ci_upper": 1.8,
  "p": 0.03,
  "percentage": 25.5,
  "n": 500,
  "mean": 10.5,
  "sd": 2.3
}}
```

如果某项数据不存在，不要包含该字段。只返回JSON，不要有其他内容。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位学术数据提取专家，擅长识别和提取研究中的统计数据。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content.strip()
            stats = json.loads(result) if result else {}

            # 添加论文ID
            stats["paper_id"] = paper.get("id", "")
            stats["paper_title"] = title

            return stats

        except Exception as e:
            print(f"[StatisticsExtractor] LLM提取失败: {e}，使用规则提取")
            return self.extract_statistics_from_text(abstract)

    def format_statistics_for_citation(self, stats: Dict[str, Any], style: str = "compact") -> str:
        """
        格式化统计数据用于引用

        Args:
            stats: 统计数据
            style: 格式样式 (compact, detailed, apa)

        Returns:
            格式化的统计字符串
        """
        if not stats:
            return ""

        if style == "compact":
            # 紧凑格式：OR=1.5, p<0.05
            parts = []

            if "or" in stats:
                or_str = f"OR={stats['or']}"
                if "or_ci_lower" in stats and "or_ci_upper" in stats:
                    or_str += f" (95%CI:{stats['or_ci_lower']}-{stats['or_ci_upper']})"
                parts.append(or_str)

            elif "rr" in stats:
                parts.append(f"RR={stats['rr']}")
            elif "hr" in stats:
                parts.append(f"HR={stats['hr']}")

            if "p" in stats:
                parts.append(f"p={stats['p']}")
            elif stats.get("p_significant"):
                parts.append("p<0.05")

            if "percentage" in stats:
                parts.append(f"{stats['percentage']}%")

            if "n" in stats:
                parts.append(f"n={stats['n']}")

            return ", ".join(parts) if parts else ""

        elif style == "detailed":
            # 详细格式：(OR=1.5, 95%CI:1.2-1.8, p=0.03, n=500)
            parts = []

            if "or" in stats:
                parts.append(f"OR={stats['or']}")
                if "or_ci_lower" in stats and "or_ci_upper" in stats:
                    parts.append(f"95%CI:{stats['or_ci_lower']}-{stats['or_ci_upper']}")

            if "p" in stats:
                parts.append(f"p={stats['p']}")
            elif stats.get("p_significant"):
                parts.append("p<0.05")

            if "n" in stats:
                parts.append(f"n={stats['n']}")

            return f"({', '.join(parts)})" if parts else ""

        elif style == "apa":
            # APA格式：OR = 1.50, 95% CI [1.20, 1.80], p = .03
            parts = []

            if "or" in stats:
                or_str = f"OR = {stats['or']:.2f}"
                if "or_ci_lower" in stats and "or_ci_upper" in stats:
                    or_str += f", 95% CI [{stats['or_ci_lower']}, {stats['or_ci_upper']}]"
                parts.append(or_str)

            if "p" in stats:
                p_val = stats['p']
                if p_val < 0.001:
                    parts.append("p < .001")
                else:
                    parts.append(f"p = {p_val:.3f}" if p_val >= 0.01 else f"p = {p_val:.2f}")

            return ", ".join(parts) if parts else ""

        return ""

    async def batch_extract_statistics(
        self,
        papers: List[Dict],
        use_llm: bool = True
    ) -> List[Dict]:
        """
        批量提取论文的统计数据

        Args:
            papers: 论文列表
            use_llm: 是否使用LLM提取

        Returns:
            添加了统计数据的论文列表
        """
        results = []

        for paper in papers:
            if use_llm:
                stats = await self.extract_statistics_with_llm(paper)
            else:
                text = paper.get("abstract", "") + " " + paper.get("title", "")
                stats = self.extract_statistics_from_text(text)
                stats["paper_id"] = paper.get("id", "")
                stats["paper_title"] = paper.get("title", "")

            # 创建论文副本并添加统计数据
            paper_copy = paper.copy()
            paper_copy["statistics"] = stats
            results.append(paper_copy)

        return results


class StatisticsEnhancedCitation:
    """统计数据增强的引用生成器"""

    def __init__(self):
        self.extractor = StatisticsExtractor()

    async def generate_enhanced_citation(
        self,
        paper: Dict,
        citation_number: int,
        style: str = "compact",
        use_llm: bool = True
    ) -> str:
        """
        生成带统计数据的引用

        Args:
            paper: 论文信息（应包含statistics字段）
            citation_number: 引用编号
            style: 引用样式
            use_llm: 是否使用LLM提取

        Returns:
            增强的引用字符串，如 "[1](OR=1.5, p<0.05)"
        """
        # 如果还没有统计数据，先提取
        if "statistics" not in paper or not paper["statistics"]:
            if use_llm:
                stats = await self.extractor.extract_statistics_with_llm(paper)
            else:
                text = paper.get("abstract", "") + " " + paper.get("title", "")
                stats = self.extractor.extract_statistics_from_text(text)
            paper["statistics"] = stats
        else:
            stats = paper["statistics"]

        # 格式化统计数据
        stats_str = self.extractor.format_statistics_for_citation(stats, style)

        if stats_str:
            return f"[{citation_number}]({stats_str})"
        else:
            return f"[{citation_number}]"

    def format_citation_with_context(
        self,
        paper: Dict,
        finding_description: str,
        citation_number: int,
        include_statistics: bool = True
    ) -> str:
        """
        生成带上下文的引用

        Args:
            paper: 论文信息
            finding_description: 研究发现描述
            citation_number: 引用编号
            include_statistics: 是否包含统计数据

        Returns:
            完整的引用句子，如 "研究发现XX能显著提高YY[1](OR=1.5, p<0.05)"
        """
        stats = paper.get("statistics", {})
        stats_str = ""

        if include_statistics and stats:
            stats_str = self.extractor.format_statistics_for_citation(stats, "compact")

        citation = f"[{citation_number}]({stats_str})" if stats_str else f"[{citation_number}]"

        return f"{finding_description}{citation}"


class EnhancedReviewGenerator:
    """增强的综述生成器（带统计数据引用）"""

    def __init__(self, api_key: str = None):
        self.extractor = StatisticsExtractor()
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

    async def generate_review_with_statistics(
        self,
        topic: str,
        papers: List[Dict],
        model: str = "deepseek-chat"
    ) -> tuple[str, List[Dict]]:
        """
        生成带统计数据的综述

        Args:
            topic: 研究主题
            papers: 论文列表
            model: 模型名称

        Returns:
            (综述内容, 带统计数据的论文列表)
        """
        # 1. 批量提取统计数据
        papers_with_stats = await self.extractor.batch_extract_statistics(papers)

        # 2. 统计提取结果
        stats_summary = self._summarize_statistics(papers_with_stats)
        print(f"[EnhancedReview] 统计数据提取完成:")
        print(f"  总论文数: {len(papers_with_stats)}")
        print(f"  提取到OR值: {stats_summary['or_count']}")
        print(f"  提取到P值: {stats_summary['p_count']}")
        print(f"  提取到百分比: {stats_summary['percentage_count']}")
        print(f"  提取到样本量: {stats_summary['n_count']}")

        # 3. 生成综述（这里简化，实际应调用ReviewGeneratorService）
        review_content = await self._generate_content_with_stats(
            topic, papers_with_stats, model
        )

        return review_content, papers_with_stats

    def _summarize_statistics(self, papers: List[Dict]) -> Dict:
        """统计数据摘要"""
        summary = {
            "or_count": 0,
            "rr_count": 0,
            "hr_count": 0,
            "p_count": 0,
            "percentage_count": 0,
            "n_count": 0,
        }

        for paper in papers:
            stats = paper.get("statistics", {})
            if "or" in stats:
                summary["or_count"] += 1
            if "rr" in stats:
                summary["rr_count"] += 1
            if "hr" in stats:
                summary["hr_count"] += 1
            if "p" in stats or stats.get("p_significant"):
                summary["p_count"] += 1
            if "percentage" in stats:
                summary["percentage_count"] += 1
            if "n" in stats:
                summary["n_count"] += 1

        return summary

    async def _generate_content_with_stats(
        self,
        topic: str,
        papers: List[Dict],
        model: str
    ) -> str:
        """生成带统计数据的综述内容（简化版）"""
        # 构建带统计数据的论文信息
        papers_info = []
        for i, paper in enumerate(papers[:10], 1):
            stats = paper.get("statistics", {})
            stats_str = self.extractor.format_statistics_for_citation(stats, "compact")

            paper_info = f"{i}. {paper.get('title', '')}"
            if stats_str:
                paper_info += f" - 数据: {stats_str}"
            papers_info.append(paper_info)

        prompt = f"""请撰写关于"{topic}"的文献综述。

要求：
1. 在引用文献时，务必包含具体的统计数据
2. 引用格式：研究发现[1](OR=1.5, p<0.05)
3. 如果某篇文献没有提供统计数据，就只写[1]
4. 重点展示有具体数据支撑的研究发现

可用文献（部分已标注统计数据）：
{chr(10).join(papers_info)}

请开始撰写综述（500-800字）："""

        if not self.api_key:
            return f"# {topic}文献综述（带统计数据）\n\n[内容占位符]"

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位学术写作专家，擅长在综述中引用具体统计数据。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 统计信息提取需要准确理解数据
                max_tokens=1500
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[EnhancedReview] 生成失败: {e}")
            return f"# {topic}文献综述（带统计数据）\n\n[生成失败]"


# 便捷导出函数
async def extract_statistics_from_papers(
    papers: List[Dict],
    use_llm: bool = True
) -> List[Dict]:
    """
    从论文列表中提取统计数据

    Args:
        papers: 论文列表
        use_llm: 是否使用LLM

    Returns:
        添加了statistics字段的论文列表
    """
    extractor = StatisticsExtractor()
    return await extractor.batch_extract_statistics(papers, use_llm)


def format_statistics_for_citation(stats: Dict[str, Any], style: str = "compact") -> str:
    """
    格式化统计数据用于引用

    Args:
        stats: 统计数据
        style: 样式 (compact, detailed, apa)

    Returns:
        格式化的统计字符串
    """
    extractor = StatisticsExtractor()
    return extractor.format_statistics_for_citation(stats, style)


# 导入json（用于LLM提取）
import json
