"""
参考文献检查器

验证综述中的参考文献是否满足要求：
- 参考文献数量是否足够（>=50篇）
- 近5年的文献占比是否>=50%
- 英文文献占比是否>=30%
- 综述正文中引用顺序是否正确（连续编号，不跳号）
"""
import re
from typing import List, Dict, Tuple
from datetime import datetime


class ReferenceValidator:
    """参考文献检查器"""

    def __init__(self):
        self.current_year = datetime.now().year

    def validate_review(
        self,
        review: str,
        papers: List[Dict]
    ) -> Dict:
        """
        综合验证综述质量

        Args:
            review: 综述正文（包含参考文献列表）
            papers: 参考文献列表

        Returns:
            验证结果字典
        """
        # 分离正文和参考文献部分
        content, references = self._split_review_and_references(review)

        # 提取正文中的引用编号
        cited_indices = self._extract_cited_indices(content)

        results = {
            "passed": True,
            "warnings": [],
            "details": {}
        }

        # 1. 验证引用数量
        citation_count_result = self.validate_citation_count(cited_indices, papers)
        results["details"]["citation_count"] = citation_count_result
        if not citation_count_result["passed"]:
            results["passed"] = False
            results["warnings"].append(citation_count_result["message"])

        # 2. 验证近5年文献占比
        recent_ratio_result = self.validate_recent_ratio(papers)
        results["details"]["recent_ratio"] = recent_ratio_result
        if not recent_ratio_result["passed"]:
            results["passed"] = False
            results["warnings"].append(recent_ratio_result["message"])

        # 3. 验证英文文献占比
        english_ratio_result = self.validate_english_ratio(papers)
        results["details"]["english_ratio"] = english_ratio_result
        if not english_ratio_result["passed"]:
            results["passed"] = False
            results["warnings"].append(english_ratio_result["message"])

        # 4. 验证引用顺序（包括检查引用编号是否超出参考文献数量）
        citation_order_result = self.validate_citation_order(content, cited_indices, len(papers))
        results["details"]["citation_order"] = citation_order_result
        if not citation_order_result["passed"]:
            results["passed"] = False
            results["warnings"].append(citation_order_result["message"])

        return results

    def validate_citation_count(
        self,
        cited_indices: set,
        papers: List[Dict],
        min_count: int = 50
    ) -> Dict:
        """
        验证引用数量是否足够

        Args:
            cited_indices: 正文中引用的文献编号集合
            papers: 参考文献列表
            min_count: 最少引用数量

        Returns:
            验证结果
        """
        unique_cited = len(cited_indices)

        result = {
            "passed": unique_cited >= min_count,
            "actual": unique_cited,
            "required": min_count,
            "message": ""
        }

        if result["passed"]:
            result["message"] = f"引用数量达标：{unique_cited}篇（要求>= {min_count}篇）"
        else:
            result["message"] = f"引用数量不足：{unique_cited}篇（要求>= {min_count}篇）"

        return result

    def validate_recent_ratio(
        self,
        papers: List[Dict],
        min_ratio: float = 0.5,
        years: int = 5
    ) -> Dict:
        """
        验证近N年文献占比

        Args:
            papers: 参考文献列表
            min_ratio: 最小占比要求
            years: 近N年

        Returns:
            验证结果
        """
        if not papers:
            return {
                "passed": False,
                "actual": 0,
                "required": min_ratio * 100,
                "message": "文献列表为空"
            }

        recent_count = 0
        current_year = datetime.now().year

        for paper in papers:
            paper_year = paper.get("year", 0)
            if paper_year and paper_year >= current_year - years:
                recent_count += 1

        actual_ratio = recent_count / len(papers)

        result = {
            "passed": actual_ratio >= min_ratio,
            "actual": round(actual_ratio * 100, 1),
            "required": min_ratio * 100,
            "recent_count": recent_count,
            "total_count": len(papers),
            "message": ""
        }

        if result["passed"]:
            result["message"] = f"近{years}年文献占比达标：{result['actual']}%（要求>= {result['required']}%）"
        else:
            result["message"] = f"近{years}年文献占比不足：{result['actual']}%（要求>= {result['required']}%）"

        return result

    def validate_english_ratio(
        self,
        papers: List[Dict],
        min_ratio: float = 0.3,
        max_ratio: float = 0.7
    ) -> Dict:
        """
        验证英文文献占比（必须在指定范围内）

        Args:
            papers: 参考文献列表
            min_ratio: 最小占比要求（默认30%）
            max_ratio: 最大占比要求（默认70%）

        Returns:
            验证结果
        """
        if not papers:
            return {
                "passed": False,
                "actual": 0,
                "required_min": min_ratio * 100,
                "required_max": max_ratio * 100,
                "message": "文献列表为空"
            }

        english_count = sum(1 for p in papers if p.get("is_english", False))
        actual_ratio = english_count / len(papers)

        # 检查是否在范围内 [min_ratio, max_ratio]
        passed = min_ratio <= actual_ratio <= max_ratio

        result = {
            "passed": passed,
            "actual": round(actual_ratio * 100, 1),
            "required_min": min_ratio * 100,
            "required_max": max_ratio * 100,
            "english_count": english_count,
            "total_count": len(papers),
            "message": ""
        }

        if passed:
            result["message"] = f"英文文献占比达标：{result['actual']}%（要求{result['required_min']}%-{result['required_max']}%）"
        else:
            if actual_ratio < min_ratio:
                result["message"] = f"英文文献占比过低：{result['actual']}%（要求>= {result['required_min']}%）"
            else:
                result["message"] = f"英文文献占比过高：{result['actual']}%（要求<= {result['required_max']}%）"

        return result

    def validate_citation_order(
        self,
        content: str,
        cited_indices: set,
        papers_count: int = None
    ) -> Dict:
        """
        验证引用顺序是否正确（连续编号，不跳号，不超过参考文献数量）

        Args:
            content: 综述正文内容
            cited_indices: 正文中引用的文献编号集合
            papers_count: 参考文献列表的数量（用于验证引用编号不超出范围）

        Returns:
            验证结果
        """
        # 找出所有引用及其位置
        citation_pattern = re.compile(r'\[(\d+)\]')
        citations = []

        for match in citation_pattern.finditer(content):
            num = int(match.group(1))
            if num in cited_indices:
                citations.append((match.start(), num))

        # 按出现顺序提取编号
        seen = set()
        ordered_nums = []
        for _, num in citations:
            if num not in seen:
                seen.add(num)
                ordered_nums.append(num)

        # 检查是否从1开始连续
        if not ordered_nums:
            return {
                "passed": False,
                "message": "正文中没有引用标记",
                "first_citation": None,
                "last_citation": None,
                "missing_numbers": [],
                "exceeds_range": False,
                "max_citation": None,
                "papers_count": papers_count
            }

        # 检查是否从1开始
        starts_from_one = ordered_nums[0] == 1

        # 检查是否连续
        expected = list(range(1, len(ordered_nums) + 1))
        is_continuous = ordered_nums == expected

        # 找出缺失的编号
        missing_numbers = []
        if ordered_nums:
            for i in range(1, max(ordered_nums) + 1):
                if i not in cited_indices:
                    missing_numbers.append(i)

        # 【新增】检查引用编号是否超过参考文献数量
        exceeds_range = False
        max_citation = max(ordered_nums) if ordered_nums else None

        if papers_count is not None and max_citation is not None:
            exceeds_range = max_citation > papers_count

        result = {
            "passed": starts_from_one and is_continuous and not exceeds_range,
            "message": "",
            "first_citation": ordered_nums[0],
            "last_citation": ordered_nums[-1],
            "total_unique": len(ordered_nums),
            "missing_numbers": missing_numbers,
            "is_continuous": is_continuous,
            "starts_from_one": starts_from_one,
            "exceeds_range": exceeds_range,
            "max_citation": max_citation,
            "papers_count": papers_count
        }

        if result["passed"]:
            result["message"] = f"引用顺序正确：从[{result['first_citation']}]到[{result['last_citation']}]，共{result['total_unique']}篇，连续编号"
        else:
            issues = []
            if exceeds_range:
                issues.append(f"引用编号超出参考文献范围：正文中最大引用为[{max_citation}]，但参考文献列表只有{papers_count}篇")
            if not starts_from_one:
                issues.append(f"第一个引用不是[1]，而是[{result['first_citation']}]")
            if not is_continuous:
                if missing_numbers:
                    issues.append(f"存在跳号：{missing_numbers[:5]}{'...' if len(missing_numbers) > 5 else ''}")
                else:
                    issues.append("引用编号不连续")

            result["message"] = "引用顺序存在问题：" + "; ".join(issues)

        return result

    def validate_paper_pool(
        self,
        papers: List[Dict],
        min_count: int = 100,
        min_recent_ratio: float = 0.5,
        min_english_ratio: float = 0.3
    ) -> Dict:
        """
        验证文献池质量（用于筛选后、生成综述前的验证）

        Args:
            papers: 文献列表
            min_count: 最少文献数量
            min_recent_ratio: 最小近5年占比
            min_english_ratio: 最小英文文献占比

        Returns:
            验证结果
        """
        result = {
            "passed": True,
            "warnings": [],
            "details": {}
        }

        # 检查数量
        count_passed = len(papers) >= min_count
        result["details"]["count"] = {
            "passed": count_passed,
            "actual": len(papers),
            "required": min_count
        }
        if not count_passed:
            result["passed"] = False
            result["warnings"].append(f"文献数量不足：{len(papers)}篇（要求>= {min_count}篇）")

        # 检查近5年占比
        recent_result = self.validate_recent_ratio(papers, min_recent_ratio)
        result["details"]["recent_ratio"] = recent_result
        if not recent_result["passed"]:
            result["passed"] = False
            result["warnings"].append(recent_result["message"])

        # 检查英文文献占比
        english_result = self.validate_english_ratio(papers, min_english_ratio)
        result["details"]["english_ratio"] = english_result
        if not english_result["passed"]:
            result["passed"] = False
            result["warnings"].append(english_result["message"])

        return result

    def _split_review_and_references(self, review: str) -> Tuple[str, str]:
        """
        分离综述正文和参考文献部分

        Args:
            review: 完整的综述文本

        Returns:
            (正文内容, 参考文献部分)
        """
        lines = review.split('\n')
        ref_start = -1

        for i, line in enumerate(lines):
            if line.strip().startswith('## 参考文献') or \
               line.strip().startswith('### 参考文献') or \
               line.strip().startswith('# 参考文献'):
                ref_start = i
                break

        if ref_start == -1:
            return review, ""

        content = '\n'.join(lines[:ref_start]).strip()
        references = '\n'.join(lines[ref_start:]).strip()

        return content, references

    def _extract_cited_indices(self, content: str) -> set:
        """
        从正文中提取引用编号

        Args:
            content: 正文内容

        Returns:
            引用编号集合
        """
        citations = re.findall(r'\[(\d+)\]', content)
        return set(int(c) for c in citations)
