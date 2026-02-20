#!/usr/bin/env python3
"""
Markdown to PDF Generator with Theme Support
从 Markdown 生成 PDF，支持主题配置
"""

import os
import re
import yaml
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class ThemeManager:
    """主题管理器"""

    def __init__(self, config_path="theme_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.font_name = self._setup_font()

    def _load_config(self):
        """加载主题配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return self._default_config()

    def _default_config(self):
        """默认配置"""
        return {
            'colors': {
                'title': '#1a365d',
                'heading': '#2c5282',
                'subheading': '#2f855a',
                'text': '#1a202c',
                'code_bg': '#f7fafc',
                'code_text': '#1a202c',
                'table_header': '#2c5282',
                'table_header_text': '#ffffff',
                'table_row': '#ebf8ff',
                'table_border': '#a0aec0',
                'link': '#3182ce',
            },
            'fonts': {
                'chinese': [
                    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                    '/usr/share/fonts/truetype/arphic/uming.ttc',
                ],
                'default': 'Helvetica'
            },
            'font_sizes': {
                'title': 28, 'heading': 18, 'subheading': 14,
                'normal': 11, 'code': 9, 'table_header': 12
            },
            'line_height': {
                'title': 36, 'heading': 24, 'subheading': 18,
                'normal': 14, 'code': 11
            },
            'spacing': {
                'page': {'top': 1.0, 'bottom': 1.0, 'left': 1.0, 'right': 1.0},
                'title_after': 0.5, 'heading_before': 0.4, 'heading_after': 0.3,
                'subheading_before': 0.3, 'subheading_after': 0.2,
                'normal_after': 0.2, 'code_after': 0.3
            },
            'code_block': {'indent': 0.5, 'padding': 0.2},
            'table': {'col_widths': [2.5, 3.5], 'border_width': 0.5},
            'page': {'size': 'A4'},
            'output': {'filename': 'output.pdf'}
        }

    def _setup_font(self):
        """设置中文字体"""
        font_paths = self.config.get('fonts', {}).get('chinese', [])
        for font_path in font_paths:
            try:
                font_name = 'ThemeFont'
                pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                print(f"[Theme] 使用字体: {font_path}")
                return font_name
            except Exception as e:
                continue
        print(f"[Theme] 警告: 未找到中文字体，使用默认字体")
        return self.config.get('fonts', {}).get('default', 'Helvetica')

    def get_color(self, key):
        """获取颜色"""
        hex_color = self.config.get('colors', {}).get(key, '#000000')
        return colors.HexColor(hex_color)

    def get_style_config(self, style_type):
        """获取样式配置"""
        config = {}
        if style_type in ['title', 'heading', 'subheading', 'normal', 'code', 'table_header']:
            config['fontSize'] = self.config.get('font_sizes', {}).get(style_type, 11)
            config['leading'] = self.config.get('line_height', {}).get(style_type, 14)
            if style_type == 'title':
                config['textColor'] = self.get_color('title')
                config['alignment'] = TA_CENTER
            elif style_type == 'heading':
                config['textColor'] = self.get_color('heading')
            elif style_type == 'subheading':
                config['textColor'] = self.get_color('subheading')
            elif style_type == 'normal':
                config['textColor'] = self.get_color('text')
            elif style_type == 'code':
                config['textColor'] = self.get_color('code_text')
                config['backColor'] = self.get_color('code_bg')
                config['leftIndent'] = self.config.get('code_block', {}).get('indent', 0.5) * cm
                config['rightIndent'] = self.config.get('code_block', {}).get('indent', 0.5) * cm
                config['borderPadding'] = self.config.get('code_block', {}).get('padding', 0.2) * cm
        return config

    def create_styles(self):
        """创建所有样式"""
        styles = getSampleStyleSheet()
        base_styles = {}

        # Title Style
        cfg = self.get_style_config('title')
        base_styles['title'] = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontName=self.font_name,
            **cfg
        )

        # Heading Style
        cfg = self.get_style_config('heading')
        cfg['spaceAfter'] = self.config.get('spacing', {}).get('heading_after', 0.3) * cm
        cfg['spaceBefore'] = self.config.get('spacing', {}).get('heading_before', 0.4) * cm
        base_styles['heading'] = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontName=self.font_name,
            **cfg
        )

        # Subheading Style
        cfg = self.get_style_config('subheading')
        cfg['spaceAfter'] = self.config.get('spacing', {}).get('subheading_after', 0.2) * cm
        cfg['spaceBefore'] = self.config.get('spacing', {}).get('subheading_before', 0.3) * cm
        base_styles['subheading'] = ParagraphStyle(
            'Subheading',
            parent=styles['Heading3'],
            fontName=self.font_name,
            **cfg
        )

        # Normal Style
        cfg = self.get_style_config('normal')
        cfg['spaceAfter'] = self.config.get('spacing', {}).get('normal_after', 0.2) * cm
        base_styles['normal'] = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontName=self.font_name,
            **cfg
        )

        # Code Style
        cfg = self.get_style_config('code')
        cfg['spaceAfter'] = self.config.get('spacing', {}).get('code_after', 0.3) * cm
        base_styles['code'] = ParagraphStyle(
            'Code',
            parent=styles['Code'],
            fontName=self.font_name,
            **cfg
        )

        return base_styles


class MarkdownParser:
    """Markdown 解析器"""

    def __init__(self, content):
        self.content = content
        self.tokens = self._parse()

    def _parse(self):
        """解析 Markdown 内容"""
        tokens = []
        lines = self.content.split('\n')
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]

            # 空行
            if not line.strip():
                i += 1
                continue

            # 标题
            if line.startswith('# '):
                tokens.append({'type': 'title', 'text': line[2:].strip()})
            elif line.startswith('## '):
                tokens.append({'type': 'heading', 'text': line[3:].strip()})
            elif line.startswith('### '):
                tokens.append({'type': 'subheading', 'text': line[4:].strip()})
            elif line.startswith('#### '):
                tokens.append({'type': 'subheading', 'text': line[5:].strip()})
            elif line.startswith('##### '):
                tokens.append({'type': 'subheading', 'text': line[6:].strip()})
            # 代码块
            elif line.strip().startswith('```'):
                code_lines = []
                i += 1
                while i < n and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                tokens.append({'type': 'code', 'text': '\n'.join(code_lines)})
            # 列表
            elif re.match(r'^\s*[-*]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                # 收集所有连续列表项
                list_items = []
                while i < n and (re.match(r'^\s*[-*]\s+', lines[i]) or
                                 re.match(r'^\s*\d+\.\s+', lines[i])):
                    match = re.match(r'^\s*[-*]\s+(.+)', lines[i])
                    if not match:
                        match = re.match(r'^\s*\d+\.\s+(.+)', lines[i])
                    if match:
                        list_items.append(match.group(1))
                    i += 1
                tokens.append({'type': 'list', 'items': list_items})
                continue
            # 表格
            elif '|' in line and i + 1 < n and '|' in lines[i + 1]:
                table_data = []
                while i < n and '|' in lines[i]:
                    row = [cell.strip() for cell in lines[i].split('|')[1:-1]]
                    if row and row[0]:  # 跳过分隔行
                        table_data.append(row)
                    i += 1
                if len(table_data) > 1:
                    tokens.append({'type': 'table', 'data': table_data})
                continue
            # 分隔线
            elif line.strip() == '---':
                tokens.append({'type': 'divider'})
            # 普通段落
            else:
                # 收集连续的非空行
                para_lines = [line]
                i += 1
                while i < n and lines[i].strip() and not lines[i].startswith('#') and \
                      lines[i].strip() != '---' and '|' not in lines[i]:
                    para_lines.append(lines[i])
                    i += 1
                tokens.append({'type': 'paragraph', 'text': ' '.join(para_lines)})
                continue

            i += 1

        return tokens


class PDFGenerator:
    """PDF 生成器"""

    def __init__(self, theme_manager=None):
        self.theme = theme_manager or ThemeManager()
        self.styles = self.theme.create_styles()

    def _escape_xml(self, text):
        """转义 XML 特殊字符"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text

    def _format_code(self, text):
        """格式化代码"""
        return self._escape_xml(text)

    def generate(self, markdown_content, output_path=None):
        """生成 PDF"""
        if output_path is None:
            output_path = self.theme.config.get('output', {}).get('filename', 'output.pdf')

        parser = MarkdownParser(markdown_content)

        # 创建文档
        page_size = A4 if self.theme.config.get('page', {}).get('size', 'A4') == 'A4' else letter
        spacing = self.theme.config.get('spacing', {}).get('page', {})

        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=spacing.get('right', 1) * cm,
            leftMargin=spacing.get('left', 1) * cm,
            topMargin=spacing.get('top', 1) * cm,
            bottomMargin=spacing.get('bottom', 1) * cm
        )

        story = []

        for token in parser.tokens:
            token_type = token['type']

            if token_type == 'title':
                story.append(Paragraph(self._escape_xml(token['text']), self.styles['title']))
                story.append(Spacer(1, self.theme.config.get('spacing', {}).get('title_after', 0.5) * cm))

            elif token_type == 'heading':
                story.append(Paragraph(self._escape_xml(token['text']), self.styles['heading']))

            elif token_type == 'subheading':
                story.append(Paragraph(self._escape_xml(token['text']), self.styles['subheading']))

            elif token_type == 'paragraph':
                story.append(Paragraph(self._escape_xml(token['text']), self.styles['normal']))

            elif token_type == 'code':
                story.append(Paragraph(self._format_code(token['text']), self.styles['code']))

            elif token_type == 'list':
                for item in token['items']:
                    story.append(Paragraph(u"\u2022 " + self._escape_xml(item), self.styles['normal']))
                story.append(Spacer(1, 0.2 * cm))

            elif token_type == 'table':
                col_widths = [w * inch for w in self.theme.config.get('table', {}).get('col_widths', [2.5, 3.5])]
                table = Table(token['data'], colWidths=col_widths)
                border_width = self.theme.config.get('table', {}).get('border_width', 0.5)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.theme.get_color('table_header')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), self.theme.get_color('table_header_text')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), self.theme.font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), self.theme.config.get('font_sizes', {}).get('table_header', 12)),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), self.theme.get_color('table_row')),
                    ('GRID', (0, 0), (-1, -1), border_width, self.theme.get_color('table_border'))
                ]))
                story.append(table)
                story.append(Spacer(1, 0.5 * cm))

            elif token_type == 'divider':
                story.append(Spacer(1, 0.5 * cm))

        # 生成 PDF
        def draw_white_bg(canvas, doc):
            canvas.saveState()
            canvas.setFillColorRGB(1, 1, 1)
            canvas.rect(0, 0, page_size[0], page_size[1], fill=1, stroke=0)
            canvas.restoreState()

        doc.build(story, onFirstPage=draw_white_bg, onLaterPages=draw_white_bg)
        return output_path


def main():
    """主函数"""
    import sys
    content_path = sys.argv[1] if len(sys.argv) > 1 else "main.md"
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(content_path):
        print(f"错误: 找不到 {content_path}")
        sys.exit(1)

    with open(content_path, 'r', encoding='utf-8') as f:
        content = f.read()

    generator = PDFGenerator()
    output_path = generator.generate(content, out_path)
    print(f"PDF 生成成功: {output_path}")


if __name__ == "__main__":
    main()
