#!/usr/bin/env python3
"""
命令行工具：检查文献综述中的引用序号顺序

用法:
    python check_citation_order.py "文本内容"
    python check_citation_order.py input.txt
    echo "文本" | python check_citation_order.py
"""
import sys
import os
from services.citation_order_checker import CitationOrderChecker


def main():
    if len(sys.argv) < 2:
        print("用法: python check_citation_order.py <文本内容或文件路径>")
        print("示例:")
        print('  python check_citation_order.py "这是测试[1]，然后是[2]"')
        print('  python check_citation_order.py review.txt')
        sys.exit(1)

    input_arg = sys.argv[1]

    # 判断是文件路径还是文本内容
    if os.path.exists(input_arg):
        print(f"从文件读取: {input_arg}")
        with open(input_arg, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = input_arg

    if not text.strip():
        print("错误: 输入内容为空")
        sys.exit(1)

    print("=" * 80)
    print("引用序号检查")
    print("=" * 80)
    print(f"文本长度: {len(text)} 字符\n")

    checker = CitationOrderChecker()
    result = checker.check_order(text)

    print(f"检查结果: {result['message']}\n")

    if result['total_citations'] == 0:
        print("未检测到引用序号")
        return

    print(f"总引用数: {result['total_citations']}")
    print(f"唯一序号: {result['unique_numbers']}")
    print()

    # 显示问题
    if result['issues']:
        print("发现的问题:")
        for issue in result['issues']:
            severity_icon = {
                'error': '✗',
                'warning': '⚠',
                'info': 'ℹ'
            }.get(issue['severity'], '•')

            print(f"  {severity_icon} {issue['message']}")

        print()

    # 显示详细信息
    if result['missing_numbers']:
        print(f"缺失的序号: {result['missing_numbers']}")
        print()

    if result['duplicate_numbers']:
        print("重复的序号:")
        for dup in result['duplicate_numbers']:
            print(f"  序号 [{dup['number']}] 被使用了 {dup['count']} 次")
            for i, ctx in enumerate(dup['contexts'][:3], 1):
                print(f"    {i}. ...{ctx}...")
        print()

    if result['out_of_order']:
        print("顺序错误的引用:")
        for err in result['out_of_order']:
            print(f"  序号 [{err['number']}] 出现在位置 {err['position']}")
            print(f"    预期应 >= {err['expected_min']}")
            print(f"    上下文: ...{err['context']}...")
        print()

    # 显示引用列表
    print("引用列表（按出现顺序）:")
    citations = checker.extract_citations(text)
    for i, cit in enumerate(citations[:20], 1):  # 最多显示20个
        print(f"  {i:2d}. [{cit['number']}] 位置:{cit['position']:4d} | ...{cit['context']}...")

    if len(citations) > 20:
        print(f"  ... 还有 {len(citations) - 20} 个引用")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
