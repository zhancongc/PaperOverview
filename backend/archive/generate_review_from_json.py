#!/usr/bin/env python3
"""
直接从 JSON 文件加载论文并生成综述
使用 303 篇 Semantic Scholar 搜索结果作为阶段5的输入
"""
import os
import sys
import json
import asyncio
from typing import List, Dict
from dotenv import load_dotenv

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env 文件
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"已加载环境变量 from {dotenv_path}")

from services.review_generator_fc_unified import ReviewGeneratorFCUnified


def load_papers_from_json(json_path: str) -> List[Dict]:
    """
    从 JSON 文件加载论文

    Args:
        json_path: JSON 文件路径

    Returns:
        展平的论文列表
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_papers = []
    for category, papers in data.items():
        for paper in papers:
            # 确保论文有必要的字段
            if 'source' not in paper:
                paper['source'] = 'semantic_scholar'
            if 'category' not in paper:
                paper['category'] = category
            all_papers.append(paper)

    return all_papers


def create_framework_for_cas() -> Dict:
    """
    为计算机代数系统主题创建框架（大纲）

    Returns:
        framework 字典
    """
    return {
        'outline': {
            'introduction': {
                'focus': '介绍计算机代数系统（CAS）的发展背景、重要性以及在数学、科学和工程领域的广泛应用',
                'key_papers': []
            },
            'body_sections': [
                {
                    'title': '计算机代数系统的发展历程与主要系统',
                    'focus': '梳理 CAS 的历史发展脉络，介绍主流系统如 Mathematica、Maple、Maxima、SageMath、OSCAR 等的特点和应用场景',
                    'key_points': [
                        'CAS 的起源与早期发展',
                        '主流计算机代数系统比较',
                        '开源与商业 CAS 的差异',
                        '现代 CAS 的架构设计'
                    ],
                    'comparison_points': [
                        '不同系统的功能特点对比',
                        '开源 vs 商业 CAS 的优劣势'
                    ],
                    'search_keywords': [
                        'computer algebra system history',
                        'Mathematica Maple Maxima comparison',
                        'open source CAS software'
                    ]
                },
                {
                    'title': '符号计算核心算法与技术',
                    'focus': '探讨 CAS 中的核心符号计算算法，包括符号积分、Gröbner 基、多项式运算、化简等关键技术',
                    'key_points': [
                        '符号积分算法与 Risch 算法',
                        'Gröbner 基理论与应用',
                        '多项式代数与符号化简',
                        '计算机代数中的数学逻辑'
                    ],
                    'comparison_points': [
                        '不同算法的计算效率对比',
                        '数值计算与符号计算的互补性'
                    ],
                    'search_keywords': [
                        'symbolic integration algorithms',
                        'Gröbner basis computer algebra',
                        'polynomial symbolic computation'
                    ]
                },
                {
                    'title': '计算机代数系统在教育中的应用',
                    'focus': '分析 CAS 在数学教育、STEM 教育中的应用效果、挑战和最佳实践',
                    'key_points': [
                        'CAS 提升数学学习效果的实证研究',
                        '针对视障学生的无障碍 CAS 设计',
                        '高等教育中的 CAS 教学实践',
                        'CAS 应用于教育的挑战与对策'
                    ],
                    'comparison_points': [
                        '传统教学与 CAS 辅助教学的效果对比',
                        '不同教育阶段的 CAS 应用策略差异'
                    ],
                    'search_keywords': [
                        'CAS in mathematics education',
                        'computer algebra system for visually impaired',
                        'STEM education with CAS'
                    ]
                },
                {
                    'title': 'CAS 在科学研究与工程中的应用',
                    'focus': '综述计算机代数系统在物理学、工程学、计算机科学等领域的实际应用案例和研究成果',
                    'key_points': [
                        '理论物理中的符号计算应用',
                        '有限元分析与工程计算',
                        '密码学与安全中的代数方法',
                        '科研工作流中的 CAS 集成'
                    ],
                    'comparison_points': [
                        '不同领域的 CAS 应用模式对比',
                        'CAS 与其他计算工具的协同'
                    ],
                    'search_keywords': [
                        'CAS in scientific research',
                        'computer algebra engineering applications',
                        'symbolic computation physics'
                    ]
                },
                {
                    'title': '计算机代数系统的挑战与未来方向',
                    'focus': '讨论当前 CAS 面临的技术挑战、性能瓶颈以及未来发展趋势',
                    'key_points': [
                        '大规模符号计算的性能挑战',
                        '符号与数值混合计算',
                        'AI 与机器学习在 CAS 中的应用',
                        'Web 端与云端 CAS 的发展'
                    ],
                    'comparison_points': [
                        '不同技术路线的发展前景对比',
                        '传统 CAS 与新一代工具的差异'
                    ],
                    'search_keywords': [
                        'CAS future directions',
                        'symbolic computation challenges',
                        'AI computer algebra integration'
                    ]
                }
            ],
            'conclusion': {
                'focus': '总结计算机代数系统的研究现状、指出不足和未来方向'
            }
        }
    }


async def main():
    """主函数"""
    # 配置
    json_path = os.path.join(
        os.path.dirname(__file__),
        'semantic_scholar_results_20260405_114423.json'
    )

    topic = "计算机代数系统（CAS）的发展、技术与应用研究综述"

    # 加载论文
    print("=" * 80)
    print("加载论文...")
    print("=" * 80)
    papers = load_papers_from_json(json_path)
    print(f"共加载 {len(papers)} 篇论文")

    # 统计信息
    papers_with_abstract = sum(1 for p in papers if p.get('abstract'))
    print(f"  - 有摘要: {papers_with_abstract} 篇")
    print(f"  - 无摘要: {len(papers) - papers_with_abstract} 篇")

    # 按年份统计
    from collections import Counter
    year_counts = Counter(p.get('year', 'Unknown') for p in papers)
    print("\n按年份统计:")
    for year in sorted(year_counts.keys()):
        print(f"  - {year}: {year_counts[year]} 篇")

    # 创建框架
    print("\n" + "=" * 80)
    print("创建综述大纲...")
    print("=" * 80)
    framework = create_framework_for_cas()
    outline = framework['outline']
    print(f"引言: {outline['introduction']['focus']}")
    print(f"\n主体章节:")
    for i, section in enumerate(outline['body_sections'], 1):
        print(f"  {i}. {section['title']}")
        print(f"     - {section['focus']}")

    # 获取 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("\n错误: 请设置 DEEPSEEK_API_KEY 环境变量")
        return

    # 生成综述
    print("\n" + "=" * 80)
    print("开始生成综述...")
    print("=" * 80)

    generator = ReviewGeneratorFCUnified(api_key=api_key)

    # 配置参数
    target_citation_count = 80  # 目标引用 80 篇
    min_citation_count = 60     # 最小引用 60 篇

    review, cited_papers = await generator.generate_review(
        topic=topic,
        papers=papers,
        framework=framework,
        model="deepseek-reasoner",
        target_citation_count=target_citation_count,
        min_citation_count=min_citation_count,
        recent_years_ratio=0.5,
        english_ratio=0.8,
        enable_reasoning=False
    )

    # 保存结果
    if review:
        output_path = os.path.join(
            os.path.dirname(__file__),
            'cas_review_result.md'
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(review)

        print("\n" + "=" * 80)
        print(f"✓ 综述已保存至: {output_path}")
        print(f"✓ 总字数: {len(review)} 字符")
        print(f"✓ 引用文献: {len(cited_papers)} 篇")
        print("=" * 80)
    else:
        print("\n错误: 综述生成失败")


if __name__ == "__main__":
    asyncio.run(main())
