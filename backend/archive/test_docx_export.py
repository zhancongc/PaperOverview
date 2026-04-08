#!/usr/bin/env python3
"""
测试带表格的 Markdown 导出到 docx
"""
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.docx_generator import DocxGenerator


def main():
    print("=" * 80)
    print("测试带表格的 Markdown 导出到 docx")
    print("=" * 80)

    # 加载之前生成的带表格的综述
    md_file = "test_with_tables_final_20260405_144323.md"

    if not os.path.exists(md_file):
        print(f"错误: 文件不存在: {md_file}")
        return

    print(f"\n加载 Markdown 文件: {md_file}")

    with open(md_file, "r", encoding="utf-8") as f:
        review_content = f.read()

    # 初始化生成器
    generator = DocxGenerator()

    # 生成 docx
    print("\n生成 Word 文档...")
    docx_bytes = generator.generate_review_docx(
        topic="computer algebra system的算法实现及应用",
        review=review_content,
        papers=[],
        statistics=None
    )

    # 保存文件
    output_file = "test_with_tables.docx"
    with open(output_file, "wb") as f:
        f.write(docx_bytes)

    print(f"✓ Word 文档已保存: {output_file}")
    print("\n" + "=" * 80)
    print("请打开 test_with_tables.docx 验证表格是否正常导出")
    print("=" * 80)


if __name__ == "__main__":
    main()
