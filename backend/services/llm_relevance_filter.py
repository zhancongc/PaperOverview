"""
基于LLM的文献相关性判断服务

使用大模型的语义理解能力，判断文献是否与主题相关。

DEPRECATED: 此模块为 v5.x 旧版本遗留代码，当前 v6.0 流程已不再使用。
保留仅用于历史参考，新代码请使用 PaperSearchAgent + SmartReviewGeneratorFinal。
"""
import warnings
warnings.warn(
    "llm_relevance_filter 模块已废弃，v6.0 流程不再使用",
    DeprecationWarning,
    stacklevel=2
)
import os
import httpx
from typing import List, Dict, Tuple


class LLMRelevanceFilter:
    """基于LLM的相关性过滤器"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    async def batch_check_relevance(
        self,
        papers: List[Dict],
        topic: str,
        section_title: str = "",
        section_keywords: List[str] = None
    ) -> Tuple[List[Dict], List[Dict], List[str]]:
        """
        批量检查论文相关性（使用LLM）

        Args:
            papers: 论文列表
            topic: 研究主题
            section_title: 小节标题（可选）
            section_keywords: 小节关键词（可选）

        Returns:
            (相关论文, 不相关论文, 判断理由列表)
        """
        if not papers:
            return [], [], []

        if not self.api_key:
            print("[LLM相关性] 无API key，保守策略：保留所有论文", flush=True)
            return papers, [], ["无API key，保留所有文献"]

        # 构建论文信息（只使用标题，节省token）
        papers_info = []
        for i, paper in enumerate(papers, 1):
            title = paper.get('title', '')
            venue = paper.get('journal', '') or paper.get('venue', '')

            info = f"{i}. {title}"
            if venue:
                info += f" ({venue})"
            papers_info.append(info)

        papers_text = "\n".join(papers_info)

        # 构建关键词描述
        keywords_desc = ", ".join(section_keywords) if section_keywords else "未提供"
        section_desc = f"当前小节: {section_title}\n小节关键词: {keywords_desc}" if section_title else ""

        # 构建prompt
        prompt = f"""你是一位学术文献检索专家。请根据论文标题判断文献是否与给定研究主题相关。

**研究主题**: {topic}
{section_desc}

**文献列表**（仅包含标题和来源）:
{papers_text}

请仔细分析每篇论文的标题，判断其是否真正研究主题相关的内容。

**特别注意：术语歧义**
- "symbolic execution"（符号执行）是软件测试技术，用于程序分析和测试生成
- "symbolic computation"（符号计算）是计算机代数系统，用于数学公式计算
- 两者完全不同！包含"symbolic execution"的论文通常与符号计算无关

**不相关论文的典型特征**：
- 软件测试、程序分析、代码覆盖（symbolic execution, path exploration）
- 教学应用、课程设计（teaching, education, course）
- 安全漏洞检测（vulnerability detection, fault attack）
- 时间序列预测、深度学习通用应用

**输出格式**（严格按格式输出）:
相关: [序号列表，用逗号分隔]
不相关: [序号列表，用逗号分隔]

理由: [仅对不相关文献说明原因，每条用分号分隔]

请开始判断:"""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 1000  # 减少输出token，节省成本
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()

                # 解析结果
                relevant_indices = []
                irrelevant_indices = []
                reasons_text = ""

                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('相关:'):
                        indices_str = line.replace('相关:', '').strip()
                        relevant_indices = [int(x.strip()) for x in indices_str.split(',') if x.strip().strip('。').isdigit()]
                    elif line.startswith('不相关:'):
                        indices_str = line.replace('不相关:', '').strip()
                        irrelevant_indices = [int(x.strip()) for x in indices_str.split(',') if x.strip().strip('。').isdigit()]
                    elif line.startswith('理由:'):
                        reasons_text = line.replace('理由:', '').strip()

                # 分类论文
                relevant_papers = []
                irrelevant_papers = []
                reasons_list = []

                for idx, paper in enumerate(papers, 1):
                    paper_copy = paper.copy()
                    if idx in relevant_indices:
                        relevant_papers.append(paper_copy)
                    elif idx in irrelevant_indices:
                        paper_copy['_llm_reject_reason'] = 'LLM判定不相关'
                        irrelevant_papers.append(paper_copy)

                # 解析理由
                if reasons_text:
                    reasons_list = [r.strip() for r in reasons_text.split(';') if r.strip()]

                print(f"[LLM相关性] 判断完成: 相关{len(relevant_papers)}篇, 不相关{len(irrelevant_papers)}篇", flush=True)

                return relevant_papers, irrelevant_papers, reasons_list

        except Exception as e:
            print(f"[LLM相关性] 判断失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # 失败时保留所有论文（保守策略）
            return papers, [], [f"LLM判断失败，保留所有文献: {str(e)}"]


# 全局实例
_llm_filter_instance = None


def get_llm_relevance_filter() -> LLMRelevanceFilter:
    """获取LLM相关性过滤器实例"""
    global _llm_filter_instance
    if _llm_filter_instance is None:
        _llm_filter_instance = LLMRelevanceFilter()
    return _llm_filter_instance
