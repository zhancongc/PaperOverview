"""
测试引用拆分功能
演示如何将[1-5]式引用拆分为结构化表述
"""
import asyncio
from services.citation_splitter import (
    CitationSplitter,
    StructuredReviewFormatter,
    split_continuous_citations,
    detect_continuous_citations
)


# 模拟论文数据
MOCK_PAPERS = [
    {
        "id": "1",
        "title": "Media Coverage and Earnings Management: Evidence from Chinese Listed Firms",
        "abstract": "Using a sample of 2,500 firm-year observations, we find that high media coverage reduces earnings management.",
        "year": 2019,
        "authors": ["Zhang", "Wang", "Li"]
    },
    {
        "id": "2",
        "title": "Media Attention and Corporate Governance",
        "abstract": "This study examines how media attention affects corporate governance quality.",
        "year": 2020,
        "authors": ["Liu", "Chen"]
    },
    {
        "id": "3",
        "title": "The Monitoring Role of Media in Emerging Markets",
        "abstract": "We investigate the monitoring effect of media in 20 emerging markets.",
        "year": 2018,
        "authors": ["Wang", "Zhao", "Sun"]
    },
    {
        "id": "4",
        "title": "Social Media and Firm Disclosure",
        "abstract": "This paper explores how social media affects firm disclosure practices.",
        "year": 2021,
        "authors": ["Li", "Yang"]
    },
    {
        "id": "5",
        "title": "Media Pressure and Earnings Management",
        "abstract": "Contrary findings show media pressure may increase earnings management under certain conditions.",
        "year": 2022,
        "authors": ["Chen", "Wu", "Liu"]
    },
    {
        "id": "6",
        "title": "QFD Implementation in Manufacturing",
        "abstract": "A study of QFD implementation in 100 manufacturing firms.",
        "year": 2017,
        "authors": ["Wu", "Chen"]
    },
]


async def test_detection():
    """测试连续引用检测"""
    print("=" * 80)
    print("测试1: 连续引用检测")
    print("=" * 80)

    splitter = CitationSplitter()

    # 测试文本
    test_texts = [
        "多项研究表明该效应显著[1-5]",
        "现有文献支持这一观点[1,2,3,4,5]",
        "相关研究包括[1][2][3][4][5]",
        "只有两篇文献[1-2]，不需要拆分",
        "单一引用[1]，也不需要拆分"
    ]

    for text in test_texts:
        print(f"\n测试文本: {text}")
        citations = splitter.detect_continuous_citations(text)
        if citations:
            for c in citations:
                print(f"  ✅ 检测到连续引用: {c['match_str']}, 包含{len(c['citation_indices'])}篇文献")
        else:
            print(f"  ⏭️  不需要拆分（引用数≤3）")


async def test_splitting():
    """测试引用拆分"""
    print("\n" + "=" * 80)
    print("测试2: 引用拆分")
    print("=" * 80)

    splitter = CitationSplitter()

    # 测试文本段落
    test_paragraph = """关于媒体关注对盈余管理的影响，多项研究提供了实证支持[1-5]。这些研究一致发现媒体关注度与盈余管理程度呈显著负相关。"""

    print(f"\n原始文本:\n{test_paragraph}")

    # 拆分引用
    split_text = await splitter.split_citation(
        test_paragraph,
        MOCK_PAPERS,
        citation_indices=[1, 2, 3, 4, 5],
        context="媒体关注与盈余管理"
    )

    print(f"\n拆分后:\n{split_text}")


async def test_batch_splitting():
    """测试批量拆分"""
    print("\n" + "=" * 80)
    print("测试3: 批量拆分整篇综述")
    print("=" * 80)

    # 模拟一篇包含多处连续引用的综述
    sample_review = """# 媒体关注与盈余管理研究综述

## 引言

媒体关注作为重要的外部治理机制，近年来受到广泛关注[1-4]。多项研究发现媒体能够发挥监督职能[5-8]。

## 主体部分

关于媒体监督的效应，现有研究提供了丰富证据[1-5]。Zhang等(2019)基于中国上市公司数据发现媒体关注度与盈余管理呈负相关[1]。

然而，也有研究指出了媒体关注的潜在负面影响[9-12]。特别是在特定情境下，媒体压力可能诱发机会主义行为[13-15]。

## 结论

综上所述，媒体监督效应具有复杂性[1-3,16-18]。未来研究需要进一步探讨其边界条件[19-20]。
"""

    print("\n原始综述:")
    print("-" * 80)
    print(sample_review)
    print("-" * 80)

    # 批量拆分
    formatter = StructuredReviewFormatter()
    formatted_review, stats = await formatter.format_review(
        content=sample_review,
        papers=MOCK_PAPERS,
        enable_splitting=True
    )

    print(f"\n格式化后的综述:")
    print("-" * 80)
    print(formatted_review)
    print("-" * 80)

    print(f"\n格式化统计:")
    print(f"  原始长度: {stats['original_length']} 字符")
    print(f"  最终长度: {stats['final_length']} 字符")
    print(f"  拆分处数: {stats['citations_split']}")
    print(f"\n{stats.get('split_summary', '')}")


async def test_author_formatting():
    """测试带作者信息的引用格式化"""
    print("\n" + "=" * 80)
    print("测试4: 带作者的引用格式化")
    print("=" * 80)

    formatter = StructuredReviewFormatter()

    for i, paper in enumerate(MOCK_PAPERS[:3], 1):
        # 中文格式
        citation_cn = formatter.format_citation_with_authors(paper, i, style="chinese")
        print(f"{paper['title'][:40]}...")
        print(f"  中文格式: {citation_cn}")

        # 西文格式
        citation_en = formatter.format_citation_with_authors(paper, i, style="western")
        print(f"  西文格式: {citation_en}")
        print()


async def test_practical_example():
    """演示实际使用场景"""
    print("\n" + "=" * 80)
    print("演示: 实际使用场景")
    print("=" * 80)

    print("\n场景：将综述中的笼统引用替换为结构化表述\n")

    # 原始段落（包含笼统引用）
    original = """关于QFD在质量管理中的应用效果，多项实证研究提供了支持[1-5]。这些研究普遍发现QFD能够显著提升产品质量和客户满意度。"""

    print("原始段落:")
    print(f"  {original}")

    # 拆分后（使用规则拆分）
    splitter = CitationSplitter()
    split_text = await splitter.split_citation(
        original,
        MOCK_PAPERS[:5],  # 使用前5篇论文
        citation_indices=[1, 2, 3, 4, 5],
        context="QFD质量管理应用"
    )

    print("\n拆分后:")
    print(f"  {split_text}")

    print("\n效果对比:")
    print("  ❌ 原始: ...提供了支持[1-5]。")
    print("  ✅ 拆分: ...提供了支持。Zhang等[1]、Liu等[2]发现...；而Wang等[3]则指出...")
    print("\n优势:")
    print("  - 清晰展示不同研究者的观点")
    print("  - 避免读者需要逐个查找参考文献")
    print("  - 提高综述的可读性和逻辑性")


async def test_different_citation_styles():
    """测试不同引用格式的拆分"""
    print("\n" + "=" * 80)
    print("测试5: 不同引用格式的拆分")
    print("=" * 80)

    splitter = CitationSplitter()

    # 不同格式的连续引用
    test_cases = [
        "[1-5]",
        "[1,2,3,4,5]",
        "[1][2][3][4][5]",
        "[1, 2, 3, 4, 5]"
    ]

    print("\n解析不同格式的连续引用:\n")
    for case in test_cases:
        indices = splitter._parse_citation_indices(case)
        print(f"  {case} → {indices}")


async def demo_before_after():
    """演示拆分前后的对比"""
    print("\n" + "=" * 80)
    print("演示: 拆分前后对比")
    print("=" * 80)

    examples = [
        {
            "before": "多项研究发现媒体监督能抑制盈余管理[1-6]",
            "after": "多项研究发现媒体监督能抑制盈余管理。其中，Zhang等[1]基于中国上市公司数据发现显著负相关；Liu等[2]从公司治理角度证实了这一效应；Wang等[3]在新兴市场研究中也得到类似结论。"
        },
        {
            "before": "关于QFD的效果，现有研究提供了丰富证据[1-5,7-9]",
            "after": "关于QFD的效果，现有研究提供了丰富证据。Wu等[6]在制造业的应用研究中显示QFD能提升产品质量；而Chen等[5]则指出在某些情境下QFD可能存在成本约束。"
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n示例{i}:")
        print(f"  ❌ 拆分前: {example['before']}")
        print(f"  ✅ 拆分后: {example['after']}")


async def main():
    """运行所有测试"""
    await test_detection()
    await test_splitting()
    await test_batch_splitting()
    await test_author_formatting()
    await test_practical_example()
    await test_different_citation_styles()
    await demo_before_after()

    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
