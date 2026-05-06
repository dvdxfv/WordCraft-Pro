"""
Regression tests for FormatRules and FormatChecker.
"""

from core.document_model import DocumentModel, DocElement, ElementType, FontStyle
from core.format_checker import FormatChecker, FormatRules
from core.qa_models import IssueSeverity, IssueCategory


def _make_rules(h1f="FONT_A", h1s=16.0, h2f="FONT_A", h2s=14.0, h3f="FONT_A", h3s=12.0,
                bf="FONT_BODY", bs=12.0) -> FormatRules:
    return FormatRules(h1Font=h1f, h1Size=h1s, h2Font=h2f, h2Size=h2s,
                       h3Font=h3f, h3Size=h3s, bFont=bf, bSize=bs)


def _make_doc(*elements: DocElement) -> DocumentModel:
    doc = DocumentModel(title="test", source_format="test")
    doc.elements = list(elements)
    return doc


def _heading(level: int, text: str, font_cn: str = "", size_pt: float = 0.0) -> DocElement:
    fs = FontStyle(font_name_cn=font_cn, font_size_pt=size_pt)
    return DocElement(element_type=ElementType.HEADING, content=text, level=level, font_style=fs)


def _para(text: str, font_cn: str = "", size_pt: float = 0.0, metadata: dict | None = None) -> DocElement:
    fs = FontStyle(font_name_cn=font_cn, font_size_pt=size_pt)
    return DocElement(element_type=ElementType.PARAGRAPH, content=text, font_style=fs, metadata=metadata or {})


class TestFormatRulesModel:
    def test_from_dict_basic(self):
        r = FormatRules.from_dict({"h1Font": "FONT_A", "h1Size": 16, "bFont": "FONT_BODY", "bSize": 12})
        assert r.h1Font == "FONT_A"
        assert r.h1Size == 16.0
        assert r.bFont == "FONT_BODY"
        assert r.bSize == 12.0

    def test_from_dict_handles_missing_keys(self):
        r = FormatRules.from_dict({})
        assert r.h1Font == ""
        assert r.h1Size == 0.0
        assert r.is_empty()

    def test_from_dict_converts_numeric_strings(self):
        r = FormatRules.from_dict({"h1Size": "16.0", "bSize": "12"})
        assert r.h1Size == 16.0
        assert r.bSize == 12.0


class TestFormatCheckerNoIssues:
    def test_empty_rules_returns_empty_report(self):
        report = FormatChecker(FormatRules()).check(_make_doc(_heading(1, "Title", "FONT_A", 16)))
        assert len(report.issues) == 0

    def test_matching_font_no_issue(self):
        report = FormatChecker(_make_rules()).check(_make_doc(_heading(1, "Title", "FONT_A", 16)))
        assert len(report.issues) == 0

    def test_no_font_info_skipped(self):
        report = FormatChecker(_make_rules()).check(_make_doc(_heading(1, "Title", "", 0.0)))
        assert len(report.issues) == 0


class TestFormatCheckerMismatch:
    def test_h1_font_mismatch_detected(self):
        report = FormatChecker(_make_rules()).check(_make_doc(_heading(1, "Chapter 1", "FONT_B", 16)))
        font_issue = next(i for i in report.issues if i.rule_id.startswith("format_font_"))
        assert font_issue.category == IssueCategory.FORMAT
        assert font_issue.severity == IssueSeverity.WARNING
        assert "FONT_A" in font_issue.description
        assert "FONT_B" in font_issue.description

    def test_h1_size_mismatch_detected(self):
        report = FormatChecker(_make_rules()).check(_make_doc(_heading(1, "Chapter 1", "FONT_A", 12)))
        size_issue = next(i for i in report.issues if i.rule_id.startswith("format_size_"))
        assert "16" in size_issue.description
        assert "12" in size_issue.description

    def test_size_within_tolerance_no_issue(self):
        report = FormatChecker(_make_rules()).check(_make_doc(_heading(1, "Chapter 1", "FONT_A", 16.3)))
        assert not any(i.rule_id.startswith("format_size_") for i in report.issues)

    def test_body_size_mismatch_detected(self):
        report = FormatChecker(_make_rules()).check(_make_doc(_para("Body", "FONT_BODY", 10.5)))
        assert any(i.rule_id.startswith("format_size_") for i in report.issues)

    def test_lists_all_font_mismatches(self):
        doc = _make_doc(
            _heading(1, "One", "FONT_B", 16),
            _heading(1, "Two", "FONT_B", 16),
            _heading(1, "Three", "FONT_B", 16),
        )
        report = FormatChecker(_make_rules()).check(doc)
        assert len([i for i in report.issues if i.rule_id.startswith("format_font_")]) == 3
        assert not any(i.rule_id == "format_font_summary" for i in report.issues)

    def test_lists_all_size_mismatches(self):
        doc = _make_doc(
            _heading(1, "One", "FONT_A", 12),
            _heading(1, "Two", "FONT_A", 12),
            _heading(1, "Three", "FONT_A", 12),
        )
        report = FormatChecker(_make_rules()).check(doc)
        assert len([i for i in report.issues if i.rule_id.startswith("format_size_")]) == 3

    def test_excluded_cover_element_skipped(self):
        doc = _make_doc(_para("Cover", "FONT_B", 14, metadata={"exclude_from_format_body": True}))
        report = FormatChecker(_make_rules()).check(doc)
        assert len(report.issues) == 0


class TestFormatCheckerIntegration:
    def test_mixed_heading_levels(self):
        doc = _make_doc(
            _heading(1, "Chapter 1", "FONT_A", 16),
            _heading(2, "1.1 Section", "FONT_B", 14),
            _para("Body", "FONT_BODY", 12),
        )
        report = FormatChecker(_make_rules()).check(doc)
        assert len(report.issues) == 1
        assert "二级标题" in report.issues[0].title

    def test_element_index_recorded(self):
        doc = _make_doc(_para("Preface", "FONT_BODY", 12), _heading(1, "Chapter 1", "FONT_B", 16))
        report = FormatChecker(_make_rules()).check(doc)
        font_issue = next(i for i in report.issues if i.rule_id.startswith("format_font_"))
        assert font_issue.element_index == 1

    def test_confidence_is_high(self):
        report = FormatChecker(_make_rules()).check(_make_doc(_heading(1, "Chapter 1", "FONT_B", 16)))
        for issue in report.issues:
            assert issue.confidence >= 0.8

    def test_pseudo_heading_uses_structure_metadata(self):
        doc = _make_doc(
            _para(
                "1.2 Pseudo Section",
                "FONT_B",
                14,
                metadata={"structure_role": "heading", "heading_level": 2},
            )
        )
        report = FormatChecker(_make_rules()).check(doc)
        assert len(report.issues) == 1
        assert "二级标题" in report.issues[0].title

    def test_deeper_pseudo_heading_reuses_h3_rules(self):
        doc = _make_doc(
            _para(
                "2.2.1 Deep Pseudo Section",
                "FONT_B",
                12,
                metadata={"structure_role": "heading", "heading_level": 4},
            )
        )
        report = FormatChecker(_make_rules(h3f="FONT_A", h3s=12.0)).check(doc)
        assert len(report.issues) == 1
        assert "三级标题" in report.issues[0].title


class TestQAEngineFormatRulesIntegration:
    def test_qa_engine_accepts_format_rules(self):
        from core.qa_engine import QAEngine
        report = QAEngine().check(_make_doc(_heading(1, "Chapter 1", "FONT_B", 12)), ["format"], format_rules=_make_rules())
        assert len([i for i in report.issues if i.checker == "FormatChecker"]) >= 1

    def test_qa_engine_no_format_rules_no_format_checker_issues(self):
        from core.qa_engine import QAEngine
        report = QAEngine().check(_make_doc(_heading(1, "Chapter 1", "FONT_B", 12)), ["format"], format_rules=None)
        assert len([i for i in report.issues if i.checker == "FormatChecker"]) == 0
