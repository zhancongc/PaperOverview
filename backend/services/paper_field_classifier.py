"""
论文领域分类与智能匹配服务
解决"乱引用"问题 - 确保材料章节不引用医学论文等
"""
import re
import os
from typing import List, Dict, Optional, Set
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class FieldCategory:
    """领域分类枚举"""
    MATERIALS = "materials"          # 材料科学
    CHEMISTRY = "chemistry"          # 化学
    MEDICINE = "medicine"            # 医学
    COMPUTER_SCIENCE = "cs"          # 计算机科学
    ECONOMICS = "economics"          # 经济学
    MANAGEMENT = "management"        # 管理学
    SOCIOLOGY = "sociology"          # 社会学
    ENGINEERING = "engineering"      # 工程技术
    PHYSICS = "physics"              # 物理学
    BIOLOGY = "biology"              # 生物学
    GENERAL = "general"              # 通用/跨学科


class PaperFieldClassifier:
    """论文领域分类器"""

    # 领域关键词映射（基于期刊名、标题关键词、概念标签）
    FIELD_KEYWORDS = {
        FieldCategory.MATERIALS: {
            "journals": [
                "nature materials", "advanced materials", "materials today",
                "journal of materials chemistry", "acs applied materials",
                "materials science and engineering", "nanomaterials",
                "carbon", "composite materials", "ceramics"
            ],
            "keywords": [
                "材料", "合成", "制备", "表征", "纳米", "薄膜", "涂层",
                "composite", "synthesis", "fabrication", "characterization",
                "nanostructure", "thin film", "coating", "polymer",
                "陶瓷", "高分子", "复合材料", "纳米材料", "光催化",
                "photocatalytic", "titanium dioxide", "solvothermal",
                "microsphere", "adsorption"
            ],
            "concepts": [
                "materials science", "nanotechnology", "polymers and plastics",
                "ceramics and composites", "metals and alloys"
            ]
        },
        FieldCategory.CHEMISTRY: {
            "journals": [
                "journal of the american chemical society", "angewandte chemie",
                "chemical reviews", "chemical science", "analytical chemistry",
                "journal of chromatography", "electrochemistry"
            ],
            "keywords": [
                "化学", "催化", "电化学", "分析化学", "有机化学",
                "catalysis", "electrochemical", "chromatography",
                "oxidation", "reduction", "reaction mechanism"
            ],
            "concepts": [
                "chemistry", "catalysis", "chemical physics",
                "electrochemistry", "organic chemistry"
            ]
        },
        FieldCategory.MEDICINE: {
            "journals": [
                "new england journal of medicine", "the lancet", "jama",
                "nature medicine", "bmj", "journal of clinical medicine",
                "plos medicine", "bmc medicine"
            ],
            "keywords": [
                "医学", "临床", "病理", "诊断", "治疗", "患者", "疾病",
                "medical", "clinical", "pathology", "diagnosis", "therapy",
                "patient", "disease", "hospital", "healthcare",
                "药物", "药理", "临床试验"
            ],
            "concepts": [
                "medicine", "clinical medicine", "pathology", "pharmacology",
                "nursing", "health sciences"
            ]
        },
        FieldCategory.COMPUTER_SCIENCE: {
            "journals": [
                "ieee transactions on", "acm transactions on", "nature machine intelligence",
                "journal of machine learning research", "neural computation",
                "software", "algorithm", "database", "information systems"
            ],
            "keywords": [
                "算法", "数据结构", "软件", "编程", "机器学习", "深度学习",
                "algorithm", "data structure", "software", "programming",
                "machine learning", "deep learning", "neural network",
                "artificial intelligence", "computer vision"
            ],
            "concepts": [
                "computer science", "artificial intelligence", "machine learning",
                "theoretical computer science", "software engineering"
            ]
        },
        FieldCategory.ECONOMICS: {
            "journals": [
                "american economic review", "journal of political economy",
                "econometrica", "journal of finance", "review of financial studies",
                "journal of monetary economics"
            ],
            "keywords": [
                "经济", "金融", "投资", "股市", "市场", "货币政策",
                "economics", "finance", "investment", "stock market",
                "monetary policy", "fiscal policy", "gdp"
            ],
            "concepts": [
                "economics", "finance", "business", "management",
                "monetary economics", "financial economics"
            ]
        },
        FieldCategory.MANAGEMENT: {
            "journals": [
                "academy of management journal", "strategic management journal",
                "journal of management", "organization science",
                "harvard business review", "management science"
            ],
            "keywords": [
                "管理", "组织", "战略", "企业", "公司治理", "领导力",
                "management", "organization", "strategy", "corporate governance",
                "leadership", "human resource management"
            ],
            "concepts": [
                "management", "business", "organizational behavior",
                "strategic management", "human resource management"
            ]
        },
        FieldCategory.SOCIOLOGY: {
            "journals": [
                "american sociological review", "social forces", "sociology",
                "journal of personality and social psychology", "social networks"
            ],
            "keywords": [
                "社会", "社会网络", "社会关系", "社会结构", "社会影响",
                "society", "social network", "social relation", "social structure"
            ],
            "concepts": [
                "sociology", "social sciences", "social psychology",
                "anthropology", "political science"
            ]
        },
        FieldCategory.ENGINEERING: {
            "journals": [
                "ieee transactions on engineering", "engineering applications",
                "journal of engineering", "mechanical engineering"
            ],
            "keywords": [
                "工程", "机械", "电气", "土木", "工业",
                "engineering", "mechanical", "electrical", "civil", "industrial"
            ],
            "concepts": [
                "engineering", "mechanical engineering", "electrical engineering",
                "civil engineering", "industrial engineering"
            ]
        },
        FieldCategory.PHYSICS: {
            "journals": [
                "physical review", "physics letters", "nature physics",
                "journal of physics", "applied physics"
            ],
            "keywords": [
                "物理", "量子", "力学", "热力学", "电磁学",
                "physics", "quantum", "mechanics", "thermodynamics", "electromagnetism"
            ],
            "concepts": [
                "physics", "quantum mechanics", "thermodynamics", "optics", "acoustics"
            ]
        },
        FieldCategory.BIOLOGY: {
            "journals": [
                "nature", "science", "cell", "molecular cell", "genetics",
                "journal of biology", "bmc biology"
            ],
            "keywords": [
                "生物", "基因", "细胞", "分子", "蛋白质", "生态",
                "biology", "gene", "cell", "molecular", "protein", "ecology"
            ],
            "concepts": [
                "biology", "molecular biology", "genetics", "ecology",
                "evolutionary biology", "cell biology"
            ]
        }
    }

    def __init__(self):
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    def classify_paper(self, paper: Dict) -> tuple[str, float]:
        """
        分类论文领域

        Args:
            paper: 论文信息

        Returns:
            (领域类型, 置信度)
        """
        scores = {}

        title = paper.get("title", "").lower()
        abstract = (paper.get("abstract") or "").lower()
        venue_name = (paper.get("venue_name") or "").lower()
        concepts = [c.lower() if isinstance(c, str) else str(c).lower() for c in paper.get("concepts", [])]

        # 组合文本用于匹配
        combined_text = f"{title} {abstract} {venue_name}"

        # 对每个领域计算匹配分数
        for field, keywords_dict in self.FIELD_KEYWORDS.items():
            score = 0.0

            # 1. 期刊名匹配（权重最高：30分）
            for journal in keywords_dict.get("journals", []):
                if journal in venue_name:
                    score += 30
                    break  # 期刊名只计算一次

            # 2. 标题关键词匹配（权重：20分/词）
            for kw in keywords_dict.get("keywords", []):
                if kw in title:
                    score += 20

            # 3. 摘要关键词匹配（权重：5分/词）
            for kw in keywords_dict.get("keywords", []):
                if kw in abstract:
                    score += 5

            # 4. 概念标签匹配（权重：10分/标签）
            for concept in concepts:
                for field_concept in keywords_dict.get("concepts", []):
                    if field_concept in concept:
                        score += 10
                        break

            scores[field] = score

        # 找出得分最高的领域
        if not scores or max(scores.values()) == 0:
            return FieldCategory.GENERAL, 0.0

        best_field = max(scores, key=scores.get)
        best_score = scores[best_field]

        # 计算置信度（0-1）
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.0

        return best_field, confidence

    async def classify_paper_with_llm(self, paper: Dict) -> tuple[str, float]:
        """
        使用LLM分类论文领域（更准确但较慢）

        Args:
            paper: 论文信息

        Returns:
            (领域类型, 置信度)
        """
        if not self.client:
            return self.classify_paper(paper)

        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        venue = paper.get("venue_name", "")

        prompt = f"""请判断以下论文属于哪个学科领域。

论文标题：{title}
期刊/会议：{venue}
摘要：{abstract[:500] if abstract else '无'}

请从以下领域中选择最合适的一个：
1. materials - 材料科学（合成、制备、表征、纳米材料、陶瓷、高分子等）
2. chemistry - 化学（催化、电化学、分析化学、有机化学等）
3. medicine - 医学（临床、病理、诊断、治疗、药物等）
4. cs - 计算机科学（算法、软件、机器学习、人工智能等）
5. economics - 经济学（经济、金融、投资、市场等）
6. management - 管理学（企业管理、组织、战略等）
7. sociology - 社会学（社会关系、社会结构、社会网络等）
8. engineering - 工程技术（机械、电气、土木等）
9. physics - 物理学（量子、力学、热力学等）
10. biology - 生物学（基因、细胞、生态等）

请只返回领域名称（如 materials、chemistry 等），不要有其他内容。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个学术文献分类专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )

            result = response.choices[0].message.content.strip().lower()

            # 验证返回的领域是否有效
            valid_fields = [f for f in dir(FieldCategory) if not f.startswith('_')]
            if result in valid_fields:
                return result, 0.9  # LLM分类给予较高置信度
            else:
                # LLM返回无效，使用规则分类
                return self.classify_paper(paper)

        except Exception as e:
            print(f"[FieldClassifier] LLM分类失败: {e}，使用规则分类")
            return self.classify_paper(paper)

    def batch_classify_papers(self, papers: List[Dict], use_llm: bool = False) -> List[Dict]:
        """
        批量分类论文

        Args:
            papers: 论文列表
            use_llm: 是否使用LLM分类（更准确但较慢）

        Returns:
            添加了field字段的论文列表
        """
        result = []
        for paper in papers:
            if use_llm:
                # 异步分类需要在async上下文中调用
                field, confidence = self.classify_paper(paper)
            else:
                field, confidence = self.classify_paper(paper)

            paper_copy = paper.copy()
            paper_copy['field'] = field
            paper_copy['field_confidence'] = confidence
            result.append(paper_copy)

        return result


class SectionFieldMatcher:
    """章节与领域匹配器"""

    # 章节到领域的映射
    SECTION_FIELD_MAPPING = {
        # 材料制备相关章节
        "材料制备": [FieldCategory.MATERIALS, FieldCategory.CHEMISTRY, FieldCategory.ENGINEERING],
        "制备方法": [FieldCategory.MATERIALS, FieldCategory.CHEMISTRY],
        "合成": [FieldCategory.CHEMISTRY, FieldCategory.MATERIALS],
        "表征": [FieldCategory.MATERIALS, FieldCategory.PHYSICS, FieldCategory.CHEMISTRY],

        # 性能测试相关章节
        "性能测试": [FieldCategory.MATERIALS, FieldCategory.ENGINEERING, FieldCategory.PHYSICS],
        "光催化性能": [FieldCategory.MATERIALS, FieldCategory.CHEMISTRY],
        "电化学性能": [FieldCategory.CHEMISTRY, FieldCategory.MATERIALS],

        # 应用相关章节
        "应用": [FieldCategory.MATERIALS, FieldCategory.ENGINEERING, FieldCategory.CHEMISTRY],
        "环境应用": [FieldCategory.MATERIALS, FieldCategory.CHEMISTRY, FieldCategory.ENGINEERING],

        # 理论相关章节
        "机理": [FieldCategory.PHYSICS, FieldCategory.CHEMISTRY, FieldCategory.MATERIALS],
        "理论": [FieldCategory.PHYSICS, FieldCategory.CHEMISTRY],
        "模拟": [FieldCategory.COMPUTER_SCIENCE, FieldCategory.PHYSICS],

        # 管理相关章节
        "风险管理": [FieldCategory.MANAGEMENT, FieldCategory.ECONOMICS, FieldCategory.ENGINEERING],
        "质量管理": [FieldCategory.MANAGEMENT, FieldCategory.ENGINEERING],
        "项目管理": [FieldCategory.MANAGEMENT, FieldCategory.ECONOMICS],

        # 经济相关章节
        "经济分析": [FieldCategory.ECONOMICS, FieldCategory.MANAGEMENT],
        "成本分析": [FieldCategory.ECONOMICS, FieldCategory.MANAGEMENT],

        # 社会相关章节
        "社会影响": [FieldCategory.SOCIOLOGY, FieldCategory.ECONOMICS],
        "政策分析": [FieldCategory.SOCIOLOGY, FieldCategory.ECONOMICS, FieldCategory.MANAGEMENT],

        # 技术相关章节
        "算法": [FieldCategory.COMPUTER_SCIENCE],
        "系统设计": [FieldCategory.COMPUTER_SCIENCE, FieldCategory.ENGINEERING],
        "数据": [FieldCategory.COMPUTER_SCIENCE],

        # 通用章节
        "引言": [FieldCategory.GENERAL],
        "结论": [FieldCategory.GENERAL],
        "综述": [FieldCategory.GENERAL],
    }

    @classmethod
    def get_allowed_fields_for_section(cls, section_name: str) -> List[str]:
        """
        获取章节允许的领域列表

        Args:
            section_name: 章节名称

        Returns:
            允许的领域列表
        """
        # 模糊匹配章节名
        for section_key, allowed_fields in cls.SECTION_FIELD_MAPPING.items():
            if section_key in section_name:
                return allowed_fields

        # 默认返回所有领域（不过滤）
        return [FieldCategory.GENERAL]

    @classmethod
    def is_paper_allowed_for_section(cls, paper: Dict, section_name: str) -> tuple[bool, str]:
        """
        判断论文是否允许用于某个章节

        Args:
            paper: 论文信息（需包含field字段）
            section_name: 章节名称

        Returns:
            (是否允许, 原因说明)
        """
        paper_field = paper.get("field", FieldCategory.GENERAL)
        allowed_fields = cls.get_allowed_fields_for_section(section_name)

        # 如果允许所有领域，不过滤
        if FieldCategory.GENERAL in allowed_fields and len(allowed_fields) == 1:
            return True, "通用章节，允许所有领域"

        # 检查论文领域是否在允许列表中
        if paper_field in allowed_fields:
            return True, f"领域匹配: {paper_field}"

        # 不匹配
        return False, f"领域不匹配: 论文属于{paper_field}，但章节{section_name}要求{allowed_fields}"

    @classmethod
    def filter_papers_by_section(cls, papers: List[Dict], section_name: str) -> tuple[List[Dict], List[Dict]]:
        """
        根据章节过滤论文

        Args:
            papers: 论文列表
            section_name: 章节名称

        Returns:
            (允许的论文列表, 被过滤的论文列表)
        """
        allowed = []
        filtered = []

        for paper in papers:
            is_allowed, reason = cls.is_paper_allowed_for_section(paper, section_name)

            if is_allowed:
                allowed.append(paper)
            else:
                paper_copy = paper.copy()
                paper_copy['_filter_reason'] = reason
                filtered.append(paper_copy)

        return allowed, filtered


class EnhancedPaperFilterService:
    """增强的论文过滤服务（支持领域过滤）"""

    def __init__(self):
        self.field_classifier = PaperFieldClassifier()

    def filter_and_sort_with_field(
        self,
        papers: List[Dict],
        section_name: str = None,
        target_count: int = 50,
        recent_years_ratio: float = 0.5,
        english_ratio: float = 0.3,
        topic_keywords: List[str] | None = None,
        enable_field_filter: bool = True,
        use_llm_classification: bool = False
    ) -> tuple[List[Dict], Dict]:
        """
        筛选并排序论文（支持领域过滤）

        Args:
            papers: 原始论文列表
            section_name: 章节名称（用于领域过滤）
            target_count: 目标数量
            recent_years_ratio: 近5年占比要求
            english_ratio: 英文文献占比要求
            topic_keywords: 题目关键词
            enable_field_filter: 是否启用领域过滤
            use_llm_classification: 是否使用LLM分类

        Returns:
            (筛选后的论文列表, 过滤统计信息)
        """
        if not papers:
            return [], {}

        stats = {
            "total_input": len(papers),
            "field_filtered": 0,
            "field_filter_details": []
        }

        # 1. 领域分类
        classified_papers = self.field_classifier.batch_classify_papers(
            papers, use_llm=use_llm_classification
        )

        # 2. 领域过滤（如果启用）
        if enable_field_filter and section_name:
            allowed_papers, filtered_papers = SectionFieldMatcher.filter_papers_by_section(
                classified_papers, section_name
            )

            stats["field_filtered"] = len(filtered_papers)
            stats["field_filter_details"] = [
                {"paper_id": p.get("id", "unknown"), "title": p.get("title", ""), "reason": p.get("_filter_reason", "")}
                for p in filtered_papers[:10]  # 只记录前10个
            ]

            if filtered_papers:
                print(f"[EnhancedFilter] 章节'{section_name}'过滤了{len(filtered_papers)}篇不相关论文")
                for p in filtered_papers[:3]:
                    print(f"  - {p.get('title', '')[:50]}... ({p.get('_filter_reason', '')})")

            papers_to_sort = allowed_papers
        else:
            papers_to_sort = classified_papers

        # 3. 相关性评分和排序
        scored_papers = []
        for paper in papers_to_sort:
            score = self._calculate_enhanced_relevance_score(paper, topic_keywords)
            scored_papers.append({**paper, '_relevance_score': score})

        scored_papers.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)

        # 4. 按年份和语言筛选
        current_year = datetime.now().year
        recent_threshold = current_year - 5

        recent_papers = [p for p in scored_papers if p.get("year") is not None and p.get("year") >= recent_threshold]
        old_papers = [p for p in scored_papers if p.get("year") is not None and p.get("year") < recent_threshold]

        english_papers = [p for p in scored_papers if p.get("is_english", False)]
        non_english_papers = [p for p in scored_papers if not p.get("is_english", False)]

        recent_needed = int(target_count * recent_years_ratio)
        english_needed = int(target_count * english_ratio)

        selected = set()
        result = []
        english_count = 0

        # 优先选择：近5年 + 英文
        for paper in recent_papers:
            if paper.get("is_english") and len(result) < target_count and english_count < english_needed:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)
                    english_count += 1

        # 补充：近5年 + 非英文
        for paper in recent_papers:
            if not paper.get("is_english") and len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 补充：5年前 + 英文
        for paper in old_papers:
            if paper.get("is_english") and len(result) < target_count and english_count < english_needed:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)
                    english_count += 1

        # 补充：5年前 + 非英文
        for paper in old_papers:
            if not paper.get("is_english") and len(result) < target_count:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)

        # 如果不足，从所有论文中补充
        if len(result) < target_count:
            for paper in scored_papers:
                paper_id = paper.get("id")
                if paper_id not in selected:
                    selected.add(paper_id)
                    result.append(paper)
                    if len(result) >= target_count:
                        break

        # 转换relevance_score
        for paper in result:
            if '_relevance_score' in paper:
                paper['relevance_score'] = paper.pop('_relevance_score')

        stats["total_output"] = len(result)
        stats["fields_in_output"] = self._count_fields(result)

        return result[:target_count], stats

    def _calculate_enhanced_relevance_score(self, paper: Dict, topic_keywords: List[str] | None) -> float:
        """
        计算增强的相关性评分

        Args:
            paper: 论文信息
            topic_keywords: 主题关键词

        Returns:
            相关性评分（0-100）
        """
        score = 0.0

        # 基础分：被引量（归一化到 0-30 分）
        citations = paper.get("cited_by_count", 0)
        score += min(citations / 10, 30)

        # 关键词匹配
        if topic_keywords:
            title_lower = paper.get("title", "").lower()
            abstract_lower = paper.get("abstract", "").lower()

            for kw in topic_keywords:
                if kw is None:
                    continue
                kw_lower = kw.lower()
                if kw_lower in title_lower:
                    score += 15
                elif kw_lower in abstract_lower:
                    score += 5

            # 概念标签匹配
            concepts = paper.get("concepts", [])
            for concept in concepts:
                if concept is None:
                    continue
                concept_lower = concept.lower()
                for kw in topic_keywords:
                    if kw is not None and kw.lower() in concept_lower:
                        score += 3
                        break

        # 新近论文加分
        current_year = datetime.now().year
        paper_year = paper.get("year")
        if paper_year is not None and paper_year >= current_year - 5:
            score += 10
        elif paper_year is not None and paper_year >= current_year - 10:
            score += 5

        # 英文论文加分
        if paper.get("is_english", False):
            score += 5

        # 领域置信度加分
        field_confidence = paper.get("field_confidence", 0)
        score += field_confidence * 10

        return min(score, 100)

    def _count_fields(self, papers: List[Dict]) -> Dict[str, int]:
        """统计各领域的论文数量"""
        field_counts = {}
        for paper in papers:
            field = paper.get("field", FieldCategory.GENERAL)
            field_counts[field] = field_counts.get(field, 0) + 1
        return field_counts


# 导出接口
def classify_papers(papers: List[Dict], use_llm: bool = False) -> List[Dict]:
    """
    批量分类论文领域

    Args:
        papers: 论文列表
        use_llm: 是否使用LLM分类

    Returns:
        添加了field字段的论文列表
    """
    classifier = PaperFieldClassifier()
    return classifier.batch_classify_papers(papers, use_llm=use_llm)


def filter_papers_for_section(papers: List[Dict], section_name: str) -> tuple[List[Dict], List[Dict]]:
    """
    根据章节过滤论文

    Args:
        papers: 论文列表（需包含field字段）
        section_name: 章节名称

    Returns:
        (允许的论文, 被过滤的论文)
    """
    return SectionFieldMatcher.filter_papers_by_section(papers, section_name)
