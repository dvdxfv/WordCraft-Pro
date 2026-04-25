"""交叉引用检查器：基于 crossref_engine 输出 QA 问题。"""

from __future__ import annotations

from core.crossref_engine import CrossRefEngine
from core.crossref_models import CrossRefStatus
from core.document_model import DocumentModel
from core.qa_models import QAIssue, IssueCategory, IssueSeverity, QAReport


class CrossRefChecker:
    """将 CrossRefEngine 的匹配结果映射为 QAReport。"""

    def __init__(self):
        self.enabled = True
        self.engine = CrossRefEngine()
        # QA 检查场景默认启用交叉引用扫描。
        self.engine.rules.enabled = True

    def check(self, doc: DocumentModel) -> QAReport:
        report = QAReport()
        if not self.enabled:
            return report

        xref_report = self.engine.check(doc)
        for match in xref_report.matches:
            if match.status == CrossRefStatus.VALID:
                continue
            issue = self._match_to_issue(match)
            report.add_issue(issue)
        return report

    @staticmethod
    def _match_to_issue(match) -> QAIssue:
        status = match.status
        target_type = match.target.target_type.value if match.target else "reference"
        ref_text = (match.ref_point.ref_text or "").strip() if match.ref_point else ""
        location_text = ref_text or (match.target.label if match.target else "")

        if status == CrossRefStatus.DANGLING:
            return QAIssue(
                category=IssueCategory.REFERENCE,
                severity=IssueSeverity.ERROR,
                title=f'悬空引用："{ref_text}"',
                description=match.message or "引用目标不存在或编号不匹配",
                suggestion="检查编号是否正确，或补充对应图/表/章节目标",
                location_text=location_text,
                element_index=getattr(match.ref_point, "element_index", -1),
                rule_id=f"xref.dangling.{target_type}",
                checker="crossref_checker",
                confidence=0.95,
            )

        if status == CrossRefStatus.UNREFERENCED:
            return QAIssue(
                category=IssueCategory.REFERENCE,
                severity=IssueSeverity.WARNING,
                title=f'未被引用目标："{match.target.label}"',
                description=match.message or "该目标未在正文引用",
                suggestion="在正文补充对应引用，或删除无用目标",
                location_text=location_text,
                element_index=getattr(match.target, "element_index", -1),
                rule_id=f"xref.unreferenced.{target_type}",
                checker="crossref_checker",
                confidence=0.8,
            )

        if status == CrossRefStatus.DUPLICATE:
            return QAIssue(
                category=IssueCategory.REFERENCE,
                severity=IssueSeverity.WARNING,
                title=f'重复编号："{match.target.label}"',
                description=match.message or "引用目标出现重复编号",
                suggestion="调整重复编号，确保编号唯一",
                location_text=location_text,
                element_index=getattr(match.target, "element_index", -1),
                rule_id=f"xref.duplicate.{target_type}",
                checker="crossref_checker",
                confidence=0.85,
            )

        return QAIssue(
            category=IssueCategory.REFERENCE,
            severity=IssueSeverity.INFO,
            title=f'交叉引用待确认："{ref_text}"',
            description=match.message or f"交叉引用状态：{status.value}",
            suggestion="请人工确认该引用是否正确",
            location_text=location_text,
            element_index=getattr(match.ref_point, "element_index", -1),
            rule_id=f"xref.{status.value}.{target_type}",
            checker="crossref_checker",
            confidence=0.6,
        )
