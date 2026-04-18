"""
WordCraft Pro - 排版规则面板

模板选择、规则编辑、实时预览。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox,
    QLineEdit, QCheckBox, QPushButton, QTextEdit,
)
from PyQt6.QtCore import pyqtSignal

from core.formatting_rules import FormattingRules, StyleRules, PageRules
from core.template_manager import TemplateManager


class FormatPanel(QWidget):
    """排版规则面板"""

    rules_changed = pyqtSignal(object)  # FormattingRules

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_rules: Optional[FormattingRules] = None
        self._template_mgr = TemplateManager()
        self._setup_ui()
        self._load_template_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 模板选择
        template_group = QGroupBox("模板选择")
        template_layout = QHBoxLayout(template_group)

        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        template_layout.addWidget(self.template_combo, stretch=1)

        self.load_btn = QPushButton("加载模板")
        self.load_btn.clicked.connect(self._on_load_template)
        template_layout.addWidget(self.load_btn)

        layout.addWidget(template_group)

        # 页面设置
        page_group = QGroupBox("页面设置")
        page_form = QFormLayout(page_group)

        self.paper_size_combo = QComboBox()
        self.paper_size_combo.addItems(["A4", "A3", "B5", "Letter"])
        page_form.addRow("纸张大小:", self.paper_size_combo)

        self.margin_top_spin = QDoubleSpinBox()
        self.margin_top_spin.setRange(0, 10)
        self.margin_top_spin.setSuffix(" cm")
        self.margin_top_spin.setSingleStep(0.5)
        self.margin_top_spin.setValue(2.5)
        page_form.addRow("上边距:", self.margin_top_spin)

        self.margin_bottom_spin = QDoubleSpinBox()
        self.margin_bottom_spin.setRange(0, 10)
        self.margin_bottom_spin.setSuffix(" cm")
        self.margin_bottom_spin.setSingleStep(0.5)
        self.margin_bottom_spin.setValue(2.5)
        page_form.addRow("下边距:", self.margin_bottom_spin)

        self.margin_left_spin = QDoubleSpinBox()
        self.margin_left_spin.setRange(0, 10)
        self.margin_left_spin.setSuffix(" cm")
        self.margin_left_spin.setSingleStep(0.5)
        self.margin_left_spin.setValue(3.0)
        page_form.addRow("左边距:", self.margin_left_spin)

        self.margin_right_spin = QDoubleSpinBox()
        self.margin_right_spin.setRange(0, 10)
        self.margin_right_spin.setSuffix(" cm")
        self.margin_right_spin.setSingleStep(0.5)
        self.margin_right_spin.setValue(2.5)
        page_form.addRow("右边距:", self.margin_right_spin)

        layout.addWidget(page_group)

        # 标题样式
        heading_group = QGroupBox("标题样式")
        heading_form = QFormLayout(heading_group)

        self.h1_font_edit = QLineEdit()
        self.h1_font_edit.setPlaceholderText("如：黑体")
        self.h1_font_edit.setText("黑体")
        heading_form.addRow("一级标题字体:", self.h1_font_edit)

        self.h1_size_spin = QDoubleSpinBox()
        self.h1_size_spin.setRange(5, 72)
        self.h1_size_spin.setSuffix(" pt")
        self.h1_size_spin.setValue(16)
        heading_form.addRow("一级标题字号:", self.h1_size_spin)

        self.h2_font_edit = QLineEdit()
        self.h2_font_edit.setPlaceholderText("如：黑体")
        self.h2_font_edit.setText("黑体")
        heading_form.addRow("二级标题字体:", self.h2_font_edit)

        self.h2_size_spin = QDoubleSpinBox()
        self.h2_size_spin.setRange(5, 72)
        self.h2_size_spin.setSuffix(" pt")
        self.h2_size_spin.setValue(14)
        heading_form.addRow("二级标题字号:", self.h2_size_spin)

        layout.addWidget(heading_group)

        # 正文样式
        body_group = QGroupBox("正文样式")
        body_form = QFormLayout(body_group)

        self.body_font_edit = QLineEdit()
        self.body_font_edit.setPlaceholderText("如：宋体")
        self.body_font_edit.setText("宋体")
        body_form.addRow("正文字体:", self.body_font_edit)

        self.body_size_spin = QDoubleSpinBox()
        self.body_size_spin.setRange(5, 72)
        self.body_size_spin.setSuffix(" pt")
        self.body_size_spin.setValue(12)
        body_form.addRow("正文字号:", self.body_size_spin)

        # 中文号选择
        body_size_row = QHBoxLayout()
        self.body_cn_size_combo = QComboBox()
        self.body_cn_size_combo.addItem("-- pt --", None)
        cn_size_map = [
            ("一号 (26pt)", 26), ("小一 (24pt)", 24),
            ("二号 (22pt)", 22), ("小二 (18pt)", 18),
            ("三号 (16pt)", 16), ("小三 (15pt)", 15),
            ("四号 (14pt)", 14), ("小四 (12pt)", 12),
            ("五号 (10.5pt)", 10.5), ("小五 (9pt)", 9),
        ]
        for label, pt in cn_size_map:
            self.body_cn_size_combo.addItem(label, pt)
        self.body_cn_size_combo.currentIndexChanged.connect(self._on_cn_size_changed)
        body_size_row.addWidget(QLabel("中文号:"))
        body_size_row.addWidget(self.body_cn_size_combo, stretch=1)
        body_form.addRow(body_size_row)

        # 西文字体
        self.western_font_combo = QComboBox()
        self.western_font_combo.addItems([
            "Times New Roman", "Arial", "Calibri", "Cambria", "Georgia",
        ])
        self.western_font_combo.setCurrentText("Times New Roman")
        body_form.addRow("西文字体:", self.western_font_combo)

        self.body_indent_spin = QDoubleSpinBox()
        self.body_indent_spin.setRange(0, 10)
        self.body_indent_spin.setSuffix(" 字符")
        self.body_indent_spin.setSingleStep(0.5)
        self.body_indent_spin.setValue(2)
        body_form.addRow("首行缩进:", self.body_indent_spin)

        self.body_line_spin = QDoubleSpinBox()
        self.body_line_spin.setRange(1.0, 3.0)
        self.body_line_spin.setSingleStep(0.5)
        self.body_line_spin.setValue(1.5)
        body_form.addRow("行距倍数:", self.body_line_spin)

        # 对齐方式
        self.alignment_combo = QComboBox()
        self.alignment_combo.addItem("两端对齐", "justify")
        self.alignment_combo.addItem("左对齐", "left")
        self.alignment_combo.addItem("居中", "center")
        self.alignment_combo.addItem("右对齐", "right")
        self.alignment_combo.setCurrentText("两端对齐")
        body_form.addRow("对齐方式:", self.alignment_combo)

        layout.addWidget(body_group)

        # 应用按钮
        self.apply_btn = QPushButton("应用排版规则")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(self.apply_btn)

        layout.addStretch()

    def _load_template_list(self):
        """加载可用模板列表"""
        templates = self._template_mgr.list_templates()
        self.template_combo.clear()
        self.template_combo.addItem("-- 自定义 --")
        for t in templates:
            if isinstance(t, dict):
                self.template_combo.addItem(t["name"], userData=t)
            else:
                self.template_combo.addItem(str(t))

    def _on_template_changed(self, name: str):
        """模板选择变更"""
        pass  # 实际加载在 _on_load_template

    def _on_cn_size_changed(self, index: int):
        """中文号选择变更，同步到正文字号 SpinBox"""
        pt = self.body_cn_size_combo.itemData(index)
        if pt is not None:
            self.body_size_spin.setValue(pt)

    def _on_load_template(self):
        """加载选中的模板"""
        name = self.template_combo.currentText()
        if name == "-- 自定义 --":
            return

        rules = self._template_mgr.load_template(name)
        if rules:
            self.set_rules(rules)

    def set_rules(self, rules: FormattingRules):
        """设置排版规则并更新UI"""
        self._current_rules = rules

        # 页面设置
        if rules.page.paper_size:
            idx = self.paper_size_combo.findText(rules.page.paper_size)
            if idx >= 0:
                self.paper_size_combo.setCurrentIndex(idx)
        if rules.page.margin_top_cm:
            self.margin_top_spin.setValue(rules.page.margin_top_cm)
        if rules.page.margin_bottom_cm:
            self.margin_bottom_spin.setValue(rules.page.margin_bottom_cm)
        if rules.page.margin_left_cm:
            self.margin_left_spin.setValue(rules.page.margin_left_cm)
        if rules.page.margin_right_cm:
            self.margin_right_spin.setValue(rules.page.margin_right_cm)

        # 标题样式
        if rules.heading1:
            if rules.heading1.font_name_cn:
                self.h1_font_edit.setText(rules.heading1.font_name_cn)
            if rules.heading1.font_size_pt:
                self.h1_size_spin.setValue(rules.heading1.font_size_pt)
        if rules.heading2:
            if rules.heading2.font_name_cn:
                self.h2_font_edit.setText(rules.heading2.font_name_cn)
            if rules.heading2.font_size_pt:
                self.h2_size_spin.setValue(rules.heading2.font_size_pt)

        # 正文样式
        if rules.body:
            if rules.body.font_name_cn:
                self.body_font_edit.setText(rules.body.font_name_cn)
            if rules.body.font_size_pt:
                self.body_size_spin.setValue(rules.body.font_size_pt)
            if rules.body.first_indent_chars:
                self.body_indent_spin.setValue(rules.body.first_indent_chars)

    def get_rules(self) -> FormattingRules:
        """从UI获取当前排版规则"""
        rules = FormattingRules()

        # 页面设置
        rules.page.paper_size = self.paper_size_combo.currentText()
        rules.page.margin_top_cm = self.margin_top_spin.value()
        rules.page.margin_bottom_cm = self.margin_bottom_spin.value()
        rules.page.margin_left_cm = self.margin_left_spin.value()
        rules.page.margin_right_cm = self.margin_right_spin.value()

        # 标题样式
        if self.h1_font_edit.text():
            rules.heading1 = rules.heading1 or StyleRules()
            rules.heading1.font_name_cn = self.h1_font_edit.text()
            rules.heading1.font_size_pt = self.h1_size_spin.value()
            rules.heading1.bold = True

        if self.h2_font_edit.text():
            rules.heading2 = rules.heading2 or StyleRules()
            rules.heading2.font_name_cn = self.h2_font_edit.text()
            rules.heading2.font_size_pt = self.h2_size_spin.value()
            rules.heading2.bold = True

        # 正文样式
        if self.body_font_edit.text():
            rules.body = rules.body or StyleRules()
            rules.body.font_name_cn = self.body_font_edit.text()
            rules.body.font_size_pt = self.body_size_spin.value()
            rules.body.first_indent_chars = self.body_indent_spin.value()
            rules.body.font_name_en = self.western_font_combo.currentText()
            rules.body.alignment = self.alignment_combo.currentData()

        return rules

    def _on_apply(self):
        """应用按钮点击"""
        rules = self.get_rules()
        self._current_rules = rules
        self.rules_changed.emit(rules)
