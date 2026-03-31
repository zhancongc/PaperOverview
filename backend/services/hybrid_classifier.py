"""
混合分类器：模式识别 + 大模型
- 先用模式识别强制判定混血题目
- 再用大模型智能分类其他题目
"""
import re
from services.llm_classifier import LLTopicClassifier, TopicType


class HybridTopicClassifier:
    """混合分类器：模式识别 + 大模型"""

    # ==================== 模式识别规则（强制判定） ====================

    # 规则1：应用型+实证型 → 实证型（基于XX模型的影响研究）
    EMPIRICAL_WITH_MODEL_PATTERN = re.compile(
        r'基于.+?(?:模型|方法|算法).+?(?:影响|效应|作用|关系|相关)'
    )

    # 规则2：评价型+实证型 → 实证型（成熟度/评价对...的影响）
    EMPIRICAL_WITH_MATURITY_PATTERN = re.compile(
        r'(?:成熟度|评价|评估).+?(?:对|与).+?(?:影响|效应|作用)'
    )

    # 规则3：评价型+应用型 → 评价型（评价与提升/优化）
    EVALUATION_WITH_IMPROVEMENT_PATTERN = re.compile(
        r'(?:成熟度|评价|评估).+?(?:与|及).+?(?:提升|优化|改进|路径)'
    )

    # 规则4：直接的X对Y影响 → 实证型
    DIRECT_INFLUENCE_PATTERN = re.compile(
        r'(.+?)对(.+?)(?:的影响|效应|作用|关系|相关性)'
    )

    def __init__(self):
        self.llm_classifier = LLTopicClassifier()

    async def classify(self, title: str):
        """
        混合分类：先模式识别，再大模型

        Args:
            title: 论文题目

        Returns:
            (题目类型, 判定理由, 判定详情)
        """
        # 第一步：模式识别（强制判定）
        pattern_result = self._pattern_classify(title)
        if pattern_result:
            return pattern_result

        # 第二步：大模型分类
        try:
            return await self.llm_classifier.classify(title)
        except Exception as e:
            print(f"[HybridClassifier] 大模型分类失败: {e}")
            # 使用规则引擎作为回退
            return self._fallback_classification(title)

    def _fallback_classification(self, title: str):
        """回退分类：使用简单规则"""
        title_lower = title.lower()

        if any(kw in title for kw in ['成熟度', '评价', '评估', '指标体系']):
            # 提取评价对象
            obj_match = re.search(r'(.+?)(?:成熟度|评价|评估|指标体系)', title)
            obj = obj_match.group(1) if obj_match else title.split('成熟度')[0].split('评价')[0].strip()
            return (
                TopicType.EVALUATION,
                '识别到评价型关键词（规则回退）',
                {
                    'method': 'fallback',
                    'confidence': 'low',
                    'key_elements': {
                        'research_object': obj,
                        'optimization_goal': None,
                        'methodology': None
                    }
                }
            )
        if any(kw in title for kw in ['基于', '优化', '改进', '应用']):
            # 提取应用型元素：基于XX方法的YY对象的ZZ优化
            elements = self._extract_application_elements(title)
            return (
                TopicType.APPLICATION,
                '识别到应用型关键词（规则回退）',
                {
                    'method': 'fallback',
                    'confidence': 'low',
                    'key_elements': elements
                }
            )
        if any(kw in title for kw in ['影响', '效应', '关系', '相关']):
            return (
                TopicType.EMPIRICAL,
                '识别到实证型关键词（规则回退）',
                {
                    'method': 'fallback',
                    'confidence': 'low',
                    'key_elements': {
                        'variables': {
                            'independent': None,
                            'dependent': None
                        }
                    }
                }
            )
        if any(kw in title for kw in ['理论', '机理', '综述', '进展']):
            return (
                TopicType.THEORETICAL,
                '识别到理论型关键词（规则回退）',
                {'method': 'fallback', 'confidence': 'low'}
            )

        return (
            TopicType.GENERAL,
            '无法识别，使用通用类型（规则回退）',
            {'method': 'fallback', 'confidence': 'low'}
        )

    def _pattern_classify(self, title: str):
        """
        模式识别分类（强制判定混血题目）

        Returns:
            如果匹配到模式，返回 (TopicType, 判定理由, 详情)
            否则返回 None
        """
        # 规则1：基于XX模型的影响研究 → 实证型
        if self.EMPIRICAL_WITH_MODEL_PATTERN.search(title):
            return (
                TopicType.EMPIRICAL,
                f'【模式识别】题目同时包含「基于XX模型」和「影响/效应」，判定为实证型（核心是检验影响关系，模型是工具）',
                {
                    'method': 'pattern',
                    'pattern': 'empirical_with_model',
                    'key_elements': {
                        'research_object': '研究对象',
                        'optimization_goal': '优化目标',
                        'methodology': '模型方法'
                    },
                    'variables': {
                        'independent': '模型方法',
                        'dependent': '影响'
                    }
                }
            )

        # 规则2：成熟度/评价对...的影响 → 实证型
        if self.EMPIRICAL_WITH_MATURITY_PATTERN.search(title):
            return (
                TopicType.EMPIRICAL,
                f'【模式识别】题目同时包含「成熟度/评价」和「对...的影响」，判定为实证型（核心是检验影响关系，成熟度是自变量）',
                {
                    'method': 'pattern',
                    'pattern': 'empirical_with_maturity',
                    'key_elements': {
                        'research_object': '研究对象',
                        'optimization_goal': '成熟度评价',
                        'methodology': '评价方法'
                    },
                    'variables': {
                        'independent': '成熟度',
                        'dependent': '研究对象'
                    }
                }
            )

        # 规则3：评价与提升/优化 → 评价型
        if self.EVALUATION_WITH_IMPROVEMENT_PATTERN.search(title):
            import re
            obj_match = re.search(r'(.+?)(?:成熟度|评价|评估|体系)', title)
            obj = obj_match.group(1) if obj_match else '研究对象'

            return (
                TopicType.EVALUATION,
                f'【模式识别】题目同时包含「评价」和「提升/优化」，判定为评价型（核心是构建评价体系，提升是应用延伸）',
                {
                    'method': 'pattern',
                    'pattern': 'evaluation_with_improvement',
                    'key_elements': {
                        'research_object': obj,
                        'optimization_goal': '提升优化',
                        'methodology': '评价方法'
                    }
                }
            )

        # 规则4：直接的X对Y影响 → 实证型
        match = self.DIRECT_INFLUENCE_PATTERN.search(title)
        if match:
            iv = match.group(1).strip()
            dv = match.group(2).strip()
            return (
                TopicType.EMPIRICAL,
                f'【模式识别】题目结构为「{iv}对{dv}的影响」，判定为实证型（核心是检验影响关系）',
                {
                    'method': 'pattern',
                    'pattern': 'direct_influence',
                    'key_elements': {
                        'research_object': iv,
                        'optimization_goal': dv,
                        'methodology': '分析方法'
                    },
                    'variables': {
                        'independent': iv,
                        'dependent': dv
                    }
                }
            )

        # 没有匹配到模式，返回 None 让大模型处理
        return None

    def _extract_application_elements(self, title: str) -> dict:
        """
        从应用型题目中提取关键元素

        支持格式：
        - 基于XX方法的YY对象的ZZ优化
        - XX在YY中的应用
        - 基于XX的YY优化研究

        Returns:
            {'research_object': str, 'optimization_goal': str, 'methodology': str}
        """
        import re

        # 默认值
        elements = {
            'research_object': None,
            'optimization_goal': None,
            'methodology': None
        }

        # 模式1：基于XX方法的YY对象的ZZ优化
        # 例如：基于QFD和FMEA的软件外包项目质量管理
        based_match = re.search(r'基于(.+?)的(.+?)(?:优化|改进|管理|控制|提升|研究)?$', title)
        if based_match:
            methodology_part = based_match.group(1).strip()
            rest = based_match.group(2).strip()

            # 方法论可能包含多个（用和、与、及连接）
            elements['methodology'] = methodology_part

            # 从剩余部分提取研究对象和优化目标
            # 通常是"对象的优化"格式
            goal_keywords = ['优化', '改进', '管理', '控制', '提升', '质量', '效率', '性能', '安全']
            for kw in goal_keywords:
                if kw in rest:
                    parts = rest.split(kw)
                    if len(parts) >= 2:
                        elements['research_object'] = parts[0].strip()
                        elements['optimization_goal'] = f"{kw}{parts[1]}" if len(parts) > 1 else kw
                        break
            else:
                # 没有找到优化关键词，整个都是研究对象
                elements['research_object'] = rest

            return elements

        # 模式2：XX在YY中的应用
        # 例如：QFD在软件外包质量管理中的应用
        apply_match = re.search(r'(.+?)在(.+?)中的应用', title)
        if apply_match:
            elements['methodology'] = apply_match.group(1).strip()
            elements['research_object'] = apply_match.group(2).strip()
            elements['optimization_goal'] = '应用'
            return elements

        # 模式3：只有关键词匹配，尝试简单提取
        if '基于' in title:
            after_based = title.split('基于', 1)[1].strip()
            # 找到第一个"的"之后的部分
            if '的' in after_based:
                parts = after_based.split('的', 1)
                elements['methodology'] = parts[0].strip()
                elements['research_object'] = parts[1].strip()
            else:
                elements['methodology'] = after_based

        return elements


# 为了兼容现有代码，导出混合分类器
class FrameworkGenerator:
    """综述框架生成器（使用混合分类器）"""

    def __init__(self):
        self.classifier = HybridTopicClassifier()

    async def generate_framework(self, title: str) -> dict:
        """
        根据题目类型生成综述框架

        Args:
            title: 论文题目

        Returns:
            综述框架
        """
        topic_type, reason, details = await self.classifier.classify(title)

        framework = {
            'title': title,
            'type': topic_type.value,
            'type_name': self._get_type_name(topic_type),
            'classification_reason': reason,
            'confidence': 'high' if details.get('method') == 'pattern' else details.get('confidence', 'medium'),
            'key_elements': details.get('key_elements', {}),
            'reasoning': details.get('reasoning', {}),
            'framework': None,
            'search_queries': []
        }

        # 根据类型生成框架
        if topic_type == TopicType.APPLICATION:
            framework['framework'] = self._application_framework(title, details.get('key_elements', {}))
            framework['search_queries'] = self._application_queries(title, details.get('key_elements', {}))
        elif topic_type == TopicType.EVALUATION:
            framework['framework'] = self._evaluation_framework(title, details.get('key_elements', {}))
            framework['search_queries'] = self._evaluation_queries(title, details.get('key_elements', {}))
        elif topic_type == TopicType.THEORETICAL:
            framework['framework'] = self._theoretical_framework(title)
            framework['search_queries'] = self._theoretical_queries(title)
        elif topic_type == TopicType.EMPIRICAL:
            framework['framework'] = self._empirical_framework(title, details.get('key_elements', {}))
            framework['search_queries'] = self._empirical_queries(title, details.get('key_elements', {}))
        else:
            framework['framework'] = self._general_framework(title)
            framework['search_queries'] = self._general_queries(title)

        return framework

    def _get_type_name(self, topic_type) -> str:
        """获取类型名称"""
        # 如果传入的是字符串值，直接映射
        if isinstance(topic_type, str):
            names = {
                "application": "应用型/解决方案型",
                "evaluation": "评价型/体系构建型",
                "theoretical": "理论型/研究型",
                "empirical": "实证型",
                "general": "通用型"
            }
            return names.get(topic_type, "未知类型")

        # 如果是枚举类型
        names = {
            TopicType.APPLICATION: "应用型/解决方案型",
            TopicType.EVALUATION: "评价型/体系构建型",
            TopicType.THEORETICAL: "理论型/研究型",
            TopicType.EMPIRICAL: "实证型",
            TopicType.GENERAL: "通用型"
        }
        return names.get(topic_type, "未知类型")

    # ==================== 框架生成方法（与 llm_classifier.py 相同） ====================

    def _application_framework(self, title: str, elements: dict) -> dict:
        """应用型综述框架 - 三圈交集"""
        return {
            'structure': '三圈交集式',
            'description': '证明「工具+场景+目标」三者结合的必要性和可行性',
            'sections': [
                {
                    'title': '研究对象分析',
                    'description': f'分析{elements.get("research_object", "研究对象")}的重要性和特殊性',
                    'key_points': ['发展现状', '特征分析', '面临的挑战']
                },
                {
                    'title': '优化目标现状',
                    'description': f'分析{elements.get("optimization_goal", "优化目标")}的现状与痛点',
                    'key_points': ['理论基础', '当前问题', '改进需求']
                },
                {
                    'title': '方法论应用',
                    'description': f'分析{elements.get("methodology", "方法论")}的应用可行性',
                    'key_points': ['理论框架', '相关应用', '优势局限']
                },
                {
                    'title': '研究缺口与机会',
                    'description': '识别三者结合的研究空白',
                    'key_points': ['现有不足', '创新点', '预期贡献']
                }
            ]
        }

    def _application_queries(self, title: str, elements: dict) -> list:
        """应用型检索查询"""
        obj = elements.get("research_object", "")
        goal = elements.get("optimization_goal", "")
        method = elements.get("methodology", "")

        queries = []
        if obj:
            queries.append({'query': f'{obj} 特点 挑战', 'section': '研究对象分析'})
        if goal:
            queries.append({'query': f'{goal} 现状 问题', 'section': '优化目标现状'})
        if method:
            queries.append({'query': f'{method} 应用 案例', 'section': '方法论应用'})

        return queries

    def _evaluation_framework(self, title: str, elements: dict) -> dict:
        """评价型综述框架 - 金字塔式"""
        obj = elements.get("research_object", "研究对象")

        return {
            'structure': '金字塔式',
            'description': '从理论基础到实践应用，层层递进证明评价体系的科学性',
            'sections': [
                {
                    'title': '评价理论基础',
                    'description': f'确立{obj}评价的理论依据',
                    'key_points': ['概念界定', '评价理论发展', '成熟度模型基础', '设计原则']
                },
                {
                    'title': '评价维度与指标',
                    'description': '梳理现有研究的评价维度和指标体系',
                    'key_points': ['主流维度', '关键指标', '权重方法', '维度关系']
                },
                {
                    'title': '评价方法与技术',
                    'description': '总结评价方法和技术手段',
                    'key_points': ['定性方法', '定量方法', '综合方法', '数据处理']
                },
                {
                    'title': '评价实践与应用',
                    'description': '分析评价体系的实践应用情况',
                    'key_points': ['应用案例', '效果分析', '问题改进', '趋势展望']
                },
                {
                    'title': '研究缺口',
                    'description': '识别现有评价体系的不足',
                    'key_points': ['理论薄弱', '维度缺失', '方法局限', '改进方向']
                }
            ]
        }

    def _evaluation_queries(self, title: str, elements: dict) -> list:
        """评价型检索查询"""
        import re
        obj_match = re.search(r'(.+?)(?:成熟度|评价|评估|体系)', title)
        obj = obj_match.group(1) if obj_match else (elements.get("research_object", title.split("成熟度")[0].split("评价")[0]))

        return [
            {'query': f'{obj} 评价 理论', 'section': '评价理论基础'},
            {'query': f'{obj} 成熟度 模型', 'section': '评价理论基础'},
            {'query': f'{obj} 评价 指标 维度', 'section': '评价维度与指标'},
            {'query': f'{obj} 评价 方法', 'section': '评价方法与技术'},
            {'query': f'{obj} 评价 实践', 'section': '评价实践与应用'}
        ]

    def _empirical_framework(self, title: str, elements: dict) -> dict:
        """实证型综述框架 - 问题-方案式"""
        vars_info = elements.get("variables", {})
        iv = vars_info.get("independent", "自变量")
        dv = vars_info.get("dependent", "因变量")

        return {
            'structure': '问题-方案式',
            'description': '围绕研究问题和假设，梳理相关实证研究',
            'sections': [
                {
                    'title': '研究背景与问题',
                    'description': '阐述研究背景和核心问题',
                    'key_points': [f'{iv}背景', f'{dv}挑战', '问题提出']
                },
                {
                    'title': f'{iv}的理论基础与测量',
                    'description': f'梳理{iv}的相关理论和测量方法',
                    'key_points': ['概念界定', '维度划分', '测量方法', '相关研究']
                },
                {
                    'title': f'{dv}的理论基础与测量',
                    'description': f'梳理{dv}的相关理论和测量方法',
                    'key_points': ['概念界定', '维度划分', '测量方法', '相关研究']
                },
                {
                    'title': f'{iv}对{dv}的影响机制',
                    'description': '总结实证研究的主要发现',
                    'key_points': ['直接影响', '中介机制', '调节效应', '结论对比']
                },
                {
                    'title': '研究不足与展望',
                    'description': '指出研究不足和未来方向',
                    'key_points': ['方法局限', '情境因素', '未来方向']
                }
            ]
        }

    def _empirical_queries(self, title: str, elements: dict) -> list:
        """实证型检索查询"""
        vars_info = elements.get("variables", {})
        iv = vars_info.get("independent", "")
        dv = vars_info.get("dependent", "")

        queries = []
        if iv and dv:
            queries.append({'query': f'{iv} 测量 量表', 'section': f'{iv}的理论基础与测量'})
            queries.append({'query': f'{dv} 测量 量表', 'section': f'{dv}的理论基础与测量'})
            queries.append({'query': f'{iv} {dv} 影响', 'section': '影响机制'})
            queries.append({'query': f'{iv} {dv} 中介 调节', 'section': '影响机制'})

        return queries

    def _theoretical_framework(self, title: str) -> dict:
        """理论型综述框架 - 溯源式"""
        return {
            'structure': '溯源式',
            'description': '从理论源头出发，梳理理论发展脉络',
            'sections': [
                {'title': '理论起源', 'description': '追溯理论起源', 'key_points': ['起源背景', '奠基研究', '概念界定']},
                {'title': '理论发展', 'description': '梳理发展历程', 'key_points': ['阶段划分', '理论突破', '代表研究']},
                {'title': '当前研究现状', 'description': '分析研究重点', 'key_points': ['研究热点', '主要学派', '争议问题']},
                {'title': '理论应用', 'description': '总结实践应用', 'key_points': ['应用领域', '应用效果', '理论验证']},
                {'title': '理论前沿与展望', 'description': '展望发展方向', 'key_points': ['前沿问题', '发展趋势', '未来方向']}
            ]
        }

    def _theoretical_queries(self, title: str) -> list:
        """理论型检索查询"""
        return [
            {'query': f'{title} 理论 起源', 'section': '理论起源'},
            {'query': f'{title} 理论 发展', 'section': '理论发展'},
            {'query': f'{title} 研究现状', 'section': '当前研究现状'},
            {'query': f'{title} 理论 应用', 'section': '理论应用'}
        ]

    def _general_framework(self, title: str) -> dict:
        """通用综述框架"""
        return {
            'structure': '通用结构',
            'description': '采用标准文献综述结构',
            'sections': [
                {'title': '引言', 'description': '介绍研究背景', 'key_points': ['研究背景', '研究意义', '综述目标']},
                {'title': '研究现状', 'description': '梳理研究现状', 'key_points': ['国内研究', '国外研究', '对比分析']},
                {'title': '主要问题与挑战', 'description': '总结问题挑战', 'key_points': ['技术问题', '管理问题', '研究挑战']},
                {'title': '发展趋势', 'description': '分析发展趋势', 'key_points': ['技术趋势', '应用趋势', '研究方向']}
            ]
        }

    def _general_queries(self, title: str) -> list:
        """通用检索查询"""
        return [
            {'query': f'{title} 研究现状', 'section': '研究现状'},
            {'query': f'{title} 综述', 'section': '研究现状'},
            {'query': f'{title} 发展趋势', 'section': '发展趋势'}
        ]
