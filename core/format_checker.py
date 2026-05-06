"""
Format rules checker.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.document_model import DocumentModel, ElementType
from core.qa_models import QAIssue, IssueCategory, IssueSeverity, QAReport


@dataclass
class FormatRules:
    h1Font: str = ""
    h1Size: float = 0.0
    h2Font: str = ""
    h2Size: float = 0.0
    h3Font: str = ""
    h3Size: float = 0.0
    bFont: str = ""
    bSize: float = 0.0
    lineSpacing: float = 0.0
    savedAt: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "FormatRules":
        def _f(v) -> float:
            try:
                return float(v) if v else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            h1Font=d.get("h1Font") or "",
            h1Size=_f(d.get("h1Size")),
            h2Font=d.get("h2Font") or "",
            h2Size=_f(d.get("h2Size")),
            h3Font=d.get("h3Font") or "",
            h3Size=_f(d.get("h3Size")),
            bFont=d.get("bFont") or "",
            bSize=_f(d.get("bSize")),
            lineSpacing=_f(d.get("lineSpacing")),
            savedAt=d.get("savedAt") or "",
        )

    def is_empty(self) -> bool:
        return not any([
            self.h1Font, self.h1Size,
            self.h2Font, self.h2Size,
            self.h3Font, self.h3Size,
            self.bFont, self.bSize,
        ])


class FormatChecker:
    SIZE_TOL = 0.5

    def __init__(self, rules: FormatRules):
        self.rules = rules

    @staticmethod
    def _resolve_semantic_slot(elem) -> tuple[ElementType, int]:
        """Prefer structure metadata so pseudo-headings participate in title checks."""
        meta = elem.metadata if isinstance(elem.metadata, dict) else {}
        role = str(meta.get("structure_role") or "").strip().lower()
        heading_level = meta.get("heading_level")

        if role == "heading":
            try:
                lvl = int(heading_level)
            except (TypeError, ValueError):
                lvl = int(elem.level or 0)
            # The UI only exposes H1-H3 rules today; deeper headings reuse H3 checks.
            if lvl >= 3:
                lvl = 3
            if lvl > 0:
                return (ElementType.HEADING, lvl)

        if elem.element_type == ElementType.HEADING:
            lvl = int(elem.level or 0)
            if lvl >= 3:
                lvl = 3
            return (ElementType.HEADING, lvl)

        return (ElementType.PARAGRAPH, 0)

    def check(self, doc: DocumentModel) -> QAReport:
        report = QAReport()
        if self.rules.is_empty():
            return report

        type_rules: dict[tuple, tuple] = {
            (ElementType.HEADING, 1): (self.rules.h1Font, self.rules.h1Size, "一级标题"),
            (ElementType.HEADING, 2): (self.rules.h2Font, self.rules.h2Size, "二级标题"),
            (ElementType.HEADING, 3): (self.rules.h3Font, self.rules.h3Size, "三级标题"),
            (ElementType.PARAGRAPH, 0): (self.rules.bFont, self.rules.bSize, "正文段落"),
        }

        for idx, elem in enumerate(doc.elements):
            if isinstance(elem.metadata, dict) and elem.metadata.get("exclude_from_format_body"):
                continue

            key = self._resolve_semantic_slot(elem)
            if key not in type_rules:
                continue

            exp_font, exp_size, label = type_rules[key]
            loc = elem.content[:40].strip()
            if not loc:
                continue

            fs = elem.font_style
            actual_font = fs.font_name_cn or fs.font_name_en
            actual_size = fs.font_size_pt
            tk = f"{key[0].value}_{key[1]}"

            if actual_font and exp_font and actual_font != exp_font:
                report.add_issue(QAIssue(
                    category=IssueCategory.FORMAT,
                    severity=IssueSeverity.WARNING,
                    title=f"{label}字体不符规范",
                    description=f"规范要求 {exp_font}，实际为 {actual_font}",
                    suggestion=f'将"{loc}"的字体改为 {exp_font}',
                    location_text=loc,
                    element_index=idx,
                    rule_id=f"format_font_{tk}",
                    checker="FormatChecker",
                    confidence=0.9,
                ))

            if actual_size and exp_size and abs(actual_size - exp_size) > self.SIZE_TOL:
                report.add_issue(QAIssue(
                    category=IssueCategory.FORMAT,
                    severity=IssueSeverity.WARNING,
                    title=f"{label}字号不符规范",
                    description=f"规范要求 {exp_size}pt，实际为 {actual_size}pt",
                    suggestion=f'将"{loc}"的字号改为 {exp_size}pt',
                    location_text=loc,
                    element_index=idx,
                    rule_id=f"format_size_{tk}",
                    checker="FormatChecker",
                    confidence=0.9,
                ))

        return report
