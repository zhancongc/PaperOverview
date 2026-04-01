"""
测试自然统计数据嵌入功能
演示如何将数据自然融入叙述，避免AI痕迹
"""
import asyncio
from services.natural_statistics import (
    NaturalStatisticsIntegrator,
    NaturalReviewGenerator,
    generate_natural_review_summary,
    format_natural_citation,
    EXAMPLES
)


# 模拟论文数据（包含统计数据）
MOCK_PAPERS = [
    {
        "id": "1",
        "title": "QFD Implementation Reduces Product Defects in Manufacturing",
        "abstract": "Using a sample of 2,000 manufacturing firms, we find that QFD implementation significantly reduces product defects. The defect rate decreased by 35% after QFD adoption, with high statistical significance (p<0.001).",
        "year": 2021,
        "authors": ["Zhang", "Wang"],
        "is_english": True,
        "statistics": {
            "n": 2000,
            "percentage": 35,
            "p": 0.0001
        }
    },
    {
        "id": "2",
        "title": "QFD Effectiveness Varies by Organizational Context",
        "abstract": "Based on a survey of 300 service companies, we find that QFD effectiveness attenuates in organizations with low process standardization. The effect size is moderate (Cohen's d=0.45) and not always significant.",
        "year": 2019,
        "authors": ["Wang", "Li"],
        "is_english": True,
        "statistics": {
            "n": 300,
            "cohens_d": 0.45,
            "p": 0.08
        }
    },
    {
        "id": "3",
        "title": "QFD and Quality Performance: A Meta-Analysis",
        "abstract": "Meta-analysis of 50 studies shows strong positive correlation between QFD and quality performance (r=0.72, p<0.001). The relationship is robust across different industries.",
        "year": 2022,
        "authors": ["Chen", "Liu"],
        "is_english": True,
        "statistics": {
            "r": 0.72,
            "p": 0.0001,
            "n": 50000  # meta-analysis sample
        }
    },
    {
        "id": "4",
        "title": "QFD在制造业质量管理中的应用研究",
        "abstract": "本文以500家制造业企业为样本，发现实施QFD后产品合格率提升28%。",
        "year": 2020,
        "authors": ["李明", "王强"],
        "is_english": False,
        "statistics": {
            "n": 500,
            "percentage": 28,
            "p": 0.005
        }
    },
    {
        "id": "5",
        "title": "QFD实施与企业绩效：基于A股上市公司的实证研究",
        "abstract": "研究发现实施QFD的企业，其ROA比未实施企业高出15%（OR=1.15, p<0.05）。",
        "year": 2021,
        "authors": ["刘伟", "张华"],
        "is_english": False,
        "statistics": {
            "n": 800,
            "or": 1.15,
            "p": 0.03,
            "percentage": 15
        }
    },
]


async def test_should_use_statistics():
    """测试统计数据使用判断"""
    print("=" * 80)
    print("测试1: 统计数据使用判断")
    print("=" * 80)

    integrator = NaturalStatisticsIntegrator()

    for i, paper in enumerate(MOCK_PAPERS, 1):
        should_use, reason = integrator.should_use_statistics(paper)

        print(f"\n论文{i}: {paper['title'][:50]}...")
        print(f"  样本量: {paper.get('statistics', {}).get('n', 'N/A')}")
        print(f"  是否使用数据: {'是' if should_use else '否'}")
        print(f"  原因: {reason}")


async def test_natural_citation_format():
    """测试自然引用格式"""
    print("\n" + "=" * 80)
    print("测试2: 自然引用格式")
    print("=" * 80)

    integrator = NaturalStatisticsIntegrator()

    print("\n场景：带研究发现描述的引用")
    for i, paper in enumerate(MOCK_PAPERS[:3], 1):
        finding = paper["abstract"].split("。")[0][:50]
        citation = integrator.format_natural_citation(paper, i, finding)
        print(f"  {citation}")

    print("\n场景：简单引用编号")
    for i, paper in enumerate(MOCK_PAPERS[:3], 1):
        citation = integrator.format_natural_citation(paper, i)
        print(f"  论文{i}: {citation}")


async def test_data_embedding():
    """测试数据嵌入"""
    print("\n" + "=" * 80)
    print("测试3: 数据嵌入")
    print("=" * 80)

    integrator = NaturalStatisticsIntegrator()

    test_cases = [
        (MOCK_PAPERS[0], "QFD能有效降低产品缺陷率"),
        (MOCK_PAPERS[1], "QFD的效果受组织情境影响"),
        (MOCK_PAPERS[2], "QFD与质量绩效呈强相关"),
        (MOCK_PAPERS[3], "QFD能提升产品合格率"),
    ]

    for paper, statement in test_cases:
        stat = paper.get("statistics", {})
        key_stat = integrator._select_key_statistic(stat, paper)
        embedded = integrator._embed_data_in_statement(statement, key_stat, 1)

        print(f"\n陈述: {statement}")
        print(f"  关键统计: {key_stat}")
        print(f"  嵌入后: {embedded}")


async def test_natural_summary():
    """测试自然综述摘要生成"""
    print("\n" + "=" * 80)
    print("测试4: 自然综述摘要生成")
    print("=" * 80)

    integrator = NaturalStatisticsIntegrator()

    topic = "QFD在质量管理中的应用效果"

    summary = await integrator.generate_natural_summary(MOCK_PAPERS, topic)

    print(f"\n生成的综述摘要:")
    print("-" * 80)
    print(summary)
    print("-" * 80)


async def test_natural_review_generation():
    """测试自然综述生成"""
    print("\n" + "=" * 80)
    print("测试5: 自然综述生成")
    print("=" * 80)

    generator = NaturalReviewGenerator()

    topic = "QFD在质量管理中的应用效果"

    review = await generator.generate_natural_review(topic, MOCK_PAPERS)

    print(f"\n生成的综述:")
    print("-" * 80)
    print(review)
    print("-" * 80)


async def test_ai_vs_natural_comparison():
    """对比AI风格和自然风格"""
    print("\n" + "=" * 80)
    print("演示: AI风格 vs 自然风格对比")
    print("=" * 80)

    print("\n❌ AI风格（堆砌数据）:")
    print(EXAMPLES["ai_style"]["example"])

    print("\n✅ 自然风格（融入叙述）:")
    print(EXAMPLES["natural_style"]["example"])

    print("\n💡 关键区别:")
    print("  1. AI风格：每个引用都带(OR=0.65, p<0.001)")
    print("  2. 自然风格：只对重要发现嵌入具体数据")
    print("  3. AI风格：机械罗列")
    print("  4. 自然风格：数据服务于叙事")


async def test_practical_example():
    """演示实际应用场景"""
    print("\n" + "=" * 80)
    print("演示: 实际应用场景")
    print("=" * 80)

    print("\n场景：为QFD综述生成一段关于效果的论述\n")

    integrator = NaturalStatisticsIntegrator()

    # 生成自然综述
    topic = "QFD的实际效果"
    summary = await integrator.generate_natural_summary(MOCK_PAPERS, topic)

    print("生成的自然综述:")
    print("-" * 80)
    print(summary)
    print("-" * 80)

    print("\n分析:")
    print("  - 并非每个引用都带数据")
    print("  - 数据自然融入结论")
    print("  - 突出重要发现（大样本、强效应）")
    print("  - 避免机械的(OR=xxx, p<xxx)格式")


async def test_breakthrough_detection():
    """测试突破性发现检测"""
    print("\n" + "=" * 80)
    print("测试6: 突破性发现检测")
    print("=" * 80)

    integrator = NaturalStatisticsIntegrator()

    breakthrough_papers = [
        {
            "title": "强保护效应研究",
            "statistics": {"or": 0.3, "p": 0.001},
            "abstract": "OR=0.3表示强保护效应"
        },
        {
            "title": "强风险效应研究",
            "statistics": {"or": 3.5, "p": 0.001},
            "abstract": "OR=3.5表示强风险效应"
        },
        {
            "title": "强相关研究",
            "statistics": {"r": 0.85, "p": 0.001},
            "abstract": "r=0.85表示强相关"
        },
        {
            "title": "大效应量研究",
            "statistics": {"cohens_d": 1.2, "p": 0.001},
            "abstract": "Cohen's d=1.2表示大效应"
        },
    ]

    print("\n突破性发现（会使用数据）:")
    for paper in breakthrough_papers:
        is_breakthrough = integrator._is_breakthrough_finding(paper, paper["statistics"])
        should_use, reason = integrator.should_use_statistics(paper)
        print(f"  {paper['title']}: OR/r/d={list(paper['statistics'].values())[0]}")
        print(f"    突破性: {is_breakthrough}, 原因: {reason}")

    normal_papers = [
        {
            "title": "弱效应研究",
            "statistics": {"or": 1.1, "p": 0.04},
            "abstract": "OR=1.1效应较弱"
        },
        {
            "title": "中等相关研究",
            "statistics": {"r": 0.3, "p": 0.02},
            "abstract": "r=0.3中等相关"
        },
    ]

    print("\n常规发现（可能不使用数据）:")
    for paper in normal_papers:
        is_breakthrough = integrator._is_breakthrough_finding(paper, paper["statistics"])
        should_use, reason = integrator.should_use_statistics(paper)
        print(f"  {paper['title']}: OR/r={list(paper['statistics'].values())[0]}")
        print(f"    突破性: {is_breakthrough}, 使用数据: {should_use}, 原因: {reason}")


async def main():
    """运行所有测试"""
    await test_should_use_statistics()
    await test_natural_citation_format()
    await test_data_embedding()
    await test_natural_summary()
    await test_natural_review_generation()
    await test_ai_vs_natural_comparison()
    await test_practical_example()
    await test_breakthrough_detection()

    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
