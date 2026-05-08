#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 回归：XRefCitationStyleChecker 行为验证。

当前覆盖 DocumentModel 纯文字层（检测手动 [n] 引用）。
DOCX XML 层（REF 域 / 上标 / 超链接）由更高层负责，本文件不覆盖。
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.document_model import DocElement, DocumentModel, ElementType
from core.xref_citation_checker import XRefCitationStyleChecker, _parse_citation_numbers


def _elem(content: str, etype: ElementType = ElementType.PARAGRAPH,
          level: int = 0) -> DocElement:
    e = DocElement(element_type=etype, content=content, level=level)
    return e


def _heading(content: str, level: int = 1) -> DocElement:
    return _elem(content, ElementType.HEADING, level)


def _doc(*elements: DocElement) -> DocumentModel:
    doc = DocumentModel(title="test", source_format="docx")
    doc.elements = list(elements)
    return doc


def _checker() -> XRefCitationStyleChecker:
    return XRefCitationStyleChecker()


# ── 基础：无参考文献节 ──────────────────────────────────────────

class TestNoReferenceSection:
    def test_returns_warning_not_crash(self):
        doc = _doc(
            _elem("本文对鱼类资源 [1] 进行了分析。"),
            _elem("结果如 [2] 所示。"),
        )
        report = _checker().check(doc)
        assert "xref_citation_warning" in report.metadata
        assert "参考文献" in report.metadata["xref_citation_warning"]

    def test_returns_empty_issues_when_no_ref_section(self):
        doc = _doc(
            _elem("本文对鱼类资源 [1] 进行了分析。"),
        )
        report = _checker().check(doc)
        assert report.issues == []


# ── 基础：检测手动 [n] 文字引用 ─────────────────────────────────

class TestPlainTextCitationDetected:
    def _base_doc(self, body_content: str) -> DocumentModel:
        return _doc(
            _elem(body_content),
            _heading("参考文献", level=1),
            _elem("[1] 张三. 研究报告. 2020."),
            _elem("[2] 李四. 分析报告. 2021."),
        )

    def test_single_citation_detected(self):
        doc = self._base_doc("本文参照 [1] 中的方法进行分析。")
        report = _checker().check(doc)
        issues = [i for i in report.issues if i.rule_id == "xref.plain_text_citation"]
        assert len(issues) == 1

    def test_multiple_citations_each_reported(self):
        doc = self._base_doc("如 [1] 和 [2] 所示，结果相符。")
        report = _checker().check(doc)
        issues = [i for i in report.issues if i.rule_id == "xref.plain_text_citation"]
        assert len(issues) == 2

    def test_citation_issue_category_is_reference(self):
        from core.qa_models import IssueCategory
        doc = self._base_doc("见 [1]。")
        report = _checker().check(doc)
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert issue.category == IssueCategory.REFERENCE

    def test_citation_text_in_location_text(self):
        doc = self._base_doc("研究结果参照 [1] 中的分析。")
        report = _checker().check(doc)
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert "[1]" in issue.location_text

    def test_fixable_when_ref_in_list(self):
        doc = self._base_doc("见 [1]。")
        report = _checker().check(doc)
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert issue.fixable is True
        assert issue.fix_type == "xref"
        assert issue.fix_payload is not None
        assert 1 in issue.fix_payload["ref_numbers"]

    def test_not_fixable_when_ref_number_missing_from_list(self):
        doc = _doc(
            _elem("见 [99]。"),
            _heading("参考文献", level=1),
            _elem("[1] 张三. 研究报告. 2020."),
        )
        report = _checker().check(doc)
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert issue.fixable is False
        assert issue.fix_type is None


# ── 不扫描参考文献节之后 ─────────────────────────────────────────

class TestBodyOnlyScope:
    def test_citations_in_ref_section_not_reported(self):
        doc = _doc(
            _elem("正文见 [1]。"),
            _heading("参考文献", level=1),
            _elem("[1] 张三. 研究，引用 [2]。"),  # 参考文献条目内的 [n] 不应报告
        )
        report = _checker().check(doc)
        issues = [i for i in report.issues if i.rule_id == "xref.plain_text_citation"]
        # 只有正文中的 [1] 应被报告，参考文献条目内的 [2] 不应被报告
        assert len(issues) == 1
        assert issues[0].element_index == 0


# ── 页眉/页脚不扫描 ─────────────────────────────────────────────

class TestHeaderFooterIgnored:
    def test_header_citation_not_reported(self):
        doc = _doc(
            _elem("[1] 页眉中的引用", ElementType.HEADER),
            _elem("正文内容无引用。"),
            _heading("参考文献", level=1),
            _elem("[1] 张三. 研究报告."),
        )
        report = _checker().check(doc)
        issues = [i for i in report.issues if i.rule_id == "xref.plain_text_citation"]
        assert issues == []

    def test_footer_citation_not_reported(self):
        doc = _doc(
            _elem("[2] 页脚注释", ElementType.FOOTER),
            _elem("正文内容无引用。"),
            _heading("参考文献", level=1),
            _elem("[2] 李四. 分析."),
        )
        report = _checker().check(doc)
        issues = [i for i in report.issues if i.rule_id == "xref.plain_text_citation"]
        assert issues == []


# ── 参考文献编号从实际列表提取（不假设顺序连续）───────────────────

class TestCitationNumberMappedFromActualList:
    def test_non_sequential_ref_list_mapped_correctly(self):
        doc = _doc(
            _elem("见 [2] 和 [4]。"),
            _heading("参考文献", level=1),
            _elem("[2] 张三. 报告甲."),
            _elem("[4] 李四. 报告乙."),
        )
        report = _checker().check(doc)
        issues = [i for i in report.issues if i.rule_id == "xref.plain_text_citation"]
        for issue in issues:
            assert issue.fixable is True  # [2] 和 [4] 都在列表中

    def test_missing_ref_number_not_fixable(self):
        doc = _doc(
            _elem("见 [3]。"),   # [3] 不在列表
            _heading("参考文献", level=1),
            _elem("[2] 张三."),
            _elem("[4] 李四."),
        )
        report = _checker().check(doc)
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert issue.fixable is False

    def test_fix_payload_contains_ref_element_indices(self):
        doc = _doc(
            _elem("见 [1]。"),
            _heading("参考文献", level=1),
            _elem("[1] 张三. 报告."),
        )
        report = _checker().check(doc)
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert issue.fix_payload is not None
        assert len(issue.fix_payload["ref_element_indices"]) >= 1


# ── fix_payload 结构校验 ─────────────────────────────────────────

class TestFixPayloadStructure:
    def _simple_doc(self) -> DocumentModel:
        return _doc(
            _elem("研究 [1] 表明结论有效。"),
            _heading("参考文献", level=1),
            _elem("[1] 张三. 研究报告. 2020."),
        )

    def test_fix_payload_has_para_idx(self):
        report = _checker().check(self._simple_doc())
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert "para_idx" in issue.fix_payload

    def test_fix_payload_has_para_fingerprint(self):
        report = _checker().check(self._simple_doc())
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert "para_fingerprint" in issue.fix_payload
        assert len(issue.fix_payload["para_fingerprint"]) > 0

    def test_fix_payload_para_idx_matches_element_index(self):
        report = _checker().check(self._simple_doc())
        issue = next(i for i in report.issues if i.rule_id == "xref.plain_text_citation")
        assert issue.fix_payload["para_idx"] == issue.element_index


# ── 辅助函数 ────────────────────────────────────────────────────

class TestParseCitationNumbers:
    def test_single_number(self):
        assert _parse_citation_numbers("3") == [3]

    def test_comma_separated(self):
        assert _parse_citation_numbers("1,2,3") == [1, 2, 3]

    def test_chinese_comma_separated(self):
        assert _parse_citation_numbers("1，2") == [1, 2]

    def test_range_with_dash(self):
        result = _parse_citation_numbers("1-3")
        assert result == [1, 2, 3]

    def test_range_with_en_dash(self):
        result = _parse_citation_numbers("2–4")
        assert result == [2, 3, 4]

    def test_mixed(self):
        result = _parse_citation_numbers("1,3-5")
        assert set(result) == {1, 3, 4, 5}
