"""
综述要求测试用例

检查生成的综述是否符合以下要求：
1. 文献数量是否大于50
2. 英文文献数量是否大于30%
3. 近5年文献数量是否大于50%
4. 参考文献列表中的文献是否在正文中都有引用
"""
import re
from datetime import datetime
from typing import List, Dict, Tuple


class ReviewRequirementsTest:
    """综述要求测试类"""

    def __init__(self, record: Dict):
        """
        初始化测试

        Args:
            record: 包含 topic, review, papers, statistics 的记录字典
        """
        self.topic = record.get('topic', '')
        self.review = record.get('review', '')
        self.papers = record.get('papers', [])
        self.statistics = record.get('statistics', {})

        # 分析数据
        self._analyze_review()

    def _analyze_review(self):
        """分析综述数据"""
        # 分离正文和参考文献列表
        self.main_text, self.reference_list = self._split_review_and_references()

        # 提取正文中的引用编号
        self.cited_in_text = self._extract_citations_from_text(self.main_text)

        # 提取参考文献列表中的编号
        self.cited_in_refs = set(range(1, len(self.reference_list) + 1))

    def _split_review_and_references(self) -> Tuple[str, List[str]]:
        """
        分离正文和参考文献列表

        Returns:
            (正文内容, 参考文献列表行)
        """
        lines = self.review.split('\n')
        ref_start = -1

        # 查找参考文献部分
        for i, line in enumerate(lines):
            if line.strip().startswith('## 参考文献') or \
               line.strip().startswith('### 参考文献') or \
               line.strip().startswith('# 参考文献'):
                ref_start = i
                break

        if ref_start == -1:
            # 没有找到参考文献部分，尝试从最后一篇参考文献的格式判断
            for i, line in enumerate(lines):
                if re.match(r'^\[\d+\]', line.strip()):
                    ref_start = i
                    break

        if ref_start == -1:
            return self.review, []

        main_text = '\n'.join(lines[:ref_start]).strip()
        ref_lines = lines[ref_start + 1:]  # 跳过标题行
        reference_list = [line.strip() for line in ref_lines if line.strip() and re.match(r'^\[\d+\]', line.strip())]

        return main_text, reference_list

    def _extract_citations_from_text(self, text: str) -> set:
        """从正文中提取引用编号"""
        citations = re.findall(r'\[(\d+)\]', text)
        return set(int(c) for c in citations)

    def test_paper_count(self) -> Dict:
        """
        测试1: 文献数量是否大于50

        Returns:
            {"passed": bool, "count": int, "message": str}
        """
        count = len(self.papers)
        passed = count > 50

        return {
            "passed": passed,
            "count": count,
            "message": f"文献数量: {count} {'✓ 通过' if passed else '✗ 未通过'} (要求 > 50)"
        }

    def test_english_ratio(self) -> Dict:
        """
        测试2: 英文文献数量是否大于30%

        Returns:
            {"passed": bool, "count": int, "ratio": float, "message": str}
        """
        english_count = sum(1 for p in self.papers if p.get('is_english', False))
        total_count = len(self.papers)
        ratio = english_count / total_count if total_count > 0 else 0
        passed = ratio > 0.3

        return {
            "passed": passed,
            "count": english_count,
            "ratio": round(ratio * 100, 2),
            "message": f"英文文献: {english_count}/{total_count} ({ratio*100:.1f}%) {'✓ 通过' if passed else '✗ 未通过'} (要求 > 30%)"
        }

    def test_recent_years_ratio(self) -> Dict:
        """
        测试3: 近5年文献数量是否大于50%

        Returns:
            {"passed": bool, "count": int, "ratio": float, "message": str}
        """
        current_year = datetime.now().year
        recent_threshold = current_year - 5

        recent_count = sum(1 for p in self.papers if p.get('year', 0) >= recent_threshold)
        total_count = len(self.papers)
        ratio = recent_count / total_count if total_count > 0 else 0
        passed = ratio > 0.5

        return {
            "passed": passed,
            "count": recent_count,
            "ratio": round(ratio * 100, 2),
            "message": f"近5年文献: {recent_count}/{total_count} ({ratio*100:.1f}%) {'✓ 通过' if passed else '✗ 未通过'} (要求 > 50%)"
        }

    def test_all_references_cited(self) -> Dict:
        """
        测试4: 参考文献列表中的文献是否在正文中都有引用

        Returns:
            {"passed": bool, "uncited": list, "message": str}
        """
        # 找出在参考文献列表中但未在正文中引用的编号
        uncited = sorted(self.cited_in_refs - self.cited_in_text)
        passed = len(uncited) == 0

        # 获取未引用文献的标题
        uncited_titles = []
        for num in uncited[:5]:  # 最多显示5个
            if num <= len(self.papers):
                uncited_titles.append(f"[{num}] {self.papers[num-1].get('title', 'N/A')[:60]}...")

        return {
            "passed": passed,
            "uncited_count": len(uncited),
            "uncited_numbers": uncited,
            "uncited_titles": uncited_titles,
            "message": f"未引用文献: {len(uncited)} 篇 {'✓ 通过' if passed else '✗ 未通过'}"
        }

    def test_citation_distribution(self) -> Dict:
        """
        额外测试: 引用分布分析

        Returns:
            引用分布统计信息
        """
        import collections

        citations = re.findall(r'\[(\d+)\]', self.main_text)
        cited_counts = collections.Counter(citations)

        # 统计引用次数分布
        cited_once = sum(1 for c in cited_counts.values() if c == 1)
        cited_twice = sum(1 for c in cited_counts.values() if c == 2)
        cited_thrice = sum(1 for c in cited_counts.values() if c >= 3)

        return {
            "total_citations": len(citations),
            "unique_cited": len(cited_counts),
            "cited_once": cited_once,
            "cited_twice": cited_twice,
            "cited_thrice_plus": cited_thrice,
            "message": f"总引用: {len(citations)} 次, 独立文献: {len(cited_counts)} 篇"
        }

    def run_all_tests(self) -> Dict:
        """
        运行所有测试

        Returns:
            测试结果汇总
        """
        results = {
            "topic": self.topic,
            "tests": {
                "paper_count": self.test_paper_count(),
                "english_ratio": self.test_english_ratio(),
                "recent_years_ratio": self.test_recent_years_ratio(),
                "all_references_cited": self.test_all_references_cited(),
            },
            "extra": {
                "citation_distribution": self.test_citation_distribution()
            }
        }

        # 计算通过率
        passed_count = sum(1 for t in results["tests"].values() if t["passed"])
        results["summary"] = {
            "total_tests": 4,
            "passed": passed_count,
            "failed": 4 - passed_count,
            "all_passed": passed_count == 4
        }

        return results

    def print_report(self):
        """打印测试报告"""
        results = self.run_all_tests()

        print("=" * 70)
        print(f"综述要求测试报告 - {results['topic']}")
        print("=" * 70)

        print("\n【核心测试】")
        for test_name, result in results["tests"].items():
            print(f"  {result['message']}")

        print("\n【额外信息】")
        extra = results["extra"]["citation_distribution"]
        print(f"  {extra['message']}")
        print(f"  引用1次: {extra['cited_once']} 篇")
        print(f"  引用2次: {extra['cited_twice']} 篇")
        print(f"  引用3次及以上: {extra['cited_thrice_plus']} 篇")

        # 显示未引用的文献
        uncited_test = results["tests"]["all_references_cited"]
        if uncited_test["uncited_count"] > 0:
            print(f"\n【未引用文献示例】(共{uncited_test['uncited_count']}篇)")
            for title in uncited_test["uncited_titles"]:
                print(f"  {title}")

        print("\n" + "=" * 70)
        summary = results["summary"]
        status = "✓ 全部通过" if summary["all_passed"] else f"✗ {summary['failed']}/{summary['total_tests']} 未通过"
        print(f"测试结果: {status}")
        print("=" * 70)


def test_record_from_db(record_id: int):
    """从数据库加载记录并测试"""
    from database import db
    from models import ReviewRecord
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.connect())
    session = SessionLocal()
    record = session.query(ReviewRecord).filter(ReviewRecord.id == record_id).first()

    if not record:
        print(f"错误: 未找到 record_id={record_id} 的记录")
        return

    # 转换为字典格式
    record_dict = {
        'topic': record.topic,
        'review': record.review,
        'papers': record.papers,
        'statistics': record.statistics
    }

    tester = ReviewRequirementsTest(record_dict)
    tester.print_report()

    session.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 从命令行参数获取 record_id
        record_id = int(sys.argv[1])
        test_record_from_db(record_id)
    else:
        # 使用示例数据
        sample_record = {
            'topic': '示例题目',
            'review': '''
这是正文内容[1][2][3]。更多内容[4][5]。

## 参考文献

[1] 作者1. 文章1[J]. 期刊, 2023, 1(1): 1-10.
[2] 作者2. 文章2[J]. 期刊, 2022, 2(2): 20-30.
[3] 作者3. 文章3[J]. 期刊, 2021, 3(3): 30-40.
[4] 作者4. 文章4[J]. 期刊, 2020, 4(4): 40-50.
[5] 作者5. 文章5[J]. 期刊, 2019, 5(5): 50-60.
            ''',
            'papers': [
                {'title': '文章1', 'is_english': True, 'year': 2023},
                {'title': '文章2', 'is_english': True, 'year': 2022},
                {'title': '文章3', 'is_english': False, 'year': 2021},
                {'title': '文章4', 'is_english': True, 'year': 2020},
                {'title': '文章5', 'is_english': False, 'year': 2019},
            ],
            'statistics': {}
        }

        tester = ReviewRequirementsTest(sample_record)
        tester.print_report()
