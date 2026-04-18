"""
WordCraft Pro - 主窗口

应用主界面，包含菜单栏、工具栏、状态栏和中央工作区。
集成工作流引擎，串联完整流程。
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QLabel, QTabWidget, QProgressDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QFont

# 确保项目根目录在 sys.path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


class MainWindow(QMainWindow):
    """WordCraft Pro 主窗口"""

    def __init__(self):
        super().__init__()
        self._current_file: Optional[str] = None
        self._document = None

        self.setWindowTitle("WordCraft Pro")
        self.setMinimumSize(QSize(1280, 860))
        self._apply_global_style()
        self._setup_ui()
        self._connect_workflow()

    def _apply_global_style(self):
        """应用全局 QSS 样式"""
        from ui.styles import QSS_STYLE
        self.setStyleSheet(QSS_STYLE)

    def _setup_ui(self):
        """初始化界面"""
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()

    # ---- 菜单栏 ----

    def _setup_menu_bar(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        open_action = QAction("打开文件(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("保存结果(&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        export_action = QAction("导出Word(&E)", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        qa_action = QAction("质量检查(&Q)", self)
        qa_action.setShortcut("F5")
        qa_action.triggered.connect(self._on_run_qa)
        tools_menu.addAction(qa_action)

        xref_action = QAction("交叉引用检查(&X)", self)
        xref_action.setShortcut("F6")
        xref_action.triggered.connect(self._on_run_crossref)
        tools_menu.addAction(xref_action)

        full_action = QAction("一键排版+检查+导出(&A)", self)
        full_action.setShortcut("F7")
        full_action.triggered.connect(self._on_run_full)
        tools_menu.addAction(full_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ---- 工具栏 ----

    def _setup_toolbar(self):
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))

        open_btn = QAction("打开", self)
        open_btn.setToolTip("打开文件 (Ctrl+O)")
        open_btn.triggered.connect(self._on_open_file)
        toolbar.addAction(open_btn)

        toolbar.addSeparator()

        format_btn = QAction("排版", self)
        format_btn.setToolTip("应用排版规则")
        format_btn.triggered.connect(self._on_run_format)
        toolbar.addAction(format_btn)

        qa_btn = QAction("QA检查", self)
        qa_btn.setToolTip("质量检查 (F5)")
        qa_btn.triggered.connect(self._on_run_qa)
        toolbar.addAction(qa_btn)

        xref_btn = QAction("交叉引用", self)
        xref_btn.setToolTip("交叉引用检查 (F6)")
        xref_btn.triggered.connect(self._on_run_crossref)
        toolbar.addAction(xref_btn)

        toolbar.addSeparator()

        delete_btn = QAction("删除选中文件", self)
        delete_btn.setToolTip("删除文件列表中选中的文件")
        delete_btn.triggered.connect(self._on_delete_selected_file)
        toolbar.addAction(delete_btn)

        toolbar.addSeparator()

        export_btn = QAction("导出", self)
        export_btn.setToolTip("导出Word (Ctrl+E)")
        export_btn.triggered.connect(self._on_export)
        toolbar.addAction(export_btn)

    # ---- 中央工作区 ----

    def _setup_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        from ui.file_panel import FilePanel
        from ui.preview_panel import PreviewPanel
        from ui.format_panel import FormatPanel
        from ui.qa_panel import QAPanel
        from ui.crossref_panel import CrossRefPanel
        from ui.llm_chat_panel import LLMChatPanel

        # 左侧: 文件资源管理器 (固定宽度220px)
        self.file_panel = FilePanel()
        self.file_panel.file_selected.connect(self._on_file_selected)
        self.file_panel.setMinimumWidth(180)
        self.file_panel.setMaximumWidth(350)

        # 中间: 文档预览区 (弹性伸缩)
        self.preview_panel = PreviewPanel()

        # 右侧: QTabWidget 包含 FormatPanel + QAPanel + CrossRefPanel + LLMChatPanel
        self.right_tabs = QTabWidget()
        self.right_tabs.setMinimumWidth(280)
        self.right_tabs.setMaximumWidth(450)

        self.format_panel = FormatPanel()
        self.qa_panel = QAPanel()
        self.crossref_panel = CrossRefPanel()
        self.llm_chat_panel = LLMChatPanel()

        self.right_tabs.addTab(self.format_panel, "排版规则")
        self.right_tabs.addTab(self.llm_chat_panel, "AI 助手")
        self.right_tabs.addTab(self.qa_panel, "质量检查")
        self.right_tabs.addTab(self.crossref_panel, "交叉引用")

        # 三栏分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.file_panel)
        splitter.addWidget(self.preview_panel)
        splitter.addWidget(self.right_tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([220, 740, 320])

        main_layout.addWidget(splitter)

    # ---- 状态栏 ----

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.file_label = QLabel("就绪")
        self.status_bar.addPermanentWidget(self.file_label)

        self.element_count_label = QLabel("")
        self.status_bar.addWidget(self.element_count_label)

    # ---- 工作流连接 ----

    def _connect_workflow(self):
        """连接工作流引擎信号"""
        from ui.workflow_engine import WorkflowEngine
        self.workflow = WorkflowEngine(self)

        self.workflow.progress.connect(self._on_progress)
        self.workflow.workflow_finished.connect(self._on_workflow_finished)
        self.workflow.workflow_error.connect(self._on_workflow_error)

        # 初始化 LLM 客户端
        try:
            from llm.client import create_llm_client, LLMConfig
            config_path = os.path.join(_project_root, "config.yaml")
            llm_client = create_llm_client(config_path=config_path)

            from llm.nl_rule_parser import NLRuleParser
            parser = NLRuleParser(llm_client)
            self.llm_chat_panel.set_parser(parser)
            self.llm_chat_panel.rules_generated.connect(self._on_llm_rules_generated)

            self.status_bar.showMessage(
                f"LLM 已连接: {llm_client.__class__.__name__}", 3000
            )
        except Exception as e:
            self.status_bar.showMessage(f"LLM 初始化失败: {e}", 5000)

        # 排版面板的按钮
        self.format_panel.rules_changed.connect(self._on_run_format)
        self.format_panel.apply_btn.clicked.disconnect()
        self.format_panel.apply_btn.clicked.connect(self._on_run_format)

        # QA面板的按钮
        self.qa_panel.run_btn.clicked.connect(self._on_run_qa)

        # 交叉引用面板的按钮
        self.crossref_panel.run_btn.clicked.connect(self._on_run_crossref)

    # ---- 工作流操作 ----

    def _on_run_format(self):
        """执行排版"""
        if not self._document:
            QMessageBox.information(self, "提示", "请先打开文件")
            return
        rules = self.format_panel.get_rules()
        self.workflow.set_document(self._document)
        self.workflow.run_format(rules)

    def _on_run_qa(self):
        """执行QA检查"""
        if not self._document:
            QMessageBox.information(self, "提示", "请先打开文件")
            return
        self.workflow.set_document(self._document)
        self.workflow.run_qa()

    def _on_run_crossref(self):
        """执行交叉引用检查"""
        if not self._document:
            QMessageBox.information(self, "提示", "请先打开文件")
            return
        self.workflow.set_document(self._document)
        self.workflow.run_crossref()

    def _on_run_full(self):
        """一键排版+检查+导出"""
        if not self._document:
            QMessageBox.information(self, "提示", "请先打开文件")
            return

        export_path, _ = QFileDialog.getSaveFileName(
            self, "导出文件", "", "Word文档 (*.docx)"
        )
        if not export_path:
            return

        rules = self.format_panel.get_rules()
        self.workflow.set_document(self._document)
        self.workflow.run_full(rules, export_path)

    def _on_export(self):
        """导出Word"""
        if not self._document:
            QMessageBox.information(self, "提示", "没有可导出的文档")
            return

        export_path, _ = QFileDialog.getSaveFileName(
            self, "导出文件", "", "Word文档 (*.docx)"
        )
        if export_path:
            self.workflow.set_document(self._document)
            self.workflow.run_export(export_path)

    # ---- 工作流回调 ----

    def _on_progress(self, message: str):
        """进度更新"""
        self.status_bar.showMessage(message)

    def _on_workflow_finished(self, result):
        """工作流完成"""
        from ui.workflow_engine import WorkflowResult

        if result.document:
            self._document = result.document
            self.preview_panel.set_document(result.document)
            counts = result.document.element_count()
            total = sum(counts.values())
            self.element_count_label.setText(f"元素: {total}")

        if result.qa_report:
            self.qa_panel.set_report(result.qa_report)
            self.right_tabs.setCurrentWidget(self.qa_panel)

        if result.crossref_report:
            self.crossref_panel.set_report(result.crossref_report)

        if result.output_path:
            QMessageBox.information(self, "导出成功",
                                    f"文件已导出到:\n{result.output_path}")

        self.status_bar.showMessage("就绪")

    def _on_workflow_error(self, message: str):
        """工作流出错"""
        QMessageBox.critical(self, "错误", f"操作失败:\n{message}")
        self.status_bar.showMessage("操作失败")

    def _on_llm_rules_generated(self, rules):
        """LLM 生成了排版规则"""
        self.format_panel.set_rules(rules)
        self.right_tabs.setCurrentWidget(self.format_panel)
        self.status_bar.showMessage("AI 已生成排版规则，请查看排版规则面板", 3000)

    # ---- 文件操作 ----

    def _on_open_file(self):
        """打开文件对话框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开文件",
            "",
            "支持的格式 (*.docx *.doc *.pdf *.xlsx *.xls *.txt *.md);;所有文件 (*)",
        )
        if file_path:
            self.file_panel.add_file(file_path)

    def _on_file_selected(self, file_path: str):
        """文件被选中时触发解析"""
        self._current_file = file_path
        self.file_label.setText(f"文件: {os.path.basename(file_path)}")
        self.status_bar.showMessage(f"正在解析: {file_path}...")

        try:
            from parsers.dispatcher import parse_file
            doc = parse_file(file_path)
            self._document = doc

            # 更新工作流引擎
            self.workflow.set_document(doc)

            # 更新预览
            self.preview_panel.set_document(doc)

            # 更新状态栏
            counts = doc.element_count()
            total = sum(counts.values())
            self.element_count_label.setText(f"元素: {total}")
            self.status_bar.showMessage(
                f"解析完成: {doc.source_format} | 元素: {total} | "
                f"段落: {counts.get('paragraph', 0)} | 表格: {counts.get('table', 0)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "解析错误", f"文件解析失败:\n{str(e)}")
            self.status_bar.showMessage("解析失败")

    def _on_delete_selected_file(self):
        """删除文件列表中选中的文件"""
        self.file_panel.delete_selected()

    def _on_save(self):
        """保存结果"""
        if not self._document:
            QMessageBox.information(self, "提示", "没有可保存的文档")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "", "Word文档 (*.docx)"
        )
        if file_path:
            try:
                from core.exporter import Exporter
                Exporter().export(self._document, file_path)
                self.status_bar.showMessage(f"已保存: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存错误", f"保存失败:\n{str(e)}")

    def _show_about(self):
        QMessageBox.about(
            self,
            "关于 WordCraft Pro",
            "WordCraft Pro - 智能Word排版桌面应用\n\n"
            "版本: 0.6.0\n"
            "功能: 文件解析、智能排版、质量检查、交叉引用\n\n"
            "支持格式: DOCX, DOC, PDF, XLSX, TXT, MD\n\n"
            "快捷键:\n"
            "  Ctrl+O  打开文件\n"
            "  F5      质量检查\n"
            "  F6      交叉引用检查\n"
            "  F7      一键排版+检查+导出\n"
            "  Ctrl+E  导出Word"
        )

    # ---- 公共方法 ----

    def get_document(self):
        """获取当前文档模型"""
        return self._document

    def set_document(self, doc):
        """设置当前文档模型并更新UI"""
        self._document = doc
        self.workflow.set_document(doc)
        self.preview_panel.set_document(doc)
        counts = doc.element_count()
        total = sum(counts.values())
        self.element_count_label.setText(f"元素: {total}")


def launch():
    """启动应用"""
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
