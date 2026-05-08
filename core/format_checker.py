"""
Format rules checker.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.document_model import DocumentModel, ElementType, LineSpacingType
from core.qa_models import QAIssue, IssueCategory, IssueSeverity, QAReport


@dataclass
class FormatRules:
    h1Font: str = ""
    h1Size: float = 0.0
    h2Font: str = ""
    h2Size: float = 0.0
    h3Font: str = ""
    h3Size: float = 0.0
    h4Font: str = ""
    h4Size: float = 0.0
    bFont: str = ""
    bSize: float = 0.0
    lineSpacing: float = 0.0
    lineSpacingMode: str = ""
    lineSpacingValue: float = 0.0
    h1NumFormat: str = ""
    h2NumFormat: str = ""
    h3NumFormat: str = ""
    h4NumFormat: str = ""
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
            h4Font=d.get("h4Font") or "",
            h4Size=_f(d.get("h4Size")),
            bFont=d.get("bFont") or "",
            bSize=_f(d.get("bSize")),
            lineSpacing=_f(d.get("lineSpacing")),
            lineSpacingMode=d.get("lineSpacingMode") or "",
            lineSpacingValue=_f(d.get("lineSpacingValue") or d.get("lineSpacing")),
            h1NumFormat=d.get("h1NumFormat") or "",
            h2NumFormat=d.get("h2NumFormat") or "",
            h3NumFormat=d.get("h3NumFormat") or "",
            h4NumFormat=d.get("h4NumFormat") or "",
            savedAt=d.get("savedAt") or "",
        )

    def is_empty(self) -> bool:
        return not any([
            self.h1Font, self.h1Size,
            self.h2Font, self.h2Size,
            self.h3Font, self.h3Size,
            self.h4Font, self.h4Size,
            self.bFont, self.bSize,
        ])


class FormatChecker:
    SIZE_TOL = 0.5
    SPACING_TOL_PT = 1.0    # exact 模式容差（磅）
    SPACING_TOL_MUL = 0.05  # multiple 模式容差（倍数）
    MAX_LINE_SPACING_ISSUES = 5  # 全文行距问题上限，避免刷屏

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
            if lvl >= 4:
                lvl = 4
            if lvl > 0:
                return (ElementType.HEADING, lvl)

        if elem.element_type == ElementType.HEADING:
            lvl = int(elem.level or 0)
            if lvl >= 4:
                lvl = 4
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
            (ElementType.HEADING, 4): (self.rules.h4Font, self.rules.h4Size, "四级标题"),
            (ElementType.PARAGRAPH, 0): (self.rules.bFont, self.rules.bSize, "正文段落"),
        }

        ls_mode = (self.rules.lineSpacingMode or "").strip().lower()
        ls_value = self.rules.lineSpacingValue
        _ls_count = 0

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
                    fixable=True,
                    fix_type="format_attr",
                    fix_payload={
                        "attr": "font_name",
                        "scope": "paragraph",
                        "value": exp_font,
                        "para_idx": idx,
                        "para_fingerprint": elem.content[:40].strip(),
                    },
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
                    fixable=True,
                    fix_type="format_attr",
                    fix_payload={
                        "attr": "font_size",
                        "scope": "paragraph",
                        "value": exp_size,
                        "para_idx": idx,
                        "para_fingerprint": elem.content[:40].strip(),
                    },
                ))

            # 行距检查：只对解析器已明确设置行距（非默认 SINGLE/1.0）的元素进行比对
            if ls_mode in ("multiple", "exact") and ls_value > 0 and _ls_count < self.MAX_LINE_SPACING_ISSUES:
                ps = elem.paragraph_style
                a_type = ps.line_spacing_type
                a_val = ps.line_spacing_value
                # 跳过默认值（未被解析器显式设置的元素）
                if not (a_type == LineSpacingType.SINGLE and a_val == 1.0):
                    mismatch = False
                    if ls_mode == "exact":
                        if a_type != LineSpacingType.EXACT or abs(a_val - ls_value) > self.SPACING_TOL_PT:
                            mismatch = True
                            actual_desc = (f"固定值 {a_val:.1f}pt" if a_type == LineSpacingType.EXACT
                                           else f"非固定值行距（{a_type.value}）")
                            desc = f"规范要求固定值 {ls_value}pt，实际为{actual_desc}"
                    else:
                        if a_type != LineSpacingType.MULTIPLE or abs(a_val - ls_value) > self.SPACING_TOL_MUL:
                            mismatch = True
                            actual_desc = (f"{a_val:.2f} 倍" if a_type == LineSpacingType.MULTIPLE
                                           else f"非倍数行距（{a_type.value}）")
                            desc = f"规范要求 {ls_value} 倍行距，实际为{actual_desc}"
                    if mismatch:
                        _ls_count += 1
                        report.add_issue(QAIssue(
                            category=IssueCategory.FORMAT,
                            severity=IssueSeverity.WARNING,
                            title="行距不符规范",
                            description=desc,
                            suggestion=f'将"{loc[:20]}"的行距调整为规范要求',
                            location_text=loc,
                            element_index=idx,
                            rule_id="format_line_spacing",
                            checker="FormatChecker",
                            confidence=0.85,
                            fixable=True,
                            fix_type="format_attr",
                            fix_payload={
                                "attr": "line_spacing",
                                "scope": "paragraph",
                                "mode": ls_mode,
                                "value": ls_value,
                                "para_idx": idx,
                                "para_fingerprint": elem.content[:40].strip(),
                            },
                        ))

        return report
