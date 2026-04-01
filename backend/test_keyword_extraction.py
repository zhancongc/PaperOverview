"""
测试关键词提取能力和泛化能力
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.hybrid_classifier import FrameworkGenerator, HybridTopicClassifier

load_dotenv()

# 测试论文标题（从数据库获取的随机20篇）
TEST_TITLES = [
    "绿色制造工艺在船舶结构中的应用",
    "基于现代化机械设计制造工艺及精密加工技术分析",
    "Open-access bacterial population genomics: BIGSdb software, the PubMLST.org website and their applications",
    "Estimates of the severity of coronavirus disease 2019: a model-based analysis",
    "Recent Advances in Electrocatalytic Hydrogen Evolution Using Nanoparticles",
    "High-quality health systems in the Sustainable Development Goals era: time for a revolution",
    "The Effect of Risk Management on Nursing Safety in Psychiatric Department",
    "New Technology of Wire and Cable Manufacturing",
    "构建高效的突发公共卫生事件预警机制",
    "Minimal information for studies of extracellular vesicles (MISEV2023): From basic to advanced approaches",
    "探讨妇产科护理管理中风险管理理念的应用价值",
    "现代化机械设计制造工艺及精密加工技术的思考",
    "Array programming with NumPy",
    "The 5th edition of the World Health Organization Classification of Haematolymphoid Tumours: Lymphoid Neoplasms",
    "Management of Hyperglycemia in Type 2 Diabetes, 2018. A Consensus Report by the American Diabetes Association (ADA) and the European Association for the Study of Diabetes (EASD)",
    "Inflammatory responses and inflammation-associated diseases in organs",
    "基于风险管理的中小企业内部控制问题与策略分析",
    "Nursing risk management in emergency digestive endoscopy procedures",
    "Microbiota in health and diseases",
    "Collaborative Design of General Quality Characteristics for Payloads in Space Station"
]

# 额外测试标题（涵盖不同类型和领域）
ADDITIONAL_TITLES = [
    # 原始问题案例
    "基于FMEA法的Agent开发项目风险管理研究",
    "基于QFD的铝合金轮毂质量管理研究",
    "基于深度学习的图像识别算法优化研究",
    "新能源汽车电池管理系统设计与实现",
    "基于BIM的大型工程项目管理优化研究",
    # 跨领域题目
    "基于区块链的供应链金融风险管理研究",
    "基于大数据的用户行为分析与推荐系统优化",
    "人工智能在医疗诊断中的应用与挑战",
    # 理论型
    "深度学习理论框架研究进展",
    "复杂网络演化动力学分析",
    # 实证型
    "社交媒体使用对青少年心理健康的影响研究",
    "远程办公对员工工作效率的影响分析",
    # 评价型
    "软件系统成熟度评价指标体系构建",
    "城市可持续发展能力评估模型研究"
]


async def test_keyword_extraction():
    """测试关键词提取能力"""
    print("=" * 100)
    print("关键词提取能力和泛化能力测试")
    print("=" * 100)

    # 检查API配置
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️  警告: DEEPSEEK_API_KEY 未配置，LLM功能将禁用")
        print("建议: 在 .env 文件中配置 DEEPSEEK_API_KEY 以启用完整功能\n")

    # 初始化生成器
    gen = FrameworkGenerator()
    classifier = HybridTopicClassifier()

    # 合并测试标题
    all_titles = TEST_TITLES + ADDITIONAL_TITLES

    results = []

    print(f"\n📊 测试样本: {len(all_titles)} 篇论文标题")
    print("-" * 100)

    for i, title in enumerate(all_titles, 1):
        print(f"\n{'=' * 100}")
        print(f"测试 {i}/{len(all_titles)}: {title}")
        print("=" * 100)

        try:
            # 生成框架（包含关键词提取）
            framework = await gen.generate_framework(title, enable_llm_validation=True)

            # 提取关键信息
            topic_type = framework.get('type', 'unknown')
            type_name = framework.get('type_name', '未知类型')
            key_elements = framework.get('key_elements', {})
            search_queries = framework.get('search_queries', [])

            # 分类结果
            print(f"\n✓ 题目类型: {type_name}")

            # 关键元素
            research_object = key_elements.get('research_object', '未识别')
            optimization_goal = key_elements.get('optimization_goal', '未识别')
            methodology = key_elements.get('methodology', '未识别')

            print(f"  研究对象: {research_object}")
            print(f"  优化目标: {optimization_goal}")
            print(f"  方法论: {methodology}")

            # 搜索查询（显示前5个）
            print(f"\n✓ 生成的搜索查询 ({len(search_queries)} 个):")
            for j, query in enumerate(search_queries[:5], 1):
                lang_emoji = "🇺🇸" if query.get('lang') == 'en' else "🇨🇳"
                section = query.get('section', '未知')
                query_str = query.get('query', '')
                print(f"  {j}. [{lang_emoji}] {section}: {query_str}")

            if len(search_queries) > 5:
                print(f"  ... 还有 {len(search_queries) - 5} 个查询")

            # 评估
            if research_object != '未识别':
                print(f"\n✅ 关键词提取: 成功")
            else:
                print(f"\n⚠️  关键词提取: 未识别到关键元素")

            if search_queries:
                print(f"✅ 查询生成: 成功 ({len(search_queries)} 个)")
            else:
                print(f"❌ 查询生成: 失败")

            results.append({
                'title': title,
                'type': topic_type,
                'type_name': type_name,
                'research_object': research_object,
                'optimization_goal': optimization_goal,
                'methodology': methodology,
                'query_count': len(search_queries),
                'success': research_object != '未识别' and len(search_queries) > 0
            })

        except Exception as e:
            print(f"\n❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'title': title,
                'success': False,
                'error': str(e)
            })

    # 统计分析
    print("\n" + "=" * 100)
    print("📊 统计分析")
    print("=" * 100)

    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]

    print(f"\n总数: {len(results)}")
    print(f"成功: {len(successful)} ({len(successful)*100//len(results)}%)")
    print(f"失败: {len(failed)} ({len(failed)*100//len(results)}%)")

    if successful:
        # 按类型统计
        type_counts = {}
        for r in successful:
            type_name = r.get('type_name', '未知')
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        print(f"\n✓ 题目类型分布:")
        for type_name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {type_name}: {count} 篇")

        # 关键元素识别统计
        obj_identified = sum(1 for r in successful if r.get('research_object') != '未识别')
        goal_identified = sum(1 for r in successful if r.get('optimization_goal') != '未识别')
        method_identified = sum(1 for r in successful if r.get('methodology') != '未识别')

        print(f"\n✓ 关键元素识别率:")
        print(f"  - 研究对象: {obj_identified}/{len(successful)} ({obj_identified*100//len(successful)}%)")
        print(f"  - 优化目标: {goal_identified}/{len(successful)} ({goal_identified*100//len(successful)}%)")
        print(f"  - 方法论: {method_identified}/{len(successful)} ({method_identified*100//len(successful)}%)")

    # 展示失败案例
    if failed:
        print(f"\n❌ 失败案例:")
        for r in failed[:5]:  # 只显示前5个
            print(f"  - {r.get('title', 'Unknown')}: {r.get('error', 'Unknown')}")

    # 泛化能力评估
    print("\n" + "=" * 100)
    print("🎯 泛化能力评估")
    print("=" * 100)

    # 测试不同领域的覆盖
    domains = {
        '制造/工艺': ['绿色制造工艺', '机械设计制造', '制造工艺', '精密加工'],
        '医疗/护理': ['护理安全', '妇产科护理', '护理管理', '风险管理(医疗)', '消化内镜'],
        'AI/技术': ['深度学习', '图像识别', '算法优化', '人工智能', '大数据'],
        '医疗理论': ['冠状病毒', '炎症反应', '微生物组'],
        '项目/管理': ['风险管理(项目)', '内部控制', '护理管理', '预警机制'],
        '软件/系统': ['软件系统', '编程语言', '开发'],
        '评价/评估': ['评价指标体系', '可持续发展能力', '成熟度']
    }

    print("\n各领域处理能力:")
    for domain, keywords in domains.items():
        related_titles = [
            r['title'] for r in successful
            if any(kw in r['title'] for kw in keywords)
        ]
        if related_titles:
            print(f"\n  {domain} ({len(related_titles)} 篇):")
            for title in related_titles[:3]:  # 最多显示3个
                result = next((r for r in results if r['title'] == title), None)
                if result:
                    obj = result.get('research_object', '未识别')
                    print(f"    - {title[:50]}")
                    print(f"      → 对象: {obj}")

    # 保存结果
    import json
    output_file = 'keyword_extraction_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 详细结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(test_keyword_extraction())
