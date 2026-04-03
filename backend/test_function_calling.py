"""
测试 Function Calling vs 传统方式的 token 消耗对比
"""
import asyncio
import json
import os
from dotenv import load_dotenv
from services.review_generator_function_calling import ReviewGeneratorFunctionCalling

load_dotenv()


async def test_token_comparison():
    """对比两种方式的 token 消耗"""

    # 模拟60篇论文
    papers = []
    for i in range(1, 61):
        papers.append({
            "id": f"paper_{i}",
            "title": f"深度学习在{['图像识别', '自然语言处理', '推荐系统', '质量控制', '异常检测'][i%5]}中的应用研究 #{i}",
            "authors": [f"作者{i}A", f"作者{i}B", f"作者{i}C"],
            "year": 2020 + (i % 6),
            "venue_name": f"Journal of {['Computer Science', 'AI', 'Machine Learning', 'Quality Engineering'][i%4]}",
            "abstract": f"这是第{i}篇论文的摘要。本研究探讨了深度学习技术在相关领域的应用，通过实验验证了方法的有效性。研究采用了卷积神经网络、循环神经网络等深度学习模型，在标准数据集上取得了优异的性能表现。该方法具有较高的实用价值和推广前景。" * 5,  # 模拟长摘要
            "concepts": [f"concept{j}" for j in range(1, 11)],
            "cited_by_count": i * 10
        })

    # 模拟框架
    framework = {
        "outline": {
            "introduction": {
                "focus": "介绍深度学习在质量控制中的应用背景"
            },
            "body_sections": [
                {
                    "title": "深度学习在图像识别中的应用",
                    "focus": "综述CNN等模型在图像识别领域的研究进展"
                },
                {
                    "title": "深度学习在自然语言处理中的应用",
                    "focus": "综述Transformer、BERT等模型的研究进展"
                },
                {
                    "title": "深度学习在质量控制中的应用",
                    "focus": "综述深度学习在质量检测、异常识别中的应用"
                }
            ]
        }
    }

    # === 计算 token 消耗 ===

    print("=" * 80)
    print("Token 消耗对比分析")
    print("=" * 80)

    # 方式1：传统方式（发送完整元数据）
    print("\n【方式1：传统方式】")
    papers_json = json.dumps(papers, ensure_ascii=False)
    traditional_tokens = len(papers_json) // 4  # 粗略估算：1 token ≈ 4 字符
    print(f"  - 发送内容：完整论文元数据（标题、作者、摘要、概念等）")
    print(f"  - 论文数量：{len(papers)} 篇")
    print(f"  - 字符数：{len(papers_json):,}")
    print(f"  - Token 估算：{traditional_tokens:,} tokens")
    print(f"  - 假设每篇摘要500字，摘要总token：{len(papers) * 500 // 4:,} tokens")

    # 方式2：Function Calling（只发送标题）
    print("\n【方式2：Function Calling】")

    # 标题列表
    title_lines = ["【参考文献列表】"]
    for i, paper in enumerate(papers, 1):
        title = paper["title"]
        year = paper["year"]
        first_author = paper["authors"][0]
        title_lines.append(f"{i}. {title} ({year}) - {first_author}等")
    title_list = "\n".join(title_lines)

    fc_initial_tokens = len(title_list) // 4
    print(f"  - 初始发送：仅标题列表")
    print(f"  - 字符数：{len(title_list):,}")
    print(f"  - Token 估算：{fc_initial_tokens:,} tokens")

    # 假设访问了30篇论文的详细信息
    accessed_count = 30
    details_per_paper = 800  # 每篇论文详情平均字符数
    fc_details_tokens = accessed_count * details_per_paper // 4
    total_fc_tokens = fc_initial_tokens + fc_details_tokens

    print(f"\n  - 访问论文详情：{accessed_count} 篇（按需获取）")
    print(f"  - 每篇详情字符数：{details_per_paper}")
    print(f"  - 详情 Token：{fc_details_tokens:,} tokens")
    print(f"  - 总 Token：{total_fc_tokens:,} tokens")

    # 对比
    print("\n" + "=" * 80)
    print("【对比结果】")
    print("=" * 80)
    print(f"  - 传统方式：{traditional_tokens:,} tokens")
    print(f"  - Function Calling：{total_fc_tokens:,} tokens")
    print(f"  - 节省：{traditional_tokens - total_fc_tokens:,} tokens ({(1 - total_fc_tokens/traditional_tokens)*100:.1f}%)")
    print(f"  - 假设 $0.14/1M tokens（输入），节省费用：${(traditional_tokens - total_fc_tokens) * 0.14 / 1000000:.4f}")

    # 注意力分散分析
    print("\n【注意力分散分析】")
    print(f"  - 传统方式：LLM 需要从 60 篇完整摘要中找出相关内容")
    print(f"  - Function Calling：LLM 按需获取 30 篇摘要，注意力更集中")
    print(f"  - 注意力效率提升：{(60/30):.1f}x")

    # 实际测试（如果有 API key）
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        print("\n" + "=" * 80)
        print("【实际测试】")
        print("=" * 80)

        try:
            generator = ReviewGeneratorFunctionCalling(api_key=api_key)

            # 使用较小的论文集进行测试（10篇）
            test_papers = papers[:10]
            test_framework = framework

            print("\n开始测试（10篇论文）...")

            content, cited_papers = await generator.generate_review_with_tools(
                topic="深度学习在质量控制中的应用",
                papers=test_papers,
                framework=test_framework,
                model="deepseek-chat"
            )

            print(f"\n✓ 测试完成")
            print(f"  - 生成内容长度：{len(content)} 字符")
            print(f"  - 引用论文数：{len(cited_papers)} 篇")

        except Exception as e:
            print(f"\n✗ 测试失败：{e}")
    else:
        print("\n【实际测试】")
        print("  - DEEPSEEK_API_KEY 未设置，跳过实际测试")


if __name__ == "__main__":
    asyncio.run(test_token_comparison())
