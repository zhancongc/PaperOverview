"""
混合分类器：模式识别 + 大模型验证
- 先用模式识别提取关键词
- 再用大模型判断是否合理，不合理则优化
"""
import re
import os
from enum import Enum
from typing import List, Dict, Optional, Any
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

    async def validate_and_fix_search_queries(
        self,
        title: str,
        queries: List[Dict],
        max_retries: int = 1
    ) -> List[Dict]:
        """
        使用LLM验证搜索关键词是否合理，并修复不相关的关键词

        Args:
            title: 论文题目
            queries: 搜索查询列表
            max_retries: 最大重试次数

        Returns:
            修复后的搜索查询列表
        """
        if not self.client:
            print("[HybridClassifier] LLM未配置，跳过搜索关键词验证")
            return queries

        # 提取所有查询的query部分
        query_list = [q['query'] for q in queries]

        prompt = f"""论文题目：{title}

当前生成的搜索关键词：
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(query_list))}

请判断以上搜索关键词是否与论文主题相关。

具体要求：
1. 判断每个关键词是否相关
2. 对于不相关的关键词，说明为什么（例如：属于不同领域、概念不符等）
3. 如果有关键词不相关，请提供更合适的关键词建议

格式要求：
- 如果所有关键词都相关，只回答"全部相关"
- 如果有不相关的关键词，按格式回答：
  "关键词X不相关：原因。建议改为：新关键词1、新关键词2"
"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            result = response.choices[0].message.content.strip()
            print(f"[HybridClassifier] LLM关键词验证结果: {result}")

            if result == "全部相关":
                return queries

            # 解析LLM的修改建议
            fixed_queries = []
            queries_to_fix = []

            # 检查每个查询
            for i, query_info in enumerate(queries):
                query = query_info['query']

                # 检查LLM是否认为这个查询不相关
                is_relevant = True
                fix_reason = None

                # 查找是否提到这个关键词不相关
                for line in result.split('\n'):
                    if f'关键词{i+1}' in line or query in line:
                        if '不相关' in line or '无关' in line:
                            is_relevant = False
                            fix_reason = line
                            break

                if is_relevant:
                    fixed_queries.append(query_info)
                else:
                    queries_to_fix.append({
                        'index': i,
                        'query': query,
                        'reason': fix_reason
                    })

            # 如果有不相关的查询，尝试修复
            if queries_to_fix:
                print(f"[HybridClassifier] 发现 {len(queries_to_fix)} 个不相关的关键词，尝试修复...")

                # 生成修复prompt
                fix_prompt = f"""论文题目：{title}

以下搜索关键词与论文主题不相关：
{chr(10).join(f"- {q['query']}: {q['reason']}" for q in queries_to_fix)}

请为每个不相关的关键词提供2-3个更合适的替代关键词，要求：
1. 与论文主题高度相关
2. 包含论文的核心概念（研究对象、优化目标、方法论）
3. 既有中文关键词也有英文关键词

格式要求：
关键词1：替代1、替代2、替代3
关键词2：替代1、替代2、替代3
...
"""

                try:
                    fix_response = await self.client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "user", "content": fix_prompt}
                        ],
                        temperature=0.5,
                        max_tokens=800
                    )

                    fix_result = fix_response.choices[0].message.content.strip()
                    print(f"[HybridClassifier] LLM修复建议: {fix_result}")

                    # 解析修复建议并添加新查询
                    lines = fix_result.split('\n')
                    for i, query_to_fix in enumerate(queries_to_fix):
                        # 找到对应的修复建议
                        for line in lines:
                            if f'关键词{i+1}' in line or query_to_fix['query'] in line:
                                # 提取替代关键词
                                if '替代' in line or ':' in line:
                                    # 分割替代关键词
                                    parts = line.split(':')[1] if ':' in line else line.split('：')[1] if '：' in line else line
                                    alternatives = [alt.strip() for alt in parts.replace('替代', ',').split('、') if alt.strip()]
                                    alternatives = [alt for alt in alternatives if alt and alt != '、']

                                    # 为每个替代关键词创建查询
                                    original_query = next((q for q in queries if q['query'] == query_to_fix['query']), None)
                                    if original_query:
                                        for alt in alternatives[:3]:  # 最多3个替代
                                            # 判断语言
                                            is_english = self._contains_english_terms(alt)
                                            fixed_queries.append({
                                                'query': alt,
                                                'section': original_query.get('section', '关键词修复'),
                                                'lang': 'en' if is_english else 'zh'
                                            })
                                            print(f"[HybridClassifier] 修复关键词: {query_to_fix['query']} → {alt}")
                                break

                except Exception as e:
                    print(f"[HybridClassifier] LLM修复失败: {e}，保留原查询")
                    # 修复失败，保留原查询
                    for query_to_fix in queries_to_fix:
                        original_query = next((q for q in queries if q['query'] == query_to_fix['query']), None)
                        if original_query:
                            fixed_queries.append(original_query)

            return fixed_queries

        except Exception as e:
            print(f"[HybridClassifier] LLM关键词验证出错: {e}，使用原查询")
            import traceback
            traceback.print_exc()
            return queries

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
            framework['search_queries'] = await self._application_queries(title, details.get('key_elements', {}))
        elif topic_type == TopicType.EVALUATION:
            framework['framework'] = self._evaluation_framework(title, details.get('key_elements', {}))
            framework['search_queries'] = self._evaluation_queries(title, details.get('key_elements', {}))
        elif topic_type == TopicType.THEORETICAL:
            framework['framework'] = self._theoretical_framework(title)
            framework['search_queries'] = self._theoretical_queries(title)
        elif topic_type == TopicType.EMPIRICAL:
            framework['framework'] = self._empirical_framework(title, details.get('key_elements', {}))
            framework['search_queries'] = self._empirical_queries(title, details)
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

    async def _application_queries(self, title: str, elements: dict) -> list:
        """
        应用型检索查询 - 使用LLM动态生成更精准的搜索关键词

        策略：
        1. 使用LLM动态生成相关关键词，替代硬编码
        2. 研究对象分析 - 分别搜索中英文
        3. 优化目标现状 - 只组合核心关键词
        4. 方法论应用 - 根据方法类型处理

        Returns:
            查询列表
        """
        obj = elements.get("research_object", "")
        goal = elements.get("optimization_goal", "")
        method = elements.get("methodology", "")

        queries = []

        # 使用LLM动态生成关键词
        print(f"[HybridClassifier] 使用LLM动态生成搜索关键词...")
        dynamic_keywords = await self._generate_dynamic_keywords(
            title=title,
            research_object=obj,
            optimization_goal=goal,
            methodology=method
        )

        # 提取生成的关键词
        object_keywords = dynamic_keywords.get('object_keywords', [])
        goal_keywords = dynamic_keywords.get('goal_keywords', [])
        method_keywords = dynamic_keywords.get('method_keywords', [])
        avoid_domains = dynamic_keywords.get('avoid_domains', [])

        # 检测题目中是否包含英文术语
        has_english_terms = self._contains_english_terms(obj) or self._contains_english_terms(method)

        # 通用关键词列表（不单独搜索）
        generic_keywords = {'研究进展', '问题', '应用', '质量改进', '优化', '改进', '分析', '方法', '技术'}

        # 1. 研究对象分析 - 使用动态生成的关键词
        if obj:
            # 判断是否应该搜索英文文献
            if has_english_terms or self._should_search_english(obj):
                # 生成英文搜索查询
                en_query = self._translate_to_english(obj)
                if en_query:
                    queries.append({
                        'query': en_query,
                        'section': '研究对象分析',
                        'lang': 'en'  # 英文查询
                    })

                    # 如果研究对象包含Agent相关术语，添加同义词搜索
                    agent_synonyms = self._get_agent_synonyms(obj)
                    for synonym in agent_synonyms:
                        if synonym.lower() != en_query.lower():
                            queries.append({
                                'query': synonym,
                                'section': '研究对象分析',
                                'lang': 'en'
                            })

            # 中文查询
            queries.append({
                'query': obj,
                'section': '研究对象分析',
                'lang': 'zh'
            })

            # 如果研究对象包含Agent相关术语，添加中文同义词搜索
            agent_synonyms_zh = self._get_agent_synonyms_chinese(obj)
            for synonym in agent_synonyms_zh:
                if synonym != obj:
                    queries.append({
                        'query': synonym,
                        'section': '研究对象分析',
                        'lang': 'zh'
                    })

            # 使用动态生成的对象关键词（过滤掉避免领域的词）
            for obj_kw in object_keywords[:3]:  # 最多3个关键词
                # 检查是否在避免领域中
                should_skip = False
                for avoid_domain in avoid_domains:
                    if avoid_domain.lower() in obj_kw.lower():
                        print(f"[HybridClassifier] 跳过关键词 '{obj_kw}'（属于避免领域: {avoid_domain}）")
                        should_skip = True
                        break

                if not should_skip and obj_kw != obj:
                    queries.append({
                        'query': f'{obj} {obj_kw}',
                        'section': '研究对象分析',
                        'lang': 'zh'
                    })

        # 2. 优化目标现状 - 使用动态生成的目标关键词
        if obj and goal_keywords:
            for goal_kw in goal_keywords[:2]:  # 最多2个关键词
                queries.append({
                    'query': f'{obj} {goal_kw}',
                    'section': '优化目标现状',
                    'lang': 'zh'
                })
        elif obj and goal:
            # 回退到原逻辑
            if goal not in generic_keywords:
                queries.append({
                    'query': f'{obj} {goal}',
                    'section': '优化目标现状',
                    'lang': 'zh'
                })
            else:
                queries.append({
                    'query': obj,
                    'section': '优化目标现状',
                    'lang': 'zh'
                })

        # 3. 方法论应用 - 使用动态生成的方法关键词
        if method and obj:
            method_clean = self._clean_methodology_name(method)

            # 检查方法是否为英文缩写
            if self._is_english_acronym(method_clean):
                # 英文缩写（如 QFD、FMEA、Agent）：生成英文查询
                en_obj = self._translate_to_english(obj)
                if en_obj:
                    queries.append({
                        'query': f'{method_clean} {en_obj}',
                        'section': '方法论应用',
                        'lang': 'en',
                        'keywords': [en_obj, method_clean],
                        'search_mode': 'title_keyword'
                    })

                # 中文组合查询
                queries.append({
                    'query': f'{method_clean} {obj}',
                    'section': '方法论应用',
                    'lang': 'zh',
                    'keywords': [obj, method_clean],
                    'search_mode': 'title_keyword'
                })
            else:
                # 使用动态生成的方法关键词
                for method_kw in method_keywords[:2]:  # 最多2个关键词
                    queries.append({
                        'query': f'{method_clean} {obj} {method_kw}',
                        'section': '方法论应用',
                        'lang': 'zh'
                    })

                # 如果没有动态关键词，回退到原逻辑
                if not method_keywords:
                    obj_type = self._classify_object_type(obj)
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

    def _contains_english_terms(self, text: str) -> bool:
        """检测文本中是否包含英文术语"""
        if not text:
            return False
        # 检测是否包含英文单词（不含中文）
        import re
        # 提取英文单词
        english_words = re.findall(r'[A-Za-z]{2,}', text)
        return len(english_words) > 0

    def _should_search_english(self, obj: str) -> bool:
        """判断是否应该搜索英文文献"""
        if not obj:
            return False  # 如果 obj 是 None，返回 False

        # 常见的应该搜索英文的术语
        english_related_terms = {
            'Agent', 'agent', 'AI', '人工智能',
            'FMEA', 'QFD', 'AHP', 'DMAIC', 'SWOT',
            'Machine Learning', '机器学习',
            'Deep Learning', '深度学习',
            'Software', '软件',
            'Development', '开发',
            'Project', '项目',
            'Management', '管理',
            'Risk', '风险',
            'Data', '数据'
        }

        obj_lower = obj.lower()
        for term in english_related_terms:
            if term.lower() in obj_lower:
                return True
        return False

    def _translate_to_english(self, chinese_text: str) -> str:
        """将中文术语翻译为英文（简单映射）"""
        # 常见术语映射表（按优先级排序，完整短语在前）
        translations = {
            # 完整短语优先
            'Agent开发项目': 'Agent Development Project',
            '智能体开发项目': 'Agent Development Project',
            '多智能体系统开发项目': 'Multi-Agent System Development Project',
            '软件开发项目': 'Software Development Project',
            '开发项目': 'Development Project',
            '项目风险管理': 'Project Risk Management',
            '失效模式与影响分析': 'FMEA',
            # Agent 相关术语（同义词）
            'Agent': 'Agent',
            '智能体': 'Agent',
            '代理': 'Agent',
            '多智能体': 'Multi-Agent',
            '多智能体系统': 'Multi-Agent System',
            '智能代理': 'Intelligent Agent',
            '软件代理': 'Software Agent',
            # 方法论
            'FMEA': 'FMEA',
            '失效模式': 'Failure Mode and Effects Analysis',
            'QFD': 'QFD',
            '质量功能展开': 'Quality Function Deployment',
            '风险管理': 'Risk Management',
            # 通用术语
            '软件': 'Software',
            '开发': 'Development',
            '项目': 'Project',
            '质量管理': 'Quality Management',
            '机器学习': 'Machine Learning',
            '深度学习': 'Deep Learning',
            '人工智能': 'Artificial Intelligence',
            '优化': 'Optimization',
            '改进': 'Improvement',
            '应用': 'Application',
        }

        # 先尝试完整短语匹配
        for cn, en in translations.items():
            if cn == chinese_text:
                return en

        # 部分匹配替换
        result = chinese_text
        for cn, en in translations.items():
            if cn in result:
                result = result.replace(cn, en)

        # 如果包含英文，直接返回
        if self._contains_english_terms(result):
            return result

        return result if result != chinese_text else None

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

    def _get_agent_synonyms(self, obj: str) -> List[str]:
        """
        获取Agent相关的英文同义词

        Args:
            obj: 研究对象

        Returns:
            英文同义词列表
        """
        synonyms = []
        obj_lower = obj.lower()

        # 如果研究对象包含agent相关术语
        if any(term in obj_lower for term in ['agent', '智能体', '代理']):
            synonyms.extend([
                'Multi-Agent System',
                'Intelligent Agent',
                'Software Agent',
                'Autonomous Agent',
                'Agent-Based System'
            ])

        return synonyms

    def _get_agent_synonyms_chinese(self, obj: str) -> List[str]:
        """
        获取Agent相关的中文同义词

        Args:
            obj: 研究对象

        Returns:
            中文同义词列表
        """
        synonyms = []

        # 如果研究对象包含agent相关术语
        if any(term in obj for term in ['Agent', '智能体', '代理']):
            synonyms.extend([
                '多智能体系统',
                '智能代理',
                '软件代理',
                '自主智能体',
                '基于智能体的系统'
            ])

        return synonyms

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

    async def _generate_dynamic_keywords(
        self,
        title: str,
        research_object: str = None,
        optimization_goal: str = None,
        methodology: str = None
    ) -> dict:
        """
        使用LLM动态生成相关的搜索关键词

        Args:
            title: 论文题目
            research_object: 研究对象
            optimization_goal: 优化目标
            methodology: 方法论

        Returns:
            {
                'object_keywords': [],  # 研究对象相关关键词
                'goal_keywords': [],     # 优化目标相关关键词
                'method_keywords': [],   # 方法论相关关键词
                'avoid_domains': []     # 需要避免的领域
            }
        """
        if not self.classifier.client:
            print("[HybridClassifier] LLM未配置，使用默认关键词")
            return self._get_default_keywords(title, research_object, optimization_goal, methodology)

        prompt = f"""论文题目：{title}

研究要素：
- 研究对象：{research_object or '未知'}
- 优化目标：{optimization_goal or '未知'}
- 方法论：{methodology or '未知'}

请分析以上论文题目，生成适合文献搜索的关键词。

要求：
1. **研究对象关键词**（4-6个）：与研究对象直接相关的术语
2. **优化目标关键词**（2-3个）：与优化目标相关的术语
3. **方法论关键词**（2-3个）：与方法论相关的术语
4. **需要避免的领域**（如果适用）：说明这个题目不属于哪些领域

**注意事项**：
- 关键词应该具体、准确，避免过于宽泛
- 如果研究对象是"项目"或"系统"，不要混入制造、工艺等不相关的术语
- 对于软件开发/项目管理类题目，避免使用"制造工艺"、"生产流程"等制造领域术语
- 对于AI/机器学习类题目，避免使用传统制造领域的术语

**输出格式（JSON）**：
```json
{{
  "object_keywords": ["关键词1", "关键词2", ...],
  "goal_keywords": ["关键词1", "关键词2", ...],
  "method_keywords": ["关键词1", "关键词2", ...],
  "avoid_domains": ["领域1", "领域2", ...]
}}
```
"""

        try:
            response = await self.classifier.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个学术文献检索专家，擅长生成准确的搜索关键词。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content.strip()
            print(f"[HybridClassifier] LLM动态关键词生成结果: {result}")

            # 解析JSON结果
            import json
            keywords_data = json.loads(result)

            # 验证和清理返回的数据
            cleaned_data = {
                'object_keywords': keywords_data.get('object_keywords', [])[:8],
                'goal_keywords': keywords_data.get('goal_keywords', [])[:5],
                'method_keywords': keywords_data.get('method_keywords', [])[:5],
                'avoid_domains': keywords_data.get('avoid_domains', [])
            }

            print(f"[HybridClassifier] 清洗后的关键词:")
            print(f"  对象关键词: {cleaned_data['object_keywords']}")
            print(f"  目标关键词: {cleaned_data['goal_keywords']}")
            print(f"  方法关键词: {cleaned_data['method_keywords']}")
            print(f"  避免领域: {cleaned_data['avoid_domains']}")

            return cleaned_data

        except Exception as e:
            print(f"[HybridClassifier] LLM动态关键词生成失败: {e}，使用默认关键词")
            import traceback
            traceback.print_exc()
            return self._get_default_keywords(title, research_object, optimization_goal, methodology)

    def _get_default_keywords(
        self,
        title: str,
        research_object: str = None,
        optimization_goal: str = None,
        methodology: str = None
    ) -> dict:
        """
        获取默认关键词（回退方案）

        Args:
            title: 论文题目
            research_object: 研究对象
            optimization_goal: 优化目标
            methodology: 方法论

        Returns:
            默认关键词字典
        """
        # 简单的默认关键词生成逻辑
        object_keywords = []
        goal_keywords = []
        method_keywords = []
        avoid_domains = []

        if research_object:
            # 基础关键词：直接使用研究对象
            object_keywords.append(research_object)

            # 检测领域并添加相关关键词
            obj_lower = research_object.lower()

            # 软件开发/项目领域
            if any(kw in obj_lower for kw in ['软件', '开发', '系统', '平台', 'agent', '智能体', '项目']):
                object_keywords.extend(['开发', '设计', '实现', '架构'])
                avoid_domains.extend(['制造', '工艺', '生产', '装配'])

            # 数据/AI领域
            if any(kw in obj_lower for kw in ['数据', '算法', '模型', '学习', '智能']):
                object_keywords.extend(['模型', '算法', '数据'])
                avoid_domains.extend(['制造工艺', '生产流程'])

        if optimization_goal:
            goal_keywords.append(optimization_goal)

        if methodology:
            method_keywords.append(methodology)

        return {
            'object_keywords': object_keywords[:8],
            'goal_keywords': goal_keywords[:5],
            'method_keywords': method_keywords[:5],
            'avoid_domains': avoid_domains
        }

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
