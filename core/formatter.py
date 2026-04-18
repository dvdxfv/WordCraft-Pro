"""
排版引擎 (Formatter)

将 FormattingRules 中的排版规则应用到 DocumentModel 的元素上。
不直接操作 .docx 文件，而是修改 DocumentModel 中的样式属性，
最终由 Exporter 负责将 DocumentModel 写入 .docx。
"""

from __future__ import annotations

from typing import Optional

from core.document_model import (
    DocumentModel, DocElement, ElementType,
    FontStyle, ParagraphStyle, Alignment, LineSpacingType,
    TableData, TableCell,
)
from core.formatting_rules import FormattingRules, StyleRules


class Formatter:
    """排版引擎 — 将排版规则应用到文档模型"""

    def __init__(self, rules: FormattingRules):
        self.rules = rules

    def apply(self, doc: DocumentModel) -> DocumentModel:
        """
        将排版规则应用到文档模型。

        Args:
            doc: 待排版的文档模型

        Returns:
            排版后的文档模型（原地修改并返回）
        """
        # 1. 应用页面设置
        self._apply_page_setup(doc)

        # 2. 应用多节配置
        self._apply_sections(doc)

        # 3. 应用元素样式
        self._apply_element_styles(doc)

        # 4. 应用表格样式
        self._apply_table_styles(doc)

        return doc

    def _apply_page_setup(self, doc: DocumentModel):
        """应用页面设置"""
        page = self.rules.page
        if page.paper_size:
            doc.page_setup.paper_size = page.paper_size
        if page.orientation:
            doc.page_setup.orientation = page.orientation
        if page.margin_top_cm is not None:
            doc.page_setup.margin_top_cm = page.margin_top_cm
        if page.margin_bottom_cm is not None:
            doc.page_setup.margin_bottom_cm = page.margin_bottom_cm
        if page.margin_left_cm is not None:
            doc.page_setup.margin_left_cm = page.margin_left_cm
        if page.margin_right_cm is not None:
            doc.page_setup.margin_right_cm = page.margin_right_cm
        if page.gutter_cm is not None:
            doc.page_setup.gutter_cm = page.gutter_cm
        if page.header_distance_cm is not None:
            doc.page_setup.header_distance_cm = page.header_distance_cm
        if page.footer_distance_cm is not None:
            doc.page_setup.footer_distance_cm = page.footer_distance_cm

    def _apply_sections(self, doc: DocumentModel):
        """应用多节页眉页脚配置"""
        if self.rules.sections:
            doc.sections = []
            for section_rule in self.rules.sections:
                from core.document_model import (
                    SectionConfig, HeaderFooterConfig, PageNumberConfig
                )
                section = SectionConfig(
                    name=section_rule.name,
                    first_page_different=section_rule.first_page_different or False,
                )
                if section_rule.header_text:
                    section.header = HeaderFooterConfig(
                        text=section_rule.header_text,
                        font_name=section_rule.header_font or "",
                        font_size_pt=section_rule.header_size_pt or 10.5,
                        bold=section_rule.header_bold or False,
                    )
                if section_rule.first_page_header_text:
                    section.first_page_header = HeaderFooterConfig(
                        text=section_rule.first_page_header_text,
                        font_name=section_rule.first_page_header_font or "",
                        font_size_pt=section_rule.first_page_header_size_pt or 10.5,
                        bold=section_rule.first_page_header_bold or False,
                    )
                if section_rule.page_number_enabled:
                    from core.document_model import PageNumberFormat
                    pn = PageNumberConfig(enabled=True)
                    if section_rule.page_number_format:
                        pn.format = section_rule.page_number_format
                    if section_rule.page_number_type:
                        pn.number_format = section_rule.page_number_type
                    if section_rule.page_number_start_from:
                        pn.start_from = section_rule.page_number_start_from
                    section.page_number = pn
                doc.sections.append(section)

    def _apply_element_styles(self, doc: DocumentModel):
        """遍历所有元素，根据类型应用对应的样式规则"""
        for elem in doc.elements:
            self._apply_style_to_element(elem)

    def _apply_style_to_element(self, elem: DocElement):
        """根据元素类型应用样式"""
        if elem.element_type == ElementType.HEADING:
            self._apply_heading_style(elem)
        elif elem.element_type == ElementType.PARAGRAPH:
            self._apply_body_style(elem)
        elif elem.element_type == ElementType.CAPTION:
            self._apply_caption_style(elem)
        elif elem.element_type == ElementType.REFERENCE:
            self._apply_reference_style(elem)
        elif elem.element_type == ElementType.LIST_ITEM:
            self._apply_body_style(elem)

        # 递归处理子元素
        for child in elem.children:
            self._apply_style_to_element(child)

    def _apply_heading_style(self, elem: DocElement):
        """应用标题样式"""
        level = elem.level if elem.level > 0 else 1
        style_rules = self.rules.get_heading_style(level)

        if style_rules is None:
            # 如果没有对应层级的规则，尝试用正文样式
            self._apply_body_style(elem)
            return

        self._merge_font_style(elem.font_style, style_rules)
        self._merge_paragraph_style(elem.paragraph_style, style_rules)

    def _apply_body_style(self, elem: DocElement):
        """应用正文样式"""
        self._merge_font_style(elem.font_style, self.rules.body)
        self._merge_paragraph_style(elem.paragraph_style, self.rules.body)

    def _apply_caption_style(self, elem: DocElement):
        """应用题注样式（根据内容判断图题/表题）"""
        content = elem.content
        if content.startswith("表"):
            self._merge_font_style(elem.font_style, self.rules.table_caption)
            self._merge_paragraph_style(elem.paragraph_style, self.rules.table_caption)
        elif content.startswith("图"):
            self._merge_font_style(elem.font_style, self.rules.figure_caption)
            self._merge_paragraph_style(elem.paragraph_style, self.rules.figure_caption)
        else:
            self._merge_font_style(elem.font_style, self.rules.table_caption)
            self._merge_paragraph_style(elem.paragraph_style, self.rules.table_caption)

    def _apply_reference_style(self, elem: DocElement):
        """应用参考文献样式"""
        self._merge_font_style(elem.font_style, self.rules.reference)
        self._merge_paragraph_style(elem.paragraph_style, self.rules.reference)

    def _merge_font_style(self, target: FontStyle, source: StyleRules):
        """将 StyleRules 中的字体属性合并到 FontStyle（None 值不覆盖）"""
        if source.font_name_cn is not None:
            target.font_name_cn = source.font_name_cn
        if source.font_name_en is not None:
            target.font_name_en = source.font_name_en
        if source.font_size_pt is not None:
            target.font_size_pt = source.font_size_pt
        if source.bold is not None:
            target.bold = source.bold
        if source.italic is not None:
            target.italic = source.italic
        if source.underline is not None:
            target.underline = source.underline
        if source.color is not None:
            target.color = source.color

    def _merge_paragraph_style(self, target: ParagraphStyle, source: StyleRules):
        """将 StyleRules 中的段落属性合并到 ParagraphStyle（None 值不覆盖）"""
        if source.alignment is not None:
            target.alignment = source.alignment
        if source.first_indent_chars is not None:
            target.first_indent_chars = source.first_indent_chars
        if source.first_indent_cm is not None:
            target.first_indent_cm = source.first_indent_cm
        if source.left_indent_cm is not None:
            target.left_indent_cm = source.left_indent_cm
        if source.right_indent_cm is not None:
            target.right_indent_cm = source.right_indent_cm
        if source.line_spacing_type is not None:
            target.line_spacing_type = source.line_spacing_type
        if source.line_spacing_value is not None:
            target.line_spacing_value = source.line_spacing_value
        if source.space_before_pt is not None:
            target.space_before_pt = source.space_before_pt
        if source.space_after_pt is not None:
            target.space_after_pt = source.space_after_pt
        if source.keep_with_next is not None:
            target.keep_with_next = source.keep_with_next

    def _apply_table_styles(self, doc: DocumentModel):
        """应用表格样式"""
        for table in doc.tables:
            self._apply_table_style(table)

    def _apply_table_style(self, table: TableData):
        """应用单个表格的样式"""
        # 表体样式
        body_style = self.rules.table_body
        if body_style:
            for row in table.rows:
                for cell in row:
                    if not cell.is_header:
                        self._apply_cell_style(cell, body_style)

        # 表题样式（通过 caption 元素应用，这里设置表格属性）
        if self.rules.table_caption.alignment:
            table.alignment = self.rules.table_caption.alignment
