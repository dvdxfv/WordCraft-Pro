"""
WordCraft Pro - 质量检查面板

显示 QA 检查结果：错别字、数据一致性、逻辑问题。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
    QTreeWidgetItem, QPushButton, QComboBox, QTextEdit,
    QHeaderView, QGroupBox, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from core.qa_models import QAReport, QAIssue, IssueCategory, IssueSeverity


# 严重程度颜色
_SEVERITY_COLORS = {
    IssueSeverity.ERROR: QColor("#e74c3c"),
    IssueSeverity.WARNING: QColor("#f39c12"),
    IssueSeverity.INFO: QColor("#3498db"),
}

_CATEGORY_NAMES = {
    IssueCategory.TYPO: "错别字",
    IssueCategory.INCONSISTENCY: "数据不一致",
    IssueCategory.LOGIC: "逻辑问题",
}


class QAPanel(QWidget):
    """质量检查结果面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._report: Optional[QAReport] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题 + 统计
        header = QHBoxLayout()
        title = QLabel("质量检查结果")
        title.setObjectName("panelTitle")
        header.addWidget(title)

        self.summary_label = QLabel("未检查")
        self.summary_label.setObjectName("summaryLabel")
        header.addWidget(self.summary_label)

        layout.addLayout(header)

        # 筛选栏
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("筛选:"))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "错误", "警告", "提示",
                                     "错别字", "数据不一致", "逻辑问题"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 联动排版规则检查
        self.format_check_cb = QCheckBox("联动排版规则检查")
        self.format_check_cb.setToolTip(
            "勾选后，QA结果中额外显示排版规则相关的检查项\n"
            "(如字号不一致、缺少缩进等)"
        )
        layout.addWidget(self.format_check_cb)

        # 问题列表
        self.issue_tree = QTreeWidget()
        self.issue_tree.setHeaderLabels(["严重程度", "类别", "标题", "位置"])
        self.issue_tree.setColumnWidth(0, 70)
        self.issue_tree.setColumnWidth(1, 80)
        self.issue_tree.header().setStretchLastSection(True)
        self.issue_tree.setAlternatingRowColors(True)
        self.issue_tree.itemClicked.connect(self._on_issue_clicked)
        layout.addWidget(self.issue_tree)

        # 详情区域
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMaximumHeight(150)
        self.detail_view.setObjectName("detailView")
        layout.addWidget(self.detail_view)

        # 运行按钮
        self.run_btn = QPushButton("运行质量检查")
        self.run_btn.setObjectName("accentBtn")
        layout.addWidget(self.run_btn)

    def set_report(self, report: QAReport):
        """设置QA报告并刷新显示"""
        self._report = report
        self._refresh_display()

    def _refresh_display(self):
        """刷新显示"""
        self.issue_tree.clear()
        self.detail_view.clear()

        if not self._report:
            self.summary_label.setText("未检查")
            return

        report = self._report

        # 更新统计
        self.summary_label.setText(
            f"共 {report.total} 个问题 | "
            f"错误: {report.error_count} | "
            f"警告: {report.warning_count} | "
            f"提示: {report.info_count}"
        )

        # 获取筛选条件
        filter_text = self.filter_combo.currentText()
        issues = self._filter_issues(report, filter_text)

        # 填充列表
        for issue in issues:
            severity_name = issue.severity.value
            category_name = _CATEGORY_NAMES.get(issue.category, issue.category.value)

            item = QTreeWidgetItem(self.issue_tree, [
                severity_name,
                category_name,
                issue.title,
                issue.location_text or "",
            ])

            # 设置颜色
            color = _SEVERITY_COLORS.get(issue.severity, QColor("#333"))
            item.setForeground(0, color)

            # 存储问题索引用于详情显示
            item.setData(0, Qt.ItemDataRole.UserRole, id(issue))

        # 联动排版规则检查
        if self.format_check_cb.isChecked():
            self._add_format_check_items()

    def _add_format_check_items(self):
        """添加排版规则相关的检查项"""
        try:
            # 尝试获取排版规则面板的规则
            main_win = self.window()
            if main_win and hasattr(main_win, 'format_panel'):
                rules = main_win.format_panel.get_rules()
                format_issues = self._check_formatting_rules(rules)
                for fi in format_issues:
                    item = QTreeWidgetItem(self.issue_tree, [
                        fi["severity"],
                        "排版检查",
                        fi["title"],
                        fi.get("location", ""),
                    ])
                    color = _SEVERITY_COLORS.get(
                        IssueSeverity(fi["severity"]), QColor("#f39c12")
                    )
                    item.setForeground(0, color)
                    item.setData(0, Qt.ItemDataRole.UserRole, id(fi))
        except Exception:
            pass

    def _check_formatting_rules(self, rules) -> list[dict]:
        """根据排版规则生成检查项"""
        items = []
        if not rules:
            return items

        # 检查正文字号是否为标准中文号
        standard_cn_sizes = [26, 24, 22, 18, 16, 15, 14, 12, 10.5, 9]
        if rules.body and rules.body.font_size_pt:
            if rules.body.font_size_pt not in standard_cn_sizes:
                items.append({
                    "severity": "警告",
                    "title": f"正文字号 {rules.body.font_size_pt}pt 不是标准中文号",
                    "location": "正文样式",
                })

        # 检查首行缩进
        if rules.body:
            if not rules.body.first_indent_chars or rules.body.first_indent_chars == 0:
                items.append({
                    "severity": "警告",
                    "title": "正文缺少首行缩进",
                    "location": "正文样式",
                })
            elif rules.body.first_indent_chars != 2:
                items.append({
                    "severity": "提示",
                    "title": f"首行缩进为 {rules.body.first_indent_chars} 字符（通常为2字符）",
                    "location": "正文样式",
                })

        # 检查标题字号是否大于正文字号
        if rules.heading1 and rules.body:
            if (rules.heading1.font_size_pt and rules.body.font_size_pt
                    and rules.heading1.font_size_pt <= rules.body.font_size_pt):
                items.append({
                    "severity": "警告",
                    "title": "一级标题字号不大于正文字号",
                    "location": "标题样式",
                })

        # 检查行距
        if rules.body and hasattr(rules.body, 'line_spacing'):
            pass  # 行距检查预留

        return items

    def _filter_issues(self, report: QAReport, filter_text: str) -> list[QAIssue]:
        """根据筛选条件过滤问题"""
        if filter_text == "全部":
            return report.issues

        severity_map = {"错误": IssueSeverity.ERROR,
                        "警告": IssueSeverity.WARNING,
                        "提示": IssueSeverity.INFO}
        category_map = {"错别字": IssueCategory.TYPO,
                        "数据不一致": IssueCategory.INCONSISTENCY,
                        "逻辑问题": IssueCategory.LOGIC}

        if filter_text in severity_map:
            return [i for i in report.issues if i.severity == severity_map[filter_text]]
        if filter_text in category_map:
            return [i for i in report.issues if i.category == category_map[filter_text]]
        return report.issues

    def _on_filter_changed(self, text: str):
        """筛选条件变更"""
        if self._report:
            self._refresh_display()

    def _on_issue_clicked(self, item: QTreeWidgetItem, column: int):
        """点击问题时显示详情"""
        if not self._report:
            return

        # 查找对应问题
        for issue in self._report.issues:
            if id(issue) == item.data(0, Qt.ItemDataRole.UserRole):
                lines = [
                    f"<b>标题:</b> {issue.title}",
                    f"<b>类别:</b> {_CATEGORY_NAMES.get(issue.category, issue.category.value)}",
                    f"<b>严重程度:</b> {issue.severity.value}",
                    f"<b>置信度:</b> {issue.confidence:.0%}" if issue.confidence else "",
                    "",
                    f"<b>描述:</b> {issue.description or '无'}",
                ]
                if issue.suggestion:
                    lines.append(f"<b>建议:</b> {issue.suggestion}")
                if issue.location_text:
                    lines.append(f"<b>位置:</b> {issue.location_text}")
                if issue.related_text:
                    lines.append(f"<b>相关:</b> {issue.related_text}")

                self.detail_view.setHtml("<br>".join(l for l in lines if l))
                break
