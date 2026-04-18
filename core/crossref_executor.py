"""
交叉引用执行器 (Cross-Reference Executor)

在导出 DOCX 时：
1. 为每个引用目标插入 Word 书签（Bookmark）
2. 将引用点文本替换为 REF 域代码（指向对应书签）
"""

from __future__ import annotations

from typing import Optional

from docx import Document
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

from core.crossref_models import (
    RefTarget, RefPoint, CrossRefReport, CrossRefMatch,
    RefTargetType, CrossRefStatus,
)


class CrossRefExecutor:
    """交叉引用执行器 — 在 Word 文档中插入书签和 REF 域"""

    def __init__(self):
        self.bookmark_id_counter = 0

    def execute(self, word_doc: Document, report: CrossRefReport,
                doc_model=None) -> None:
        """
        在 Word 文档中执行交叉引用。

        Args:
            word_doc: python-docx Document 对象
            report: 交叉引用检查报告
            doc_model: 原始文档模型（用于定位元素）
        """
        if not report.targets and not report.ref_points:
            return

        # 构建 element_index → paragraph 映射
        para_map = self._build_para_map(word_doc, doc_model)

        # 第一步：为目标插入书签
        self._insert_bookmarks(word_doc, report.targets, para_map)

        # 第二步：为有效引用点插入 REF 域
        self._insert_ref_fields(word_doc, report, para_map)

    def _build_para_map(self, word_doc: Document, doc_model=None) -> dict[int, any]:
        """构建元素索引到 Word 段落的映射"""
        para_map: dict[int, any] = {}
        if doc_model is None:
            return para_map

        para_idx = 0
        for elem in doc_model.elements:
            from core.document_model import ElementType
            if elem.element_type in (ElementType.HEADING, ElementType.PARAGRAPH,
                                      ElementType.CAPTION, ElementType.REFERENCE):
                if para_idx < len(word_doc.paragraphs):
                    para_map[elem.metadata.get("_original_index", para_idx)] = \
                        word_doc.paragraphs[para_idx]
                    para_idx += 1

        return para_map

    def _insert_bookmarks(self, word_doc: Document,
                          targets: list[RefTarget],
                          para_map: dict[int, any]) -> None:
        """为引用目标插入 Word 书签"""
        for target in targets:
            if not target.bookmark_name:
                continue

            para = para_map.get(target.element_index)
            if para is None:
                continue

            self._add_bookmark_to_paragraph(para, target.bookmark_name)

    def _insert_ref_fields(self, word_doc: Document,
                           report: CrossRefReport,
                           para_map: dict[int, any]) -> None:
        """为有效引用点插入 REF 域代码"""
        for match in report.matches:
            if match.status != CrossRefStatus.VALID:
                continue

            rp = match.ref_point
            target = match.target

            if not target.bookmark_name:
                continue

            para = para_map.get(rp.element_index)
            if para is None:
                continue

            # 在段落中查找引用文本并替换为 REF 域
            self._replace_ref_with_field(para, rp.ref_text, target.bookmark_name)

    @staticmethod
    def _add_bookmark_to_paragraph(para, bookmark_name: str) -> None:
        """在段落中添加书签"""
        if not para.runs:
            return

        p_elem = para._element
        first_run = para.runs[0]._element
        last_run = para.runs[-1]._element

        # bookmarkStart
        bm_start = parse_xml(
            f'<w:bookmarkStart {nsdecls("w")} w:id="0" w:name="{bookmark_name}"/>'
        )
        first_run.addprevious(bm_start)

        # bookmarkEnd
        bm_end = parse_xml(
            f'<w:bookmarkEnd {nsdecls("w")} w:id="0"/>'
        )
        last_run.addnext(bm_end)

    @staticmethod
    def _replace_ref_with_field(para, ref_text: str, bookmark_name: str) -> None:
        """将段落中的引用文本替换为 REF 域代码"""
        if not para.runs:
            return

        # 在所有 run 的文本中查找引用文本
        full_text = "".join(run.text for run in para.runs)
        pos = full_text.find(ref_text)
        if pos < 0:
            return

        # 简化实现：在引用文本位置插入 REF 域
        # 找到包含引用文本起始位置的 run
        char_count = 0
        target_run = None
        run_offset = 0

        for run in para.runs:
            if char_count + len(run.text) > pos:
                target_run = run
                run_offset = pos - char_count
                break
            char_count += len(run.text)

        if target_run is None:
            return

        # 在目标 run 前插入 REF 域
        r_elem = target_run._element

        # REF 域代码：REF 书签名
        fld_begin = parse_xml(
            f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>'
        )
        instr_text = parse_xml(
            f'<w:instrText {nsdecls("w")} xml:space="preserve"> REF {bookmark_name} \\h </w:instrText>'
        )
        fld_end = parse_xml(
            f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>'
        )

        # 创建一个包含 REF 域的新 run
        ref_run = parse_xml(f'<w:r {nsdecls("w")}></w:r>')
        ref_run.append(fld_begin)
        ref_run.append(instr_text)
        ref_run.append(fld_end)

        # 在目标 run 前插入
        r_elem.addprevious(ref_run)
