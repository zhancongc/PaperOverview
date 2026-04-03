"""
观点碰撞分析服务
在综述的每个章节末尾生成"争议与对话"小节
"""
import os
import re
import json
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class ViewpointExtractor:
    """观点提取器 - 从论文中提取核心观点"""

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    async def extract_viewpoints(self, papers: List[Dict], topic: str) -> List[Dict]:
        """
        从论文列表中提取核心观点

        Args:
            papers: 论文列表
            topic: 研究主题

        Returns:
            观点列表，每个观点包含：
            - paper_id: 论文ID
            - title: 论文标题
            - viewpoint: 核心观点
            - methodology: 方法论
            - conclusion: 结论
            - year: 年份
        """
        if not self.client:
            return self._extract_viewpoints_simple(papers)

        # 构建论文摘要
        papers_summary = []
        for i, paper in enumerate(papers[:20], 1):  # 最多处理20篇
            title = paper.get("title", "")
            abstract = (paper.get("abstract") or "")[:300]  # 限制摘要长度
            year = paper.get("year", "Unknown")
            papers_summary.append(f"{i}. {title} ({year})\n   摘要: {abstract}\n")

        prompt = f"""请分析以下关于"{topic}"的论文，提取每篇论文的核心观点。

论文列表：
{chr(10).join(papers_summary)}

请按以下JSON格式返回：
```json
[
  {{
    "paper_index": 1,
    "viewpoint": "论文的核心观点或主要发现",
    "methodology": "使用的研究方法（实验、调查、模拟等）",
    "conclusion": "研究结论",
    "key_findings": ["关键发现1", "关键发现2"]
  }}
]
```

只返回JSON，不要有其他内容。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位学术分析专家，擅长提取和总结研究观点。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content.strip()
            viewpoints_data = json.loads(result)

            # 组合论文信息和观点
            viewpoints = []
            for vp in viewpoints_data:
                idx = vp.get("paper_index", 1) - 1
                if idx < len(papers):
                    viewpoints.append({
                        "paper_id": papers[idx].get("id", ""),
                        "title": papers[idx].get("title", ""),
                        "year": papers[idx].get("year"),
                        "viewpoint": vp.get("viewpoint", ""),
                        "methodology": vp.get("methodology", ""),
                        "conclusion": vp.get("conclusion", ""),
                        "key_findings": vp.get("key_findings", [])
                    })

            return viewpoints

        except Exception as e:
            print(f"[ViewpointExtractor] LLM提取失败: {e}，使用简单提取")
            return self._extract_viewpoints_simple(papers)

    def _extract_viewpoints_simple(self, papers: List[Dict]) -> List[Dict]:
        """简单的观点提取（基于摘要）"""
        viewpoints = []
        for paper in papers:
            abstract = paper.get("abstract", "")
            # 提取摘要的第一句话作为观点
            first_sentence = abstract.split("。")[0] if abstract else ""
            viewpoints.append({
                "paper_id": paper.get("id", ""),
                "title": paper.get("title", ""),
                "year": paper.get("year"),
                "viewpoint": first_sentence[:200] if first_sentence else paper.get("title", ""),
                "methodology": "",
                "conclusion": "",
                "key_findings": []
            })
        return viewpoints


class ControversyAnalyzer:
    """争议分析器 - 识别和分析观点冲突"""

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    async def analyze_controversies(
        self,
        viewpoints: List[Dict],
        topic: str,
        section_name: str = None
    ) -> Dict:
        """
        分析观点中的争议点

        Args:
            viewpoints: 观点列表
            topic: 研究主题
            section_name: 章节名称（可选）

        Returns:
            争议分析结果，包含：
            - controversies: 争议点列表
            - summary: 争议总结
        """
        if not self.client or len(viewpoints) < 2:
            return self._simple_controversy_analysis(viewpoints, topic)

        # 构建观点摘要
        viewpoints_text = []
        for i, vp in enumerate(viewpoints[:15], 1):  # 最多处理15个观点
            viewpoints_text.append(
                f"论文{i}: {(vp.get('title') or '')[:50]}...\n"
                f"  观点: {(vp.get('viewpoint') or '')[:150]}\n"
                f"  方法: {vp.get('methodology') or '未说明'}\n"
                f"  结论: {(vp.get('conclusion') or '')[:100]}\n"
            )

        section_context = f"在'{section_name}'方面" if section_name else ""

        prompt = f"""请分析以下关于"{topic}"{section_context}的研究观点，识别存在的争议和分歧。

研究观点：
{chr(10).join(viewpoints_text)}

请从以下角度分析：

1. **主要争议点**：识别2-3个核心争议问题
2. **对立观点**：每个争议点下，列出对立的观点及其支持文献
3. **可能原因**：分析产生分歧的可能原因：
   - 样本差异（研究对象、样本量、地域等）
   - 方法差异（实验方法、测量方式、数据分析等）
   - 时间差异（研究时间、技术发展阶段等）
   - 情境差异（应用场景、环境条件等）
   - 理论差异（理论基础、假设前提等）

请按以下JSON格式返回：
```json
{{
  "controversies": [
    {{
      "issue": "争议问题描述",
      "side_a": {{
        "viewpoint": "观点A的描述",
        "supporting_papers": [1, 2, 3],
        "rationale": "支持理由"
      }},
      "side_b": {{
        "viewpoint": "观点B的描述（与A对立）",
        "supporting_papers": [4, 5],
        "rationale": "支持理由"
      }},
      "possible_causes": [
        "原因1：样本差异...",
        "原因2：方法差异..."
      ]
    }}
  ],
  "summary": "对整体争议情况的总结"
}}
```

只返回JSON，不要有其他内容。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位学术分析专家，擅长识别研究中的争议和分歧。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content.strip()
            analysis = json.loads(result)

            return analysis

        except Exception as e:
            print(f"[ControversyAnalyzer] LLM分析失败: {e}，使用简单分析")
            return self._simple_controversy_analysis(viewpoints, topic)

    def _simple_controversy_analysis(self, viewpoints: List[Dict], topic: str) -> Dict:
        """简单的争议分析（基于关键词对比）"""
        # 简单实现：检查观点中的对比词
        contrast_keywords = ["但是", "然而", "相反", "不同", "差异", "争议", "分歧",
                           "however", "although", "contrast", "difference", "controversy"]

        controversies = []

        for i, vp1 in enumerate(viewpoints):
            for vp2 in viewpoints[i+1:]:
                # 检查是否有对比
                text1 = vp1.get("viewpoint", "") + vp1.get("conclusion", "")
                text2 = vp2.get("viewpoint", "") + vp2.get("conclusion", "")

                has_contrast = any(kw in text1.lower() or kw in text2.lower()
                                 for kw in contrast_keywords)

                if has_contrast:
                    controversies.append({
                        "issue": f"关于{topic}的不同观点",
                        "side_a": {
                            "viewpoint": vp1.get("viewpoint", ""),
                            "supporting_papers": [i+1],
                            "rationale": "基于研究分析"
                        },
                        "side_b": {
                            "viewpoint": vp2.get("viewpoint", ""),
                            "supporting_papers": [i+2],
                            "rationale": "基于研究分析"
                        },
                        "possible_causes": ["研究方法或样本可能存在差异"]
                    })

        return {
            "controversies": controversies[:3],  # 最多3个争议
            "summary": f"关于{topic}的研究存在一定分歧，需要进一步研究验证。"
        }


class ControversySectionGenerator:
    """争议章节生成器 - 生成结构化的"争议与对话"内容"""

    def __init__(self):
        self.viewpoint_extractor = ViewpointExtractor()
        self.controversy_analyzer = ControversyAnalyzer()

    async def generate_controversy_section(
        self,
        papers: List[Dict],
        topic: str,
        section_name: str = None,
        cited_indices: List[int] = None
    ) -> str:
        """
        生成"争议与对话"章节

        Args:
            papers: 论文列表
            topic: 研究主题
            section_name: 章节名称
            cited_indices: 已被引用的论文索引列表（用于保持引用编号一致）

        Returns:
            Markdown格式的"争议与对话"内容
        """
        # 1. 提取观点
        viewpoints = await self.viewpoint_extractor.extract_viewpoints(papers, topic)

        if len(viewpoints) < 2:
            return self._generate_no_controversy_section()

        # 2. 分析争议
        analysis = await self.controversy_analyzer.analyze_controversies(
            viewpoints, topic, section_name
        )

        # 3. 生成结构化内容
        return self._format_controversy_section(
            analysis, viewpoints, papers, cited_indices
        )

    def _format_controversy_section(
        self,
        analysis: Dict,
        viewpoints: List[Dict],
        papers: List[Dict],
        cited_indices: List[int] = None
    ) -> str:
        """格式化争议章节内容"""
        content = ["## 争议与对话\n"]

        # 添加总结
        summary = analysis.get("summary", "")
        if summary:
            content.append(f"{summary}\n")

        controversies = analysis.get("controversies", [])

        if not controversies:
            content.append("现有研究在该方面观点较为一致，暂无明显争议。\n")
            return "\n".join(content)

        # 生成每个争议点的详细分析
        for i, controversy in enumerate(controversies, 1):
            content.append(f"### 争议点{i}：{controversy.get('issue', '未知争议')}\n")

            # 观点A
            side_a = controversy.get("side_a", {})
            content.append("**对立观点A：**")
            content.append(f"{side_a.get('viewpoint', '')}")

            # 支持文献（需要转换为引用编号）
            papers_a = side_a.get("supporting_papers", [])
            if papers_a and cited_indices:
                citations = self._convert_to_citations(papers_a, cited_indices)
                if citations:
                    content.append(f" {citations}")

            content.append(f"\n{side_a.get('rationale', '')}\n")

            # 观点B
            side_b = controversy.get("side_b", {})
            content.append("**对立观点B：**")
            content.append(f"{side_b.get('viewpoint', '')}")

            # 支持文献
            papers_b = side_b.get("supporting_papers", [])
            if papers_b and cited_indices:
                citations = self._convert_to_citations(papers_b, cited_indices)
                if citations:
                    content.append(f" {citations}")

            content.append(f"\n{side_b.get('rationale', '')}\n")

            # 可能原因
            causes = controversy.get("possible_causes", [])
            if causes:
                content.append("**可能的原因：**")
                for cause in causes:
                    content.append(f"- {cause}")
                content.append("")

        return "\n".join(content)

    def _convert_to_citations(self, paper_indices: List[int], cited_indices: List[int]) -> str:
        """将论文索引转换为引用编号"""
        citations = []
        for idx in paper_indices:
            if idx <= len(cited_indices):
                # 找到该论文在cited_indices中的位置+1（引用编号从1开始）
                original_idx = cited_indices[idx - 1]
                citations.append(f"[{original_idx}]")
        return "".join(citations) if citations else ""

    def _generate_no_controversy_section(self) -> str:
        """生成无争议时的内容"""
        return """## 争议与对话

现有研究在该方面观点较为一致，尚未形成明显的学术争议或对立观点。这可能表明该领域的研究已经形成了较为稳定的共识，或者是该问题尚未引起足够的学术关注和探讨。

未来研究可以进一步探索：
- 不同研究情境下的适用性
- 边界条件和限制因素
- 与其他理论或观点的关联性
"""


class StructuredReviewGenerator:
    """结构化综述生成器（带争议分析）"""

    def __init__(self, api_key: str = None, base_url: str = "https://api.deepseek.com"):
        self.client = None
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if api_key:
                self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self.controversy_generator = ControversySectionGenerator()

    async def generate_review_with_controversies(
        self,
        topic: str,
        papers: List[Dict],
        sections: List[str] = None,
        model: str = "deepseek-chat"
    ) -> tuple[str, List[Dict], Dict]:
        """
        生成带争议分析的综述

        Args:
            topic: 研究主题
            papers: 论文列表
            sections: 章节列表（可选，如未提供则自动生成）
            model: 模型名称

        Returns:
            (综述内容, 被引用文献, 争议分析统计)
        """
        # 生成主体综述（这里可以调用原有的ReviewGeneratorService）
        # 为了简化，这里假设已经有主体内容
        main_content = await self._generate_main_content(topic, papers, model)

        # 提取引用的文献编号
        cited_indices = self._extract_cited_indices(main_content)

        # 为每个章节生成争议分析
        if sections:
            controversy_sections = []
            controversy_stats = {}

            for section in sections:
                # 为该章节筛选相关论文（简化处理，实际应根据章节主题筛选）
                section_papers = papers[:10]  # 取前10篇作为示例

                controversy_content = await self.controversy_generator.generate_controversy_section(
                    section_papers, topic, section, cited_indices
                )

                controversy_sections.append({
                    "section": section,
                    "content": controversy_content
                })

                # 统计该章节的争议点数量
                controversy_count = controversy_content.count("### 争议点")
                controversy_stats[section] = controversy_count

            # 组装最终综述
            final_review = self._assemble_review(main_content, controversy_sections)

            stats = {
                "total_sections": len(sections),
                "sections_with_controversies": sum(1 for s in controversy_stats if controversy_stats[s] > 0),
                "controversy_stats": controversy_stats
            }

            return final_review, papers, stats
        else:
            # 生成整体争议分析
            controversy_content = await self.controversy_generator.generate_controversy_section(
                papers, topic, None, cited_indices
            )

            final_review = f"{main_content}\n\n{controversy_content}"

            stats = {
                "total_sections": 1,
                "sections_with_controversies": 1 if "争议点" in controversy_content else 0,
                "controversy_stats": {"整体分析": controversy_content.count("### 争议点")}
            }

            return final_review, papers, stats

    async def _generate_main_content(self, topic: str, papers: List[Dict], model: str) -> str:
        """生成主体综述内容（简化版）"""
        # 这里应该调用ReviewGeneratorService
        # 为了演示，返回一个占位符
        papers_info = "\n".join([f"{i+1}. {p.get('title', '')}" for i, p in enumerate(papers[:5])])

        prompt = f"""请撰写关于"{topic}"的文献综述主体部分（不包括争议与对话章节）。

可用参考文献：
{papers_info}

要求：
1. 按主题组织内容
2. 构建文献矩阵进行对比分析
3. 每个观点后添加引用[序号]
4. 字数：2000-3000字

只输出综述正文，不要参考文献列表。"""

        if not self.client:
            return f"# {topic}文献综述\n\n[主体内容占位符]"

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位学术写作专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 争议分析需要准确识别不同观点
                max_tokens=3000
            )

            return response.choices[0].message.content.strip()
        except:
            return f"# {topic}文献综述\n\n[主体内容占位符]"

    def _extract_cited_indices(self, content: str) -> List[int]:
        """提取内容中的引用编号"""
        matches = re.findall(r'\[(\d+)\]', content)
        return sorted(set(int(m) for m in matches))

    def _assemble_review(self, main_content: str, controversy_sections: List[Dict]) -> str:
        """组装最终综述"""
        parts = [main_content]

        for section_data in controversy_sections:
            parts.append("\n\n---\n\n")  # 分隔线
            parts.append(section_data["content"])

        return "".join(parts)


# 便捷导出函数
async def generate_controversy_section(
    papers: List[Dict],
    topic: str,
    section_name: str = None,
    cited_indices: List[int] = None
) -> str:
    """
    生成争议与对话章节

    Args:
        papers: 论文列表
        topic: 研究主题
        section_name: 章节名称
        cited_indices: 已被引用的论文索引

    Returns:
        Markdown格式的争议章节内容
    """
    generator = ControversySectionGenerator()
    return await generator.generate_controversy_section(
        papers, topic, section_name, cited_indices
    )


async def analyze_viewpoints_and_controversies(
    papers: List[Dict],
    topic: str
) -> Dict:
    """
    分析观点和争议

    Args:
        papers: 论文列表
        topic: 研究主题

    Returns:
        包含观点和争议的分析结果
    """
    extractor = ViewpointExtractor()
    analyzer = ControversyAnalyzer()

    viewpoints = await extractor.extract_viewpoints(papers, topic)
    analysis = await analyzer.analyze_controversies(viewpoints, topic)

    return {
        "viewpoints": viewpoints,
        "controversies": analysis
    }
