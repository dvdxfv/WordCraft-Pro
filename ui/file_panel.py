"""
WordCraft Pro - 文件管理面板

支持拖拽上传、文件列表显示、解析触发。
"""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent


class FilePanel(QWidget):
    """文件管理面板"""

    file_selected = pyqtSignal(str)  # 发射选中的文件路径
    file_deleted = pyqtSignal(str)   # 发射被删除的文件路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[str] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 标题
        title = QLabel("文件管理")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        # 拖拽区域
        self.drop_label = QLabel("拖拽文件到此处，或点击下方按钮添加")
        self.drop_label.setObjectName("dropZone")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(60)
        self.drop_label.setAcceptDrops(True)
        layout.addWidget(self.drop_label)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.file_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.file_list)

        # 按钮栏
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("添加文件")
        self.add_btn.clicked.connect(self._on_add_file)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("移除")
        self.remove_btn.clicked.connect(self._on_remove_file)
        btn_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("删除选中")
        self.clear_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

    # ---- 拖拽支持 ----

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                self.add_file(path)

    # ---- 公共方法 ----

    def add_file(self, file_path: str):
        """添加文件到列表"""
        abs_path = os.path.abspath(file_path)
        if abs_path not in self._files:
            self._files.append(abs_path)
            item = QListWidgetItem(os.path.basename(abs_path))
            item.setToolTip(abs_path)
            self.file_list.addItem(item)

    def get_files(self) -> list[str]:
        """获取所有文件路径"""
        return self._files.copy()

    def get_current_file(self) -> Optional[str]:
        """获取当前选中的文件"""
        row = self.file_list.currentRow()
        if 0 <= row < len(self._files):
            return self._files[row]
        return None

    # ---- 事件处理 ----

    def _on_add_file(self):
        from PyQt6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "支持的格式 (*.docx *.doc *.pdf *.xlsx *.xls *.txt *.md);;所有文件 (*)",
        )
        for p in paths:
            self.add_file(p)

    def _on_remove_file(self):
        row = self.file_list.currentRow()
        if row >= 0:
            self.file_list.takeItem(row)
            self._files.pop(row)

    def delete_selected(self):
        """删除当前选中的文件并发射信号"""
        row = self.file_list.currentRow()
        if 0 <= row < len(self._files):
            removed_path = self._files.pop(row)
            self.file_list.takeItem(row)
            self.file_deleted.emit(removed_path)

    def _on_clear_files(self):
        self.file_list.clear()
        self._files.clear()

    def _on_item_double_clicked(self, item: QListWidgetItem):
        file_path = self._files[self.file_list.row(item)]
        self.file_selected.emit(file_path)
