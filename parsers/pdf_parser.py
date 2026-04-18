"""
PDF 解析器

解析 .pdf 文件，提取文本和表格内容。
使用 pdfplumber 作为默认引擎。
"""

from __future__ import annotations

import re
from typing import Optional

import pdfplumber

from parsers.base import BaseParser
from core.document_model import (
    DocumentModel, DocElement, ElementType, ParagraphStyle, Alignment,
    TableData, TableCell,
)


class PdfParser(BaseParser):
    """PDF 文件解析器"""

    supported_extensions = [".pdf"]

    def parse(self, file_path: str, **kwargs) -> DocumentModel:
        """解析 .pdf 文件"""
        abs_path = self._validate_file(file_path)

        model = DocumentModel(
            source_file=abs_path,
            source_format="pdf",
            title=kwargs.get("title", ""),
        )

        with pdfplumber.open(abs_path) as pdf:
            model.metadata["page_count"] = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, start=1):
                self._extract_page(page, page_num, model)

        return model

    def _extract_page(self, page, page_num: int, model: DocumentModel):
        """提取单页内容"""
        # 提取文本
        text = page.extract_text()
        if text:
            self._extract_text_blocks(text, page_num, model)

        # 提取表格
        tables = page.extract_tables()
        if tables:
            for table_idx, table_data in enumerate(tables, start=1):
                table = self._parse_pdf_table(table_data, page_num, table_idx)
                if table and table.num_rows > 0:
                    model.tables.append(table)

    def _extract_text_blocks(self, text: str, page_num: int, model: DocumentModel):
        """从提取的文本中识别段落和标题"""
        # pdfplumber 通常按行提取文本，用换行分隔
        lines = text.split("\n")

        # 合并连续短行为段落
        paragraphs = self._merge_lines_to_paragraphs(lines)

        for para_text in paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue

            elem_type, level = self._detect_element_type(para_text)

            model.elements.append(DocElement(
                element_type=elem_type,
                content=para_text,
                level=level,
                paragraph_style=ParagraphStyle(
                    alignment=Alignment.CENTER if level > 0 else Alignment.JUSTIFY,
                ),
                metadata={"page": page_num},
            ))

    def _merge_lines_to_paragraphs(self, lines: list[str]) -> list[str]:
        """将连续的行合并为段落"""
        paragraphs = []
        current_para = ""

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_para:
                    paragraphs.append(current_para)
                    current_para = ""
                continue

            # 如果当前行看起来像标题（短且无标点），独立成段
            if self._is_likely_heading(stripped):
                if current_para:
                    paragraphs.append(current_para)
                    current_para = ""
                paragraphs.append(stripped)
                continue

            if current_para:
                current_para += " " + stripped
            else:
                current_para = stripped

        if current_para:
            paragraphs.append(current_para)

        return paragraphs

    def _is_likely_heading(self, text: str) -> bool:
        """判断文本是否像标题"""
        if len(text) > 50:
            return False
        if re.match(r"^[一二三四五六七八九十]+、", text):
            return True
        if re.match(r"^第[一二三四五六七八九十\d]+[章节篇部]", text):
            return True
        if re.match(r"^\d+(\.\d+)*\s", text) and len(text) < 40:
            return True
        # 短行且无中文标点
        if len(text) < 25 and not re.search(r"[，。！？；：]", text):
            return True
        return False

    def _detect_element_type(self, text: str) -> tuple[ElementType, int]:
        """检测元素类型"""
        # 标题模式
        if re.match(r"^第[一二三四五六七八九十\d]+[章节篇部]", text):
            return ElementType.HEADING, 1
        if re.match(r"^[一二三四五六七八九十]+、", text):
            return ElementType.HEADING, 1
        if re.match(r"^（[一二三四五六七八九十]+）", text):
            return ElementType.HEADING, 2
        if re.match(r"^\d+\.\s", text) and len(text) < 50:
            return ElementType.HEADING, 3
        if re.match(r"^（\d+）", text):
            return ElementType.HEADING, 4
        # 参考文献
        if re.match(r"^\[[\d,\-–]+\]", text):
            return ElementType.REFERENCE, 0
        # 图表题注
        if re.match(r"^(图|表|Figure|Table)\s*[\d\-–]", text):
            return ElementType.CAPTION, 0

        return ElementType.PARAGRAPH, 0

    def _parse_pdf_table(self, table_data: list, page_num: int, table_idx: int) -> Optional[TableData]:
        """解析 PDF 中提取的表格数据"""
        rows = []
        for row_idx, row in enumerate(table_data):
            cells = []
            for cell_text in row:
                cells.append(TableCell(
                    content=str(cell_text).strip() if cell_text else "",
                    is_header=(row_idx == 0),
                ))
            if any(c.content for c in cells):
                rows.append(cells)

        if not rows:
            return None

        return TableData(
            caption=f"表{page_num}-{table_idx}",
            numbering=f"表{page_num}-{table_idx}",
            rows=rows,
        )
