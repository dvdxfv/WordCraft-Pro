"""
WordCraft Pro - 文档预览面板

树形展示文档结构，支持元素预览。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QTextEdit, QSplitter, QHeaderView,
)
from PyQt6.QtCore import Qt

from core.document_model import DocumentModel, DocElement, ElementType


# 元素类型中文映射
_TYPE_NAMES = {
    ElementType.HEADING: "标题",
    ElementType.PARAGRAPH: "段落",
    ElementType.TABLE: "表格",
    ElementType.LIST: "列表",
    ElementType.LIST_ITEM: "列表项",
    ElementType.IMAGE: "图片",
    ElementType.CODE_BLOCK: "代码块",
    ElementType.PAGE_BREAK: "分页符",
    ElementType.SECTION_BREAK: "分节符",
    ElementType.CAPTION: "题注",
    ElementType.EQUATION: "公式",
    ElementType.REFERENCE: "参考文献",
    ElementType.BOOKMARK: "书签",
    ElementType.CROSS_REF: "交叉引用",
}

_TYPE_ICONS = {
    ElementType.HEADING: "H",
    ElementType.PARAGRAPH: "P",
    ElementType.TABLE: "T",
    ElementType.CAPTION: "C",
    ElementType.REFERENCE: "R",
    ElementType.LIST: "L",
    ElementType.IMAGE: "I",
}


class PreviewPanel(QWidget):
    """文档预览面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document: Optional[DocumentModel] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 标题
        title = QLabel("文档结构")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        # 分割器：树形结构 + 详情预览
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 树形结构
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["类型", "内容预览"])
        self.tree.setColumnWidth(0, 80)
        self.tree.header().setStretchLastSection(True)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        splitter.addWidget(self.tree)

        # 详情预览
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMaximumHeight(200)
        self.detail_view.setObjectName("detailView")
        splitter.addWidget(self.detail_view)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def set_document(self, doc: DocumentModel):
        """设置文档并刷新树形结构"""
        self._document = doc
        self._refresh_tree()

    def _refresh_tree(self):
        """刷新树形结构"""
        self.tree.clear()

        if not self._document:
            return

        doc = self._document

        # 文档根节点
        root = QTreeWidgetItem(self.tree, ["文档", doc.title or "未命名"])
        root.setExpanded(True)

        # 元素节点
        for idx, elem in enumerate(doc.elements):
            type_name = _TYPE_NAMES.get(elem.element_type, elem.element_type.value)
            icon = _TYPE_ICONS.get(elem.element_type, "?")
            preview = (elem.content[:50] + "...") if len(elem.content) > 50 else elem.content

            item = QTreeWidgetItem(root, [f"[{icon}] {type_name}", preview])
            item.setData(0, Qt.ItemDataRole.UserRole, idx)

            # 标题层级信息
            if elem.element_type == ElementType.HEADING and elem.level:
                item.setData(0, Qt.ItemDataRole.UserRole + 1, elem.level)

        # 表格节点
        if doc.tables:
            tables_node = QTreeWidgetItem(root, ["表格", f"共 {len(doc.tables)} 个"])
            for idx, table in enumerate(doc.tables):
                caption = table.caption or f"表格 {idx + 1}"
                rows_info = f"{len(table.rows)} 行"
                QTreeWidgetItem(tables_node, ["表格", f"{caption} ({rows_info})"])

        self.tree.expandAll()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击树节点时显示详情"""
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        if idx is None or self._document is None:
            self.detail_view.clear()
            return

        if idx < 0 or idx >= len(self._document.elements):
            return

        elem = self._document.elements[idx]
        type_name = _TYPE_NAMES.get(elem.element_type, elem.element_type.value)

        # 构建详情文本
        lines = [
            f"<b>类型:</b> {type_name}",
            f"<b>层级:</b> {elem.level}" if elem.level else "",
            f"<b>样式名:</b> {elem.style_name}" if elem.style_name else "",
            f"<b>编号:</b> {elem.numbering_text}" if elem.numbering_text else "",
            "",
            "<b>内容:</b>",
            elem.content or "(空)",
        ]

        # 字体信息
        if elem.font_style:
            fs = elem.font_style
            font_info = []
            if fs.font_name_cn:
                font_info.append(f"中文字体: {fs.font_name_cn}")
            if fs.font_name_en:
                font_info.append(f"英文字体: {fs.font_name_en}")
            if fs.font_size_pt:
                font_info.append(f"字号: {fs.font_size_pt}pt")
            if fs.bold:
                font_info.append("加粗")
            if font_info:
                lines.insert(4, "")
                lines.insert(5, "<b>字体:</b> " + " | ".join(font_info))

        self.detail_view.setHtml("<br>".join(line for line in lines if line))
