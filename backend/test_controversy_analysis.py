"""
测试观点碰撞分析功能
"""
import asyncio
import os
from services.controversy_analyzer import (
    ViewpointExtractor,
    ControversyAnalyzer,
    ControversySectionGenerator,
    StructuredReviewGenerator,
    generate_controversy_section,
    analyze_viewpoints_and_controversies
)


# 模拟论文数据
MOCK_PAPERS = [
    {
        "id": "1",
        "title": "QFD在质量管理中的应用效果研究",
        "abstract": "本研究通过实证分析发现，QFD方法能显著提高产品质量和客户满意度。我们调查了100家制造企业，结果显示实施QFD的企业产品缺陷率降低了30%。",
        "year": 2020,
        "authors": ["张三"]
    },
    {
        "id": "2",
        "title": "QFD实施的成本效益分析",
        "abstract": "虽然QFD能提高产品质量，但本研究发现其实施成本高昂。对50家企业的案例分析显示，QFD实施平均耗时6个月，成本增加20%，可能抵消其带来的质量收益。",
        "year": 2021,
        "authors": ["李四"]
    },
    {
        "id": "3",
        "title": "中小企业QFD应用模式研究",
        "abstract": "本研究探讨了QFD在中小企业中的适用性。研究发现，项目规模适中的企业使用简化版QFD效果最佳，大型企业则可能面临组织协调困难。",
        "year": 2022,
        "authors": ["王五"]
    },
    {
        "id": "4",
        "title": "媒体关注度对盈余管理的监督作用",
        "abstract": "基于上市公司数据的研究表明，高媒体关注度能够发挥监督职能，有效抑制企业的盈余管理行为。媒体报道增加了信息透明度，降低了管理层操纵利润的空间。",
        "year": 2019,
        "authors": ["赵六"]
    },
    {
        "id": "5",
        "title": "媒体关注与盈余管理：业绩压力的调节作用",
        "abstract": "本研究发现，在特定的业绩压力下，高媒体关注度反而可能诱发企业进行应计盈余管理。当企业面临业绩目标难以实现时，媒体关注可能迫使管理层采取激进的会计政策。",
        "year": 2020,
        "authors": ["钱七"]
    },
]


async def test_viewpoint_extraction():
    """测试观点提取"""
    print("=" * 80)
    print("测试1: 观点提取")
    print("=" * 80)

    extractor = ViewpointExtractor()

    # 测试简单提取（不使用LLM）
    viewpoints = await extractor.extract_viewpoints(MOCK_PAPERS, "QFD质量管理")

    print(f"\n提取到 {len(viewpoints)} 个观点:\n")
    for i, vp in enumerate(viewpoints, 1):
        print(f"{i}. {vp['title']}")
        print(f"   观点: {vp['viewpoint'][:100]}...")
        print(f"   方法: {vp['methodology'] or '未说明'}")
        print()


async def test_controversy_analysis():
    """测试争议分析"""
    print("=" * 80)
    print("测试2: 争议分析")
    print("=" * 80)

    # 检查API配置
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️  警告: DEEPSEEK_API_KEY 未配置，使用简单分析模式\n")

    analyzer = ControversyAnalyzer()
    extractor = ViewpointExtractor()

    # 提取观点
    viewpoints = await extractor.extract_viewpoints(MOCK_PAPERS, "QFD质量管理")

    # 分析争议
    analysis = await analyzer.analyze_controversies(viewpoints, "QFD质量管理", "应用效果")

    print(f"\n争议总结: {analysis.get('summary', '')}\n")

    controversies = analysis.get("controversies", [])
    print(f"发现 {len(controversies)} 个争议点:\n")

    for i, controversy in enumerate(controversies, 1):
        print(f"争议点{i}: {controversy.get('issue', '')}")
        print(f"  观点A: {controversy.get('side_a', {}).get('viewpoint', '')}")
        print(f"  观点B: {controversy.get('side_b', {}).get('viewpoint', '')}")
        causes = controversy.get('possible_causes', [])
        if causes:
            print(f"  可能原因:")
            for cause in causes:
                print(f"    - {cause}")
        print()


async def test_controversy_section_generation():
    """测试争议章节生成"""
    print("=" * 80)
    print("测试3: 争议章节生成")
    print("=" * 80)

    generator = ControversySectionGenerator()

    # 生成争议章节
    cited_indices = [1, 2, 3, 4, 5]  # 模拟已引用的文献编号

    controversy_section = await generator.generate_controversy_section(
        papers=MOCK_PAPERS,
        topic="QFD质量管理",
        section_name="应用效果评价",
        cited_indices=cited_indices
    )

    print("\n生成的争议与对话章节:")
    print("-" * 80)
    print(controversy_section)
    print("-" * 80)


async def test_structured_review_generation():
    """测试结构化综述生成"""
    print("\n" + "=" * 80)
    print("测试4: 结构化综述生成（带争议分析）")
    print("=" * 80)

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️  需要配置 DEEPSEEK_API_KEY 才能测试完整功能")
        return

    generator = StructuredReviewGenerator()

    sections = ["引言", "QFD方法概述", "应用效果评价", "实施挑战"]

    review, cited_papers, stats = await generator.generate_review_with_controversies(
        topic="QFD在质量管理中的应用",
        papers=MOCK_PAPERS,
        sections=sections,
        model="deepseek-chat"
    )

    print(f"\n生成统计:")
    print(f"  总章节数: {stats['total_sections']}")
    print(f"  包含争议的章节: {stats['sections_with_controversies']}")
    print(f"  各章节争议点数: {stats['controversy_stats']}")

    print(f"\n综述长度: {len(review)} 字符")
    print(f"引用文献数: {len(cited_papers)}")


async def test_api_export():
    """测试导出API"""
    print("\n" + "=" * 80)
    print("测试5: 便捷API")
    print("=" * 80)

    # 测试 generate_controversy_section
    section = await generate_controversy_section(
        papers=MOCK_PAPERS,
        topic="QFD质量管理",
        section_name="应用效果",
        cited_indices=[1, 2, 3]
    )

    print("生成的争议章节:")
    print(section[:300] + "..." if len(section) > 300 else section)

    # 测试 analyze_viewpoints_and_controversies
    print("\n" + "-" * 80 + "\n")

    result = await analyze_viewpoints_and_controversies(MOCK_PAPERS, "QFD质量管理")

    print(f"分析结果:")
    print(f"  观点数: {len(result['viewpoints'])}")
    print(f"  争议点数: {len(result['controversies'].get('controversies', []))}")
    print(f"  总结: {result['controversies'].get('summary', '')}")


async def test_controversy_with_real_example():
    """测试真实案例：媒体关注与盈余管理"""
    print("\n" + "=" * 80)
    print("测试6: 真实案例分析 - 媒体关注与盈余管理")
    print("=" * 80)

    # 使用真实相关的论文
    media_papers = [
        {
            "id": "1",
            "title": "Media Coverage and Earnings Management: The Monitoring Role",
            "abstract": "We find that high media coverage acts as a monitoring mechanism, reducing earnings management practices.",
            "year": 2019
        },
        {
            "id": "2",
            "title": "Media Attention and Earnings Management under Performance Pressure",
            "abstract": "Contrary to conventional wisdom, we find that media attention may increase earnings management when firms face performance pressure.",
            "year": 2020
        },
        {
            "id": "3",
            "title": "Corporate Governance as a Moderator in Media-Earnings Relation",
            "abstract": "The effect of media coverage on earnings management depends on corporate governance quality. Well-governed firms benefit more from media monitoring.",
            "year": 2021
        },
    ]

    generator = ControversySectionGenerator()

    controversy_section = await generator.generate_controversy_section(
        papers=media_papers,
        topic="媒体关注与盈余管理",
        section_name="监督效应",
        cited_indices=[1, 2, 3]
    )

    print("\n生成的争议与对话章节:")
    print("-" * 80)
    print(controversy_section)
    print("-" * 80)


async def main():
    """运行所有测试"""
    await test_viewpoint_extraction()
    await test_controversy_analysis()
    await test_controversy_section_generation()
    await test_structured_review_generation()
    await test_api_export()
    await test_controversy_with_real_example()

    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
