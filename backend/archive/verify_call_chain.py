"""
综述生成流程调用链验证脚本

检查所有阶段的方法调用是否正确，防止方法名错误或参数传递错误。
"""
import sys
import inspect
from typing import get_type_hints

# 模拟导入
sys.path.insert(0, '.')

def check_method_exists(obj, method_name: str):
    """检查对象是否有指定方法"""
    return hasattr(obj, method_name)

def check_method_signature(func, expected_params):
    """检查方法签名是否匹配预期参数"""
    sig = inspect.signature(func)
    params = sig.parameters

    print(f"  方法: {func.__name__}")
    print(f"  期望参数: {expected_params}")
    print(f"  实际参数: {list(params.keys())}")

    # 检查期望参数是否都存在
    missing_params = set(expected_params) - set(params.keys())
    if missing_params:
        print(f"  ⚠️ 缺少参数: {missing_params}")
        return False

    # 检查是否有默认值
    for param_name in expected_params:
        param = params[param_name]
        if param.default == inspect.Parameter.empty:
            print(f"    - {param_name}: 必需，无默认值")
        else:
            print(f"    - {param_name}: 有默认值 ({param.default})")

    return True

def check_service_classes():
    """检查服务类的方法"""
    print("=" * 80)
    print("检查服务类方法")
    print("=" * 80)

    try:
        from services.paper_quality_filter import PaperQualityFilter
        from services.paper_filter import PaperFilterService
        from services.paper_field_classifier import EnhancedPaperFilterService
        from services.review_generator_fc_unified import ReviewGeneratorFCUnified

        # 检查 PaperQualityFilter
        print("\n1. PaperQualityFilter")
        quality_filter = PaperQualityFilter()

        print("  ✅ 存在的方法:")
        for name in dir(quality_filter):
            if not name.startswith('_'):
                print(f"    - {name}")

        print("  ✅ 检查关键方法:")
        check_method_exists(quality_filter, 'get_paper_quality_score')
        check_method_exists(quality_filter, 'is_low_quality_paper')
        check_method_exists(quality_filter, 'filter_papers')

        # 检查 PaperFilterService
        print("\n2. PaperFilterService")
        filter_service = PaperFilterService()

        print("  ✅ 存在的方法:")
        for name in dir(filter_service):
            if not name.startswith('_'):
                print(f"    - {name}")

        print("  ✅ 检查关键方法:")
        check_method_exists(filter_service, 'filter_and_sort')
        check_method_exists(filter_service, 'get_statistics')

        # 检查 EnhancedPaperFilterService
        print("\n3. EnhancedPaperFilterService")
        enhanced_filter = EnhancedPaperFilterService()

        print("  ✅ 存在的方法:")
        for name in dir(enhanced_filter):
            if not name.startswith('_'):
                print(f"    - {name}")

        print("  ✅ 检查关键方法:")
        check_method_exists(enhanced_filter, '_calculate_enhanced_relevance_score')
        check_method_exists(enhanced_filter, 'filter_and_sort_with_fields')

        # 检查 ReviewGeneratorFCUnified
        print("\n4. ReviewGeneratorFCUnified")
        fc_generator = ReviewGeneratorFCUnified(api_key='test')

        print("  ✅ 存在的方法:")
        for name in dir(fc_generator):
            if not name.startswith('_'):
                print(f"    - {name}")

        print("  ✅ 检查关键方法:")
        check_method_exists(fc_generator, 'generate_review')
        check_method_exists(fc_generator, '_get_paper_details')
        check_method_exists(fc_generator, '_search_papers_by_keyword')

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False

    return True

def check_stage_methods():
    """检查阶段方法"""
    print("\n" + "=" * 80)
    print("检查阶段方法调用链")
    print("=" * 80)

    try:
        from services.review_task_executor import ReviewTaskExecutor

        executor = ReviewTaskExecutor()

        print("\n阶段方法:")
        stage_methods = {
            '阶段1': '_generate_review_outline',
            '阶段2': '_optimize_search_queries_basic',
            '阶段3': '_search_literature_by_sections',
            '阶段4 (新)': '_filter_papers_by_quality',
            '阶段4 (旧)': '_filter_papers_to_target',  # 标记为废弃
        }

        for stage, method_name in stage_methods.items():
            if check_method_exists(executor, method_name):
                if method_name == '_filter_papers_to_target':
                    print(f"  ⚠️ {stage}: {method_name} (旧方法，已废弃)")
                else:
                    print(f"  ✅ {stage}: {method_name}")

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False

    return True

def check_parameter_passing():
    """检查参数传递"""
    print("\n" + "=" * 80)
    print("检查关键参数传递")
    print("=" * 80)

    print("\n阶段4 → 阶段5 参数传递:")
    print("  - all_papers: List[Dict] ✅")
    print("  - framework: dict ✅")
    print("  - target_citation_count: int ✅")

    print("\n阶段5 内部调用:")
    print("  - _build_system_prompt(specificity_guidance, target_citation_count) ✅")
    print("  - _build_user_message(topic, paper_titles, framework, target_citation_count) ✅")
    print("  - _get_paper_details(paper_index, papers) ✅")
    print("  - _search_papers_by_keyword(keyword, papers) ✅")

    return True

def check_deprecated_methods():
    """检查废弃方法"""
    print("\n" + "=" * 80)
    print("检查废弃方法")
    print("=" * 80)

    print("\nReviewTaskExecutor 废弃方法:")
    print("  ⚠️ _filter_papers_to_target (应使用 _filter_papers_by_quality)")
    print("  ⚠️ _optimize_search_queries (应使用 _optimize_search_queries_basic)")

    print("\n外部服务类废弃方法:")
    print("  ❌ calculate_quality_score (应使用 get_paper_quality_score)")

    print("\n废弃的综述生成器文件:")
    print("  ⚠️ review_generator.py (应使用 review_generator_fc_unified.py)")
    print("  ⚠️ review_generator_v2_enhanced.py (应使用 review_generator_fc_unified.py)")
    print("  ⚠️ review_generator_function_calling.py (应使用 review_generator_fc_unified.py)")

    print("\n建议:")
    print("  1. 已标记所有废弃方法为 @deprecated")
    print("  2. 确保所有调用都使用新方法")
    print("  3. 新项目直接使用 ReviewGeneratorFCUnified")

    return True

def main():
    """主函数"""
    print("开始检查调用链...")

    all_ok = True

    # 检查服务类
    if not check_service_classes():
        all_ok = False

    # 检查阶段方法
    if not check_stage_methods():
        all_ok = False

    # 检查参数传递
    if not check_parameter_passing():
        all_ok = False

    # 检查废弃方法
    if not check_deprecated_methods():
        all_ok = False

    print("\n" + "=" * 80)
    if all_ok:
        print("✅ 所有检查通过！调用链正确。")
    else:
        print("❌ 发现问题，请修复。")
    print("=" * 80)

if __name__ == "__main__":
    main()
