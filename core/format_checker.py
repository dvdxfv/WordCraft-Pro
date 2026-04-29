"""
格式规范检查器 (Format Rules Checker)

根据用户保存的排版规范（FormatRules）检查文档各元素的字体、字号是否合规。
FormatRules 的 JSON 格式与前端 _collectFormatRules() 输出完全对应。
"""

from __future__ import annotations

from dataclasses import dataclass

from core.document_model import DocumentModel, ElementType
from core.qa_models import QAIssue, IssueCategory, IssueSeverity, QAReport


@dataclass
class FormatRules:
    """用户保存的排版规范（对应前端 _collectFormatRules() 输出的 JSON 结构）。"""
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
    def from_dict(cls, d: dict) -> FormatRules:
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
    """
    格式规范检查器。

    对 DocumentModel 中每个带有字体信息的元素，与 FormatRules 进行比对，
    输出字体/字号不合规的 QAReport。

    当元素的 font_style.font_size_pt == 0（例如 HTML 解析后无字体信息）时
    跳过该元素，不产生误报。
    """

    MAX_PER_TYPE = 2   # 每种元素类型最多报告几条，避免刷屏
    SIZE_TOL = 0.5     # 字号容差（pt）

    def __init__(self, rules: FormatRules):
        self.rules = rules

    def check(self, doc: DocumentModel) -> QAReport:
        report = QAReport()
        if self.rules.is_empty():
            return report

        # (element_type, heading_level) → (expected_font, expected_size, label)
        type_rules: dict[tuple, tuple] = {
            (ElementType.HEADING, 1): (self.rules.h1Font, self.rules.h1Size, "一级标题"),
            (ElementType.HEADING, 2): (self.rules.h2Font, self.rules.h2Size, "二级标题"),
            (ElementType.HEADING, 3): (self.rules.h3Font, self.rules.h3Size, "三级标题"),
            (ElementType.PARAGRAPH, 0): (self.rules.bFont, self.rules.bSize, "正文段落"),
        }

        font_counts: dict[str, int] = {}
        size_counts: dict[str, int] = {}
        total_font_mismatch: dict[str, int] = {}

        for idx, elem in enumerate(doc.elements):
            # 第十八批：结构识别层标记的封面/目录/参考文献/题注/表格不参与正文体格式检查
            if isinstance(elem.metadata, dict) and elem.metadata.get("exclude_from_format_body"):
                continue

            lvl = elem.level if elem.element_type == ElementType.HEADING else 0
            key = (elem.element_type, lvl)
            if key not in type_rules:
                continue

            exp_font, exp_size, label = type_rules[key]
            loc = elem.content[:40].strip()
            if not loc:
                continue

            fs = elem.font_style
            actual_font = fs.font_name_cn or fs.font_name_en
            actual_size = fs.font_size_pt
            tk = f"{elem.element_type.value}_{lvl}"

            if actual_font and exp_font and actual_font != exp_font:
                total_font_mismatch[tk] = total_font_mismatch.get(tk, 0) + 1
                cnt = font_counts.get(tk, 0)
                if cnt < self.MAX_PER_TYPE:
                    font_counts[tk] = cnt + 1
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
                cnt = size_counts.get(tk, 0)
                if cnt < self.MAX_PER_TYPE:
                    size_counts[tk] = cnt + 1
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

        # 汇总提示：字体问题超出 MAX_PER_TYPE 时额外说明范围
        total_mm = sum(total_font_mismatch.values())
        shown = sum(font_counts.values())
        if total_mm > shown:
            suppressed = total_mm - shown
            report.add_issue(QAIssue(
                category=IssueCategory.FORMAT,
                severity=IssueSeverity.INFO,
                title="文档字体与规范存在大范围差异",
                description=f"显示 {shown} 个格式错误（共检出 {total_mm} 个同类问题）。为避免过多提示，仅显示最严重的 {shown} 个字体不符合规范的问题。还有 {suppressed} 个类似问题已折叠。",
                suggestion="可在排版面板重新应用格式后导出，或在设置中调整显示数量",
                location_text="",
                rule_id="format_font_summary",
                checker="FormatChecker",
                confidence=0.8,
            ))

        return report
