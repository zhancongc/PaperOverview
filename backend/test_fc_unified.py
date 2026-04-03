"""
测试 Function Calling 统一版本
"""
import asyncio
import os
from dotenv import load_dotenv
from services.review_generator_fc_unified import ReviewGeneratorFCUnified

load_dotenv()


async def test_unified_version():
    """测试统一版本的综述生成"""

    # 模拟论文数据
    papers = [
        {
            "id": "p1",
            "title": "基于深度学习的图像识别研究",
            "authors": ["张三", "李四"],
            "year": 2023,
            "venue_name": "Computer Vision Conference",
            "abstract": "本文提出了一种新的深度学习模型用于图像识别，通过改进卷积神经网络结构，在ImageNet数据集上取得了优异的性能表现。实验结果表明，该方法在准确率和计算效率方面都有显著提升。该方法在多个标准数据集上进行了验证，包括CIFAR-10、CIFAR-100和ImageNet。与现有的ResNet、DenseNet等模型相比，提出的模型在参数量更少的情况下实现了更高的准确率。",
            "concepts": ["深度学习", "图像识别", "卷积神经网络"],
            "cited_by_count": 50
        },
        {
            "id": "p2",
            "title": "机器学习在自然语言处理中的应用",
            "authors": ["王五", "赵六"],
            "year": 2022,
            "venue_name": "NLP Conference",
            "abstract": "本文综述了机器学习技术在自然语言处理领域的应用，包括文本分类、情感分析、机器翻译等任务。通过对比不同方法的性能，分析了各种技术的优缺点。文章详细介绍了BERT、GPT等预训练语言模型的工作原理和应用场景，并讨论了未来发展方向。",
            "concepts": ["机器学习", "自然语言处理", "文本分析"],
            "cited_by_count": 80
        },
        {
            "id": "p3",
            "title": "质量控制中的数据挖掘技术",
            "authors": ["孙七", "周八"],
            "year": 2023,
            "venue_name": "Quality Engineering Journal",
            "abstract": "本文研究了数据挖掘技术在质量管理中的应用，提出了一种基于关联规则的质量缺陷分析方法。实际应用表明，该方法能够有效识别生产过程中的质量问题。研究在某汽车制造厂进行了实地测试，成功识别出多个影响产品质量的关键因素。",
            "concepts": ["数据挖掘", "质量控制", "关联规则"],
            "cited_by_count": 30
        },
        {
            "id": "p4",
            "title": "六西格玛在制造业中的应用研究",
            "authors": ["吴九", "郑十"],
            "year": 2021,
            "venue_name": "Manufacturing Journal",
            "abstract": "本文探讨了六西格玛方法论在制造业质量管理中的应用实践，通过案例分析了DMAIC流程在改进生产效率方面的效果。研究涵盖了定义、测量、分析、改进和控制五个阶段的具体实施方法，并总结了成功实施的关键因素。",
            "concepts": ["六西格码", "质量管理", "DMAIC"],
            "cited_by_count": 60
        },
        {
            "id": "p5",
            "title": "深度强化学习在决策优化中的应用",
            "authors": ["冯一", "陈二"],
            "year": 2023,
            "venue_name": "AI Conference",
            "abstract": "本文提出了一种基于深度强化学习的决策优化方法，应用于复杂系统的实时决策。仿真实验验证了方法的有效性，在多个基准测试中取得了优于传统方法的性能。该方法特别适用于动态环境和不确定条件下的决策问题。",
            "concepts": ["强化学习", "决策优化", "深度学习"],
            "cited_by_count": 40
        },
        {
            "id": "p6",
            "title": "卷积神经网络在医学影像诊断中的应用",
            "authors": ["褚三", "卫四"],
            "year": 2022,
            "venue_name": "Medical Imaging Journal",
            "abstract": "本文研究了CNN在医学影像诊断中的应用，重点关注肺部CT图像的疾病检测。提出了一种改进的CNN架构，结合了注意力机制和多尺度特征融合。实验表明，该方法在肺部疾病检测任务上达到了专家级别的准确率。",
            "concepts": ["卷积神经网络", "医学影像", "疾病检测"],
            "cited_by_count": 45
        },
        {
            "id": "p7",
            "title": "质量管理体系的数字化转型研究",
            "authors": ["蒋五", "沈六"],
            "year": 2023,
            "venue_name": "Quality Management Journal",
            "abstract": "本文探讨了数字化技术在质量管理体系转型中的应用，分析了物联网、大数据、人工智能等技术对质量管理的影响。研究提出了数字化质量管理框架，并通过案例分析验证了框架的实用性。",
            "concepts": ["质量管理", "数字化转型", "工业4.0"],
            "cited_by_count": 35
        },
        {
            "id": "p8",
            "title": "自然语言处理技术在情感分析中的进展",
            "authors": ["韩七", "杨八"],
            "year": 2021,
            "venue_name": "Text Mining Conference",
            "abstract": "本文综述了NLP技术在情感分析领域的发展，从传统的词典方法到现代的深度学习方法都进行了详细分析。特别关注了跨领域情感迁移和少样本学习等前沿技术。",
            "concepts": ["自然语言处理", "情感分析", "深度学习"],
            "cited_by_count": 55
        }
    ]

    # 模拟框架
    framework = {
        "outline": {
            "introduction": {
                "focus": "介绍AI技术在质量管理中的应用背景和发展趋势",
                "key_papers": [3, 4, 7]
            },
            "body_sections": [
                {
                    "title": "深度学习在图像识别中的应用",
                    "focus": "综述CNN等深度学习模型在图像识别领域的研究进展和技术演进",
                    "key_points": [
                        "卷积神经网络的基本原理和发展历程",
                        "主流CNN架构（ResNet、DenseNet等）的对比分析",
                        "图像识别技术的应用场景和性能指标"
                    ],
                    "comparison_points": [
                        "不同CNN架构在准确率和效率上的权衡",
                        "传统计算机视觉方法与深度学习方法的对比"
                    ]
                },
                {
                    "title": "质量管理中的数据驱动方法",
                    "focus": "综述数据挖掘、机器学习在质量控制中的应用实践",
                    "key_points": [
                        "基于关联规则的质量缺陷分析方法",
                        "六西格玛DMAIC流程的数字化改进",
                        "质量管理体系的数字化转型框架"
                    ],
                    "comparison_points": [
                        "传统质量管理方法与数据驱动方法的对比",
                        "不同数据挖掘技术在质量预测中的效果比较"
                    ]
                },
                {
                    "title": "AI技术的跨领域应用",
                    "focus": "分析深度学习、NLP等技术在医疗、制造等多个领域的应用",
                    "key_points": [
                        "CNN在医学影像诊断中的应用",
                        "NLP技术在情感分析中的进展",
                        "深度强化学习在决策优化中的应用"
                    ],
                    "comparison_points": [
                        "同一技术在不同领域的应用差异",
                        "跨领域技术迁移的挑战和解决方案"
                    ]
                }
            ],
            "conclusion": {
                "focus": "总结AI技术在质量管理中的应用现状，指出未来研究方向"
            }
        },
        "section_keywords": {
            "深度学习在图像识别中的应用": ["深度学习", "图像识别", "CNN"],
            "质量管理中的数据驱动方法": ["数据挖掘", "质量控制", "六西格码"],
            "AI技术的跨领域应用": ["深度学习", "自然语言处理", "强化学习"]
        }
    }

    # 创建生成器
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("DEEPSEEK_API_KEY 未设置，跳过实际测试")
        return

    generator = ReviewGeneratorFCUnified(api_key=api_key)

    print("=" * 80)
    print("测试：Function Calling 统一版本")
    print("=" * 80)
    print(f"\n测试参数:")
    print(f"  - 论文数量: {len(papers)} 篇")
    print(f"  - 小节数量: {len(framework['outline']['body_sections'])} 个")
    print(f"  - 模型: deepseek-chat")

    try:
        # 生成综述
        review, cited_papers = await generator.generate_review(
            topic="AI技术在质量管理中的应用研究",
            papers=papers,
            framework=framework
        )

        print("\n" + "=" * 80)
        print("测试成功！")
        print("=" * 80)
        print(f"\n生成统计:")
        print(f"  - 内容长度: {len(review)} 字符")
        print(f"  - 引用论文数: {len(cited_papers)}/{len(papers)} 篇")
        print(f"  - 引用率: {len(cited_papers)/len(papers)*100:.1f}%")

        print(f"\n引用的论文:")
        for i, paper in enumerate(cited_papers, 1):
            print(f"  {i}. [{paper.get('id')}] {paper.get('title', '')}")

        print(f"\n综述预览（前800字）:")
        print(review[:800] + "...")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_unified_version())
