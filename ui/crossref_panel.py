"""
WordCraft Pro - 交叉引用面板

显示交叉引用检查结果：引用目标、引用点、匹配状态。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
    QTreeWidgetItem, QPushButton, QComboBox, QTextEdit,
    QHeaderView, QGroupBox, QTabWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from core.crossref_models import (
    CrossRefReport, RefTarget, RefPoint, CrossRefMatch,
    RefTargetType, CrossRefStatus,
)


_TYPE_NAMES = {
    RefTargetType.FIGURE: "图",
    RefTargetType.TABLE: "表",
    RefTargetType.EQUATION: "公式",
    RefTargetType.CHAPTER: "章节",
    RefTargetType.APPENDIX: "附录",
    RefTargetType.REFERENCE: "参考文献",
}

_STATUS_NAMES = {
    CrossRefStatus.VALID: "有效",
    CrossRefStatus.DANGLING: "悬空引用",
    CrossRefStatus.MISMATCH: "类型不匹配",
    CrossRefStatus.DUPLICATE: "重复编号",
    CrossRefStatus.UNREFERENCED: "未引用",
    CrossRefStatus.NEEDS_CONFIRM: "需确认",
}

_STATUS_COLORS = {
    CrossRefStatus.VALID: QColor("#27ae60"),
    CrossRefStatus.DANGLING: QColor("#e74c3c"),
    CrossRefStatus.MISMATCH: QColor("#e74c3c"),
    CrossRefStatus.DUPLICATE: QColor("#f39c12"),
    CrossRefStatus.UNREFERENCED: QColor("#f39c12"),
    CrossRefStatus.NEEDS_CONFIRM: QColor("#3498db"),
}


class CrossRefPanel(QWidget):
    """交叉引用检查面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._report: Optional[CrossRefReport] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题 + 统计
        header = QHBoxLayout()
        title = QLabel("交叉引用检查")
        title.setObjectName("panelTitle")
        header.addWidget(title)

        self.summary_label = QLabel("未检查")
        self.summary_label.setObjectName("summaryLabel")
        header.addWidget(self.summary_label)

        layout.addLayout(header)

        # 选项卡
        self.tabs = QTabWidget()

        # Tab 1: 引用目标
        self.target_tree = QTreeWidget()
        self.target_tree.setHeaderLabels(["类型", "编号", "标签", "标题"])
        self.target_tree.setColumnWidth(0, 60)
        self.target_tree.setColumnWidth(1, 60)
        self.target_tree.header().setStretchLastSection(True)
        self.target_tree.setAlternatingRowColors(True)
        self.tabs.addTab(self.target_tree, "引用目标")

        # Tab 2: 匹配结果
        self.match_tree = QTreeWidget()
        self.match_tree.setHeaderLabels(["状态", "引用", "目标", "说明"])
        self.match_tree.setColumnWidth(0, 80)
        self.match_tree.setColumnWidth(1, 100)
        self.match_tree.header().setStretchLastSection(True)
        self.match_tree.setAlternatingRowColors(True)
        self.match_tree.itemClicked.connect(self._on_match_clicked)
        self.tabs.addTab(self.match_tree, "匹配结果")

        layout.addWidget(self.tabs)

        # 详情
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMaximumHeight(120)
        self.detail_view.setObjectName("detailView")
        layout.addWidget(self.detail_view)

        # 运行按钮
        self.run_btn = QPushButton("运行交叉引用检查")
        self.run_btn.setObjectName("purpleBtn")
        layout.addWidget(self.run_btn)

    def set_report(self, report: CrossRefReport):
        """设置交叉引用报告并刷新显示"""
        self._report = report
        self._refresh_display()

    def _refresh_display(self):
        """刷新显示"""
        self.target_tree.clear()
        self.match_tree.clear()
        self.detail_view.clear()

        if not self._report:
            self.summary_label.setText("未检查")
            return

        report = self._report

        # 统计
        self.summary_label.setText(
            f"目标: {report.target_count} | "
            f"引用: {report.ref_point_count} | "
            f"有效: {report.valid_count} | "
            f"悬空: {report.dangling_count} | "
            f"未引用: {report.unreferenced_count}"
        )

        # 引用目标列表
        for target in report.targets:
            type_name = _TYPE_NAMES.get(target.target_type, target.target_type.value)
            QTreeWidgetItem(self.target_tree, [
                type_name,
                target.number,
                target.label,
                target.title or "",
            ])

        # 匹配结果列表
        for match in report.matches:
            status_name = _STATUS_NAMES.get(match.status, match.status.value)
            ref_text = match.ref_point.ref_text or "(目标)"
            target_label = match.target.label or match.target.number
            message = match.message or ""

            item = QTreeWidgetItem(self.match_tree, [
                status_name,
                ref_text,
                target_label,
                message,
            ])

            color = _STATUS_COLORS.get(match.status, QColor("#333"))
            item.setForeground(0, color)

    def _on_match_clicked(self, item: QTreeWidgetItem, column: int):
        """点击匹配结果时显示详情"""
        row = self.match_tree.indexOfTopLevelItem(item)
        if row < 0 or not self._report or row >= len(self._report.matches):
            return

        match = self._report.matches[row]
        lines = [
            f"<b>状态:</b> {_STATUS_NAMES.get(match.status, match.status.value)}",
            f"<b>引用文本:</b> {match.ref_point.ref_text or '无'}",
            f"<b>引用类型:</b> {_TYPE_NAMES.get(match.ref_point.target_type, '')}",
            f"<b>引用编号:</b> {match.ref_point.target_number}",
            f"<b>上下文:</b> {match.ref_point.context or '无'}",
            "",
            f"<b>目标标签:</b> {match.target.label}",
            f"<b>目标类型:</b> {_TYPE_NAMES.get(match.target.target_type, '')}",
            f"<b>目标编号:</b> {match.target.number}",
        ]
        if match.message:
            lines.append(f"<b>说明:</b> {match.message}")

        self.detail_view.setHtml("<br>".join(lines))
