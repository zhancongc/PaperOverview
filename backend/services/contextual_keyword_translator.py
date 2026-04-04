"""
基于主题的上下文关键词翻译服务

解决关键词翻译的语义歧义问题，确保翻译后的关键词与题目主题一致。
"""
import os
import httpx
from typing import List, Dict, Optional
import re


class DomainKnowledge:
    """领域知识库"""

    # 领域缩写词扩展表（优先级最高，防止搜到不相关文献）
    ABBREVIATION_EXPANSIONS = {
        # 计算机代数系统
        "CAS": "Computer Algebra System",
        "MACSYMA": "Project MAC's Symbolic Manipulation System",
        # 机器学习
        "ML": "Machine Learning",
        "DL": "Deep Learning",
        "NLP": "Natural Language Processing",
        "CV": "Computer Vision",
        "RL": "Reinforcement Learning",
        # 符号执行
        "SE": "Symbolic Execution",
        "CBMC": "Bounded Model Checking for C",
        # 区块链
        "DeFi": "Decentralized Finance",
        "DApp": "Decentralized Application",
        # 其他
        "IoT": "Internet of Things",
        "VR": "Virtual Reality",
        "AR": "Augmented Reality",
        "AI": "Artificial Intelligence",
        "API": "Application Programming Interface",
        "GUI": "Graphical User Interface",
        "CLI": "Command Line Interface",
        "IDE": "Integrated Development Environment",
        "OS": "Operating System",
        "DB": "Database",
        "RDBMS": "Relational Database Management System",
        "NoSQL": "Not Only SQL",
        "SQL": "Structured Query Language",
    }

    # 领域定义
    DOMAINS = {
        "computer_algebra": {
            "name": "计算机代数系统",
            "keywords": ["CAS", "computer algebra", "symbolic computation", "mathematica", "maple", "maxima"],
            "chinese_keywords": ["计算机代数", "符号计算", "代数系统", "数学软件"],
            "exclude_terms": ["execution", "testing", "verification", "vulnerability", "software analysis"],
            "related_concepts": ["symbolic integration", "equation solving", "polynomial", "algorithm", "mathematics education"],
        },
        "symbolic_execution": {
            "name": "符号执行",
            "keywords": ["symbolic execution", "path exploration", "constraint solving", "klee", "angr"],
            "chinese_keywords": ["符号执行", "路径探索", "约束求解", "软件验证"],
            "exclude_terms": ["mathematica", "maple", "algebra system", "equation solving"],
            "related_concepts": ["software testing", "vulnerability detection", "formal verification", "program analysis"],
        },
        "machine_learning": {
            "name": "机器学习",
            "keywords": ["machine learning", "deep learning", "neural network", "CNN", "RNN", "transformer"],
            "chinese_keywords": ["机器学习", "深度学习", "神经网络"],
            "exclude_terms": [],
            "related_concepts": ["AI", "pattern recognition", "data mining"],
        },
        "blockchain": {
            "name": "区块链",
            "keywords": ["blockchain", "smart contract", "consensus", "cryptocurrency"],
            "chinese_keywords": ["区块链", "智能合约", "共识机制"],
            "exclude_terms": [],
            "related_concepts": ["bitcoin", "ethereum", "distributed ledger"],
        },
    }

    @classmethod
    def expand_abbreviations(cls, text: str, topic: str = None) -> str:
        """
        扩展文本中的领域缩写词

        Args:
            text: 包含可能的缩写词的文本
            topic: 论文题目（用于上下文判断）

        Returns:
            扩展后的文本
        """
        result = text
        expansions_made = []

        for abbr, expansion in cls.ABBREVIATION_EXPANSIONS.items():
            # 检查文本中是否包含该缩写（支持中英混合）
            if abbr in result:
                # 根据上下文决定是否扩展
                should_expand = cls._should_expand_abbreviation(abbr, result, topic)

                if should_expand:
                    # 替换缩写（保留原始大小写）
                    result = result.replace(abbr, expansion)
                    expansions_made.append(f"{abbr} -> {expansion}")

        if expansions_made:
            print(f"[缩写扩展] {', '.join(expansions_made)}")

        return result

    @classmethod
    def _should_expand_abbreviation(cls, abbr: str, text: str, topic: str = None) -> bool:
        """
        判断是否应该扩展某个缩写

        Args:
            abbr: 缩写词
            text: 包含缩写的文本
            topic: 论文题目

        Returns:
            是否应该扩展
        """
        # 特殊处理 CAS
        if abbr == "CAS":
            # 如果主题明确是计算机代数系统，必须扩展
            if topic and any(kw in topic.lower() for kw in ["computer algebra", "符号计算", "代数系统"]):
                return True
            # 如果文本中已经包含 "computer algebra"，说明这是 CAS 的正确用法，需要扩展
            if "computer algebra" in text.lower():
                return True
            # 否则不扩展（可能是其他含义的 CAS）
            return False

        # 对于常见缩写，始终扩展
        common_abbreviations = ["ML", "DL", "NLP", "CV", "RL", "AI", "API", "SQL", "NoSQL"]
        if abbr in common_abbreviations:
            return True

        # 默认扩展其他缩写
        return True

    @classmethod
    def identify_domain(cls, topic: str) -> Optional[str]:
        """
        识别题目的主题领域

        Args:
            topic: 论文题目

        Returns:
            领域名称，如 "computer_algebra", "symbolic_execution" 等
        """
        topic_lower = topic.lower()

        # 计算每个领域的相关性得分
        scores = {}
        for domain_name, domain_info in cls.DOMAINS.items():
            score = 0

            # 检查领域关键词
            for keyword in domain_info["keywords"]:
                if keyword.lower() in topic_lower:
                    score += 10

            # 检查中文关键词
            for keyword in domain_info["chinese_keywords"]:
                if keyword in topic:
                    score += 10

            # 检查缩写（如 CAS）
            if domain_name == "computer_algebra" and "CAS" in topic:
                score += 20

            scores[domain_name] = score

        # 返回得分最高的领域
        if scores:
            best_domain = max(scores, key=scores.get)
            if scores[best_domain] > 0:
                return best_domain

        return None

    @classmethod
    def get_domain_constraints(cls, domain: str) -> Dict:
        """
        获取领域的约束条件

        Args:
            domain: 领域名称

        Returns:
            约束条件字典，包含相关术语和排除术语
        """
        if domain in cls.DOMAINS:
            domain_info = cls.DOMAINS[domain]
            return {
                "related_terms": domain_info["related_concepts"],
                "exclude_terms": domain_info["exclude_terms"],
                "chinese_keywords": domain_info["chinese_keywords"],
            }
        return {
            "related_terms": [],
            "exclude_terms": [],
            "chinese_keywords": [],
        }


class ContextualKeywordTranslator:
    """基于上下文的关键词翻译服务"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"

    async def expand_abbreviations_with_llm(
        self,
        keywords: List[str],
        topic: str,
        research_direction_id: str = ""
    ) -> List[str]:
        """
        使用 LLM 智能扩展关键词中的缩写词

        Args:
            keywords: 关键词列表
            topic: 论文题目
            research_direction_id: 研究方向ID（可选）

        Returns:
            扩展后的关键词列表
        """
        if not self.api_key:
            # 回退到规则扩展（使用研究方向配置）
            print(f"[缩写扩展] 无 API key，使用规则扩展")
            return [
                self._expand_with_rules(kw, topic, research_direction_id)
                for kw in keywords
            ]

        print(f"\n[LLM 缩写扩展] 题目: {topic}")
        if research_direction_id:
            from config.research_directions import get_direction_by_id
            direction_info = get_direction_by_id(research_direction_id)
            if direction_info:
                print(f"[LLM 缩写扩展] 研究方向: {direction_info.get('name', '')}")
        print(f"[LLM 缩写扩展] 待处理关键词: {keywords}")

        # 构建提示词 - 使用 JSON 格式输出以便更可靠的解析
        prompt = f"""你是一个学术术语专家。请分析以下论文题目和关键词，识别并扩展其中的缩写词。

**论文题目**: {topic}

**关键词列表**:
{chr(10).join(f'- {kw}' for kw in keywords)}

**任务**:
识别关键词中的缩写词，根据题目主题判断其完整含义，并扩展为完整形式。

**重要原则**:
1. 只扩展明确的、与主题相关的缩写词
2. 如果缩写词有多种含义，根据题目主题选择最相关的含义
3. 不要扩展已经是完整形式的词
4. 保持原文的其他部分不变

**示例**:
- CAS符号计算算法 -> Computer Algebra System符号计算算法
- ML model optimization -> Machine Learning model optimization

**输出格式**:
请严格按照以下 JSON 格式输出（不要添加其他内容）:
{{
  "expanded_keywords": [
    "扩展后的关键词1",
    "扩展后的关键词2",
    ...
  ]
}}

请开始处理:"""

        try:
            import httpx
            client = httpx.AsyncClient(timeout=30.0)
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个学术术语专家，精通各领域的缩写词扩展。请严格按照 JSON 格式输出。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"}
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            data = response.json()

            # 解析 JSON 结果
            content = data["choices"][0]["message"]["content"].strip()
            import json
            result = json.loads(content)
            expanded_keywords = result.get("expanded_keywords", [])

            # 验证结果
            if len(expanded_keywords) == len(keywords):
                print(f"[LLM 缩写扩展] 扩展完成")
                for orig, exp in zip(keywords, expanded_keywords):
                    if orig != exp:
                        print(f"  {orig} -> {exp}")
                return expanded_keywords
            else:
                print(f"[LLM 缩写扩展] 返回数量不匹配（期望 {len(keywords)}，得到 {len(expanded_keywords)}），使用规则扩展")
                return [
                    DomainKnowledge.expand_abbreviations(kw, topic)
                    for kw in keywords
                ]

        except json.JSONDecodeError as e:
            print(f"[LLM 缩写扩展] JSON 解析失败: {e}，使用规则扩展")
            return [
                DomainKnowledge.expand_abbreviations(kw, topic)
                for kw in keywords
            ]
        except Exception as e:
            print(f"[LLM 缩写扩展] 失败: {e}，使用规则扩展")
            return [
                self._expand_with_rules(kw, topic, research_direction_id)
                for kw in keywords
            ]

    def _expand_with_rules(
        self,
        keyword: str,
        topic: str,
        research_direction_id: str = ""
    ) -> str:
        """
        使用规则扩展缩写词

        Args:
            keyword: 关键词
            topic: 论文题目
            research_direction_id: 研究方向ID

        Returns:
            扩展后的关键词
        """
        result = keyword
        expansions_made = []

        # 优先使用研究方向配置的缩写表
        if research_direction_id:
            from config.research_directions import get_direction_abbreviations
            direction_abbreviations = get_direction_abbreviations(research_direction_id)

            for abbr, expansion in direction_abbreviations.items():
                if abbr in result:
                    result = result.replace(abbr, expansion)
                    expansions_made.append(f"{abbr} -> {expansion}")

        # 使用通用的缩写表作为后备
        if not expansions_made:
            result = DomainKnowledge.expand_abbreviations(keyword, topic)

        if expansions_made:
            print(f"[缩写扩展] {', '.join(expansions_made)}")

        return result

    async def translate_keywords_with_context(
        self,
        keywords: List[str],
        topic: str,
        target_lang: str = "en",
        research_direction_id: str = ""
    ) -> Dict[str, str]:
        """
        基于题目主题翻译关键词

        Args:
            keywords: 关键词列表
            topic: 论文题目
            target_lang: 目标语言
            research_direction_id: 研究方向ID（可选，用于提高翻译相关性）

        Returns:
            翻译映射 {原词: 译词}
        """
        if not keywords:
            return {}

        # 获取研究方向名称
        research_direction = ""
        if research_direction_id:
            from config.research_directions import get_direction_by_id
            direction_info = get_direction_by_id(research_direction_id)
            if direction_info:
                research_direction = direction_info.get("name", "")

        print(f"\n[上下文翻译] 题目: {topic}")
        if research_direction:
            print(f"[上下文翻译] 研究方向: {research_direction}")
        print(f"[上下文翻译] 原始关键词: {keywords}")

        # === 第一步：使用 LLM 智能扩展缩写词（防止搜到不相关文献）===
        # 合并主题和研究方向，提高上下文理解准确性
        context = topic
        if research_direction:
            context = f"{topic} (研究方向: {research_direction})"

        expanded_keywords = await self.expand_abbreviations_with_llm(
            keywords, context, research_direction_id
        )

        # 保存原始关键词到扩展关键词的映射
        original_to_expanded = {}
        if expanded_keywords != keywords:
            print(f"[上下文翻译] 最终关键词: {expanded_keywords}")
            for orig, exp in zip(keywords, expanded_keywords):
                if orig != exp:
                    original_to_expanded[orig] = exp
            keywords = expanded_keywords

        # 第二步：识别主题领域
        domain = DomainKnowledge.identify_domain(topic)

        print(f"[上下文翻译] 识别领域: {domain if domain else '通用'}")

        # 第三步：获取领域约束
        if domain:
            constraints = DomainKnowledge.get_domain_constraints(domain)
            exclude_terms = constraints["exclude_terms"]
            related_terms = constraints["related_terms"]
            print(f"[上下文翻译] 排除术语: {exclude_terms[:5]}...")
            print(f"[上下文翻译] 相关术语: {related_terms[:5]}...")
        else:
            exclude_terms = []
            related_terms = []

        # 第四步：翻译关键词
        translations = {}

        if self.api_key:
            # 使用 LLM 翻译，提供上下文（包括研究方向）
            translations = await self._translate_with_llm(
                keywords, topic, domain, target_lang, exclude_terms, related_terms, research_direction
            )
        else:
            # 回退到规则翻译
            translations = self._translate_with_rules(
                keywords, domain, exclude_terms, related_terms
            )

        print(f"[上下文翻译] 翻译完成: {len(translations)} 个关键词")

        # 将翻译结果的键从扩展后的关键词改回原始关键词
        # 这样调用者可以使用原始关键词查找翻译结果
        final_translations = {}
        for orig_keyword, expanded_keyword in original_to_expanded.items():
            if expanded_keyword in translations:
                final_translations[orig_keyword] = translations[expanded_keyword]
        # 对于没有被扩展的关键词，直接使用翻译结果
        for kw in keywords:
            if kw in translations and kw not in original_to_expanded.values():
                final_translations[kw] = translations[kw]

        return final_translations

    async def _translate_with_llm(
        self,
        keywords: List[str],
        topic: str,
        domain: Optional[str],
        target_lang: str,
        exclude_terms: List[str],
        related_terms: List[str],
        research_direction: str = ""
    ) -> Dict[str, str]:
        """使用 LLM 翻译关键词（带上下文）"""

        # 构建领域说明
        domain_explanation = ""
        if domain:
            domain_info = DomainKnowledge.DOMAINS.get(domain, {})
            domain_explanation = f"""
**主题领域**: {domain_info.get('name', domain)}

**重要**: 请确保翻译后的关键词符合该领域的术语规范。

**排除术语**（不要使用这些词的翻译）:
{', '.join(exclude_terms[:10])}

**相关术语**（参考这些概念）:
{', '.join(related_terms[:10])}
"""

        # 构建研究方向说明
        direction_explanation = ""
        if research_direction:
            direction_explanation = f"""
**研究方向**: {research_direction}

**重要**: 翻译时请参考这个研究方向，确保术语的一致性和准确性。
"""

        # 构建提示词
        if target_lang == "en":
            prompt = f"""请将以下学术关键词翻译成英文，注意保持术语的准确性。

**论文题目**: {topic}
{direction_explanation}
{domain_explanation}

**关键词列表**:
{chr(10).join(f"{i+1}. {kw}" for i, kw in enumerate(keywords))}

**翻译要求**:
1. 返回格式：原词 -> 译词（每行一个）
2. 保持学术术语的准确性
3. 考虑主题领域，使用该领域的标准术语
4. 如果是专有名词（如人名、算法名、系统名），保持原文
5. **重要**: 确保翻译后的关键词与题目主题一致，不要翻译成其他领域的术语
6. **缩写词处理**:
   - 对于领域特定的缩写（如 CAS = Computer Algebra System），必须扩展为完整形式
   - 避免使用模糊的缩写，以防搜索到不相关的文献
   - 常见缩写扩展：CAS -> Computer Algebra System, ML -> Machine Learning, DL -> Deep Learning

示例（假设主题是计算机代数系统）:
  CAS符号计算算法 -> Computer Algebra System symbolic computation algorithms
  符号积分算法 -> symbolic integration algorithms
  Mathematica系统设计 -> Mathematica system design

**请开始翻译**:"""

        try:
            client = httpx.AsyncClient(timeout=30.0)
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术翻译专家，精通多个领域的术语翻译。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            data = response.json()

            # 解析翻译结果
            content = data["choices"][0]["message"]["content"].strip()
            translations = {}

            for line in content.split('\n'):
                line = line.strip()
                if '->' in line:
                    parts = line.split('->')
                    if len(parts) == 2:
                        original = parts[0].strip()
                        translated = parts[1].strip()
                        # 移除可能的序号
                        original = original.split('.', 1)[-1].strip() if '.' in original else original
                        translations[original] = translated

            return translations

        except Exception as e:
            print(f"[上下文翻译] LLM翻译失败: {e}")
            # 回退到规则翻译
            return self._translate_with_rules(keywords, domain, exclude_terms, related_terms)

    def _translate_with_rules(
        self,
        keywords: List[str],
        domain: Optional[str],
        exclude_terms: List[str],
        related_terms: List[str]
    ) -> Dict[str, str]:
        """使用规则翻译关键词"""

        # 预定义的翻译规则（按领域）
        domain_translations = {
            "computer_algebra": {
                "CAS": "Computer Algebra System",
                "符号计算": "symbolic computation",
                "代数系统": "algebra system",
                "符号积分": "symbolic integration",
                "方程求解": "equation solving",
                "多项式": "polynomial",
                "算法": "algorithm",
                "数学软件": "mathematical software",
                "计算机代数": "computer algebra",
            },
            "symbolic_execution": {
                "符号执行": "symbolic execution",
                "路径探索": "path exploration",
                "约束求解": "constraint solving",
                "软件验证": "software verification",
                "程序分析": "program analysis",
                "测试用例生成": "test case generation",
            },
        }

        translations = {}

        # 如果有领域定义，使用领域特定的翻译
        if domain and domain in domain_translations:
            domain_rules = domain_translations[domain]

            for keyword in keywords:
                # 精确匹配
                if keyword in domain_rules:
                    translations[keyword] = domain_rules[keyword]
                else:
                    # 尝试部分匹配
                    for key, value in domain_rules.items():
                        if key in keyword:
                            translations[keyword] = keyword.replace(key, value)
                            break

        return translations


# 全局实例
contextual_translator = ContextualKeywordTranslator()


async def translate_keywords_contextual(
    keywords: List[str],
    topic: str,
    target_lang: str = "en",
    research_direction_id: str = ""
) -> Dict[str, str]:
    """
    基于上下文翻译关键词（便捷函数）

    Args:
        keywords: 关键词列表
        topic: 论文题目
        target_lang: 目标语言
        research_direction_id: 研究方向ID（可选，用于提高翻译相关性）

    Returns:
        翻译映射
    """
    return await contextual_translator.translate_keywords_with_context(
        keywords, topic, target_lang, research_direction_id
    )


# 测试代码
if __name__ == "__main__":
    import asyncio

    async def test():
        # 测试用例1：计算机代数系统
        topic1 = "CAS (computer algebra system) 的算法、实现及应用"
        keywords1 = ["CAS符号计算算法", "计算机代数系统实现", "符号积分算法"]

        print("=" * 80)
        print("测试用例1: 计算机代数系统")
        result1 = await translate_keywords_contextual(keywords1, topic1)
        print(f"结果: {result1}")

        # 测试用例2：符号执行
        topic2 = "符号执行技术在软件验证中的应用"
        keywords2 = ["符号执行算法", "路径探索策略", "约束求解优化"]

        print("\n" + "=" * 80)
        print("测试用例2: 符号执行")
        result2 = await translate_keywords_contextual(keywords2, topic2)
        print(f"结果: {result2}")

    asyncio.run(test())
