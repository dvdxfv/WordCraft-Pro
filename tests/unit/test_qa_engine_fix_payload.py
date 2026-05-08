#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 回归：FormatChecker / TypoChecker 输出的 issue 携带 fix_payload / fix_type。"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.document_model import (
    DocElement, DocumentModel, ElementType, FontStyle, LineSpacingType, ParagraphStyle,
)
from core.format_checker import FormatChecker, FormatRules
from core.typo_checker import TypoChecker
from core.qa_models import IssueCategory


def _para(content: str, font_name_cn: str = "黑体", font_size_pt: float = 14.0,
          element_type: ElementType = ElementType.PARAGRAPH) -> DocElement:
    return DocElement(
        element_type=element_type,
        content=content,
        font_style=FontStyle(font_name_cn=font_name_cn, font_size_pt=font_size_pt),
    )


def _doc(*elements: DocElement) -> DocumentModel:
    doc = DocumentModel(title="test", source_format="docx")
    doc.elements = list(elements)
    return doc


def _rules(bFont="宋体", bSize=12.0) -> FormatRules:
    return FormatRules(bFont=bFont, bSize=bSize)


# ── 字号 ────────────────────────────────────────────────────────

class TestFontSizeFixPayload:
    def test_issue_carries_fix_payload(self):
        doc = _doc(_para("正文段落内容示例文字", font_size_pt=14.0))
        report = FormatChecker(_rules(bSize=12.0)).check(doc)
        size_issues = [i for i in report.issues if i.rule_id.startswith("format_size_")]
        assert size_issues, "应检测到字号问题"
        issue = size_issues[0]
        assert issue.fixable is True
        assert issue.fix_type == "format_attr"
        assert issue.fix_payload is not None
        assert issue.fix_payload["attr"] == "font_size"
        assert issue.fix_payload["value"] == pytest.approx(12.0)
        assert issue.fix_payload["scope"] == "paragraph"

    def test_fix_payload_has_para_fingerprint(self):
        content = "正文段落内容示例文字"
        doc = _doc(_para(content, font_size_pt=14.0))
        report = FormatChecker(_rules(bSize=12.0)).check(doc)
        issue = next(i for i in report.issues if i.rule_id.startswith("format_size_"))
        assert issue.fix_payload["para_fingerprint"] == content[:40].strip()

    def test_fix_payload_para_idx_matches_element_index(self):
        doc = _doc(
            _para("第一段落", font_size_pt=12.0),
            _para("第二段落字号不对", font_size_pt=14.0),
        )
        report = FormatChecker(_rules(bSize=12.0)).check(doc)
        size_issues = [i for i in report.issues if i.rule_id.startswith("format_size_")]
        assert size_issues
        issue = size_issues[0]
        assert issue.fix_payload["para_idx"] == issue.element_index

    def test_to_dict_includes_fix_fields(self):
        doc = _doc(_para("字号问题段落", font_size_pt=14.0))
        report = FormatChecker(_rules(bSize=12.0)).check(doc)
        issue = next(i for i in report.issues if i.rule_id.startswith("format_size_"))
        d = issue.to_dict()
        assert d["fixable"] is True
        assert d["fix_type"] == "format_attr"
        assert d["fix_payload"]["attr"] == "font_size"


# ── 字体 ────────────────────────────────────────────────────────

class TestFontNameFixPayload:
    def test_issue_carries_fix_payload(self):
        doc = _doc(_para("字体不对的段落", font_name_cn="黑体"))
        report = FormatChecker(_rules(bFont="宋体")).check(doc)
        font_issues = [i for i in report.issues if i.rule_id.startswith("format_font_")]
        assert font_issues, "应检测到字体问题"
        issue = font_issues[0]
        assert issue.fixable is True
        assert issue.fix_type == "format_attr"
        fp = issue.fix_payload
        assert fp["attr"] == "font_name"
        assert fp["value"] == "宋体"
        assert fp["scope"] == "paragraph"

    def test_fix_payload_value_is_target_not_actual(self):
        doc = _doc(_para("段落", font_name_cn="仿宋"))
        report = FormatChecker(_rules(bFont="宋体")).check(doc)
        issue = next(i for i in report.issues if i.rule_id.startswith("format_font_"))
        assert issue.fix_payload["value"] == "宋体"


# ── 行距 ────────────────────────────────────────────────────────

class TestLineSpacingFixPayload:
    def test_issue_carries_fix_payload(self):
        elem = _para("行距不对的段落")
        elem.paragraph_style = ParagraphStyle(
            line_spacing_type=LineSpacingType.MULTIPLE,
            line_spacing_value=1.5,
        )
        # is_empty() 检查 font/size，需要至少一个非空值才会执行行距检查
        rules = FormatRules(bFont="宋体", lineSpacingMode="multiple", lineSpacingValue=2.0)
        doc = _doc(elem)
        report = FormatChecker(rules).check(doc)
        ls_issues = [i for i in report.issues if i.rule_id == "format_line_spacing"]
        assert ls_issues, "应检测到行距问题"
        issue = ls_issues[0]
        assert issue.fixable is True
        assert issue.fix_type == "format_attr"
        fp = issue.fix_payload
        assert fp["attr"] == "line_spacing"
        assert fp["value"] == pytest.approx(2.0)
        assert fp["mode"] == "multiple"


# ── 错别字 ───────────────────────────────────────────────────────

class TestTypoFixType:
    def test_typo_issue_has_text_replace_fix_type(self):
        doc = _doc(_para("他门还发现CPUE较高的海域。"))
        report = TypoChecker().check(doc)
        typo_issues = [i for i in report.issues if i.rule_id == "typo.common_dict"]
        assert typo_issues, "应检测到错别字"
        for issue in typo_issues:
            assert issue.fix_type == "text_replace"
            assert issue.fixable is True

    def test_de_di_de_issue_has_text_replace_fix_type(self):
        # 句子直接以状语词开头，避免 finditer 从 pos 0 贪婪消耗匹配起点
        doc = _doc(_para("认真的做，总结工作。"))
        report = TypoChecker().check(doc)
        de_issues = [i for i in report.issues if i.rule_id == "typo.de_di_de"]
        assert de_issues, "应检测到的地得问题"
        assert de_issues[0].fix_type == "text_replace"
        assert de_issues[0].fixable is True

    def test_typo_fix_payload_is_none(self):
        doc = _doc(_para("他门还发现CPUE较高的海域。"))
        report = TypoChecker().check(doc)
        issue = next(i for i in report.issues if i.rule_id == "typo.common_dict")
        assert issue.fix_payload is None


# ── 无格式规则时不报告（兜底） ───────────────────────────────────

class TestNoRulesNoFixPayload:
    def test_empty_rules_produces_no_issues(self):
        doc = _doc(_para("任意内容", font_size_pt=14.0))
        report = FormatChecker(FormatRules()).check(doc)
        assert report.issues == []
