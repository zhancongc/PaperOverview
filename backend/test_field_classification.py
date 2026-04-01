"""
测试论文领域分类功能
"""
import asyncio
from services.paper_field_classifier import (
    PaperFieldClassifier,
    SectionFieldMatcher,
    EnhancedPaperFilterService,
    classify_papers,
    filter_papers_for_section
)


def test_field_classification():
    """测试领域分类"""
    print("=" * 80)
    print("测试1: 论文领域分类")
    print("=" * 80)

    classifier = PaperFieldClassifier()

    # 测试论文
    test_papers = [
        {
            "id": "1",
            "title": "Titanium dioxide microspheres for photocatalytic degradation of methylene blue",
            "abstract": "This paper presents the synthesis of TiO2 microspheres for dye degradation",
            "venue_name": "Journal of Materials Chemistry",
            "concepts": ["materials science", "nanotechnology"]
        },
        {
            "id": "2",
            "title": "Clinical trial of new drug for diabetes treatment",
            "abstract": "A randomized controlled trial of metformin in type 2 diabetes patients",
            "venue_name": "New England Journal of Medicine",
            "concepts": ["medicine", "clinical medicine"]
        },
        {
            "id": "3",
            "title": "Deep learning for image recognition",
            "abstract": "A convolutional neural network approach for object detection",
            "venue_name": "IEEE Transactions on Pattern Analysis",
            "concepts": ["computer science", "artificial intelligence"]
        },
        {
            "id": "4",
            "title": "二氧化钛光催化剂制备及其应用",
            "abstract": "采用溶胶-凝胶法制备TiO2光催化材料",
            "venue_name": "材料导报",
            "concepts": ["materials science"]
        },
        {
            "id": "5",
            "title": "企业风险管理框架研究",
            "abstract": "基于COSO框架的企业内部控制体系构建",
            "venue_name": "管理世界",
            "concepts": ["management", "business"]
        },
    ]

    for paper in test_papers:
        field, confidence = classifier.classify_paper(paper)
        print(f"\n论文: {paper['title'][:50]}...")
        print(f"  领域: {field}")
        print(f"  置信度: {confidence:.2f}")
        print(f"  期刊: {paper.get('venue_name', 'Unknown')}")


def test_section_field_matching():
    """测试章节-领域匹配"""
    print("\n" + "=" * 80)
    print("测试2: 章节与领域匹配")
    print("=" * 80)

    # 测试论文（带field字段）
    test_papers = [
        {
            "id": "1",
            "title": "TiO2 photocatalytic materials synthesis",
            "field": "materials"
        },
        {
            "id": "2",
            "title": "Clinical diabetes treatment trial",
            "field": "medicine"
        },
        {
            "id": "3",
            "title": "Deep learning algorithms",
            "field": "cs"
        },
        {
            "id": "4",
            "title": "Enterprise risk management framework",
            "field": "management"
        },
        {
            "id": "5",
            "title": "Stock market prediction model",
            "field": "economics"
        },
    ]

    test_sections = [
        "材料制备与表征",
        "光催化性能测试",
        "风险管理策略",
        "经济影响分析",
        "引言"
    ]

    for section in test_sections:
        print(f"\n章节: {section}")
        allowed_fields = SectionFieldMatcher.get_allowed_fields_for_section(section)
        print(f"  允许的领域: {allowed_fields}")

        allowed, filtered = SectionFieldMatcher.filter_papers_by_section(test_papers, section)

        print(f"  允许的论文 ({len(allowed)}篇):")
        for p in allowed:
            print(f"    - {p['title'][:40]}... [{p['field']}]")

        if filtered:
            print(f"  被过滤的论文 ({len(filtered)}篇):")
            for p in filtered:
                print(f"    - {p['title'][:40]}... [{p['field']}] - {p.get('_filter_reason', '')}")


def test_enhanced_filter():
    """测试增强的论文过滤"""
    print("\n" + "=" * 80)
    print("测试3: 增强的论文过滤服务")
    print("=" * 80)

    # 模拟混合领域的论文库
    test_papers = [
        # 材料类论文
        {"id": "m1", "title": "TiO2 microspheres synthesis", "year": 2023, "cited_by_count": 50, "is_english": True,
         "abstract": "Photocatalytic materials for dye degradation", "venue_name": "Journal of Materials Chemistry"},
        {"id": "m2", "title": "纳米二氧化钛制备", "year": 2022, "cited_by_count": 30, "is_english": False,
         "abstract": "溶胶凝胶法制备纳米TiO2", "venue_name": "材料导报"},

        # 医学类论文（不相关）
        {"id": "med1", "title": "Diabetes clinical trial", "year": 2023, "cited_by_count": 100, "is_english": True,
         "abstract": "Randomized trial of diabetes drug", "venue_name": "New England Journal of Medicine"},
        {"id": "med2", "title": "癌症免疫治疗研究", "year": 2022, "cited_by_count": 80, "is_english": False,
         "abstract": "PD-1抑制剂临床试验", "venue_name": "中华医学杂志"},

        # 计算机类论文（不相关）
        {"id": "cs1", "title": "Deep learning for images", "year": 2024, "cited_by_count": 200, "is_english": True,
         "abstract": "CNN for object detection", "venue_name": "IEEE Transactions on AI"},

        # 管理类论文
        {"id": "mg1", "title": "Project risk management", "year": 2023, "cited_by_count": 40, "is_english": True,
         "abstract": "Risk management in software projects", "venue_name": "Project Management Journal"},
    ]

    filter_service = EnhancedPaperFilterService()

    # 场景1: 材料制备章节 - 应该过滤掉医学和计算机论文
    print("\n场景1: 材料制备章节")
    result, stats = filter_service.filter_and_sort_with_field(
        papers=test_papers,
        section_name="材料制备与表征",
        target_count=10,
        enable_field_filter=True
    )

    print(f"  输入: {stats['total_input']}篇")
    print(f"  过滤: {stats['field_filtered']}篇")
    print(f"  输出: {stats['total_output']}篇")
    print(f"  输出领域分布: {stats['fields_in_output']}")
    print(f"  输出论文:")
    for p in result:
        print(f"    - {p['title'][:40]}... [{p.get('field', 'unknown')}]")

    # 场景2: 风险管理章节 - 应该包含管理类论文
    print("\n场景2: 风险管理章节")
    result, stats = filter_service.filter_and_sort_with_field(
        papers=test_papers,
        section_name="风险管理策略",
        target_count=10,
        enable_field_filter=True
    )

    print(f"  输入: {stats['total_input']}篇")
    print(f"  过滤: {stats['field_filtered']}篇")
    print(f"  输出: {stats['total_output']}篇")
    print(f"  输出领域分布: {stats['fields_in_output']}")
    print(f"  输出论文:")
    for p in result:
        print(f"    - {p['title'][:40]}... [{p.get('field', 'unknown')}]")


def test_api_export():
    """测试导出接口"""
    print("\n" + "=" * 80)
    print("测试4: API导出接口")
    print("=" * 80)

    test_papers = [
        {"id": "1", "title": "TiO2 synthesis", "abstract": "Materials"},
        {"id": "2", "title": "Clinical trial", "abstract": "Medicine"},
        {"id": "3", "title": "AI algorithm", "abstract": "Computer Science"},
    ]

    # 分类
    classified = classify_papers(test_papers)
    print("分类结果:")
    for p in classified:
        print(f"  {p['title']}: {p.get('field', 'unknown')}")

    # 过滤
    allowed, filtered = filter_papers_for_section(classified, "材料制备")
    print(f"\n材料制备章节过滤:")
    print(f"  允许: {len(allowed)}篇")
    print(f"  过滤: {len(filtered)}篇")


if __name__ == "__main__":
    test_field_classification()
    test_section_field_matching()
    test_enhanced_filter()
    test_api_export()

    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)
