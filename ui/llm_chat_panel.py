"""
WordCraft Pro - LLM 对话面板

提供自然语言输入界面，支持需求描述和智能交互。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from core.formatting_rules import FormattingRules


class NLParseWorker(QThread):
    """NL 解析工作线程"""

    finished = pyqtSignal(object)   # FormattingRules
    error = pyqtSignal(str)

    def __init__(self, parser, user_input: str):
        super().__init__()
        self._parser = parser
        self._user_input = user_input

    def run(self):
        try:
            rules = self._parser.parse(self._user_input)
            self.finished.emit(rules)
        except Exception as e:
            self.error.emit(str(e))


class LLMChatPanel(QWidget):
    """LLM 对话面板"""

    rules_generated = pyqtSignal(object)  # FormattingRules

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parser = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题
        title = QLabel("智能排版助手")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        # 使用说明
        hint = QLabel(
            "在下方输入您的排版需求（自然语言描述），AI 将自动解析为排版规则。\n"
            "例如：论文用A4纸，一级标题黑体三号居中，正文宋体小四号首行缩进2字符。"
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 输入区域
        input_group = QGroupBox("排版需求描述")
        input_layout = QVBoxLayout(input_group)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("请输入排版需求，例如：\n"
                                          "论文用A4纸，上下边距2.5cm，左右边距3cm。\n"
                                          "一级标题黑体三号居中加粗，正文宋体小四号首行缩进2字符，1.5倍行距。")
        self.input_edit.setMinimumHeight(120)
        input_layout.addWidget(self.input_edit)

        layout.addWidget(input_group)

        # 按钮栏
        btn_layout = QHBoxLayout()

        self.parse_btn = QPushButton("AI 解析排版规则")
        self.parse_btn.setObjectName("orangeBtn")
        self.parse_btn.clicked.connect(self._on_parse)
        btn_layout.addWidget(self.parse_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        # 结果区域
        result_group = QGroupBox("解析结果")
        result_layout = QVBoxLayout(result_group)

        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setMaximumHeight(200)
        self.result_edit.setObjectName("resultView")
        result_layout.addWidget(self.result_edit)

        layout.addWidget(result_group)

        # 快捷模板
        template_group = QGroupBox("快捷模板")
        template_layout = QVBoxLayout(template_group)

        self.template_combo = QComboBox()
        self.template_combo.addItem("-- 选择快捷模板 --")
        self.template_combo.addItem("学术论文（通用）")
        self.template_combo.addItem("政府公文")
        self.template_combo.addItem("实验报告")
        self.template_combo.addItem("毕业论文（海大模板）")
        self.template_combo.currentTextChanged.connect(self._on_template_selected)
        template_layout.addWidget(self.template_combo)

        layout.addWidget(template_group)

        layout.addStretch()

    def set_parser(self, parser):
        """设置 NL 解析器"""
        self._parser = parser

    def _on_parse(self):
        """解析按钮点击"""
        text = self.input_edit.toPlainText().strip()
        if not text:
            self.result_edit.setHtml("<i>请先输入排版需求</i>")
            return

        if self._parser is None:
            self.result_edit.setHtml("<i>LLM 未配置，请检查设置</i>")
            return

        self.parse_btn.setEnabled(False)
        self.parse_btn.setText("正在解析...")

        worker = NLParseWorker(self._parser, text)
        worker.finished.connect(self._on_parse_finished)
        worker.error.connect(self._on_parse_error)
        worker.start()

    def _on_parse_finished(self, rules: FormattingRules):
        """解析完成"""
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("AI 解析排版规则")

        # 显示结果
        yaml_text = rules.to_yaml()
        self.result_edit.setPlainText(yaml_text)

        # 发射信号
        self.rules_generated.emit(rules)

    def _on_parse_error(self, message: str):
        """解析出错"""
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("AI 解析排版规则")
        self.result_edit.setHtml(f"<span style='color:red'>解析失败: {message}</span>")

    def _on_clear(self):
        """清空"""
        self.input_edit.clear()
        self.result_edit.clear()

    def _on_template_selected(self, name: str):
        """快捷模板选择"""
        templates = {
            "学术论文（通用）": (
                "论文使用A4纸张，页边距上下2.5cm、左右3cm。"
                "一级标题黑体三号居中加粗，二级标题黑体四号加粗，三级标题黑体小四号加粗。"
                "正文宋体小四号（12pt），首行缩进2字符，1.5倍行距。"
                "图题表题黑体五号居中。"
            ),
            "政府公文": (
                "公文使用A4纸张，上边距3.7cm、下边距3.5cm、左边距2.8cm、右边距2.6cm。"
                "标题方正小标宋简体二号居中。"
                "正文仿宋GB2312三号，首行缩进2字符，行距固定值28磅。"
                "一级标题黑体三号，二级标题楷体三号加粗。"
            ),
            "实验报告": (
                "实验报告使用A4纸，页边距上下左右均为2.5cm。"
                "大标题黑体二号居中加粗。"
                "一级标题黑体四号加粗，正文宋体小四号首行缩进2字符。"
                "图表标题宋体五号居中加粗。"
            ),
            "毕业论文（海大模板）": (
                "广东海洋大学毕业论文，A4纸。"
                "章标题黑体三号居中加粗，节标题黑体四号加粗。"
                "正文宋体小四号首行缩进2字符，行距固定值20磅。"
                '页眉宋体五号居中，页码底部居中格式为"－ 1 －"。'
                "图题表题宋体五号居中。"
            ),
        }

        if name in templates:
            self.input_edit.setPlainText(templates[name])
