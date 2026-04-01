"""
简化的争议分析演示
"""
import asyncio
from services.controversy_analyzer import ControversySectionGenerator


# 模拟论文数据
DEMO_PAPERS = [
    {
        "id": "1",
        "title": "媒体关注度能抑制盈余管理",
        "abstract": "研究发现高媒体关注度发挥监督职能，有效抑制盈余管理行为。",
        "year": 2019
    },
    {
        "id": "2",
        "title": "业绩压力下媒体关注可能诱发盈余管理",
        "abstract": "在业绩压力下，高媒体关注度反而可能诱发企业进行应计盈余管理。",
        "year": 2020
    },
    {
        "id": "3",
        "title": "公司治理的调节作用研究",
        "abstract": "媒体关注度的效应取决于公司治理水平，治理良好的企业监督作用更显著。",
        "year": 2021
    },
]


async def demo():
    """演示争议分析功能"""
    print("=" * 80)
    print("观点碰撞模块演示")
    print("=" * 80)

    generator = ControversySectionGenerator()

    # 生成争议章节
    controversy_section = await generator.generate_controversy_section(
        papers=DEMO_PAPERS,
        topic="媒体关注与盈余管理",
        section_name="监督效应",
        cited_indices=[1, 2, 3]
    )

    print("\n生成的【争议与对话】章节:")
    print("-" * 80)
    print(controversy_section)
    print("-" * 80)

    print("\n核心功能说明:")
    print("1. 观点提取 (ViewpointExtractor): 从论文中提取核心观点")
    print("2. 争议分析 (ControversyAnalyzer): 识别对立观点和分歧点")
    print("3. 结构化生成: 输出Markdown格式的争议与对话内容")
    print("\n结构包括:")
    print("  - 争议点描述")
    print("  - 对立观点A + 支持文献")
    print("  - 对立观点B + 支持文献")
    print("  - 可能的原因（样本、方法、情境、理论差异）")


if __name__ == "__main__":
    asyncio.run(demo())
