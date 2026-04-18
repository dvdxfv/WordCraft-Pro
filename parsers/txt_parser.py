"""
TXT 解析器

解析纯文本文件，按空行分段，尝试识别标题层级。
"""

from __future__ import annotations

import re
from typing import Optional

from parsers.base import BaseParser
from core.document_model import (
    DocumentModel, DocElement, ElementType, ParagraphStyle, Alignment,
)


class TxtParser(BaseParser):
    """TXT 纯文本文件解析器"""

    supported_extensions = [".txt"]

    def parse(self, file_path: str, encoding: str = None, **kwargs) -> DocumentModel:
        """解析 .txt 文件"""
        abs_path = self._validate_file(file_path)
        text = self._read_text_file(abs_path, encoding)

        model = DocumentModel(
            source_file=abs_path,
            source_format="txt",
            title=kwargs.get("title", ""),
        )

        # 按空行分段
        blocks = re.split(r"\n\s*\n", text.strip())

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # 按行拆分
            lines = block.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                elem_type, level = self._detect_line_type(line)
                element = DocElement(
                    element_type=elem_type,
                    content=line,
                    level=level,
                    paragraph_style=ParagraphStyle(
                        alignment=Alignment.LEFT if level > 0 else Alignment.JUSTIFY,
                    ),
                )
                model.elements.append(element)

        return model

    def _detect_line_type(self, line: str) -> tuple[ElementType, int]:
        """检测行的类型（标题/正文/参考文献）"""
        # 中文数字标题：一、二、三、
        if re.match(r"^[一二三四五六七八九十]+、", line):
            return ElementType.HEADING, 1

        # 括号中文数字标题：（一）（二）
        if re.match(r"^（[一二三四五六七八九十]+）", line):
            return ElementType.HEADING, 2

        # 阿拉伯数字标题：1. 2. 3.
        if re.match(r"^\d+\.\s", line) and len(line) < 50:
            return ElementType.HEADING, 3

        # 括号阿拉伯数字标题：（1）（2）
        if re.match(r"^（\d+）", line):
            return ElementType.HEADING, 4

        # 第X章/节
        if re.match(r"^第[一二三四五六七八九十\d]+[章节篇部]", line):
            return ElementType.HEADING, 1

        # Markdown 风格标题
        if line.startswith("#"):
            level = len(re.match(r"^#+", line).group())
            content = line.lstrip("#").strip()
            return ElementType.HEADING, min(level, 6)

        # 参考文献
        if re.match(r"^\[[\d,\-–]+\]", line):
            return ElementType.REFERENCE, 0

        # 短行且无标点可能是标题
        if len(line) < 30 and not re.search(r"[，。！？；：、]", line):
            return ElementType.HEADING, 0

        return ElementType.PARAGRAPH, 0
