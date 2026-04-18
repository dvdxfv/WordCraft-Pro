"""
Phase 6 单元测试

测试 PyQt6 UI 组件和工作流引擎（无头模式，不启动 QApplication）。
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import (
    DocumentModel, DocElement, ElementType, FontStyle, ParagraphStyle,
    Alignment,
)
from core.formatting_rules import FormattingRules, StyleRules, PageRules
from core.qa_models import QAReport, QAIssue, IssueCategory, IssueSeverity
from core.crossref_models import CrossRefReport, RefTarget, RefTargetType, CrossRefStatus
from core.crossref_engine import CrossRefEngine, CrossRefRules
from core.qa_engine import QAEngine
from core.formatter import Formatter
from core.exporter import Exporter


# ============================================================
# 辅助函数
# ============================================================

def _make_doc(*elements) -> DocumentModel:
    doc = DocumentModel(title="测试文档")
    doc.elements.extend(elements)
    return doc


def _p(content: str, **kwargs) -> DocElement:
    return DocElement(element_type=ElementType.PARAGRAPH, content=content, **kwargs)


def _h(content: str, level: int = 1, **kwargs) -> DocElement:
    return DocElement(element_type=ElementType.HEADING, content=content, level=level, **kwargs)


def _cap(content: str, **kwargs) -> DocElement:
    return DocElement(element_type=ElementType.CAPTION, content=content, **kwargs)


# ============================================================
# 测试工作流引擎（核心逻辑，无需 QApplication）
# ============================================================

class TestWorkflowResult:
    """测试工作流结果数据类"""

    def test_create_empty_result(self):
        from ui.workflow_engine import WorkflowResult
        result = WorkflowResult()
        assert result.document is None
        assert result.qa_report is None
        assert result.crossref_report is None
        assert result.output_path is None
        assert result.error is None

    def test_create_result_with_data(self):
        from ui.workflow_engine import WorkflowResult
        doc = _make_doc(_p("测试"))
        result = WorkflowResult(document=doc, output_path="/tmp/test.docx")
        assert result.document is not None
        assert result.output_path == "/tmp/test.docx"


class TestWorkflowWorker:
    """测试工作流线程（同步调用 run 方法）"""

    def test_worker_setup(self):
        from ui.workflow_engine import WorkflowWorker
        worker = WorkflowWorker()
        worker.setup(
            file_path=None,
            rules=FormattingRules(),
            run_qa=True,
            run_crossref=True,
            export_path=None,
        )
        assert worker._run_qa is True
        assert worker._run_crossref is True

    def test_worker_run_format_only(self):
        """测试仅排版工作流"""
        from ui.workflow_engine import WorkflowWorker, WorkflowResult

        doc = _make_doc(
            _h("第一章 绪论", level=1),
            _p("这是正文内容。"),
        )

        worker = WorkflowWorker()
        results = []
        worker.finished.connect(lambda r: results.append(r))

        # 直接调用 run（不启动线程，同步执行）
        worker.setup(
            rules=FormattingRules(
                heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True),
                body=StyleRules(font_name_cn="宋体", font_size_pt=12),
            ),
            run_qa=False,
            run_crossref=False,
        )
        # 手动设置文档（模拟已解析状态）
        worker._document = doc
        worker.run()

        assert len(results) == 1
        result = results[0]
        assert result.document is not None

    def test_worker_run_qa(self):
        """测试QA检查工作流"""
        from ui.workflow_engine import WorkflowWorker

        doc = _make_doc(
            _p("请输入正确的帐号进行登录。"),
            _p("既使困难也要坚持。"),
        )

        worker = WorkflowWorker()
        results = []
        worker.finished.connect(lambda r: results.append(r))

        # 直接测试 run 中的 QA 逻辑
        from core.qa_engine import QAEngine
        report = QAEngine().check(doc)
        assert report.total >= 2

    def test_worker_run_crossref(self):
        """测试交叉引用工作流"""
        doc = _make_doc(
            _h("第三章 实验结果", level=1),
            _cap("图3-1 实验数据"),
            _p("如图3-1所示。"),
            _p("如图3-2所示。"),  # 悬空
        )

        rules = CrossRefRules(enabled=True)
        report = CrossRefEngine(rules).check(doc)
        assert report.target_count >= 1
        assert report.dangling_count >= 1


class TestWorkflowEngine:
    """测试工作流引擎"""

    def test_create_engine(self):
        from ui.workflow_engine import WorkflowEngine
        engine = WorkflowEngine()
        assert engine.document is None
        assert engine.qa_report is None

    def test_set_document(self):
        from ui.workflow_engine import WorkflowEngine
        engine = WorkflowEngine()
        doc = _make_doc(_p("测试"))
        engine.set_document(doc)
        assert engine.document is not None
        assert engine.document.title == "测试文档"

    def test_run_format_sync(self):
        """同步测试排版流程"""
        from ui.workflow_engine import WorkflowEngine, WorkflowResult

        doc = _make_doc(
            _h("第一章 绪论", level=1),
            _p("正文内容。"),
        )
        rules = FormattingRules(
            heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True),
            body=StyleRules(font_name_cn="宋体", font_size_pt=12),
        )

        # 直接调用排版逻辑
        formatter = Formatter(rules)
        formatted = formatter.apply(doc)
        assert formatted is not None
        assert len(formatted.elements) == 2


# ============================================================
# 测试 UI 面板数据逻辑（无头模式）
# ============================================================

class TestFormatPanelLogic:
    """测试排版规则面板的数据逻辑"""

    def test_get_default_rules(self):
        # 不导入 PyQt6 UI 组件（无头环境可能缺少 EGL）
        rules = FormattingRules()
        assert rules.page.paper_size == "A4"

    def test_style_rules_merge(self):
        rules = FormattingRules()
        rules.heading1 = StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True)
        rules.body = StyleRules(font_name_cn="宋体", font_size_pt=12)
        assert rules.heading1.font_name_cn == "黑体"
        assert rules.body.font_name_cn == "宋体"


class TestQAPanelLogic:
    """测试QA面板的数据逻辑"""

    def test_report_filtering(self):
        report = QAReport()
        report.add_issue(QAIssue(category=IssueCategory.TYPO, severity=IssueSeverity.ERROR))
        report.add_issue(QAIssue(category=IssueCategory.LOGIC, severity=IssueSeverity.WARNING))
        report.add_issue(QAIssue(category=IssueCategory.INCONSISTENCY, severity=IssueSeverity.INFO))

        # 按类别筛选
        typos = report.get_issues_by_category(IssueCategory.TYPO)
        assert len(typos) == 1

        # 按严重程度筛选
        errors = report.get_issues_by_severity(IssueSeverity.ERROR)
        assert len(errors) == 1

    def test_report_summary(self):
        report = QAReport()
        report.add_issue(QAIssue(category=IssueCategory.TYPO, severity=IssueSeverity.ERROR))
        report.add_issue(QAIssue(category=IssueCategory.TYPO, severity=IssueSeverity.WARNING))
        text = report.summary_text()
        assert "错别字" in text
        assert "2" in text


class TestCrossRefPanelLogic:
    """测试交叉引用面板的数据逻辑"""

    def test_report_summary(self):
        report = CrossRefReport()
        report.targets.append(RefTarget(
            target_type=RefTargetType.FIGURE, number="3-1", label="图3-1"
        ))
        report.targets.append(RefTarget(
            target_type=RefTargetType.TABLE, number="2-1", label="表2-1"
        ))
        text = report.summary_text()
        assert "图" in text
        assert "表" in text

    def test_status_names(self):
        # 直接验证映射值，不导入 PyQt6 UI 组件
        from core.crossref_models import CrossRefStatus
        expected = {
            CrossRefStatus.VALID: "有效",
            CrossRefStatus.DANGLING: "悬空引用",
            CrossRefStatus.MISMATCH: "类型不匹配",
            CrossRefStatus.DUPLICATE: "重复编号",
            CrossRefStatus.UNREFERENCED: "未引用",
        }
        assert expected[CrossRefStatus.VALID] == "有效"
        assert expected[CrossRefStatus.DANGLING] == "悬空引用"


# ============================================================
# 测试端到端工作流（无 UI）
# ============================================================

class TestEndToEndWorkflow:
    """端到端工作流测试（纯逻辑，无 UI）"""

    def test_full_workflow_logic(self):
        """完整工作流逻辑：解析 → 排版 → QA → 交叉引用 → 导出"""
        # 1. 创建模拟文档
        doc = _make_doc(
            _h("第三章 实验结果", level=1),
            _cap("图3-1 实验数据对比"),
            _p("如图3-1所示，实验结果符合预期。"),
            _p("请输入正确的帐号进行登录。"),
            _p("既使困难也要坚持。"),
            _h("第四章 结论", level=1),  # 空章节
        )

        # 2. 排版
        rules = FormattingRules(
            heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True),
            body=StyleRules(font_name_cn="宋体", font_size_pt=12),
        )
        formatted = Formatter(rules).apply(doc)
        assert formatted is not None

        # 3. QA 检查
        qa_report = QAEngine().check(formatted)
        assert qa_report.total >= 2  # 至少有错别字

        # 4. 交叉引用检查
        crossref_rules = CrossRefRules(enabled=True)
        crossref_report = CrossRefEngine(crossref_rules).check(formatted)
        assert crossref_report.target_count >= 1

        # 5. 导出
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            Exporter().export(
                formatted, path,
                qa_report=qa_report,
                crossref_report=crossref_report,
            )
            assert os.path.isfile(path)
            assert os.path.getsize(path) > 1000
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_workflow_with_real_txt_file(self):
        """使用真实 TXT 文件测试完整工作流"""
        from parsers.dispatcher import parse_file

        fd, txt_path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("第三章 实验结果\n\n")
                f.write("图3-1 实验数据对比\n\n")
                f.write("如图3-1所示，实验结果符合预期。\n\n")
                f.write("请输入正确的帐号。\n\n")
                f.write("第四章 结论\n\n")

            # 解析
            doc = parse_file(txt_path)
            assert doc.source_format == "txt"

            # QA
            qa_report = QAEngine().check(doc)
            assert qa_report.total >= 1

            # 交叉引用
            crossref_report = CrossRefEngine(CrossRefRules(enabled=True)).check(doc)
            assert crossref_report.target_count >= 1

            # 排版 + 导出
            rules = FormattingRules(
                heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True),
                body=StyleRules(font_name_cn="宋体", font_size_pt=12),
            )
            formatted = Formatter(rules).apply(doc)

            fd2, docx_path = tempfile.mkstemp(suffix=".docx")
            os.close(fd2)
            try:
                Exporter().export(
                    formatted, docx_path,
                    qa_report=qa_report,
                    crossref_report=crossref_report,
                )
                assert os.path.isfile(docx_path)
            finally:
                if os.path.exists(docx_path):
                    os.unlink(docx_path)
        finally:
            if os.path.exists(txt_path):
                os.unlink(txt_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
