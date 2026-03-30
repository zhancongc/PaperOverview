"""
Word 文档生成服务
将文献综述导出为 .docx 格式
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import re
from typing import List, Dict


class DocxGenerator:
    def __init__(self):
        pass

    def generate_review_docx(
        self,
        topic: str,
        review: str,
        papers: List[Dict],
        statistics: Dict | None = None
    ) -> bytes:
        """
        生成文献综述的 Word 文档

        Args:
            topic: 论文主题
            review: 综述内容（Markdown 格式）
            papers: 文献列表
            statistics: 统计信息

        Returns:
            Word 文档的二进制内容
        """
        doc = Document()

        # 设置文档样式
        self._setup_document_styles(doc)

        # 添加标题
        title = doc.add_heading(topic, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 添加摘要/统计信息
        if statistics:
            self._add_statistics(doc, statistics)

        # 解析并添加 Markdown 内容
        self._add_markdown_content(doc, review)

        # 保存到 BytesIO
        from io import BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return buffer.read()

    def _setup_document_styles(self, doc):
        """设置文档样式"""
        # 设置正文样式
        style = doc.styles['Normal']
        font = style.font
        font.name = '宋体'
        font.size = Pt(12)
        font.color.rgb = RGBColor(0, 0, 0)

        # 设置中文字体
        style._element.rPr.rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia', '宋体')

    def _add_statistics(self, doc, statistics):
        """添加统计信息"""
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.add_run('文献统计：').bold = True
        stats_text = (
            f"文献总数：{statistics.get('total', 0)}篇 | "
            f"近5年文献占比：{(statistics.get('recent_ratio', 0) * 100):.1f}% | "
            f"英文文献占比：{(statistics.get('english_ratio', 0) * 100):.1f}% | "
            f"总被引量：{statistics.get('total_citations', 0)}次"
        )
        p.add_run(stats_text)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _add_markdown_content(self, doc, review: str):
        """解析并添加 Markdown 内容到文档"""
        lines = review.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            # 跳过空行
            if not line or line.isspace():
                i += 1
                continue

            # 标题
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title_text = line.lstrip('#').strip()
                if title_text:
                    heading = doc.add_heading(title_text, min(level, 6))
                    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                i += 1
                continue

            # 引用块
            if line.startswith('>'):
                quote_text = line.lstrip('>').strip()
                p = doc.add_paragraph(quote_text, style='Quote')
                i += 1
                continue

            # 无序列表
            if line.strip().startswith(('- ', '* ', '+ ')):
                self._add_list_item(doc, line, ordered=False)
                i += 1
                continue

            # 有序列表
            if re.match(r'^\d+\.\s+', line.strip()):
                self._add_list_item(doc, line, ordered=True)
                i += 1
                continue

            # 分隔线
            if line.strip() in ('---', '***', '___'):
                doc.add_paragraph('_' * 50)
                i += 1
                continue

            # 普通段落（处理行内格式）
            self._add_formatted_paragraph(doc, line)
            i += 1

    def _add_list_item(self, doc, line, ordered=False):
        """添加列表项"""
        # 移除列表标记
        if ordered:
            text = re.sub(r'^\d+\.\s+', '', line.strip())
        else:
            text = re.sub(r'^[-*+]\s+', '', line.strip())

        # 处理行内格式
        p = doc.add_paragraph(style='List Paragraph')
        self._add_formatted_runs(p, text)
        p.paragraph_format.left_indent = Inches(0.25)

    def _add_formatted_paragraph(self, doc, line):
        """添加带格式的段落"""
        p = doc.add_paragraph()
        self._add_formatted_runs(p, line)

    def _add_formatted_runs(self, paragraph, text):
        """解析并添加带格式的文本"""
        i = 0
        while i < len(text):
            # 检查粗体 **text** 或 __text__
            if (text[i:i+2] == '**' or text[i:i+2] == '__') and i + 2 < len(text):
                end_marker = text[i]
                end_pos = text.find(end_marker * 2, i + 2)
                if end_pos != -1:
                    if i > 0:
                        paragraph.add_run(text[:i])
                    bold_text = text[i+2:end_pos]
                    paragraph.add_run(bold_text).bold = True
                    text = text[end_pos+2:]
                    i = 0
                    continue

            # 检查斜体 *text* 或 _text_
            if text[i] in ('*', '_') and i + 1 < len(text):
                end_pos = text.find(text[i], i + 1)
                if end_pos != -1:
                    if i > 0:
                        paragraph.add_run(text[:i])
                    italic_text = text[i+1:end_pos]
                    paragraph.add_run(italic_text).italic = True
                    text = text[end_pos+1:]
                    i = 0
                    continue

            # 检查行内代码 `text`
            if text[i] == '`' and i + 1 < len(text):
                end_pos = text.find('`', i + 1)
                if end_pos != -1:
                    if i > 0:
                        paragraph.add_run(text[:i])
                    code_text = text[i+1:end_pos]
                    run = paragraph.add_run(code_text)
                    run.font.name = 'Consolas'
                    run.font.size = Pt(10)
                    text = text[end_pos+1:]
                    i = 0
                    continue

            i += 1

        if text:
            paragraph.add_run(text)
