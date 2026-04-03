"""
测试 Function Calling 集成到现有流程
"""
import asyncio
import os
from dotenv import load_dotenv
from services.review_generator_function_calling import ReviewGeneratorFunctionCalling

load_dotenv()


async def test_integration():
    """测试按小节生成（Function Calling 版本）"""

    # 模拟论文数据
    papers = [
        {
            "id": "p1",
            "title": "基于深度学习的图像识别研究",
            "authors": ["张三", "李四"],
            "year": 2023,
            "venue_name": "Computer Vision Conference",
            "abstract": "本文提出了一种新的深度学习模型用于图像识别，通过改进卷积神经网络结构，在ImageNet数据集上取得了优异的性能表现。实验结果表明，该方法在准确率和计算效率方面都有显著提升。",
            "concepts": ["深度学习", "图像识别", "卷积神经网络"],
            "cited_by_count": 50
        },
        {
            "id": "p2",
            "title": "机器学习在自然语言处理中的应用",
            "authors": ["王五", "赵六"],
            "year": 2022,
            "venue_name": "NLP Conference",
            "abstract": "本文综述了机器学习技术在自然语言处理领域的应用，包括文本分类、情感分析、机器翻译等任务。通过对比不同方法的性能，分析了各种技术的优缺点。",
            "concepts": ["机器学习", "自然语言处理", "文本分析"],
            "cited_by_count": 80
        },
        {
            "id": "p3",
            "title": "质量控制中的数据挖掘技术",
            "authors": ["孙七", "周八"],
            "year": 2023,
            "venue_name": "Quality Engineering Journal",
            "abstract": "本文研究了数据挖掘技术在质量管理中的应用，提出了一种基于关联规则的质量缺陷分析方法。实际应用表明，该方法能够有效识别生产过程中的质量问题。",
            "concepts": ["数据挖掘", "质量控制", "关联规则"],
            "cited_by_count": 30
        },
        {
            "id": "p4",
            "title": "六西格玛在制造业中的应用研究",
            "authors": ["吴九", "郑十"],
            "year": 2021,
            "venue_name": "Manufacturing Journal",
            "abstract": "本文探讨了六西格玛方法论在制造业质量管理中的应用实践，通过案例分析了DMAIC流程在改进生产效率方面的效果。",
            "concepts": ["六西格码", "质量管理", "DMAIC"],
            "cited_by_count": 60
        },
        {
            "id": "p5",
            "title": "深度强化学习在决策优化中的应用",
            "authors": ["冯一", "陈二"],
            "year": 2023,
            "venue_name": "AI Conference",
            "abstract": "本文提出了一种基于深度强化学习的决策优化方法，应用于复杂系统的实时决策。仿真实验验证了方法的有效性。",
            "concepts": ["强化学习", "决策优化", "深度学习"],
            "cited_by_count": 40
        }
    ]

    # 模拟框架
    framework = {
        "outline": {
            "introduction": {
                "focus": "介绍AI在质量管理中的应用背景"
            },
            "body_sections": [
                {
                    "title": "深度学习在图像识别中的应用",
                    "focus": "综述CNN等模型在图像识别领域的研究进展",
                    "key_points": ["卷积神经网络的发展", "图像识别技术演进", "性能对比分析"],
                    "comparison_points": ["不同CNN架构的对比", "计算效率比较"]
                },
                {
                    "title": "质量管理中的数据挖掘技术",
                    "focus": "综述数据挖掘在质量控制中的应用",
                    "key_points": ["关联规则挖掘", "异常检测", "质量预测"],
                    "comparison_points": ["不同挖掘方法的对比", "应用场景分析"]
                }
            ]
        },
        "section_keywords": {
            "深度学习在图像识别中的应用": ["深度学习", "图像识别"],
            "质量管理中的数据挖掘技术": ["数据挖掘", "质量控制"]
        }
    }

    # 按小节分配论文
    papers_by_section = {
        "深度学习在图像识别中的应用": [papers[0], papers[1], papers[4]],  # p1, p2, p5
        "质量管理中的数据挖掘技术": [papers[2], papers[3]]  # p3, p4
    }

    # 创建生成器
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("DEEPSEEK_API_KEY 未设置，跳过实际测试")
        return

    generator = ReviewGeneratorFunctionCalling(api_key=api_key)

    print("=" * 80)
    print("测试：按小节生成综述（Function Calling 版本）")
    print("=" * 80)

    try:
        # 生成综述
        review, cited_papers = await generator.generate_review_by_sections_with_tools(
            topic="AI在质量管理中的应用研究",
            framework=framework,
            papers_by_section=papers_by_section,
            all_papers=papers
        )

        print("\n" + "=" * 80)
        print("测试成功！")
        print("=" * 80)
        print(f"\n生成内容长度: {len(review)} 字符")
        print(f"引用论文数: {len(cited_papers)} 篇")
        print(f"\n引用的论文:")
        for i, paper in enumerate(cited_papers, 1):
            print(f"  {i}. {paper.get('title', '')}")

        print(f"\n综述预览（前500字）:")
        print(review[:500] + "...")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_integration())
