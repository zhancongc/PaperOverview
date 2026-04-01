"""
正文序号检查器
检查文献综述中的引用序号是否连续、按顺序出现
"""
import re
from typing import List, Dict, Tuple, Set
from collections import defaultdict


class CitationOrderChecker:
    """引用序号顺序检查器"""

    # 匹配各种引用序号格式
    # [1], [1][2], [1-3], [1,2,3]
    CITATION_PATTERNS = [
        r'\[(\d+)\]',  # [1]
        r'\[(\d+),(\d+)\]',  # [1,2]
        r'\[(\d+)-(\d+)\]',  # [1-3]
        r'\((\d+)\)',  # (1)
        r'（(\d+)）',  # （1）
    ]

    def __init__(self):
        """编译正则表达式"""
        self.patterns = [re.compile(p) for p in self.CITATION_PATTERNS]

    def extract_citations(self, text: str) -> List[Dict]:
        """
        提取文本中所有的引用序号

        Args:
            text: 待检查的文本

        Returns:
            引用列表，每个引用包含：
            - number: 序号
            - position: 在文本中的位置
            - context: 上下文（前后各20个字符）
            - type: 引用类型
        """
        citations = []

        for pattern in self.patterns:
            for match in pattern.finditer(text):
                start = match.start()
                end = match.end()
                matched_text = match.group(0)

                # 获取上下文
                context_start = max(0, start - 20)
                context_end = min(len(text), end + 20)
                context = text[context_start:context_end]

                # 提取序号
                citation_text = matched_text
                numbers = []

                # 处理不同格式
                if '[' in matched_text:
                    # [1], [1][2], [1,2], [1-3]
                    numbers = re.findall(r'\[(\d+)\]', matched_text)
                elif '(' in matched_text:
                    # (1)
                    numbers = re.findall(r'\((\d+)\)', matched_text)
                elif '（' in matched_text:
                    # （1）
                    numbers = re.findall(r'（(\d+)）', matched_text)

                for num_str in numbers:
                    try:
                        num = int(num_str)
                        citations.append({
                            'number': num,
                            'position': start,
                            'text': citation_text,
                            'context': context.strip(),
                            'type': self._detect_citation_type(matched_text)
                        })
                    except ValueError:
                        continue

        # 按位置排序
        citations.sort(key=lambda x: x['position'])

        return citations

    def _detect_citation_type(self, text: str) -> str:
        """检测引用类型"""
        if '[' in text:
            return 'bracket'
        elif '(' in text:
            return 'parenthesis'
        elif '（' in text:
            return 'chinese_parenthesis'
        return 'unknown'

    def check_order(self, text: str) -> Dict:
        """
        检查引用序号顺序

        Args:
            text: 待检查的文本

        Returns:
            检查结果字典：
            - valid: 是否有效
            - total_citations: 总引用数
            - unique_numbers: 唯一序号集合
            - missing_numbers: 缺失的序号
            - duplicate_numbers: 重复出现的序号
            - out_of_order: 顺序错误的序号
            - issues: 问题列表
        """
        citations = self.extract_citations(text)

        if not citations:
            return {
                'valid': True,
                'total_citations': 0,
                'unique_numbers': set(),
                'missing_numbers': [],
                'duplicate_numbers': [],
                'out_of_order': [],
                'issues': [],
                'message': '未检测到引用序号'
            }

        # 提取所有序号
        numbers = [c['number'] for c in citations]
        unique_numbers = set(numbers)

        # 检查缺失的序号
        min_num = min(unique_numbers)
        max_num = max(unique_numbers)
        expected_numbers = set(range(min_num, max_num + 1))
        missing_numbers = sorted(expected_numbers - unique_numbers)

        # 检查重复的序号
        number_count = defaultdict(list)
        for i, num in enumerate(numbers):
            number_count[num].append(i)

        duplicate_numbers = []
        for num, positions in number_count.items():
            if len(positions) > 1:
                duplicate_numbers.append({
                    'number': num,
                    'count': len(positions),
                    'positions': positions,
                    'contexts': [citations[p]['context'] for p in positions[:3]]  # 最多显示3个上下文
                })

        # 检查顺序错误
        # 规则：序号应该按递增顺序出现，但允许重复引用（序号回退到已出现过的序号）
        # 例如：[1][2][3][2] 允许（重复引用2）
        #      [1][3][2] 不允许（2在3后面第一次出现，顺序乱了）
        out_of_order = []
        seen_numbers = set()
        max_seen = 0

        for i, citation in enumerate(citations):
            current_number = citation['number']

            # 更新已见过的序号集合和最大序号
            if current_number not in seen_numbers:
                seen_numbers.add(current_number)
                max_seen = max(max_seen, current_number)

            # 检查顺序：
            # 如果当前序号是第一次出现，且小于之前见过的最大序号，则是顺序错误
            # 如果当前序号已经出现过，则是重复引用，允许
            is_first_appearance = (numbers[:i].count(current_number) == 0)

            if is_first_appearance and i > 0 and current_number < max_seen:
                out_of_order.append({
                    'number': current_number,
                    'expected_min': max_seen,
                    'context': citation['context'],
                    'position': citation['position']
                })

        # 汇总问题
        issues = []

        if missing_numbers:
            issues.append({
                'type': 'missing',
                'severity': 'warning',
                'message': f'检测到 {len(missing_numbers)} 个缺失的序号: {missing_numbers[:10]}'
            })

        if duplicate_numbers:
            issues.append({
                'type': 'duplicate',
                'severity': 'info',
                'message': f'检测到 {len(duplicate_numbers)} 个重复使用的序号'
            })

        if out_of_order:
            issues.append({
                'type': 'out_of_order',
                'severity': 'error',
                'message': f'检测到 {len(out_of_order)} 个顺序错误的引用'
            })

        # 判断是否有效
        valid = len(out_of_order) == 0

        return {
            'valid': valid,
            'total_citations': len(citations),
            'unique_numbers': sorted(unique_numbers),
            'missing_numbers': missing_numbers,
            'duplicate_numbers': duplicate_numbers,
            'out_of_order': out_of_order,
            'issues': issues,
            'message': self._generate_message(valid, issues, len(unique_numbers), max_num)
        }

    def _generate_message(self, valid: bool, issues: List, count: int, max_num: int) -> str:
        """生成检查结果消息"""
        if valid:
            return f'✓ 引用序号顺序正确，共 {count} 个引用，最大序号 {max_num}'

        error_messages = []
        for issue in issues:
            if issue['severity'] == 'error':
                error_messages.append(issue['message'])

        if error_messages:
            return f'✗ ' + '; '.join(error_messages)

        return f'⚠ 引用存在问题，请检查详情'

    def fix_citation_order(self, text: str, citations: List[Dict]) -> Tuple[str, List[Dict]]:
        """
        修正引用序号顺序（重新编号）

        按引用在文中首次出现的顺序重新编号，确保序号严格递增。
        例如：[8][15][7] → [1][2][3]，同时需要相应重新排列论文列表。

        Args:
            text: 原始文本
            citations: 引用列表（extract_citations 的返回值）

        Returns:
            (修正后的文本, 新旧序号映射)
        """
        if not citations:
            return text, []

        # 按首次出现顺序收集唯一序号
        seen_numbers = set()
        unique_ordered_numbers = []
        for citation in citations:
            num = citation['number']
            if num not in seen_numbers:
                seen_numbers.add(num)
                unique_ordered_numbers.append(num)

        # 创建序号映射（旧序号 -> 新序号）
        old_to_new = {}
        new_to_old = []
        for new_num, old_num in enumerate(unique_ordered_numbers, 1):
            old_to_new[old_num] = new_num
            new_to_old.append({
                'old': old_num,
                'new': new_num
            })

        # 如果所有序号已经正确（1,2,3,...），不需要修复
        is_already_correct = True
        for i, old_num in enumerate(unique_ordered_numbers, 1):
            if old_num != i:
                is_already_correct = False
                break

        if is_already_correct:
            return text, new_to_old

        # 替换文本中的序号
        # 从后往前替换，避免位置偏移
        sorted_citations = sorted(citations, key=lambda x: x['position'], reverse=True)

        for citation in sorted_citations:
            old_num = citation['number']
            new_num = old_to_new[old_num]

            if old_num == new_num:
                continue

            # 替换序号
            old_text = citation['text']
            new_text = old_text.replace(str(old_num), str(new_num))

            # 执行替换
            start = citation['position']
            end = start + len(old_text)
            text = text[:start] + new_text + text[end:]

        return text, new_to_old


# 全局实例
checker = CitationOrderChecker()


def check_citation_order(text: str) -> Dict:
    """
    检查引用序号顺序（便捷函数）

    Args:
        text: 待检查的文本

    Returns:
        检查结果字典
    """
    return checker.check_order(text)


def fix_citation_order(text: str) -> Tuple[str, List[Dict]]:
    """
    修正引用序号顺序（便捷函数）

    Args:
        text: 原始文本

    Returns:
        (修正后的文本, 新旧序号映射)
    """
    citations = checker.extract_citations(text)
    return checker.fix_citation_order(text, citations)


# 测试代码
if __name__ == "__main__":
    # 测试用例
    test_cases = [
        # 正常情况
        ("正常情况", "这是一个测试[1]，这里有引用[2][3]，最后是[4]。"),
        # 缺失序号
        ("缺失序号", "这是测试[1]，然后是[3]，缺少了[2]。"),
        # 重复序号
        ("重复序号", "这是测试[1]，然后是[2]，又用了[1]。"),
        # 顺序错误
        ("顺序错误", "这是测试[1]，然后是[3]，后面才是[2]。"),
        # 混合格式
        ("混合格式", "这是测试[1]，然后是(2)，还有（3），最后[4]。"),
        # 空引用
        ("空引用", "这是一段没有引用的文本。"),
    ]

    print("=" * 80)
    print("引用序号检查器测试")
    print("=" * 80)

    for name, text in test_cases:
        print(f"\n测试: {name}")
        print("-" * 60)
        print(f"文本: {text}")
        print()

        result = check_citation_order(text)

        print(f"结果: {result['message']}")
        print(f"有效: {result['valid']}")
        print(f"总引用数: {result['total_citations']}")
        print(f"唯一序号: {result['unique_numbers']}")

        if result['missing_numbers']:
            print(f"缺失序号: {result['missing_numbers']}")

        if result['duplicate_numbers']:
            print(f"重复序号: {[d['number'] for d in result['duplicate_numbers']]}")

        if result['out_of_order']:
            print(f"顺序错误:")
            for err in result['out_of_order']:
                print(f"  - 序号 {err['number']} (应 >= {err['expected_min']})")
                print(f"    上下文: {err['context']}")

    # 测试修正功能
    print("\n" + "=" * 80)
    print("测试修正功能")
    print("=" * 80)

    broken_text = "这是测试[1]，然后是[3]，后面才是[2]，又用了[1]。"
    print(f"\n原始文本: {broken_text}")

    fixed_text, mapping = fix_citation_order(broken_text)
    print(f"修正后: {fixed_text}")
    print(f"序号映射: {mapping}")

    print("\n" + "=" * 80)
