"""
Markdown 解析器

解析 .md 文件，提取标题、段落、列表、表格、代码块、图片等结构化内容。
"""

from __future__ import annotations

import re
from typing import Optional

from parsers.base import BaseParser
from core.document_model import (
    DocumentModel, DocElement, ElementType, ParagraphStyle, Alignment,
    FontStyle, LineSpacingType, NumberingType,
    TableData, TableCell,
)


class MdParser(BaseParser):
    """Markdown 文件解析器"""

    supported_extensions = [".md", ".markdown"]

    def parse(self, file_path: str, encoding: str = None, **kwargs) -> DocumentModel:
        """解析 .md 文件"""
        abs_path = self._validate_file(file_path)
        text = self._read_text_file(abs_path, encoding)

        model = DocumentModel(
            source_file=abs_path,
            source_format="md",
            title=kwargs.get("title", ""),
        )

        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # 空行跳过
            if not line.strip():
                i += 1
                continue

            # 标题
            if line.startswith("#"):
                element = self._parse_heading(line)
                model.elements.append(element)
                i += 1
                continue

            # 代码块
            if line.strip().startswith("```"):
                element, i = self._parse_code_block(lines, i)
                if element:
                    model.elements.append(element)
                continue

            # 表格
            if "|" in line and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
                table, i = self._parse_table(lines, i)
                if table:
                    model.tables.append(table)
                continue

            # 无序列表
            if re.match(r"^\s*[-*+]\s", line):
                element, i = self._parse_list(lines, i, ordered=False)
                if element:
                    model.elements.append(element)
                continue

            # 有序列表
            if re.match(r"^\s*\d+\.\s", line):
                element, i = self._parse_list(lines, i, ordered=True)
                if element:
                    model.elements.append(element)
                continue

            # 图片
            img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
            if img_match:
                from core.document_model import ImageData
                model.images.append(ImageData(
                    caption=img_match.group(1),
                    file_path=img_match.group(2),
                ))
                i += 1
                continue

            # 引用块
            if line.startswith(">"):
                content = re.sub(r"^>\s*", "", line).strip()
                model.elements.append(DocElement(
                    element_type=ElementType.PARAGRAPH,
                    content=content,
                    paragraph_style=ParagraphStyle(left_indent_cm=1.0),
                    metadata={"blockquote": True},
                ))
                i += 1
                continue

            # 水平线
            if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line.strip()):
                i += 1
                continue

            # 普通段落
            content = line.strip()
            # 收集连续非空行作为同一段落
            while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith("#"):
                next_line = lines[i + 1].strip()
                if next_line.startswith(("```", "|", ">", "- ", "* ", "+ ")) and not re.match(r"^\s*[-*+]\s", lines[i + 1]):
                    break
                if re.match(r"^\s*\d+\.\s", lines[i + 1]):
                    break
                content += "\n" + next_line
                i += 1

            # 清理 Markdown 格式标记
            content = self._clean_markdown(content)

            model.elements.append(DocElement(
                element_type=ElementType.PARAGRAPH,
                content=content,
                paragraph_style=ParagraphStyle(alignment=Alignment.JUSTIFY),
            ))
            i += 1

        return model

    def _parse_heading(self, line: str) -> DocElement:
        """解析 Markdown 标题"""
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if not match:
            return DocElement(element_type=ElementType.HEADING, content=line.strip())

        level = len(match.group(1))
        content = self._clean_markdown(match.group(2).strip())

        return DocElement(
            element_type=ElementType.HEADING,
            content=content,
            level=level,
            font_style=FontStyle(bold=True),
            paragraph_style=ParagraphStyle(
                alignment=Alignment.CENTER if level == 1 else Alignment.LEFT,
                space_before_pt=12,
                space_after_pt=6,
            ),
        )

    def _parse_code_block(self, lines: list[str], start: int) -> tuple[Optional[DocElement], int]:
        """解析代码块"""
        lang = lines[start].strip()[3:].strip()
        i = start + 1
        code_lines = []
        while i < len(lines) and not lines[i].strip().startswith("```"):
            code_lines.append(lines[i])
            i += 1
        i += 1  # 跳过结束的 ```

        content = "\n".join(code_lines)
        if not content.strip():
            return None, i

        return DocElement(
            element_type=ElementType.CODE_BLOCK,
            content=content,
            font_style=FontStyle(font_name_en="Consolas", font_size_pt=9),
            paragraph_style=ParagraphStyle(
                left_indent_cm=1.0,
                line_spacing_type=LineSpacingType.SINGLE,
            ),
            metadata={"language": lang},
        ), i

    def _parse_table(self, lines: list[str], start: int) -> tuple[Optional[TableData], int]:
        """解析 Markdown 表格"""
        rows = []
        i = start

        while i < len(lines) and "|" in lines[i]:
            line = lines[i].strip()
            # 跳过分隔行
            if re.match(r"^\|[\s\-:|]+\|$", line):
                i += 1
                continue

            cells = [c.strip() for c in line.split("|")[1:-1]]  # 去掉首尾空元素
            row_cells = []
            for j, cell_text in enumerate(cells):
                row_cells.append(TableCell(
                    content=self._clean_markdown(cell_text),
                    is_header=(len(rows) == 0),
                ))
            if row_cells:
                rows.append(row_cells)
            i += 1

        if not rows:
            return None, i

        return TableData(rows=rows), i

    def _parse_list(self, lines: list[str], start: int, ordered: bool) -> tuple[Optional[DocElement], int]:
        """解析列表"""
        items = []
        i = start
        pattern = re.compile(r"^\s*(\d+\.\s|[-*+]\s)")

        while i < len(lines):
            line = lines[i]
            if not line.strip():
                break  # 空行终止列表
            if not pattern.match(line):
                break

            content = pattern.sub("", line).strip()
            content = self._clean_markdown(content)
            items.append(DocElement(
                element_type=ElementType.LIST_ITEM,
                content=content,
            ))
            i += 1

        if not items:
            return None, i

        return DocElement(
            element_type=ElementType.LIST,
            children=items,
            numbering_type=NumberingType.DECIMAL if ordered else NumberingType.BULLET,
        ), i

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """清理 Markdown 格式标记"""
        # 加粗/斜体
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)
        # 行内代码
        text = re.sub(r"`(.+?)`", r"\1", text)
        # 链接
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # 图片
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
        return text.strip()
