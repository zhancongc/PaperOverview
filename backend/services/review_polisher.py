"""
综述润色服务
消除AI腔，让语言更干练、自然
"""
import re
import os
from typing import List, Dict, Tuple, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class AIToneEliminator:
    """AI腔消除器"""

    # AI腔高频词词典
    AI_TONE_PATTERNS = {
        # === 需要删除的词 ===
        "delete": [
            r"值得注意的是[，。：]?",
            r"显而易见[，。：]?",
            r"众所周知[，。：]?",
            r"不言而喻[，。：]?",
            r"诚然[，。：]?",
            r"事实上[，。：]?",
            r"实际上[，。：]?",
            r"换言之[，。：]?",
            r"换句话说[，。：]?",
            r"也就是说[，。：]?",
            r"简而言之[，。：]?",
            r"总的来说[，。：]?",
            r"总体来看[，。：]?",
            r"从某种意义上说[，。：]?",
            r"在一定程度上[，。：]?",
            r"可以肯定的是[，。：]?",
            r"毫无疑问[，。：]?",
            r"毋庸置疑[，。：]?",
        ],

        # === 需要替换的词 ===
        "replace": [
            (r"近年来[,，]?", "近五年"),  # 更具体
            (r"随着.*?的发展[,，]?", ""),  # 删除背景铺垫
            (r"在.*?背景下[,，]?", ""),  # 删除背景铺垫
            (r"此外[,，]?", "；"),  # 用分号代替
            (r"另外[,，]?", "；"),  # 用分号代替
            (r"同时[,，]?", ""),  # 删除
            (r"一方面.*?另一方面.*?[,，。]?", ""),  # 删除对比铺垫
            (r"一方面[,，]?", ""),  # 删除
            (r"另一方面[,，]?", ""),  # 删除
            (r"然而[,，]?", "但"),  # 更简洁
            (r"不过[,，]?", "但"),  # 更简洁
            (r"因此[,，]?", "因此"),  # 保留
            (r"所以[,，]?", "因此"),  # 统一用"因此"
            (r"综上所述[,，]?", "综上"),  # 更简洁
            (r"总而言之[,，]?", "综上"),  # 更简洁
            (r"简言之[,，]?", ""),  # 删除
            (r"具体来说[,，]?", "具体而言"),  # 更正式
            (r"例如[,，]?", "如"),  # 更简洁
            (r"比如[,，]?", "如"),  # 更简洁
            (r"等等[,，]?", "等"),  # 删除逗号
            (r"等一系列.*?[,，。]?", "等"),  # 简化
            (r"以及相关.*?[,，。]?", "及"),  # 简化
            (r"以及.*?[,，。]?", "、"),  # 用顿号
            (r".*?有鉴于此[,，。]?", ""),  # 删除过渡句
            (r"基于.*?[，。]?", ""),  # 删除方法铺垫
            (r"通过.*?方法[,，]?", ""),  # 删除方法铺垫
            (r"采用.*?方法[,，]?", ""),  # 删除方法铺垫
        ],

        # === 需要优化的句式 ===
        "sentence": [
            # "本文旨在..." → 直接陈述
            (r"本文旨在.*?[,，。]", ""),
            # "研究结果表明..." → "研究表明"
            (r"研究结果表明", "研究表明"),
            (r"实证结果显示", "实证发现"),
            (r"分析结果发现", "分析发现"),
            # "具有...意义" → 更简洁
            (r"具有.*?重要意义", "具有重要意义" if True else ""),  # 根据上下文决定
            (r"具有.*?意义", "有"),  # 简化
            # "在一定程度上" → 直接删除或具体化
            (r"在一定程度上", ""),  # 通常可以删除
        ],
    }

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    def polish_with_rules(self, text: str) -> Tuple[str, Dict]:
        """
        使用规则进行润色

        Args:
            text: 原始文本

        Returns:
            (润色后的文本, 润色报告)
        """
        original_text = text
        polish_report = {
            "deletions": [],
            "replacements": [],
            "total_changes": 0
        }

        # 1. 删除AI腔词汇
        for pattern in self.AI_TONE_PATTERNS["delete"]:
            matches = re.finditer(pattern, text)
            for match in matches:
                matched_text = match.group(0)
                text = text.replace(matched_text, "", 1)
                polish_report["deletions"].append({
                    "original": matched_text,
                    "action": "删除"
                })

        # 2. 替换AI腔词汇
        for pattern, replacement in self.AI_TONE_PATTERNS["replace"]:
            matches = re.finditer(pattern, text)
            for match in matches:
                matched_text = match.group(0)
                text = text.replace(matched_text, replacement, 1)
                polish_report["replacements"].append({
                    "original": matched_text,
                    "replacement": replacement,
                    "action": "替换"
                })

        # 3. 优化句式
        for pattern, replacement in self.AI_TONE_PATTERNS["sentence"]:
            matches = re.finditer(pattern, text)
            for match in matches:
                matched_text = match.group(0)
                text = text.replace(matched_text, replacement, 1)
                polish_report["replacements"].append({
                    "original": matched_text,
                    "replacement": replacement,
                    "action": "句式优化"
                })

        # 4. 清理多余空格和标点
        text = self._cleanup_whitespace(text)

        polish_report["total_changes"] = (
            len(polish_report["deletions"]) + len(polish_report["replacements"])
        )

        # 计算压缩率
        original_length = len(original_text)
        new_length = len(text)
        polish_report["compression_ratio"] = (
            (original_length - new_length) / original_length if original_length > 0 else 0
        )

        return text, polish_report

    def _cleanup_whitespace(self, text: str) -> str:
        """清理多余空格和标点"""
        # 删除多余的空行（超过2个连续换行）
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 删除行首空格
        text = re.sub(r'^ +', '', text, flags=re.MULTILINE)

        # 清理多余的逗号
        text = re.sub(r'，+', '，', text)
        text = re.sub(r',+', ',', text)

        # 清理多余的句号
        text = re.sub(r'。+', '。', text)

        # 删除标点前的空格
        text = re.sub(r' +([，。：；！？])', r'\1', text)

        # 确保句号后有空格
        text = re.sub(r'。([^。\n])', r'。 \1', text)

        return text.strip()

    async def polish_with_llm(
        self,
        text: str,
        style: str = "academic",
        strict: bool = True
    ) -> Tuple[str, Dict]:
        """
        使用LLM进行润色

        Args:
            text: 原始文本
            style: 润色风格 (academic, concise, professional)
            strict: 是否严格删除AI腔

        Returns:
            (润色后的文本, 润色报告)
        """
        if not self.client:
            return self.polish_with_rules(text)

        style_instructions = {
            "academic": "学术规范，用词准确、逻辑严密",
            "concise": "简洁干练，删除冗余表达",
            "professional": "专业严谨，适合学术期刊发表"
        }

        strict_instruction = """
请特别注意消除以下"AI腔"表达：
- 删除："近年来"、"值得注意的是"、"换言之"、"显而易见"等
- 删除："随着...的发展"、"在...背景下"等背景铺垫
- 删除："一方面...另一方面"、"此外"、"另外"等过渡词
- 删除："本文旨在"、"研究结果表明"等程式化表达
- 直接陈述观点，用简洁的语言
""" if strict else ""

        prompt = f"""请对以下综述文本进行润色，消除AI腔，让语言更干练、自然。

润色要求：
1. {style_instructions.get(style, '学术规范')}
2. 删除冗余的过渡词和背景铺垫{strict_instruction}
3. 保持原文的核心观点和引用编号不变
4. 让句子更简洁有力
5. 避免程式化表达

原文：
{text[:2000]}

只返回润色后的文本，不要有其他说明。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位学术写作专家，擅长润色和优化综述文本。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=3000
            )

            polished_text = response.choices[0].message.content.strip()

            # 生成润色报告
            polish_report = {
                "method": "llm",
                "style": style,
                "strict": strict,
                "original_length": len(text),
                "polished_length": len(polished_text),
                "compression_ratio": (len(text) - len(polished_text)) / len(text) if len(text) > 0 else 0
            }

            return polished_text, polish_report

        except Exception as e:
            print(f"[AIToneEliminator] LLM润色失败: {e}，使用规则润色")
            return self.polish_with_rules(text)

    async def polish_review(
        self,
        content: str,
        method: str = "hybrid",
        style: str = "academic"
    ) -> Tuple[str, Dict]:
        """
        润色综述内容

        Args:
            content: 综述内容
            method: 润色方法 (rule, llm, hybrid)
            style: 润色风格

        Returns:
            (润色后的内容, 详细报告)
        """
        if method == "rule":
            polished_content, report = self.polish_with_rules(content)
            report["method"] = "rule"

        elif method == "llm":
            polished_content, report = await self.polish_with_llm(content, style)
            report["method"] = "llm"

        else:  # hybrid
            # 先用规则快速处理
            polished_content, rule_report = self.polish_with_rules(content)

            # 再用LLM优化
            final_content, llm_report = await self.polish_with_llm(
                polished_content, style, strict=False
            )

            report = {
                "method": "hybrid",
                "rule_changes": rule_report.get("total_changes", 0),
                "final_length": len(final_content),
                "compression_ratio": llm_report.get("compression_ratio", 0),
                "details": {
                    "rule_phase": rule_report,
                    "llm_phase": llm_report
                }
            }

            polished_content = final_content

        return polished_content, report


class ReviewPolisher:
    """综述润色器（集成多种润色功能）"""

    def __init__(self):
        self.tone_eliminator = AIToneEliminator()

    async def polish(
        self,
        content: str,
        options: Dict = None
    ) -> Tuple[str, Dict]:
        """
        润色综述

        Args:
            content: 综述内容
            options: 润色选项
                - method: rule/llm/hybrid
                - style: academic/concise/professional
                - remove_ai_tone: 是否消除AI腔
                - check_citations: 是否检查引用格式
                - enhance_readability: 是否增强可读性

        Returns:
            (润色后的内容, 润色报告)
        """
        if options is None:
            options = {
                "method": "hybrid",
                "style": "academic",
                "remove_ai_tone": True,
                "check_citations": True,
                "enhance_readability": True
            }

        polished_content = content
        report = {
            "steps": []
        }

        # 1. 消除AI腔
        if options.get("remove_ai_tone", True):
            polished_content, tone_report = await self.tone_eliminator.polish_review(
                polished_content,
                method=options.get("method", "hybrid"),
                style=options.get("style", "academic")
            )
            report["steps"].append({
                "step": "消除AI腔",
                "report": tone_report
            })

        # 2. 检查引用格式
        if options.get("check_citations", True):
            polished_content, citation_report = self._check_citation_format(polished_content)
            report["steps"].append({
                "step": "检查引用格式",
                "report": citation_report
            })

        # 3. 增强可读性
        if options.get("enhance_readability", True):
            polished_content, readability_report = self._enhance_readability(polished_content)
            report["steps"].append({
                "step": "增强可读性",
                "report": readability_report
            })

        # 4. 最终清理
        polished_content = self.tone_eliminator._cleanup_whitespace(polished_content)

        # 生成总报告
        report["summary"] = self._generate_summary(content, polished_content, report)

        return polished_content, report

    def _check_citation_format(self, text: str) -> Tuple[str, Dict]:
        """检查引用格式"""
        issues = []
        fixed_text = text

        # 检查连续引用是否需要拆分
        import re
        continuous_pattern = re.compile(r'\[(\d+)[-–—](\d+)\]')
        matches = continuous_pattern.findall(text)

        for start, end in matches:
            if int(end) - int(start) > 3:
                issues.append({
                    "type": "连续引用超过3篇",
                    "location": f"[{start}-{end}]",
                    "suggestion": "建议拆分为结构化表述"
                })

        # 检查引用编号是否连续
        citations = re.findall(r'\[(\d+)\]', text)
        if citations:
            citation_numbers = [int(c) for c in citations]
            max_citation = max(citation_numbers) if citation_numbers else 0
            # 这里不做强制检查，因为可能不是所有文献都被引用

        return fixed_text, {
            "issues_found": len(issues),
            "issues": issues[:5]  # 只返回前5个问题
        }

    def _enhance_readability(self, text: str) -> Tuple[str, Dict]:
        """增强可读性"""
        improvements = []

        # 1. 检查过长的句子
        sentences = text.split("。")
        long_sentences = [(i, s) for i, s in enumerate(sentences) if len(s) > 150]

        # 2. 检查段落长度
        paragraphs = text.split("\n\n")
        long_paragraphs = [(i, p) for i, p in enumerate(paragraphs) if len(p) > 500]

        # 3. 建议优化
        suggestions = []
        if len(long_sentences) > 3:
            suggestions.append(f"发现{len(long_sentences)}个超长句子（>150字），建议拆分")
        if len(long_paragraphs) > 2:
            suggestions.append(f"发现{len(long_paragraphs)}个超长段落（>500字），建议分段")

        return text, {
            "long_sentences": len(long_sentences),
            "long_paragraphs": len(long_paragraphs),
            "suggestions": suggestions
        }

    def _generate_summary(
        self,
        original: str,
        polished: str,
        report: Dict
    ) -> str:
        """生成润色摘要"""
        original_len = len(original)
        polished_len = len(polished)
        compression = (original_len - polished_len) / original_len if original_len > 0 else 0

        steps_summary = "\n".join([
            f"- {step['step']}: {step['report'].get('method', '完成')}"
            for step in report.get("steps", [])
        ])

        return f"""润色完成：
- 原始长度: {original_len} 字符
- 润色后长度: {polished_len} 字符
- 压缩率: {compression:.1%}
- 处理步骤:
{steps_summary}"""


# 便捷导出函数
def polish_review_text(text: str, method: str = "rule") -> Tuple[str, Dict]:
    """
    润色综述文本

    Args:
        text: 综述文本
        method: 润色方法

    Returns:
        (润色后的文本, 报告)
    """
    eliminator = AIToneEliminator()

    if method == "llm":
        import asyncio
        return asyncio.run(eliminator.polish_with_llm(text))
    else:
        return eliminator.polish_with_rules(text)


def detect_ai_tone(text: str) -> Dict:
    """
    检测文本中的AI腔

    Args:
        text: 文本

    Returns:
        检测结果
    """
    eliminator = AIToneEliminator()
    ai_tone_count = 0

    detected_patterns = []

    for pattern in eliminator.AI_TONE_PATTERNS["delete"]:
        matches = re.finditer(pattern, text)
        count = len(list(matches))
        if count > 0:
            detected_patterns.append({
                "pattern": pattern,
                "count": count,
                "type": "delete"
            })
            ai_tone_count += count

    for pattern, _ in eliminator.AI_TONE_PATTERNS["replace"]:
        matches = re.finditer(pattern, text)
        count = len(list(matches))
        if count > 0:
            detected_patterns.append({
                "pattern": pattern,
                "count": count,
                "type": "replace"
            })
            ai_tone_count += count

    return {
        "ai_tone_count": ai_tone_count,
        "detected_patterns": detected_patterns[:10],  # 只返回前10个
        "ai_tone_ratio": ai_tone_count / len(text) if len(text) > 0 else 0
    }
