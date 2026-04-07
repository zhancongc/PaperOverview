"""
深度对比分析服务
在文献矩阵中不仅列出观点，还追问"这种分歧可能源于..."

DEPRECATED: 此模块为 v5.x 旧版本遗留代码，当前 v6.0 流程已不再使用。
保留仅用于历史参考，新代码请使用 PaperSearchAgent + SmartReviewGeneratorFinal。
"""
import warnings
warnings.warn(
    "deep_comparison 模块已废弃，v6.0 流程不再使用",
    DeprecationWarning,
    stacklevel=2
)
import re
import os
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class DeepComparisonAnalyzer:
    """深度对比分析器"""

    # 常见分歧原因模板
    DIVERGENCE_REASONS = {
        "样本差异": [
            "样本量差异",
            "样本来源不同（如企业规模、行业分布）",
            "地理区域差异（发达国家 vs 发展中国家）",
            "时间跨度差异（横截面 vs 面板数据）",
            "研究对象特征差异（如年龄、性别、发展阶段）"
        ],
        "方法差异": [
            "研究方法差异（实验法 vs 调查法 vs 案例研究）",
            "测量方式差异（如盈余管理的度量指标）",
            "数据分析方法差异（OLS vs IV vs DID）",
            "变量定义差异（如媒体关注度的测量）",
            "模型设定差异（是否控制关键变量）"
        ],
        "情境差异": [
            "制度环境差异（法律制度、投资者保护）",
            "市场环境差异（牛市 vs 熊市、成熟市场 vs 新兴市场）",
            "行业特征差异（制造业 vs 服务业）",
            "企业生命周期差异（初创期 vs 成熟期）",
            "宏观经济环境差异（经济扩张期 vs 收缩期）"
        ],
        "理论差异": [
            "理论视角差异（代理理论 vs 权变理论）",
            "假设前提不同（理性人 vs 有限理性）",
            "分析层次差异（个体层面 vs 组织层面）",
            "理论框架差异（经济学 vs 心理学 vs 社会学）",
            "研究范式差异（实证主义 vs 规范主义）"
        ],
        "数据质量差异": [
            "数据来源差异（手工收集 vs 数据库获取）",
            "数据时效性差异（最新数据 vs 历史数据）",
            "数据准确性差异（自报数据 vs 审计数据）",
            "样本代表性差异（随机抽样 vs 便利抽样）",
            "测量精度差异（粗略度量 vs 精确度量）"
        ]
    }

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    def infer_divergence_reasons(
        self,
        paper_a: Dict,
        paper_b: Dict,
        topic: str
    ) -> List[str]:
        """
        推断两篇论文结论分歧的可能原因

        Args:
            paper_a: 论文A
            paper_b: 论文B
            topic: 研究主题

        Returns:
            可能的原因列表
        """
        reasons = []

        # 1. 基于样本量推断
        n_a = self._extract_sample_size(paper_a)
        n_b = self._extract_sample_size(paper_b)

        if n_a and n_b:
            if abs(n_a - n_b) / max(n_a, n_b) > 0.5:  # 样本量差异超过50%
                reasons.append(f"样本量差异显著（{n_a} vs {n_b}）")

        # 2. 基于年份推断
        year_a = paper_a.get("year")
        year_b = paper_b.get("year")

        if year_a and year_b:
            if abs(year_a - year_b) > 5:  # 年份差距超过5年
                reasons.append(f"研究时间跨度较大（{year_a} vs {year_b}）")
                reasons.append("技术发展阶段或市场环境可能已发生变化")

        # 3. 基于地域/语言推断
        is_en_a = paper_a.get("is_english", False)
        is_en_b = paper_b.get("is_english", False)

        if is_en_a != is_en_b:
            reasons.append("研究对象来自不同市场环境（如中国市场 vs 美国市场）")

        # 4. 基于摘要关键词推断
        abstract_a = paper_a.get("abstract", "").lower()
        abstract_b = paper_b.get("abstract", "").lower()

        # 检测方法论差异
        method_keywords = {
            "实验": ["experiment", "experimental", "lab"],
            "调查": ["survey", "questionnaire", "interview"],
            "案例": ["case study", "case-study"],
            "元分析": ["meta-analysis", "meta analysis"],
            "面板": ["panel data", "fixed effect", "random effect"]
        }

        methods_a = []
        methods_b = []

        for method, keywords in method_keywords.items():
            if any(kw in abstract_a for kw in keywords):
                methods_a.append(method)
            if any(kw in abstract_b for kw in keywords):
                methods_b.append(method)

        if set(methods_a) != set(methods_b):
            reasons.append(f"研究方法可能不同（{set(methods_a)} vs {set(methods_b)}）")

        # 5. 基于理论视角推断
        theory_keywords = {
            "代理理论": ["agency", "agency cost", "principal-agent"],
            "权变理论": ["contingency", "contingent", "moderator"],
            "利益相关者": ["stakeholder", "stakeholder theory"],
            "资源依赖": ["resource dependence", "resource-based"],
            "制度理论": ["institutional", "institution theory"]
        }

        theories_a = []
        theories_b = []

        for theory, keywords in theory_keywords.items():
            if any(kw in abstract_a for kw in keywords):
                theories_a.append(theory)
            if any(kw in abstract_b for kw in keywords):
                theories_b.append(theory)

        if set(theories_a) != set(theories_b):
            reasons.append(f"理论视角可能不同（{set(theories_a)} vs {set(theories_b)}）")

        # 6. 默认原因（如果没有推断出具体原因）
        if not reasons:
            reasons.append("样本特征或研究情境的差异")
            reasons.append("模型设定或变量度量的差异")

        return reasons

    def _extract_sample_size(self, paper: Dict) -> Optional[int]:
        """从论文中提取样本量"""
        # 从摘要中提取
        abstract = paper.get("abstract", "")
        matches = re.findall(r'[nN]\s*[=]\s*(\d+)', abstract)
        if matches:
            return int(matches[0])

        # 从统计信息中提取
        stats = paper.get("statistics", {})
        return stats.get("n") or stats.get("sample_size")

    async def generate_deep_comparison(
        self,
        papers: List[Dict],
        topic: str,
        section: str = None
    ) -> str:
        """
        生成深度对比分析内容

        Args:
            papers: 论文列表
            topic: 研究主题
            section: 章节名称

        Returns:
            深度对比分析内容（Markdown格式）
        """
        if len(papers) < 2:
            return self._generate_simple_comparison(papers, topic)

        # 使用LLM生成深度分析
        if self.client:
            return await self._generate_with_llm(papers, topic, section)
        else:
            return self._generate_with_rules(papers, topic)

    async def _generate_with_llm(
        self,
        papers: List[Dict],
        topic: str,
        section: str
    ) -> str:
        """使用LLM生成深度对比分析"""
        # 构建论文对比信息
        papers_info = []
        for i, paper in enumerate(papers[:6], 1):  # 最多6篇
            title = paper.get("title", "")
            abstract = (paper.get("abstract") or "")[:300]
            year = paper.get("year", "Unknown")
            papers_info.append(f"{i}. {title} ({year})\n   摘要: {abstract}\n")

        prompt = f"""请对以下关于"{topic}"的研究进行深度对比分析。

研究论文：
{chr(10).join(papers_info)}

请按以下格式输出：

## 观点对比

列出2-3组对立或不同的观点，每组至少包含2篇文献的支持。

## 分歧原因分析

对每组对立观点，深入分析可能的原因，包括：
1. 样本差异（样本量、来源、地域、时间等）
2. 方法差异（测量方式、分析方法、模型设定等）
3. 情境差异（制度环境、市场环境、行业特征等）
4. 理论差异（理论视角、假设前提等）

要求：
- 具体指出哪篇文献支持哪个观点
- 用"这种分歧可能源于..."的句式追问原因
- 即使只是推测，也要给出合理的解释
- 展示分析的深度和批判性思维

输出格式为Markdown。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位学术分析专家，擅长进行深度文献对比和批判性分析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 深度对比需要准确分析，保持严谨
                max_tokens=2500
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[DeepComparison] LLM生成失败: {e}，使用规则生成")
            return self._generate_with_rules(papers, topic)

    def _generate_with_rules(self, papers: List[Dict], topic: str) -> str:
        """使用规则生成深度对比分析"""
        content = ["## 深度对比分析\n"]

        # 找出对立的观点
        if len(papers) >= 2:
            # 简单策略：按年份或正负结论分组
            recent_papers = [p for p in papers if p.get("year", 0) >= 2020]
            older_papers = [p for p in papers if p.get("year", 0) < 2020]

            if recent_papers and older_papers:
                content.append("### 观点对比\n")
                content.append(f"**近期研究（2020年后）**：")
                for p in recent_papers[:2]:
                    title = (p.get("title") or "")[:60]
                    content.append(f"- {title}...")
                content.append(f"\n**早期研究（2020年前）**：")
                for p in older_papers[:2]:
                    title = (p.get("title") or "")[:60]
                    content.append(f"- {title}...")

                content.append("\n### 分歧原因分析\n")
                content.append("这种分歧可能源于：\n")
                content.append("- **时间差异**：早期研究与近期研究面临的技术环境和市场条件不同\n")
                content.append("- **数据质量**：近期研究可能使用了更精确的度量方法\n")
                content.append("- **情境变化**：研究对象所处的制度或市场环境可能已发生变化\n")

        return "\n".join(content)

    def _generate_simple_comparison(self, papers: List[Dict], topic: str) -> str:
        """生成简单对比（少于2篇论文）"""
        content = ["## 文献对比\n"]
        content.append(f"关于{topic}，现有研究较为一致，尚未形成明显分歧。")
        return "\n".join(content)

    def format_comparison_with_reasons(
        self,
        statement: str,
        supporting_papers: List[Dict],
        opposing_papers: List[Dict],
        topic: str
    ) -> str:
        """
        格式化带原因追问的对比陈述

        Args:
            statement: 研究发现陈述
            supporting_papers: 支持的论文列表
            opposing_papers: 对立的论文列表
            topic: 研究主题

        Returns:
            格式化的对比陈述
        """
        parts = [statement]

        # 添加支持文献
        if supporting_papers:
            citations = ", ".join([f"[{i}]" for i in range(1, len(supporting_papers)+1)])
            parts.append(f"{citations}")

        # 添加对立观点
        if opposing_papers:
            parts.append("；")
            opp_citations = ", ".join([f"[{len(supporting_papers)+i}]" for i in range(1, len(opposing_papers)+1)])
            parts.append(f"{opp_citations}则发现不同结果")

        # 推断分歧原因
        if supporting_papers and opposing_papers:
            reasons = self.infer_divergence_reasons(
                supporting_papers[0],
                opposing_papers[0],
                topic
            )

            if reasons:
                parts.append("。")
                parts.append(f"这种分歧可能源于{'；'.join(reasons[:3])}。")

        return "".join(parts)

    async def enhance_review_with_deep_comparison(
        self,
        review_content: str,
        papers: List[Dict],
        topic: str
    ) -> Tuple[str, Dict]:
        """
        在综述中增强深度对比分析

        Args:
            review_content: 原始综述内容
            papers: 论文列表
            topic: 研究主题

        Returns:
            (增强后的综述, 增强报告)
        """
        # 生成深度对比分析章节
        deep_comparison = await self.generate_deep_comparison(papers, topic)

        # 检测综述中是否有对比段落
        has_comparison = self._detect_comparison_paragraphs(review_content)

        if has_comparison:
            # 在现有对比后追加原因分析
            enhanced_content = self._append_reason_analysis(
                review_content,
                papers,
                topic
            )
        else:
            # 添加深度对比章节
            enhanced_content = f"{review_content}\n\n{deep_comparison}"

        report = {
            "original_length": len(review_content),
            "enhanced_length": len(enhanced_content),
            "added_reasoning": len(deep_comparison) > 0,
            "deep_comparison_added": True
        }

        return enhanced_content, report

    def _detect_comparison_paragraphs(self, text: str) -> bool:
        """检测文本中是否有对比段落"""
        comparison_keywords = [
            "对比", "不同", "分歧", "差异", "相反", "然而",
            "不一致", "矛盾", "冲突", "vs.", "versus"
        ]

        return any(kw in text.lower() for kw in comparison_keywords)

    def _append_reason_analysis(
        self,
        text: str,
        papers: List[Dict],
        topic: str
    ) -> str:
        """在现有对比后追加原因分析"""
        lines = text.split("\n")
        enhanced_lines = []

        i = 0
        while i < len(lines):
            enhanced_lines.append(lines[i])

            # 检测是否是对比段落
            if self._contains_comparison(lines[i]):
                # 检查下一段是否已经有原因分析
                if i + 1 < len(lines) and not self._contains_reasoning(lines[i+1]):
                    # 添加原因追问
                    reason_line = self._generate_reason_line(papers, topic)
                    if reason_line:
                        enhanced_lines.append(reason_line)

            i += 1

        return "\n".join(enhanced_lines)

    def _contains_comparison(self, line: str) -> bool:
        """检查行是否包含对比"""
        comparison_keywords = ["对比", "不同", "分歧", "差异", "相反"]
        return any(kw in line for kw in comparison_keywords)

    def _contains_reasoning(self, line: str) -> bool:
        """检查行是否已包含原因分析"""
        reasoning_keywords = ["源于", "由于", "因为", "可能是", "原因"]
        return any(kw in line for kw in reasoning_keywords)

    def _generate_reason_line(self, papers: List[Dict], topic: str) -> str:
        """生成原因追问行"""
        if len(papers) < 2:
            return "> 这种差异可能源于研究样本或情境的不同。"

        # 基于论文信息推断原因
        reasons = []

        # 检查样本量差异
        n_values = []
        for paper in papers[:5]:
            n = self._extract_sample_size(paper)
            if n:
                n_values.append(n)

        if n_values and max(n_values) / min(n_values) > 2:
            reasons.append("样本量差异较大")

        # 检查年份差异
        years = [p.get("year") for p in papers[:5] if p.get("year")]
        if years and max(years) - min(years) > 5:
            reasons.append("研究时间跨度较大")

        # 检查地域差异
        has_chinese = any(not p.get("is_english", True) for p in papers)
        has_english = any(p.get("is_english", False) for p in papers)
        if has_chinese and has_english:
            reasons.append("研究对象来自不同市场环境")

        if not reasons:
            reasons.append("样本特征或研究设计的差异")

        return f"> 这种差异可能源于{'、'.join(reasons[:3])}。"


class DeepComparisonFormatter:
    """深度对比格式化器"""

    def __init__(self):
        self.analyzer = DeepComparisonAnalyzer()

    def format_comparison_table(
        self,
        papers: List[Dict],
        topic: str
    ) -> str:
        """
        生成对比表格（Markdown格式）

        Args:
            papers: 论文列表
            topic: 研究主题

        Returns:
            Markdown格式的对比表格
        """
        content = ["## 文献对比矩阵\n"]
        content.append("| 研究者 | 年份 | 样本 | 核心观点 | 方法 | 可能的差异原因 |\n")
        content.append("|--------|------|------|----------|------|----------------|\n")

        for i, paper in enumerate(papers[:5], 1):
            # 提取信息
            authors = paper.get("authors", ["Unknown"])[0]
            year = paper.get("year", "Unknown")
            n = self.analyzer._extract_sample_size(paper) or "未报告"
            title = paper.get("title", "")

            # 提取核心观点（从摘要）
            abstract = paper.get("abstract", "")
            viewpoint = abstract.split("。")[0][:60] + "..." if abstract else "未提供"

            # 推断可能的差异原因
            if i > 1:
                reasons = self.analyzer.infer_divergence_reasons(papers[0], paper, topic)
                reason_str = "、".join(reasons[:2])
            else:
                reason_str = "基准研究"

            # 推断方法
            abstract_lower = abstract.lower()
            if "experiment" in abstract_lower or "experimental" in abstract_lower:
                method = "实验法"
            elif "survey" in abstract_lower:
                method = "调查法"
            elif "case study" in abstract_lower:
                method = "案例研究"
            else:
                method = "实证分析"

            content.append(f"| {authors}等 | {year} | {n} | {viewpoint} | {method} | {reason_str} |\n")

        return "\n".join(content)

    async def generate_section_with_deep_comparison(
        self,
        section_title: str,
        papers: List[Dict],
        topic: str
    ) -> str:
        """
        生成带深度对比的章节

        Args:
            section_title: 章节标题
            papers: 论文列表
            topic: 研究主题

        Returns:
            章节内容（含深度对比）
        """
        content = [f"## {section_title}\n"]

        # 1. 生成对比表格
        content.append(self.format_comparison_table(papers, topic))

        # 2. 生成深度分析
        deep_analysis = await self.analyzer.generate_deep_comparison(papers, topic)

        if deep_analysis:
            content.append("\n")
            content.append(deep_analysis)

        return "\n".join(content)


# 便捷导出函数
async def generate_deep_comparison(
    papers: List[Dict],
    topic: str,
    section: str = None
) -> str:
    """
    生成深度对比分析

    Args:
        papers: 论文列表
        topic: 研究主题
        section: 章节名称

    Returns:
        深度对比分析内容
    """
    analyzer = DeepComparisonAnalyzer()
    return await analyzer.generate_deep_comparison(papers, topic, section)


def infer_divergence_reasons(
    paper_a: Dict,
    paper_b: Dict,
    topic: str
) -> List[str]:
    """
    推断两篇论文结论分歧的可能原因

    Args:
        paper_a: 论文A
        paper_b: 论文B
        topic: 研究主题

    Returns:
        可能的原因列表
    """
    analyzer = DeepComparisonAnalyzer()
    return analyzer.infer_divergence_reasons(paper_a, paper_b, topic)
