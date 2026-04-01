"""
测试综述生成后的引用序号自动修复功能
"""
import asyncio
from services.citation_order_checker import CitationOrderChecker


def test_auto_fix():
    """测试自动修复功能"""
    print("=" * 80)
    print("测试引用序号自动修复功能")
    print("=" * 80)

    checker = CitationOrderChecker()

    # 模拟大模型生成的、有问题的综述片段
    problematic_review = """
# 基于QFD的铝合金轮毂质量管理研究文献综述

## 1. 引言

在全球汽车工业轻量化的发展趋势下，铝合金轮毂因其优异的比强度已成为主流配置[8][15]。其质量直接关系到车辆的行驶安全性[7]。传统的质量管理方法往往侧重于事后检验[3]。

质量功能展开（QFD）作为一种系统性的质量规划方法，通过构建"质量屋"将顾客需求转化为技术特性[12]。近年来，随着多准则决策（MCDM）技术的发展[10]，QFD方法得到了进一步的完善[9]。

## 2. QFD方法的理论演进

早期的QFD应用主要依赖专家经验[1]。为了更科学地处理评估过程中的模糊信息，模糊集理论被引入[5]。Haktanir等人提出了基于区间值毕达哥拉斯模糊集的QFD方法[6]。

## 参考文献

[1] Author. Title. Journal, 2020.
[2] Author. Title. Journal, 2021.
...
[15] Author. Title. Journal, 2022.
"""

    print("原始综述片段（前300字符）:")
    print(problematic_review[:300])
    print()

    # 只检查正文部分
    lines = problematic_review.split('\n')
    content_lines = []
    for line in lines:
        if line.startswith('## 参考文献'):
            break
        content_lines.append(line)
    content = '\n'.join(content_lines)

    # 检查序号顺序
    print("Step 1: 检查引用序号顺序")
    print("-" * 60)
    result = checker.check_order(content)
    print(f"检查结果: {result['message']}")
    print(f"有效: {result['valid']}")
    print()

    if not result['valid']:
        print("发现的问题:")
        for issue in result['issues']:
            print(f"  - {issue['type']}: {issue['message']} (严重程度: {issue['severity']})")
        print()

        # 显示顺序错误的引用
        if result['out_of_order']:
            print("顺序错误的引用（前5个）:")
            for err in result['out_of_order'][:5]:
                print(f"  序号 [{err['number']}] 位置 {err['position']}: ...{err['context']}...")
            print()

        # 自动修复
        print("Step 2: 自动修复引用序号")
        print("-" * 60)
        citations = checker.extract_citations(content)
        fixed_content, mapping = checker.fix_citation_order(content, citations)

        print(f"修复完成，共修改 {len(mapping)} 个序号")
        print(f"序号映射（前10个）: {mapping[:10]}")
        print()

        # 验证修复后的结果
        print("Step 3: 验证修复后的结果")
        print("-" * 60)
        result2 = checker.check_order(fixed_content)
        print(f"修复后检查: {result2['message']}")
        print(f"修复后有效: {result2['valid']}")
        print()

        # 显示修复前后的对比
        print("修复前后对比（部分）:")
        print("-" * 60)
        original_citations = checker.extract_citations(content)
        fixed_citations = checker.extract_citations(fixed_content)

        print("原始引用顺序（前10个）:")
        for i, c in enumerate(original_citations[:10], 1):
            print(f"  {i:2d}. [{c['number']}] 位置 {c['position']:4d}")

        print()
        print("修复后引用顺序（前10个）:")
        for i, c in enumerate(fixed_citations[:10], 1):
            print(f"  {i:2d}. [{c['number']}] 位置 {c['position']:4d}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    test_auto_fix()
