"""
tests/test_format_checker.py
单元测试：FormatRules 模型 + FormatChecker 规范检查逻辑
"""

import pytest
from core.document_model import DocumentModel, DocElement, ElementType, FontStyle
from core.format_checker import FormatChecker, FormatRules
from core.qa_models import IssueSeverity, IssueCategory


def _make_rules(h1f="黑体", h1s=16.0, h2f="黑体", h2s=14.0, h3f="黑体", h3s=12.0,
                bf="宋体", bs=12.0) -> FormatRules:
    return FormatRules(h1Font=h1f, h1Size=h1s, h2Font=h2f, h2Size=h2s,
                       h3Font=h3f, h3Size=h3s, bFont=bf, bSize=bs)


def _make_doc(*elements: DocElement) -> DocumentModel:
    doc = DocumentModel(title="test", source_format="test")
    doc.elements = list(elements)
    return doc


def _heading(level: int, text: str, font_cn: str = "", size_pt: float = 0.0) -> DocElement:
    fs = FontStyle(font_name_cn=font_cn, font_size_pt=size_pt)
    return DocElement(element_type=ElementType.HEADING, content=text, level=level, font_style=fs)


def _para(text: str, font_cn: str = "", size_pt: float = 0.0) -> DocElement:
    fs = FontStyle(font_name_cn=font_cn, font_size_pt=size_pt)
    return DocElement(element_type=ElementType.PARAGRAPH, content=text, font_style=fs)


class TestFormatRulesModel:
    def test_from_dict_basic(self):
        d = {"h1Font": "黑体", "h1Size": 16, "bFont": "宋体", "bSize": 12}
        r = FormatRules.from_dict(d)
        assert r.h1Font == "黑体"
        assert r.h1Size == 16.0
        assert r.bFont == "宋体"
        assert r.bSize == 12.0

    def test_from_dict_handles_missing_keys(self):
        r = FormatRules.from_dict({})
        assert r.h1Font == ""
        assert r.h1Size == 0.0
        assert r.is_empty()  # all zeros → empty

    def test_is_empty_all_zero(self):
        r = FormatRules()
        assert r.is_empty()

    def test_is_empty_with_font(self):
        r = FormatRules(h1Font="黑体")
        assert not r.is_empty()

    def test_from_dict_converts_numeric_strings(self):
        r = FormatRules.from_dict({"h1Size": "16.0", "bSize": "12"})
        assert r.h1Size == 16.0
        assert r.bSize == 12.0

    def test_from_dict_ignores_none_values(self):
        r = FormatRules.from_dict({"h1Font": None, "h1Size": None})
        assert r.h1Font == ""
        assert r.h1Size == 0.0


class TestFormatCheckerNoIssues:
    def test_empty_rules_returns_empty_report(self):
        rules = FormatRules()
        doc = _make_doc(_heading(1, "标题", "黑体", 16))
        report = FormatChecker(rules).check(doc)
        assert len(report.issues) == 0

    def test_matching_font_no_issue(self):
        rules = _make_rules(h1f="黑体", h1s=16)
        doc = _make_doc(_heading(1, "第一章", "黑体", 16))
        report = FormatChecker(rules).check(doc)
        assert len(report.issues) == 0

    def test_no_font_info_skipped(self):
        # 从 HTML 解析的元素 font_size_pt == 0，应静默跳过
        rules = _make_rules(h1f="黑体", h1s=16)
        doc = _make_doc(_heading(1, "第一章", font_cn="", size_pt=0.0))
        report = FormatChecker(rules).check(doc)
        assert len(report.issues) == 0


class TestFormatCheckerFontMismatch:
    def test_h1_font_mismatch_detected(self):
        rules = _make_rules(h1f="黑体", h1s=16)
        doc = _make_doc(_heading(1, "第一章 绪论", "宋体", 16))
        report = FormatChecker(rules).check(doc)
        font_issues = [i for i in report.issues if "字体" in i.title]
        assert len(font_issues) >= 1
        assert font_issues[0].category == IssueCategory.FORMAT
        assert font_issues[0].severity == IssueSeverity.WARNING
        assert "黑体" in font_issues[0].description
        assert "宋体" in font_issues[0].description

    def test_h2_font_mismatch_detected(self):
        rules = _make_rules(h2f="黑体")
        doc = _make_doc(_heading(2, "1.1 研究背景", "楷体", 14))
        report = FormatChecker(rules).check(doc)
        assert any("二级标题" in i.title for i in report.issues)

    def test_body_font_mismatch_detected(self):
        rules = _make_rules(bf="宋体")
        doc = _make_doc(_para("这是正文内容。", "黑体", 12))
        report = FormatChecker(rules).check(doc)
        assert any("正文" in i.title for i in report.issues)

    def test_font_rule_id_format(self):
        rules = _make_rules(h1f="黑体")
        doc = _make_doc(_heading(1, "标题", "宋体", 16))
        report = FormatChecker(rules).check(doc)
        font_issue = next(i for i in report.issues if "字体" in i.title)
        assert font_issue.rule_id.startswith("format_font_")
        assert font_issue.checker == "FormatChecker"


class TestFormatCheckerSizeMismatch:
    def test_h1_size_mismatch_detected(self):
        rules = _make_rules(h1f="黑体", h1s=16)
        doc = _make_doc(_heading(1, "第一章", "黑体", 12))  # 12 != 16
        report = FormatChecker(rules).check(doc)
        size_issues = [i for i in report.issues if "字号" in i.title]
        assert len(size_issues) >= 1
        assert "16" in size_issues[0].description
        assert "12" in size_issues[0].description

    def test_size_within_tolerance_no_issue(self):
        rules = _make_rules(h1s=16)
        doc = _make_doc(_heading(1, "标题", "黑体", 16.3))  # 0.3 < 0.5 tolerance
        report = FormatChecker(rules).check(doc)
        size_issues = [i for i in report.issues if "字号" in i.title]
        assert len(size_issues) == 0

    def test_body_size_mismatch_detected(self):
        rules = _make_rules(bs=12)
        doc = _make_doc(_para("正文内容。", "宋体", 10.5))
        report = FormatChecker(rules).check(doc)
        assert any("字号" in i.title for i in report.issues)


class TestFormatCheckerRateLimiting:
    def test_max_per_type_font(self):
        # 超过 MAX_PER_TYPE(2) 条同类问题，应限制为 2 + 1条汇总
        rules = _make_rules(h1f="黑体")
        doc = _make_doc(
            _heading(1, "第一章", "宋体", 16),
            _heading(1, "第二章", "宋体", 16),
            _heading(1, "第三章", "宋体", 16),
        )
        report = FormatChecker(rules).check(doc)
        detail = [i for i in report.issues if "字体不符" in i.title]
        summary = [i for i in report.issues if "大范围差异" in i.title]
        assert len(detail) == 2
        assert len(summary) == 1

    def test_max_per_type_size(self):
        rules = _make_rules(h1s=16)
        doc = _make_doc(
            _heading(1, "第一章", "黑体", 12),
            _heading(1, "第二章", "黑体", 12),
            _heading(1, "第三章", "黑体", 12),
        )
        report = FormatChecker(rules).check(doc)
        size_issues = [i for i in report.issues if "字号不符" in i.title]
        assert len(size_issues) == 2


class TestFormatCheckerIntegration:
    def test_mixed_heading_levels(self):
        rules = _make_rules(h1f="黑体", h1s=16, h2f="黑体", h2s=14, bf="宋体", bs=12)
        doc = _make_doc(
            _heading(1, "第一章", "黑体", 16),   # 合规
            _heading(2, "1.1 背景", "宋体", 14),  # 字体不合规
            _para("正文内容。", "宋体", 12),       # 合规
        )
        report = FormatChecker(rules).check(doc)
        issues = report.issues
        assert len(issues) == 1
        assert "二级标题" in issues[0].title

    def test_element_index_recorded(self):
        rules = _make_rules(h1f="黑体")
        doc = _make_doc(
            _para("普通段落", "宋体", 12),
            _heading(1, "第一章", "宋体", 16),   # idx=1
        )
        report = FormatChecker(rules).check(doc)
        font_issue = next(i for i in report.issues if "字体" in i.title)
        assert font_issue.element_index == 1

    def test_confidence_is_high(self):
        rules = _make_rules(h1f="黑体")
        doc = _make_doc(_heading(1, "第一章", "宋体", 16))
        report = FormatChecker(rules).check(doc)
        for issue in report.issues:
            if issue.rule_id != "format_font_summary":
                assert issue.confidence >= 0.8


class TestQAEngineFormatRulesIntegration:
    def test_qa_engine_accepts_format_rules(self):
        from core.qa_engine import QAEngine
        rules = _make_rules(h1f="黑体", h1s=16)
        doc = _make_doc(_heading(1, "第一章", "宋体", 12))
        engine = QAEngine()
        report = engine.check(doc, ["format"], format_rules=rules)
        # FormatChecker should fire
        format_issues = [i for i in report.issues if i.checker == "FormatChecker"]
        assert len(format_issues) >= 1

    def test_qa_engine_no_format_rules_no_format_checker_issues(self):
        from core.qa_engine import QAEngine
        doc = _make_doc(_heading(1, "第一章", "宋体", 12))
        engine = QAEngine()
        report = engine.check(doc, ["format"], format_rules=None)
        format_checker_issues = [i for i in report.issues if i.checker == "FormatChecker"]
        assert len(format_checker_issues) == 0
