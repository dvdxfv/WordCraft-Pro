"""
第十八批：文档结构识别层单测

覆盖 ``core/document_structure.py`` 的双入口与启发式边界。所有用例均不依赖
真实 .docx 文件，使用最小 dict / DocElement 构造测试输入。
"""

from __future__ import annotations

import pytest

from core.document_structure import (
    DEFAULT_FORMAT_THRESHOLD,
    DEFAULT_XREF_THRESHOLD,
    classify_dicts,
    classify_elements,
)
from core.document_model import (
    DocElement,
    ElementType,
    FontStyle,
    ParagraphStyle,
    Alignment,
)


# ============================================================
# 辅助构造
# ============================================================


def _mk_dict(
    text: str,
    *,
    type_="p",
    style="Normal",
    size_pt: float | None = 11.0,
    align: str | None = None,
    first_indent_twips: int = 0,
    bold: bool = False,
    section_break: str | None = None,
) -> dict:
    """构造 app.py._parse_docx 形态的 dict，含 fmt + runs。"""
    runs = []
    if size_pt is not None:
        runs.append({
            "text": text,
            "font_size_pt": size_pt,
            "bold": bold,
            "font_eastAsia": "宋体",
        })
    return {
        "type": type_,
        "text": text,
        "fmt": {
            "style": style,
            "alignment": align,
            "first_line_indent_twips": first_indent_twips,
        },
        "runs": runs,
        "section_break": section_break,
    }


def _mk_doc_elem(
    text: str,
    *,
    et=ElementType.PARAGRAPH,
    level: int = 0,
    style="Normal",
    size_pt: float = 11.0,
    align: Alignment | None = None,
    first_indent_cm: float = 0.0,
    bold: bool = False,
) -> DocElement:
    fs = FontStyle(font_size_pt=size_pt, bold=bold)
    ps = ParagraphStyle(
        alignment=align if align is not None else Alignment.JUSTIFY,
        first_indent_cm=first_indent_cm,
    )
    return DocElement(
        element_type=et,
        content=text,
        level=level,
        font_style=fs,
        paragraph_style=ps,
        style_name=style,
    )


# ============================================================
# 边界与防御
# ============================================================


class TestEmptyAndDefensive:
    def test_classify_dicts_empty(self):
        assert classify_dicts([]) == []

    def test_classify_elements_empty(self):
        assert classify_elements([]) == []

    def test_zero_size_paragraph_does_not_crash(self):
        elems = [_mk_dict("正文段落", size_pt=None)]
        out = classify_dicts(elems)
        # 字号缺失：分类器不抛异常，仍写入 metadata
        assert "structure_role" in out[0]["metadata"]
        assert 0.0 <= out[0]["metadata"]["structure_confidence"] <= 1.0

    def test_metadata_preserves_existing_fields(self):
        elems = [_mk_dict("段落")]
        elems[0]["metadata"] = {"existing": "keep"}
        classify_dicts(elems)
        assert elems[0]["metadata"]["existing"] == "keep"
        assert elems[0]["metadata"]["structure_role"] in ("body", "heading")


# ============================================================
# TOC 识别
# ============================================================


class TestTOC:
    def test_toc_by_style_name(self):
        # Word 自带 "TOC 1" 样式：必须识别为 toc 而不是 heading
        elems = [_mk_dict("第一章 引言", style="toc 1", align="LEFT")]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "toc"
        assert out[0]["metadata"]["exclude_from_format_body"] is True
        assert out[0]["metadata"]["exclude_from_xref_targets"] is True

    def test_toc_by_dotted_leader(self):
        # "第3章 模型 ......15" 的点导符是强信号
        elems = [_mk_dict("第3章 模型与方法 ......15")]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "toc"

    def test_toc_with_chinese_dots(self):
        elems = [_mk_dict("1.1 研究背景 ……… 8")]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "toc"

    def test_toc_heading_recognized_as_heading(self):
        # "目录" 标题本身不是 toc，是 heading（不进 TargetScanner 的章节列表，但也不被排除格式检查）
        elems = [_mk_dict("目录", type_="h1", size_pt=14, bold=True)]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "heading"


# ============================================================
# 封面识别
# ============================================================


class TestCover:
    def test_cover_first_page_centered_large(self):
        elems = [
            _mk_dict("研究报告标题", size_pt=20.0, align="CENTER", first_indent_twips=0),
            _mk_dict("作者：张三", size_pt=14.0, align="CENTER"),
            _mk_dict("2026 年 4 月", size_pt=12.0, align="CENTER"),
            _mk_dict("", section_break="nextPage"),  # 封面分节
            _mk_dict("正文段落开始" * 10, size_pt=11.0, align="JUSTIFY", first_indent_twips=420),
            _mk_dict("继续正文" * 10, size_pt=11.0, align="JUSTIFY", first_indent_twips=420),
        ]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "cover"
        assert out[1]["metadata"]["structure_role"] == "cover"
        # 正文应该不是 cover
        assert out[4]["metadata"]["structure_role"] != "cover"
        assert out[5]["metadata"]["structure_role"] != "cover"

    def test_no_cover_in_short_doc_without_centered(self):
        # 普通报告：无居中大字号 → 不应误判封面
        elems = [
            _mk_dict("引言部分内容" * 5, size_pt=11.0, align="JUSTIFY", first_indent_twips=420),
            _mk_dict("继续正文" * 5, size_pt=11.0, align="JUSTIFY"),
        ]
        out = classify_dicts(elems)
        for o in out:
            assert o["metadata"]["structure_role"] != "cover"


# ============================================================
# 标题识别（无 Word 样式时靠编号 + 字号）
# ============================================================


class TestHeadingByContent:
    def test_chapter_pattern_with_large_size(self):
        # "第1章 引言" 即使 style=Normal，字号大于正文也识别为 heading
        elems = [
            _mk_dict("正文" * 10, size_pt=11.0),
            _mk_dict("第1章 引言", size_pt=16.0, style="Normal", bold=True),
            _mk_dict("正文" * 10, size_pt=11.0),
        ]
        out = classify_dicts(elems)
        assert out[1]["metadata"]["structure_role"] == "heading"

    def test_subsection_numbered(self):
        elems = [
            _mk_dict("正文" * 10, size_pt=11.0),
            _mk_dict("1.1 研究背景", size_pt=14.0, style="Normal", bold=True),
            _mk_dict("正文" * 10, size_pt=11.0),
        ]
        out = classify_dicts(elems)
        assert out[1]["metadata"]["structure_role"] == "heading"

    def test_chinese_numbered_heading(self):
        elems = [
            _mk_dict("正文" * 10, size_pt=11.0),
            _mk_dict("一、研究方法", size_pt=14.0, style="Normal", bold=True),
            _mk_dict("正文" * 10, size_pt=11.0),
        ]
        out = classify_dicts(elems)
        assert out[1]["metadata"]["structure_role"] == "heading"

    def test_section_name_recognized(self):
        elems = [
            _mk_dict("正文" * 10, size_pt=11.0),
            _mk_dict("摘要", size_pt=14.0, style="Normal", bold=True),
            _mk_dict("正文" * 10, size_pt=11.0),
        ]
        out = classify_dicts(elems)
        assert out[1]["metadata"]["structure_role"] == "heading"

    def test_word_heading_keeps_heading(self):
        # 已经带 Word Heading 样式的元素 → role=heading
        elems = [_mk_dict("章节", type_="h1", size_pt=16.0, style="heading 1")]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "heading"

    def test_heading_level_for_numbered_plain_paragraphs(self):
        elems = [
            _mk_dict("1.关键环境因子及其对南海鸢乌贼分布的影响", size_pt=14.0, style="Normal", bold=True),
            _mk_dict("1.2海面高度异常（SSHA）和混合层深度（MLD）", size_pt=12.0, style="Normal", bold=True),
            _mk_dict("2.2.1广义相加模型（GAMs）", size_pt=12.0, style="Normal", bold=True),
        ]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "heading"
        assert out[0]["metadata"]["heading_level"] == 2
        assert out[0]["metadata"]["section_kind"] == "heading_2"
        assert out[1]["metadata"]["heading_level"] == 3
        assert out[1]["metadata"]["section_kind"] == "heading_3"
        assert out[2]["metadata"]["heading_level"] == 4
        assert out[2]["metadata"]["section_kind"] == "heading_4"

    def test_named_headings_have_section_kind(self):
        elems = [
            _mk_dict("摘要", type_="h1", size_pt=16.0, style="heading 1"),
            _mk_dict("Abstract", size_pt=14.0, style="Normal", bold=True),
            _mk_dict("目录", type_="h1", size_pt=16.0, style="heading 1"),
            _mk_dict("参考文献", type_="h1", size_pt=16.0, style="heading 1"),
        ]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["section_kind"] == "abstract_heading_zh"
        assert out[0]["metadata"]["heading_level"] == 1
        assert out[1]["metadata"]["section_kind"] == "abstract_heading_en"
        assert out[1]["metadata"]["heading_level"] == 1
        assert out[2]["metadata"]["section_kind"] == "toc_heading"
        assert out[2]["metadata"]["heading_level"] == 1
        assert out[3]["metadata"]["section_kind"] == "references_heading"
        assert out[3]["metadata"]["heading_level"] == 1


# ============================================================
# 参考文献 / 题注
# ============================================================


class TestReferenceAndCaption:
    def test_reference_item_pattern(self):
        elems = [_mk_dict("[1] 张三. 文章名. 期刊, 2025.", type_="p")]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "reference"

    def test_caption_pattern(self):
        elems = [_mk_dict("图1 系统架构示意图")]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["structure_role"] == "caption"

    def test_reference_section_propagates(self):
        # "参考文献" 标题之后的段落都视作 reference
        elems = [
            _mk_dict("正文" * 10, size_pt=11.0),
            _mk_dict("参考文献", type_="h1", size_pt=16.0, bold=True, style="heading 1"),
            _mk_dict("张三. 论文标题. 期刊, 2025.", size_pt=11.0),
            _mk_dict("李四. 著作名. 出版社, 2024.", size_pt=11.0),
        ]
        out = classify_dicts(elems)
        assert out[1]["metadata"]["structure_role"] == "heading"
        assert out[2]["metadata"]["structure_role"] == "reference"
        assert out[3]["metadata"]["structure_role"] == "reference"
        assert out[2]["metadata"]["section_kind"] == "reference_item"
        assert out[3]["metadata"]["section_kind"] == "reference_item"

    def test_reference_section_does_not_swallow_appendix(self):
        # 参考文献后跟"附录" → 退出 ref_section
        elems = [
            _mk_dict("参考文献", type_="h1", size_pt=16.0, bold=True, style="heading 1"),
            _mk_dict("张三. 论文. 期刊, 2025.", size_pt=11.0),
            _mk_dict("附录", type_="h1", size_pt=16.0, bold=True, style="heading 1"),
            _mk_dict("附录正文" * 10, size_pt=11.0),
        ]
        out = classify_dicts(elems)
        assert out[1]["metadata"]["structure_role"] == "reference"
        # 附录段落不应被当成参考文献条目
        assert out[3]["metadata"]["structure_role"] != "reference"

    def test_keywords_line_gets_keywords_section_kind(self):
        elems = [_mk_dict("关键词：南海鸢乌贼；捕捞量反演；遥感")]
        out = classify_dicts(elems)
        assert out[0]["metadata"]["section_kind"] == "keywords"


# ============================================================
# 排除标志位
# ============================================================


class TestExcludeFlags:
    def test_high_confidence_cover_excludes_format_and_xref(self):
        elems = [
            _mk_dict("研究报告", size_pt=22.0, align="CENTER"),
            _mk_dict("正文" * 10, size_pt=11.0, align="JUSTIFY", first_indent_twips=420),
            _mk_dict("正文" * 10, size_pt=11.0, align="JUSTIFY"),
        ]
        out = classify_dicts(elems)
        cover = out[0]["metadata"]
        assert cover["structure_role"] == "cover"
        assert cover["exclude_from_format_body"] is True
        assert cover["exclude_from_xref_targets"] is True

    def test_body_does_not_exclude(self):
        elems = [_mk_dict("正文段落" * 10, size_pt=11.0)]
        out = classify_dicts(elems)
        meta = out[0]["metadata"]
        assert meta["exclude_from_format_body"] is False
        assert meta["exclude_from_xref_targets"] is False

    def test_caption_excludes_format_only(self):
        elems = [_mk_dict("图1 示意图")]
        out = classify_dicts(elems)
        meta = out[0]["metadata"]
        assert meta["structure_role"] == "caption"
        assert meta["exclude_from_format_body"] is True
        # 题注不属于 cover/toc，所以不影响 XRef target
        assert meta["exclude_from_xref_targets"] is False


# ============================================================
# 双入口 parity（dict 与 DocElement 走同一启发式）
# ============================================================


class TestDualEntryParity:
    def test_dict_and_doc_element_agree_on_toc_style(self):
        # 同一段 TOC 样式段落，dict 与 DocElement 都应判为 toc
        d = _mk_dict("第一章 引言", style="toc 1")
        out_d = classify_dicts([d])

        e = _mk_doc_elem("第一章 引言", style="toc 1", et=ElementType.PARAGRAPH)
        out_e = classify_elements([e])

        assert out_d[0]["metadata"]["structure_role"] == out_e[0].metadata["structure_role"] == "toc"

    def test_dict_and_doc_element_agree_on_reference_item(self):
        d = _mk_dict("[1] 张三. 文章. 期刊, 2025.")
        e = _mk_doc_elem("[1] 张三. 文章. 期刊, 2025.")
        out_d = classify_dicts([d])
        out_e = classify_elements([e])
        assert out_d[0]["metadata"]["structure_role"] == out_e[0].metadata["structure_role"] == "reference"

    def test_dict_and_doc_element_agree_on_body(self):
        d = _mk_dict("普通正文段落内容很长" * 5, size_pt=11.0)
        e = _mk_doc_elem("普通正文段落内容很长" * 5, size_pt=11.0)
        out_d = classify_dicts([d])
        out_e = classify_elements([e])
        assert out_d[0]["metadata"]["structure_role"] == out_e[0].metadata["structure_role"] == "body"


# ============================================================
# 阈值常量
# ============================================================


def test_threshold_constants():
    assert DEFAULT_FORMAT_THRESHOLD == 0.6
    assert DEFAULT_XREF_THRESHOLD == 0.7
    assert DEFAULT_FORMAT_THRESHOLD < DEFAULT_XREF_THRESHOLD
