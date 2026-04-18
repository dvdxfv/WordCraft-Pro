"""
WordCraft Pro - 工作流引擎

串联完整流程：解析 → 排版 → QA检查 → 交叉引用 → 导出。
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from core.document_model import DocumentModel
from core.formatting_rules import FormattingRules
from core.formatter import Formatter
from core.exporter import Exporter
from core.qa_engine import QAEngine
from core.qa_models import QAReport
from core.crossref_engine import CrossRefEngine
from core.crossref_models import CrossRefReport
from core.formatting_rules import CrossRefRules
from parsers.dispatcher import parse_file


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    document: Optional[DocumentModel] = None
    qa_report: Optional[QAReport] = None
    crossref_report: Optional[CrossRefReport] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class WorkflowWorker(QThread):
    """工作流执行线程（避免阻塞UI）"""

    progress = pyqtSignal(str)          # 进度消息
    finished = pyqtSignal(object)       # WorkflowResult
    error = pyqtSignal(str)             # 错误消息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path: Optional[str] = None
        self._rules: Optional[FormattingRules] = None
        self._run_qa: bool = True
        self._run_crossref: bool = True
        self._export_path: Optional[str] = None

    def setup(self, file_path: str = None, rules: FormattingRules = None,
              run_qa: bool = True, run_crossref: bool = True,
              export_path: str = None):
        """配置工作流参数"""
        self._file_path = file_path
        self._rules = rules
        self._run_qa = run_qa
        self._run_crossref = run_crossref
        self._export_path = export_path

    def run(self):
        """执行工作流"""
        result = WorkflowResult()

        try:
            # Step 1: 解析
            if self._file_path:
                self.progress.emit("正在解析文件...")
                result.document = parse_file(self._file_path)
                self.progress.emit(
                    f"解析完成: {result.document.source_format}, "
                    f"{len(result.document.elements)} 个元素"
                )
            elif hasattr(self, '_document') and self._document:
                result.document = self._document

            # Step 2: 排版
            if result.document and self._rules:
                self.progress.emit("正在应用排版规则...")
                formatter = Formatter(self._rules)
                result.document = formatter.apply(result.document)
                self.progress.emit("排版完成")

            # Step 3: QA检查
            if result.document and self._run_qa:
                self.progress.emit("正在执行质量检查...")
                qa_engine = QAEngine()
                result.qa_report = qa_engine.check(result.document)
                self.progress.emit(
                    f"QA检查完成: {result.qa_report.total} 个问题"
                )

            # Step 4: 交叉引用检查
            if result.document and self._run_crossref:
                self.progress.emit("正在检查交叉引用...")
                crossref_rules = CrossRefRules(enabled=True)
                crossref_engine = CrossRefEngine(crossref_rules)
                result.crossref_report = crossref_engine.check(result.document)
                self.progress.emit(
                    f"交叉引用检查完成: {result.crossref_report.target_count} 个目标, "
                    f"{result.crossref_report.ref_point_count} 个引用点"
                )

            # Step 5: 导出
            if result.document and self._export_path:
                self.progress.emit("正在导出Word文档...")
                exporter = Exporter()
                exporter.export(
                    result.document,
                    self._export_path,
                    qa_report=result.qa_report,
                    crossref_report=result.crossref_report,
                )
                result.output_path = self._export_path
                self.progress.emit(f"导出完成: {self._export_path}")

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class WorkflowEngine(QObject):
    """工作流引擎 — 管理工作流生命周期"""

    progress = pyqtSignal(str)
    workflow_finished = pyqtSignal(object)  # WorkflowResult
    workflow_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[WorkflowWorker] = None
        self._document: Optional[DocumentModel] = None
        self._qa_report: Optional[QAReport] = None
        self._crossref_report: Optional[CrossRefReport] = None

    @property
    def document(self) -> Optional[DocumentModel]:
        return self._document

    @property
    def qa_report(self) -> Optional[QAReport]:
        return self._qa_report

    @property
    def crossref_report(self) -> Optional[CrossRefReport]:
        return self._crossref_report

    def set_document(self, doc: DocumentModel):
        """设置已解析的文档"""
        self._document = doc

    def run_format(self, rules: FormattingRules):
        """执行排版"""
        if not self._document:
            self.workflow_error.emit("没有可排版的文档，请先打开文件")
            return

        self._worker = WorkflowWorker()
        self._worker.setup(rules=rules, run_qa=False, run_crossref=False)
        self._worker.progress.connect(self.progress.emit)
        self._worker.finished.connect(self._on_format_finished)
        self._worker.error.connect(self.workflow_error.emit)
        self._worker.start()

    def run_qa(self):
        """执行QA检查"""
        if not self._document:
            self.workflow_error.emit("没有可检查的文档，请先打开文件")
            return

        self._worker = WorkflowWorker()
        self._worker.setup(run_qa=True, run_crossref=False)
        self._worker.progress.connect(self.progress.emit)
        self._worker.finished.connect(self._on_qa_finished)
        self._worker.error.connect(self.workflow_error.emit)
        self._worker.start()

    def run_crossref(self):
        """执行交叉引用检查"""
        if not self._document:
            self.workflow_error.emit("没有可检查的文档，请先打开文件")
            return

        self._worker = WorkflowWorker()
        self._worker.setup(run_qa=False, run_crossref=True)
        self._worker.progress.connect(self.progress.emit)
        self._worker.finished.connect(self._on_crossref_finished)
        self._worker.error.connect(self.workflow_error.emit)
        self._worker.start()

    def run_full(self, rules: FormattingRules, export_path: str = None):
        """执行完整流程"""
        if not self._document:
            self.workflow_error.emit("没有可处理的文档，请先打开文件")
            return

        self._worker = WorkflowWorker()
        self._worker.setup(rules=rules, run_qa=True, run_crossref=True,
                           export_path=export_path)
        self._worker.progress.connect(self.progress.emit)
        self._worker.finished.connect(self._on_full_finished)
        self._worker.error.connect(self.workflow_error.emit)
        self._worker.start()

    def run_export(self, export_path: str):
        """仅导出"""
        if not self._document:
            self.workflow_error.emit("没有可导出的文档")
            return

        self._worker = WorkflowWorker()
        self._worker.setup(
            run_qa=False, run_crossref=False, export_path=export_path
        )
        self._worker.progress.connect(self.progress.emit)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.error.connect(self.workflow_error.emit)
        self._worker.start()

    # ---- 回调 ----

    def _on_format_finished(self, result: WorkflowResult):
        if result.document:
            self._document = result.document
        self.workflow_finished.emit(result)

    def _on_qa_finished(self, result: WorkflowResult):
        if result.qa_report:
            self._qa_report = result.qa_report
        self.workflow_finished.emit(result)

    def _on_crossref_finished(self, result: WorkflowResult):
        if result.crossref_report:
            self._crossref_report = result.crossref_report
        self.workflow_finished.emit(result)

    def _on_full_finished(self, result: WorkflowResult):
        if result.document:
            self._document = result.document
        if result.qa_report:
            self._qa_report = result.qa_report
        if result.crossref_report:
            self._crossref_report = result.crossref_report
        self.workflow_finished.emit(result)

    def _on_export_finished(self, result: WorkflowResult):
        self.workflow_finished.emit(result)
