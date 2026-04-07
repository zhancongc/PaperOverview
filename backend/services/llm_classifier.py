"""
基于大模型的题目分类器
使用 DeepSeek API 进行智能分类，理解语义并准确识别题目核心

DEPRECATED: 此模块为 v5.x 旧版本遗留代码，当前 v6.0 流程已不再使用。
保留仅用于历史参考，新代码请使用 PaperSearchAgent + SmartReviewGeneratorFinal。
"""
import warnings
warnings.warn(
    "llm_classifier 模块已废弃，v6.0 流程不再使用",
    DeprecationWarning,
    stacklevel=2
)
import os
import json
from openai import AsyncOpenAI
from typing import Dict, List, Tuple
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class TopicType(Enum):
    """题目类型枚举"""
    APPLICATION = "application"  # 应用型/解决方案型 - 三圈交集
    EVALUATION = "evaluation"    # 评价型/体系构建型 - 金字塔式
    THEORETICAL = "theoretical"  # 理论型/研究型 - 溯源式
    EMPIRICAL = "empirical"      # 实证型 - 问题-方案式
    GENERAL = "general"          # 通用型


class LLTopicClassifier:
    """基于大模型的题目分类器"""

    # 分类系统的 Prompt
    CLASSIFICATION_SYSTEM_PROMPT = """你是一个专业的学术论文题目分类专家。你需要根据题目内容判断其研究类型，并给出详细的判定依据。

## 重要：优先检查混血题目

在分类之前，首先检查题目是否同时具备多种类型的特征（混血题目）：

**混血题目判定示例：**

| 题目 | 包含特征 | 研究核心 | 正确类型 | 判定理由 |
|------|---------|---------|---------|---------|
| 基于结构方程模型的制造企业质量绩效影响研究 | 基于(应用型) + 影响(实证型) | 检验影响关系 | **实证型** | SEM是分析工具，核心是检验质量绩效的影响因素 |
| 质量管理成熟度对创新绩效的影响研究 | 成熟度(评价型) + 影响(实证型) | 检验影响关系 | **实证型** | 成熟度是自变量，核心是检验对创新绩效的影响 |
| 智能制造背景下质量成熟度评价与提升路径研究 | 评价(评价型) + 提升(应用型) | 构建评价体系 | **评价型** | 核心是构建评价体系，提升路径是应用延伸 |

**判定原则：**
1. 如果题目同时包含「基于XX模型/方法」和「影响/效应/关系」，优先判定为**实证型**
2. 如果题目同时包含「成熟度/评价」和「影响/效应/关系」，优先判定为**实证型**
3. 如果题目同时包含「评价」和「提升/优化/改进」，优先判定为**评价型**

## 题目类型定义

## 题目类型定义

### 1. 应用型/解决方案型 (application)
**核心特征**：使用特定方法论/工具解决具体场景下的优化问题
**典型结构**：「基于X的Y优化」
**研究范式**：解决问题
**综述框架**：三圈交集式（研究对象+优化目标+方法论）

示例：
- 基于DMAIC的智能座舱软件持续交付流程优化研究
- 基于敏捷方法的传统制造企业生产流程改进

### 2. 评价型/体系构建型 (evaluation)
**核心特征**：构建评价体系/成熟度模型，证明体系的科学性
**典型关键词**：成熟度、评价、评估、指标体系
**研究范式**：构建工具
**综述框架**：金字塔式（理论基础→维度指标→方法技术→实践应用）

示例：
- 制造型企业质量管理成熟度评价研究
- 企业数字化转型成熟度评价模型构建

### 3. 理论型/研究型 (theoretical)
**核心特征**：梳理理论发展脉络，整合现有知识
**典型关键词**：理论、机理、综述、进展
**研究范式**：整合知识
**综述框架**：溯源式（理论起源→发展→现状→前沿）

示例：
- 质量管理理论演进研究
- 服务质量理论综述与展望

### 4. 实证型 (empirical)
**核心特征**：检验变量间的影响关系/因果机制
**典型结构**：「X对Y的影响」
**研究范式**：检验假设
**综述框架**：问题-方案式（变量1→变量2→影响机制）

示例：
- 质量管理成熟度对创新绩效的影响研究
- 供应链整合对质量绩效的影响机制研究

### 5. 通用型 (general)
**核心特征**：无法明确归入上述类型
**综述框架**：通用结构

## 混血题目处理原则

当题目同时具备多种特征时，根据**研究核心**来确定类型：

1. **应用型+实证型**（如：基于结构方程模型的制造企业质量绩效影响研究）
   - 核心是检验影响关系 → 按**实证型**处理
   - 说明：模型只是工具，核心是影响机制

2. **评价型+实证型**（如：质量管理成熟度对创新绩效的影响研究）
   - 核心是影响关系 → 按**实证型**处理
   - 说明：成熟度是自变量，核心是检验影响

3. **评价型+应用型**（如：智能制造背景下质量成熟度评价与提升路径研究）
   - 核心是构建评价体系 → 按**评价型**处理
   - 说明：提升路径是应用延伸

## 判定流程

1. **第一眼**：看核心动词/名词关键词
   - 「基于/优化/应用」→ 应用型
   - 「成熟度/评价/指标体系」→ 评价型
   - 「理论/机理/综述」→ 理论型
   - 「影响/效应/关系」→ 实证型

2. **第二眼**：看研究范式
   - 解决问题 → 应用型
   - 构建工具 → 评价型
   - 整合知识 → 理论型
   - 检验假设 → 实证型

3. **核心判定**：识别研究的真正核心
   - 混血题目需要判断哪个是核心，哪个是工具/延伸

## 输出格式

请严格按照以下 JSON 格式输出，不要添加任何其他内容：

```json
{
  "type": "application/evaluation/theoretical/empirical/general",
  "type_name": "类型名称",
  "confidence": "high/medium/low",
  "reasoning": {
    "first_look": "第一眼判定（关键词识别）",
    "second_look": "第二眼判定（研究范式）",
    "core_analysis": "核心分析（混血题目需要说明核心是什么）",
    "final_reason": "最终判定的完整理由"
  },
  "key_elements": {
    "research_object": "研究对象（如：智能座舱软件）",
    "optimization_goal": "优化目标（如：持续交付）",
    "methodology": "方法论（如：DMAIC）",
    "variables": {
      "independent": "自变量（实证型需要）",
      "dependent": "因变量（实证型需要）"
    }
  }
}
```

注意：
1. type 必须是 5 种类型之一
2. confidence 表示判定的置信度
3. reasoning 要清晰说明判定过程
4. key_elements 提取题目中的关键要素
"""

    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def classify(self, title: str) -> Tuple[TopicType, str, Dict]:
        """
        使用大模型分类题目

        Args:
            title: 论文题目

        Returns:
            (题目类型, 判定理由, 判定详情)
        """
        user_prompt = f"""请对以下论文题目进行分类：

题目：{title}

请严格按照系统提示中的 JSON 格式输出分类结果。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # 降低温度以获得更稳定的输出
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # 解析结果
            topic_type = TopicType(result['type'])
            reason = result['reasoning']['final_reason']
            details = {
                'confidence': result.get('confidence', 'medium'),
                'reasoning': result['reasoning'],
                'key_elements': result.get('key_elements', {}),
                'raw_result': result
            }

            return (topic_type, reason, details)

        except Exception as e:
            print(f"大模型分类失败: {e}")
            # 失败时回退到简单规则
            return self._fallback_classification(title)

    def _fallback_classification(self, title: str) -> Tuple[TopicType, str, Dict]:
        """回退分类：使用简单规则"""
        title_lower = title.lower()

        if any(kw in title for kw in ['成熟度', '评价', '评估', '指标体系']):
            return (TopicType.EVALUATION, '识别到评价型关键词（规则回退）', {'method': 'fallback'})
        if any(kw in title for kw in ['基于', '优化', '改进', '应用']):
            return (TopicType.APPLICATION, '识别到应用型关键词（规则回退）', {'method': 'fallback'})
        if any(kw in title for kw in ['影响', '效应', '关系', '相关']):
            return (TopicType.EMPIRICAL, '识别到实证型关键词（规则回退）', {'method': 'fallback'})
        if any(kw in title for kw in ['理论', '机理', '综述', '进展']):
            return (TopicType.THEORETICAL, '识别到理论型关键词（规则回退）', {'method': 'fallback'})

        return (TopicType.GENERAL, '无法识别，使用通用类型（规则回退）', {'method': 'fallback'})

    async def close(self):
        await self.client.close()


# 为了兼容现有代码，保留原有的 FrameworkGenerator
class FrameworkGenerator:
    """综述框架生成器（使用大模型分类）"""

    def __init__(self):
        self.classifier = LLTopicClassifier()

    async def generate_framework(self, title: str) -> Dict:
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
            'confidence': details.get('confidence', 'medium'),
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

    def _get_type_name(self, topic_type: TopicType) -> str:
        """获取类型名称"""
        names = {
            TopicType.APPLICATION: "应用型/解决方案型",
            TopicType.EVALUATION: "评价型/体系构建型",
            TopicType.THEORETICAL: "理论型/研究型",
            TopicType.EMPIRICAL: "实证型",
            TopicType.GENERAL: "通用型"
        }
        return names.get(topic_type, "未知类型")

    # ==================== 框架生成方法 ====================

    def _application_framework(self, title: str, elements: Dict) -> Dict:
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

    def _application_queries(self, title: str, elements: Dict) -> List[Dict]:
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

    def _evaluation_framework(self, title: str, elements: Dict) -> Dict:
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

    def _evaluation_queries(self, title: str, elements: Dict) -> List[Dict]:
        """评价型检索查询"""
        obj = elements.get("research_object", title.split("成熟度")[0].split("评价")[0])

        return [
            {'query': f'{obj} 评价 理论', 'section': '评价理论基础'},
            {'query': f'{obj} 成熟度 模型', 'section': '评价理论基础'},
            {'query': f'{obj} 评价 指标 维度', 'section': '评价维度与指标'},
            {'query': f'{obj} 评价 方法', 'section': '评价方法与技术'},
            {'query': f'{obj} 评价 实践', 'section': '评价实践与应用'}
        ]

    def _empirical_framework(self, title: str, elements: Dict) -> Dict:
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

    def _empirical_queries(self, title: str, elements: Dict) -> List[Dict]:
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

    def _theoretical_framework(self, title: str) -> Dict:
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

    def _theoretical_queries(self, title: str) -> List[Dict]:
        """理论型检索查询"""
        return [
            {'query': f'{title} 理论 起源', 'section': '理论起源'},
            {'query': f'{title} 理论 发展', 'section': '理论发展'},
            {'query': f'{title} 研究现状', 'section': '当前研究现状'},
            {'query': f'{title} 理论 应用', 'section': '理论应用'}
        ]

    def _general_framework(self, title: str) -> Dict:
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

    def _general_queries(self, title: str) -> List[Dict]:
        """通用检索查询"""
        return [
            {'query': f'{title} 研究现状', 'section': '研究现状'},
            {'query': f'{title} 综述', 'section': '研究现状'},
            {'query': f'{title} 发展趋势', 'section': '发展趋势'}
        ]
