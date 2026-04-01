"""
测试综述润色功能
演示如何消除AI腔，让语言更干练
"""
import asyncio
from services.review_polisher import (
    AIToneEliminator,
    ReviewPolisher,
    polish_review_text,
    detect_ai_tone
)


# 模拟包含AI腔的综述文本
AI_TONE_EXAMPLE = """# 媒体关注与盈余管理研究综述

## 引言

近年来，随着资本市场的快速发展，公司治理问题日益受到学术界的关注。值得注意的是，媒体作为重要的外部治理机制，其在抑制盈余管理方面的作用引起了广泛讨论。

换言之，媒体关注能够通过信息传播和声誉机制发挥作用。显而易见，这种监督效应对维护市场秩序具有重要意义。

## 主体部分

一方面，多项研究发现媒体关注能显著抑制盈余管理；另一方面，也有研究指出了其潜在的局限性。此外，媒体关注的监督效果还受到公司内部治理水平的影响。

具体来说，Zhang等[1]基于中国上市公司数据，通过实证分析方法发现媒体关注度与盈余管理呈显著负相关。研究结果表明，媒体负面报道每增加10%，公司进行盈余管理的概率降低约25%。换言之，媒体监督效应十分显著。

值得注意的是，Li等[2]的研究进一步探讨了这一机制的边界条件。事实上，他们发现在公司治理较弱的企业中，媒体监督的作用更加突出。可以肯定的是，这为理解媒体监督的异质性效应提供了新证据。

另一方面，Chen等[3]的研究则指出了媒体关注可能带来的负面影响。然而，这种负面影响主要体现在特定的情境下。综上所述，媒体关注的效应具有复杂性。

## 结论

总而言之，现有研究总体上支持媒体监督的积极作用。与此同时，我们也需要关注其潜在的边界条件和调节因素。有鉴于此，未来的研究应该进一步探讨不同情境下的差异化效应。

显而易见，这一领域的研究具有重要的理论价值和实践意义。毫无疑问，随着媒体形态的不断演进，相关研究也将持续深化。
"""


async def test_ai_tone_detection():
    """测试AI腔检测"""
    print("=" * 80)
    print("测试1: AI腔检测")
    print("=" * 80)

    result = detect_ai_tone(AI_TONE_EXAMPLE)

    print(f"\n检测结果:")
    print(f"  AI腔词汇数: {result['ai_tone_count']}")
    print(f"  AI腔占比: {result['ai_tone_ratio']:.2%}")
    print(f"  检测到的模式: {len(result['detected_patterns'])} 种")

    print(f"\n前5个AI腔模式:")
    for i, pattern in enumerate(result['detected_patterns'][:5], 1):
        print(f"  {i}. {pattern['pattern'][:40]}... (出现{pattern['count']}次, {pattern['type']})")


async def test_rule_polishing():
    """测试规则润色"""
    print("\n" + "=" * 80)
    print("测试2: 规则润色")
    print("=" * 80)

    eliminator = AIToneEliminator()

    # 只取前500字演示
    sample_text = AI_TONE_EXAMPLE[:500]

    print(f"\n原文 (前{len(sample_text)}字):")
    print("-" * 80)
    print(sample_text)
    print("-" * 80)

    # 规则润色
    polished_text, report = eliminator.polish_with_rules(sample_text)

    print(f"\n润色后:")
    print("-" * 80)
    print(polished_text)
    print("-" * 80)

    print(f"\n润色报告:")
    print(f"  删除: {len(report['deletions'])} 处")
    print(f"  替换: {len(report['replacements'])} 处")
    print(f"  总改动: {report['total_changes']} 处")
    print(f"  压缩率: {report['compression_ratio']:.1%}")

    if report['deletions']:
        print(f"\n删除示例:")
        for d in report['deletions'][:3]:
            print(f"  - {d['original']}")

    if report['replacements']:
        print(f"\n替换示例:")
        for r in report['replacements'][:3]:
            print(f"  - {r['original']} → {r['replacement']}")


async def test_full_polishing():
    """测试完整润色流程"""
    print("\n" + "=" * 80)
    print("测试3: 完整润色流程")
    print("=" * 80)

    import os
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️  DEEPSEEK_API_KEY 未配置，仅使用规则润色\n")

    polisher = ReviewPolisher()

    options = {
        "method": "hybrid" if os.getenv("DEEPSEEK_API_KEY") else "rule",
        "style": "academic",
        "remove_ai_tone": True,
        "check_citations": True,
        "enhance_readability": True
    }

    # 润色全文
    polished_content, report = await polisher.polish(AI_TONE_EXAMPLE, options)

    print(f"\n润色后的综述:")
    print("-" * 80)
    print(polished_content)
    print("-" * 80)

    print(f"\n{report['summary']}")


async def test_before_after_comparison():
    """测试前后对比"""
    print("\n" + "=" * 80)
    print("演示: 润色前后对比")
    print("=" * 80)

    examples = [
        {
            "before": "近年来，随着资本市场的快速发展，媒体治理受到广泛关注。值得注意的是，多项研究发现媒体监督能抑制盈余管理。换言之，媒体具有重要的治理功能。",
            "after": "近五年，媒体治理受到广泛关注。多项研究发现媒体监督能抑制盈余管理，具有重要的治理功能。"
        },
        {
            "before": "一方面，Zhang等[1]发现显著效应；另一方面，Li等[2]指出了边界条件。此外，Wang等[3]提供了新的证据。",
            "after": "Zhang等[1]发现显著效应；Li等[2]指出了边界条件，Wang等[3]提供了新证据。"
        },
        {
            "before": "值得注意的是，该研究采用了大样本数据。显而易见，这使得结论更加可靠。换言之，研究质量很高。",
            "after": "该研究采用大样本数据，结论更加可靠。"
        },
        {
            "before": "总而言之，现有研究支持了媒体监督的积极作用。与此同时，我们也需要关注其边界条件。有鉴于此，未来研究应进一步探讨。",
            "after": "综上，现有研究支持媒体监督的积极作用，未来研究应进一步探讨其边界条件。"
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n示例{i}:")
        print(f"  ❌ 润色前: {example['before']}")
        print(f"  ✅ 润色后: {example['after']}")
        print(f"  💡 改进: 删除了AI腔，语言更干练")


async def test_common_ai_tone_patterns():
    """测试常见AI腔模式"""
    print("\n" + "=" * 80)
    print("常见AI腔模式及处理")
    print("=" * 80)

    patterns = [
        ("近年来", "替换为具体时间范围，如'近五年'"),
        ("值得注意的是", "直接删除"),
        ("换言之", "直接删除"),
        ("显而易见", "直接删除"),
        ("一方面...另一方面", "删除过渡，直接陈述"),
        ("此外", "用分号';'代替"),
        ("随着...的发展", "删除背景铺垫"),
        ("研究结果表明", "简化为'研究发现'"),
        ("综上所述", "简化为'综上'"),
        ("总而言之", "简化为'综上'"),
    ]

    print(f"\n{'AI腔词汇':<15} {'处理建议'}")
    print("-" * 80)
    for pattern, suggestion in patterns:
        print(f"{pattern:<15} {suggestion}")


async def test_llm_polishing():
    """测试LLM润色"""
    print("\n" + "=" * 80)
    print("测试4: LLM增强润色")
    print("=" * 80)

    import os
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️  DEEPSEEK_API_KEY 未配置，跳过LLM测试\n")
        return

    eliminator = AIToneEliminator()

    sample_text = """近年来，随着公司治理研究的深入，媒体关注作为外部治理机制引起了学术界的广泛关注。值得注意的是，多项实证研究支持了媒体的监督作用。换言之，媒体能有效抑制盈余管理行为。"""

    print(f"\n原文:")
    print(f"  {sample_text}")

    polished, report = await eliminator.polish_with_llm(
        sample_text,
        style="concise",
        strict=True
    )

    print(f"\nLLM润色后:")
    print(f"  {polished}")

    print(f"\n润色报告:")
    print(f"  方法: {report['method']}")
    print(f"  风格: {report['style']}")
    print(f"  压缩率: {report['compression_ratio']:.1%}")


async def demo_practical_usage():
    """演示实际使用场景"""
    print("\n" + "=" * 80)
    print("演示: 实际使用场景")
    print("=" * 80)

    print("\n场景：润色已生成的综述\n")

    # 模拟AI生成的综述段落
    ai_generated = """关于QFD在质量管理中的应用，近年来引起了学术界的广泛关注。值得注意的是，多项研究提供了实证支持。具体来说，Zhang等[1]发现QFD能显著提升产品质量。换言之，QFD具有重要的应用价值。此外，Liu等[2]的研究也支持了这一结论。显而易见，QFD在制造业中具有广阔的应用前景。"""

    print("AI生成原文:")
    print(f"  {ai_generated}")

    # 润色
    polisher = ReviewPolisher()
    polished, report = await polisher.polish(ai_generated)

    print("\n润色后:")
    print(f"  {polished}")

    print(f"\n润色摘要:")
    print(f"  {report['summary']}")


async def main():
    """运行所有测试"""
    await test_ai_tone_detection()
    await test_rule_polishing()
    await test_full_polishing()
    await test_before_after_comparison()
    await test_common_ai_tone_patterns()
    await test_llm_polishing()
    await demo_practical_usage()

    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
