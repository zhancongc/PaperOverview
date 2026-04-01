"""
混合分类器：模式识别 + 大模型验证
- 先用模式识别提取关键词
- 再用大模型判断是否合理，不合理则优化
"""
import re
import os
from enum import Enum
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class TopicType(Enum):
    """题目类型枚举"""
    APPLICATION = "application"  # 应用型/解决方案型 - 三圈交集
    EVALUATION = "evaluation"    # 评价型/体系构建型 - 金字塔式
    THEORETICAL = "theoretical"  # 理论型/研究型 - 溯源式
    EMPIRICAL = "empirical"      # 实证型 - 问题-方案式
    GENERAL = "general"          # 通用型


class HybridTopicClassifier:
    """基于规则的题目分类器"""

    # ==================== 模式识别规则（强制判定混血题目） ====================

    # 规则0：基于XXX的实证研究 → 实证型（优先级最高）
    EMPIRICAL_STUDY_PATTERN = re.compile(
        r'基于(.+?)(?:的)?(?:实证研究|实证分析|实证检验|实证探讨)'
    )

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
        self.client = None
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            print("[HybridClassifier] DEEPSEEK_API_KEY not configured, LLM validation disabled")

    def classify(self, title: str):
        """
        混合分类：使用规则引擎

        Args:
            title: 论文题目

        Returns:
            (题目类型, 判定理由, 判定详情)
        """
        # 使用规则引擎进行分类和关键元素提取
        return self._rule_based_classify(title)

    async def classify(self, title: str, enable_llm_validation: bool = False):
        """
        混合分类：规则提取 + LLM验证优化

        Args:
            title: 论文题目

        Returns:
            (题目类型, 判定理由, 判定详情)
        """
        # 第一步：规则引擎提取
        topic_type, reason, details = self._rule_based_classify(title)

        # 第二步：LLM验证和优化（如果启用）
        if enable_llm_validation and self.client and details.get('key_elements', {}).get('research_object'):
            try:
                optimized = await self._validate_and_optimize_keywords(title, details)
                if optimized:
                    # 合并优化结果
                    details['key_elements'].update(optimized.get('key_elements', {}))
                    details['llm_validated'] = True
                    details['llm_optimized'] = True
                    reason += "（已通过LLM验证并优化）"
                else:
                    # 没有返回优化建议，说明验证通过
                    details['llm_validated'] = True
                    reason += "（已通过LLM验证）"
            except Exception as e:
                print(f"[HybridClassifier] LLM验证失败: {e}，使用规则提取结果")

        return topic_type, reason, details

    async def _validate_and_optimize_keywords(self, title: str, details: dict) -> dict:
        """
        让LLM验证提取的关键词是否合理，不合理则给出优化建议

        Args:
            title: 论文题目
            details: 规则提取的详情

        Returns:
            优化后的关键元素，如果验证通过返回None
        """
        elements = details.get('key_elements', {})
        obj = elements.get('research_object', '')
        goal = elements.get('optimization_goal', '')
        method = elements.get('methodology', '')

        # 简化prompt，降低token消耗
        prompt = f"""题目：{title}

提取结果：
- 研究对象：{obj}
- 优化目标：{goal}
- 方法论：{method}

判断以上提取是否准确。如果不准确，请说明应该怎么改。

格式要求：
- 如果准确，只回答"准确"
- 如果不准确，按格式回答："研究对象应该改为XXX；优化目标应该改为YYY；方法论应该改为ZZZ"
"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个学术研究助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )

            result = response.choices[0].message.content.strip()
            print(f"[HybridClassifier] LLM验证结果: {result}")

            # 判断是否准确
            if result == "准确":
                return None

            # 解析LLM的修改建议
            optimized = {}

            if "研究对象应该改为" in result:
                obj_match = re.search(r'研究对象应该改为(.+?)(?:；|$)', result)
                if obj_match:
                    optimized['research_object'] = obj_match.group(1).strip()
                    print(f"[HybridClassifier] 优化研究对象: {obj_match.group(1)}")

            if "优化目标应该改为" in result:
                goal_match = re.search(r'优化目标应该改为(.+?)(?:；|$)', result)
                if goal_match:
                    optimized['optimization_goal'] = goal_match.group(1).strip()
                    print(f"[HybridClassifier] 优化优化目标: {goal_match.group(1)}")

            if "方法论应该改为" in result:
                method_match = re.search(r'方法论应该改为(.+?)(?:；|$)', result)
                if method_match:
                    optimized['methodology'] = method_match.group(1).strip()
                    print(f"[HybridClassifier] 优化方法论: {method_match.group(1)}")

            return {'key_elements': optimized} if optimized else None

        except Exception as e:
            print(f"[HybridClassifier] LLM验证出错: {e}，使用规则提取结果")
            import traceback
            traceback.print_exc()
            return None

    def _rule_based_classify(self, title: str) -> tuple:
        """
        基于规则的分类器

        Args:
            title: 论文题目

        Returns:
            (题目类型, 判定理由, 判定详情)
        """
        # 第一步：模式识别（强制判定混血题目）
        pattern_result = self._pattern_classify(title)
        if pattern_result:
            return pattern_result

        # 第二步：基于关键词的分类
        title_lower = title.lower()

        # 评价型关键词（优先检查）
        if any(kw in title for kw in ['成熟度', '评价', '评估', '指标体系']):
            # 提取评价对象
            obj_match = re.search(r'(.+?)(?:成熟度|评价|评估|指标体系)', title)
            obj = obj_match.group(1) if obj_match else title.split('成熟度')[0].split('评价')[0].strip()
            return (
                TopicType.EVALUATION,
                '识别到评价型关键词',
                {
                    'method': 'rule',
                    'confidence': 'high',
                    'key_elements': {
                        'research_object': obj,
                        'optimization_goal': None,
                        'methodology': None
                    }
                }
            )

        # 应用型关键词
        if any(kw in title for kw in ['基于', '优化', '改进', '应用']):
            # 提取应用型元素
            elements = self._extract_application_elements(title)
            return (
                TopicType.APPLICATION,
                '识别到应用型关键词',
                {
                    'method': 'rule',
                    'confidence': 'high',
                    'key_elements': elements
                }
            )

        # 实证型关键词
        if any(kw in title for kw in ['影响', '效应', '关系', '相关']):
            # 提取自变量和因变量
            influence_match = re.search(r'(.+?)对(.+?)(?:的影响|效应|作用|关系|相关性)', title)
            if influence_match:
                iv = influence_match.group(1).strip()
                dv = influence_match.group(2).strip()
                return (
                    TopicType.EMPIRICAL,
                    '识别到实证型关键词',
                    {
                        'method': 'rule',
                        'confidence': 'high',
                        'key_elements': {
                            'research_object': iv,
                            'optimization_goal': dv,
                            'methodology': None
                        },
                        'variables': {
                            'independent': iv,
                            'dependent': dv
                        }
                    }
                )

        # 理论型关键词
        if any(kw in title for kw in ['理论', '机理', '综述', '进展', '演进']):
            return (
                TopicType.THEORETICAL,
                '识别到理论型关键词',
                {
                    'method': 'rule',
                    'confidence': 'medium',
                    'key_elements': {
                        'research_object': None,
                        'optimization_goal': None,
                        'methodology': None
                    }
                }
            )

        # 默认返回通用型
        return (
            TopicType.GENERAL,
            '无法明确归类，使用通用类型',
            {
                'method': 'rule',
                'confidence': 'low',
                'key_elements': {
                    'research_object': None,
                    'optimization_goal': None,
                    'methodology': None
                }
            }
        )

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
        # 规则0：基于XXX的实证研究 → 实证型（优先级最高）
        if self.EMPIRICAL_STUDY_PATTERN.search(title):
            # 提取理论/视角/方法
            import re
            theory_match = self.EMPIRICAL_STUDY_PATTERN.search(title)
            theory = theory_match.group(1) if theory_match else '理论框架'
            # 清理理论名称，去掉"的"、"学"等后缀
            theory = theory.rstrip('的学').rstrip('的').strip()

            # 提取研究对象（在"——"之前的部分）
            research_object = title.split('——')[0].strip() if '——' in title else title

            # 尝试提取自变量和因变量（格式：X、Y与Z——基于...）
            variables = {'independent': None, 'dependent': None}
            if '与' in research_object and '——' in title:
                # 检查是否是"X、Y与Z"格式
                parts = research_object.split('与')
                if len(parts) >= 2:
                    # 自变量是"与"之前的部分（可能有多个，用顿号分隔）
                    independent = parts[0].strip()
                    # 因变量是"与"之后的部分
                    dependent = parts[1].strip()
                    variables = {
                        'independent': independent,
                        'dependent': dependent
                    }

            return (
                TopicType.EMPIRICAL,
                f'【模式识别】题目包含「基于{theory}的实证研究」，判定为实证型（核心是检验变量间的影响关系）',
                {
                    'method': 'pattern',
                    'pattern': 'empirical_study',
                    'key_elements': {
                        'research_object': research_object,
                        'optimization_goal': f'探究变量间的影响关系（基于{theory}理论）',
                        'methodology': f'基于{theory}的实证研究方法',
                        'variables': variables
                    },
                    'variables': variables
                }
            )

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
        # 支持以"研究"结尾的题目
        based_match = re.search(r'基于(.+?)的(.+?)(?:研究|优化|改进|管理|控制|提升)?$', title)
        if based_match:
            methodology_part = based_match.group(1).strip()
            rest = based_match.group(2).strip()

            # 方法论可能包含多个（用和、与、及连接）
            elements['methodology'] = methodology_part

            # 从剩余部分提取研究对象和优化目标
            # 优先匹配组合词（如"质量管理"、"流程优化"等）
            compound_patterns = [
                ('质量管理', '质量'),
                ('流程管理', '流程'),
                ('质量控制', '控制'),
                ('流程优化', '优化'),
                ('持续交付', '交付'),
                ('效率提升', '效率'),
                ('性能优化', '性能'),
                ('安全改进', '安全'),
            ]

            matched = False
            for compound, single in compound_patterns:
                if compound in rest:
                    parts = rest.split(compound)
                    if len(parts) >= 1:
                        elements['research_object'] = parts[0].strip()
                        elements['optimization_goal'] = compound
                        matched = True
                        break

            if not matched:
                # 如果没有匹配到组合词，尝试单个关键词
                goal_keywords = ['优化', '改进', '管理', '控制', '提升', '效率', '性能', '安全']
                for kw in goal_keywords:
                    if kw in rest:
                        parts = rest.split(kw)
                        if len(parts) >= 1:
                            elements['research_object'] = parts[0].strip()
                            elements['optimization_goal'] = kw
                            matched = True
                        break

            if not matched:
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

    async def generate_framework(self, title: str, enable_llm_validation: bool = False) -> dict:
        """
        根据题目类型生成综述框架

        Args:
            title: 论文题目
            enable_llm_validation: 是否启用LLM验证（默认False）

        Returns:
            综述框架
        """
        topic_type, reason, details = await self.classifier.classify(title, enable_llm_validation)

        framework = {
            'title': title,
            'type': topic_type.value,
            'type_name': self._get_type_name(topic_type),
            'classification_reason': reason,
            'confidence': 'high' if details.get('method') == 'pattern' else details.get('confidence', 'medium'),
            'key_elements': details.get('key_elements', {}),
            'reasoning': details.get('reasoning', {}),
            'llm_validated': details.get('llm_validated', False),
            'llm_optimized': details.get('llm_optimized', False),
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
        """应用型检索查询 - 生成更精准的搜索关键词"""
        obj = elements.get("research_object", "")
        goal = elements.get("optimization_goal", "")
        method = elements.get("methodology", "")

        queries = []

        # 判断研究对象类型，生成相应的关键词
        obj_type = self._classify_object_type(obj)

        # 通用关键词列表（不单独搜索）
        generic_keywords = {'研究进展', '问题', '应用', '质量改进', '优化', '改进', '分析', '方法', '技术'}

        # 1. 研究对象分析 - 根据对象类型生成不同的关键词
        if obj:
            # 只搜索核心关键词，不添加通用词
            queries.append({
                'query': obj,
                'section': '研究对象分析',
                'lang': 'zh'
            })

            # 根据对象类型添加特定关键词
            obj_keywords = self._get_object_analysis_keywords(obj, obj_type)
            if obj_keywords:
                queries.append({
                    'query': f'{obj} {obj_keywords}',
                    'section': '研究对象分析',
                    'lang': 'zh'
                })

        # 2. 优化目标现状 - 只组合核心关键词
        if obj and goal:
            # 检查 goal 是否为通用词
            if goal not in generic_keywords:
                queries.append({
                    'query': f'{obj} {goal}',
                    'section': '优化目标现状',
                    'lang': 'zh'
                })
            else:
                # goal 是通用词，只搜索 obj
                queries.append({
                    'query': obj,
                    'section': '优化目标现状',
                    'lang': 'zh'
                })

        # 3. 方法论应用 - 根据方法类型处理
        if method and obj:
            method_clean = self._clean_methodology_name(method)

            # 检查方法是否为英文缩写
            if self._is_english_acronym(method_clean):
                # 英文缩写（如 QFD、FMEA）：使用组合搜索
                # 传递两个关键词，让 AMiner Pro 同时使用 title + keyword
                queries.append({
                    'query': f'{method_clean} {obj}',
                    'section': '方法论应用',
                    'lang': 'zh',
                    'keywords': [obj, method_clean],  # 传递两个关键词
                    'search_mode': 'title_keyword'  # 标识使用组合搜索
                })
            else:
                # 中文方法名
                app_keywords = self._get_application_keywords(obj_type)
                if app_keywords and app_keywords not in generic_keywords:
                    queries.append({
                        'query': f'{method_clean} {obj} {app_keywords}',
                        'section': '方法论应用',
                        'lang': 'zh'
                    })
                else:
                    queries.append({
                        'query': f'{method_clean} {obj}',
                        'section': '方法论应用',
                        'lang': 'zh'
                    })

        return queries

    def _is_english_acronym(self, text: str) -> bool:
        """判断是否为英文缩写（全大写字母）"""
        # 去除空格和括号
        clean = text.replace(' ', '').replace('(', '').replace(')', '')
        # 如果全是字母且长度较短（2-6个字符），可能是英文缩写
        return bool(clean) and clean.isalpha() and clean.isupper() and 2 <= len(clean) <= 6

    def _classify_object_type(self, obj: str) -> str:
        """
        判断研究对象类型

        Returns:
            'software' | 'hardware' | 'process' | 'general'
        """
        software_keywords = ['软件', '软件系统', '平台', '算法', '数据', '网络', '智能座舱', '代码', 'APP', '系统', '信息化']
        process_keywords = ['流程', '工艺', '过程', '管理', '服务', '交付', '供应链', '生产']

        obj_lower = obj.lower()
        for kw in software_keywords:
            if kw in obj:
                return 'software'

        for kw in process_keywords:
            if kw in obj:
                return 'process'

        return 'hardware'  # 默认为硬件/产品

    def _get_object_analysis_keywords(self, obj: str, obj_type: str) -> str:
        """根据对象类型返回分析关键词"""
        if obj_type == 'software':
            return '开发 质量 测试 难点'
        elif obj_type == 'process':
            return '流程 工艺 瓶颈 问题'
        else:  # hardware
            return '制造工艺 质量特性 质量控制难点'

    def _get_application_keywords(self, obj_type: str) -> str:
        """根据对象类型返回应用关键词"""
        if obj_type == 'software':
            return '应用 开发改进'
        elif obj_type == 'process':
            return '应用 优化改进'
        else:  # hardware
            return '应用 质量改进'

    def _clean_methodology_name(self, method: str) -> str:
        """
        清理方法论名称，去掉冗长的全称和括号

        例如：
        - QFD（质量功能展开） -> QFD
        - PFMEA（过程失效模式与影响分析） -> PFMEA
        - QFD和PFMEA -> QFD PFMEA
        """
        import re

        # 去掉括号及其内容
        method = re.sub(r'\([^)]+\)', '', method)

        # 将连接词替换为空格
        method = re.sub(r'[和与及]', ' ', method)

        # 去除多余空格
        method = ' '.join(method.split())

        return method

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
        """
        实证型检索查询 - 根据题目语言自动选择搜索策略

        策略说明：
        - 中文题目：生成中文搜索查询（用于 AMiner）
        - 英文题目：生成英文搜索查询（用于 OpenAlex）
        - 混合题目：同时生成中英文查询
        """
        vars_info = elements.get("variables", {})
        iv = vars_info.get("independent", "")
        dv = vars_info.get("dependent", "")

        queries = []

        # 检测题目语言
        is_chinese_title = self._contains_chinese(title)

        if iv and dv:
            # 拆分自变量中的复合关键词（处理顿号、逗号等分隔符）
            iv_keywords = self._split_compound_keyword(iv)
            dv_keywords = self._split_compound_keyword(dv)

            if is_chinese_title:
                # ========== 中文题目：生成中文搜索查询 ==========
                queries = self._generate_chinese_empirical_queries(
                    title, iv_keywords, dv_keywords, vars_info
                )
            else:
                # ========== 英文题目：生成英文搜索查询 ==========
                queries = self._generate_english_empirical_queries(
                    title, iv_keywords, dv_keywords, vars_info
                )

        return queries

    def _contains_chinese(self, text: str) -> bool:
        """检测文本是否包含中文"""
        return bool(text and any('\u4e00' <= char <= '\u9fff' for char in text))

    def _generate_chinese_empirical_queries(
        self, title: str, iv_keywords: list, dv_keywords: list, vars_info: dict
    ) -> list:
        """
        为中文实证型题目生成中文搜索查询

        策略：
        1. 核心关键词单独搜索（避免使用通用词如"测量"、"指标"）
        2. 交叉搜索：自变量 x 因变量组合
        3. 理论搜索：基于的理论/视角
        """
        queries = []

        # 通用关键词列表（不单独搜索）
        generic_keywords = {
            '测量', '指标', '评价', '分析', '研究', '方法', '影响', '效应',
            '对', '的', '与', '和', '及', '基于', '关系', '相关性', '作用'
        }

        # ========== 第一步：自变量相关查询 ==========
        for iv_kw in iv_keywords:
            # 单个关键词搜索（跳过通用词）
            if iv_kw not in generic_keywords:
                queries.append({
                    'query': iv_kw,
                    'section': f'{iv_kw}的理论基础与测量',
                    'strategy': '拆分搜索',
                    'lang': 'zh'
                })

        # ========== 第二步：因变量相关查询 ==========
        for dv_kw in dv_keywords:
            # 单个关键词搜索（跳过通用词）
            if dv_kw not in generic_keywords:
                queries.append({
                    'query': dv_kw,
                    'section': f'{dv_kw}的理论基础与测量',
                    'strategy': '拆分搜索',
                    'lang': 'zh'
                })

        # ========== 第三步：交叉搜索（变量关系） ==========
        for iv_kw in iv_keywords:
            for dv_kw in dv_keywords:
                # 跳过通用词组合
                if iv_kw in generic_keywords or dv_kw in generic_keywords:
                    continue

                # 简单组合
                queries.append({
                    'query': f'{iv_kw} {dv_kw}',
                    'section': '影响机制',
                    'strategy': '交叉筛选',
                    'lang': 'zh'
                })
                # 影响关系
                queries.append({
                    'query': f'{iv_kw} 对 {dv_kw} 的影响',
                    'section': '影响机制',
                    'strategy': '影响关系',
                    'lang': 'zh'
                })
                # 关系/相关性
                queries.append({
                    'query': f'{iv_kw} {dv_kw} 关系',
                    'section': '影响机制',
                    'strategy': '相关性',
                    'lang': 'zh'
                })

        # ========== 第四步：理论基础/方法论查询 ==========
        # 提取"基于XXX"中的理论
        theory_match = re.search(r'基于(.+?)(?:的)?(?:实证研究|实证分析|视角)', title)
        if theory_match:
            theory = theory_match.group(1).strip()
            queries.append({
                'query': theory,
                'section': '理论基础',
                'strategy': '理论视角',
                'lang': 'zh'
            })
            queries.append({
                'query': f'{theory} 理论',
                'section': '理论基础',
                'strategy': '理论视角',
                'lang': 'zh'
            })

        # 中介/调节效应
        queries.append({
            'query': '中介效应 调节效应',
            'section': '影响机制',
            'strategy': '方法论',
            'lang': 'zh'
        })

        # 特定领域查询（行为金融学）
        if '行为金融' in title:
            queries.append({
                'query': '行为金融学',
                'section': '理论基础',
                'strategy': '领域特定',
                'lang': 'zh'
            })
            queries.append({
                'query': '投资者情绪 行为金融学',
                'section': '理论基础',
                'strategy': '领域特定',
                'lang': 'zh'
            })

        # 媒体关注度相关
        if any('媒体' in kw for kw in iv_keywords + dv_keywords):
            queries.append({
                'query': '媒体关注',
                'section': '理论基础',
                'strategy': '领域特定',
                'lang': 'zh'
            })

        return queries

    def _generate_english_empirical_queries(
        self, title: str, iv_keywords: list, dv_keywords: list, vars_info: dict
    ) -> list:
        """
        为英文实证型题目生成英文搜索查询

        策略（针对 OpenAlex 优化）：
        1. 翻译关键词为英文
        2. 拆分搜索：每个关键词单独生成英文查询
        3. 交叉筛选：变量间影响关系查询
        """
        queries = []

        # 翻译关键词
        iv_en_list = []
        dv_en_list = []

        for iv_kw in iv_keywords:
            iv_en = self._translate_keyword(iv_kw)
            if iv_en:
                iv_en_list.append((iv_kw, iv_en))
            else:
                iv_en_list.append((iv_kw, iv_kw))

        for dv_kw in dv_keywords:
            dv_en = self._translate_keyword(dv_kw)
            if dv_en:
                dv_en_list.append((dv_kw, dv_en))
            else:
                dv_en_list.append((dv_kw, dv_kw))

        # ========== 第一步：自变量相关查询 ==========
        for iv_kw, iv_en in iv_en_list:
            queries.append({
                'query': f'{iv_en} measurement scale',
                'section': f'{iv_kw}的理论基础与测量',
                'strategy': '拆分搜索',
                'original_kw': iv_kw,
                'lang': 'en'
            })
            queries.append({
                'query': f'{iv_en} determinants metrics',
                'section': f'{iv_kw}的理论基础与测量',
                'strategy': '同义词扩展',
                'original_kw': iv_kw,
                'lang': 'en'
            })

        # ========== 第二步：因变量相关查询 ==========
        for dv_kw, dv_en in dv_en_list:
            queries.append({
                'query': f'{dv_en} measurement scale',
                'section': f'{dv_kw}的理论基础与测量',
                'strategy': '拆分搜索',
                'original_kw': dv_kw,
                'lang': 'en'
            })
            if 'forecast' in dv_en.lower() or 'accuracy' in dv_en.lower():
                queries.append({
                    'query': f'analyst forecast accuracy',
                    'section': f'{dv_kw}的理论基础与测量',
                    'strategy': '领域特定',
                    'original_kw': dv_kw,
                    'lang': 'en'
                })

        # ========== 第三步：交叉筛选 ==========
        for iv_kw, iv_en in iv_en_list:
            for dv_kw, dv_en in dv_en_list:
                queries.append({
                    'query': f'{iv_en} {dv_en}',
                    'section': '影响机制',
                    'strategy': '交叉筛选',
                    'original_kw': f'{iv_kw} -> {dv_kw}',
                    'lang': 'en'
                })
                queries.append({
                    'query': f'impact of {iv_en} on {dv_en}',
                    'section': '影响机制',
                    'strategy': '交叉筛选',
                    'original_kw': f'{iv_kw} -> {dv_kw}',
                    'lang': 'en'
                })

        # ========== 第四步：方法论查询 ==========
        queries.append({
            'query': 'mediation effect moderation effect empirical study',
            'section': '影响机制',
            'strategy': '方法论',
            'lang': 'en'
        })

        return queries

    def _split_compound_keyword(self, keyword: str) -> list:
        """
        拆分复合关键词

        例如：
        - "媒体关注度、投资者情绪" -> ["媒体关注度", "投资者情绪"]
        - "分析师盈利预测准确性" -> ["分析师盈利预测准确性"]

        Args:
            keyword: 原始关键词

        Returns:
            拆分后的关键词列表
        """
        import re

        # 按顿号、逗号、空格等分隔符拆分
        separators = ['、', ',', '，', '和', '与', '及']
        keywords = [keyword]

        for sep in separators:
            new_keywords = []
            for kw in keywords:
                parts = kw.split(sep)
                new_keywords.extend([p.strip() for p in parts if p.strip()])
            keywords = new_keywords

        # 去重
        seen = set()
        result = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)

        return result

    def _translate_keyword(self, chinese_keyword: str) -> str:
        """
        将中文关键词翻译为英文术语

        Args:
            chinese_keyword: 中文关键词

        Returns:
            英文翻译（如果找到匹配），否则返回空字符串
        """
        # 关键词翻译映射表
        translations = {
            # 媒体与传播
            '媒体关注度': 'media coverage',
            '媒体报道': 'media coverage',
            '新闻关注': 'news coverage',
            '舆情': 'public opinion',

            # 投资者情绪相关
            '投资者情绪': 'investor sentiment',
            '投资者情绪': 'investor sentiment',
            '市场情绪': 'market sentiment',
            '情绪': 'sentiment',

            # 分析师预测相关
            '分析师盈利预测': 'analyst earnings forecast',
            '分析师预测': 'analyst forecast',
            '盈利预测': 'earnings forecast',
            '盈利预测准确性': 'forecast accuracy',
            '分析师盈利预测准确性': 'analyst forecast accuracy',
            '预测准确性': 'forecast accuracy',

            # 行为金融学
            '行为金融学': 'behavioral finance',
            '行为金融': 'behavioral finance',

            # 公司治理
            '公司治理': 'corporate governance',
            '股权结构': 'ownership structure',
            '董事会': 'board of directors',
            '高管薪酬': 'executive compensation',

            # 创新
            '技术创新': 'technological innovation',
            '研发投入': 'R&D investment',
            '创新绩效': 'innovation performance',

            # 环境
            '环境信息披露': 'environmental disclosure',
            '企业社会责任': 'corporate social responsibility',
            'ESG': 'ESG',

            # 质量管理
            '质量管理': 'quality management',
            '质量控制': 'quality control',
            '质量保证': 'quality assurance',
            'QFD': 'QFD',
            'FMEA': 'FMEA',

            # 外包
            '软件外包': 'software outsourcing',
            '外包': 'outsourcing',

            # 风险管理
            '风险管理': 'risk management',
            '风险控制': 'risk control',

            # 财务
            '财务绩效': 'financial performance',
            '企业绩效': 'firm performance',
            '经营绩效': 'operating performance',

            # 数字化
            '数字化转型': 'digital transformation',
            '数字化': 'digitalization',

            # 通用
            '影响因素': 'determinants',
            '影响': 'impact',
            '效应': 'effect',
            '作用': 'role',
            '关系': 'relationship',
        }

        # 尝试精确匹配
        if chinese_keyword in translations:
            return translations[chinese_keyword]

        # 尝试部分匹配（处理复合关键词）
        for zh, en in translations.items():
            if zh in chinese_keyword:
                # 返回找到的翻译，或者组合翻译
                return en

        # 如果包含多个关键词，尝试拆分翻译
        keywords_to_translate = []
        remaining = chinese_keyword
        for zh, en in sorted(translations.items(), key=lambda x: len(x[0]), reverse=True):
            if zh in remaining:
                keywords_to_translate.append(en)
                remaining = remaining.replace(zh, ' ')

        if keywords_to_translate:
            return ' '.join(keywords_to_translate)

        return ''

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

    def extract_relevance_keywords(self, framework: dict) -> list:
        """
        从框架分析中提取相关性关键词（用于文献相关性评分）

        Args:
            framework: 智能分析生成的框架

        Returns:
            相关性关键词列表
        """
        keywords = []

        # 从 key_elements 中提取
        key_elements = framework.get('key_elements', {})
        for key, value in key_elements.items():
            if value and isinstance(value, str):
                # 添加原始值
                keywords.append(value)
                # 添加拆分后的关键词
                keywords.extend(value.split())

        # 从 variables 中提取（实证型）
        variables = key_elements.get('variables', {})
        if variables:
            iv = variables.get('independent')
            dv = variables.get('dependent')
            if iv:
                keywords.append(iv)
                keywords.extend(iv.split('、'))  # 处理中文顿号
            if dv:
                keywords.append(dv)

        # 移除空值和重复
        keywords = list(set(k for k in keywords if k and k.strip()))

        return keywords
