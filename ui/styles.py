"""
WordCraft Pro - 全局样式表

设计风格：浅色专业主题，与网页版保持一致。
苹果风格配色，干净克制的视觉语言。
"""

# ============================================================
# 全局 QSS 样式表
# ============================================================

QSS_STYLE = """
/* ========================================
   CSS 变量（通过 QSS 属性模拟）
   主背景: #f5f5f7
   面板/卡片: #ffffff
   输入框: #ffffff, 边框 #d1d1d6
   边框: #d1d1d6 / #e5e5ea
   主文字: #1d1d1f
   次文字: #86868b
   占位文字: #aeaeb2
   强调: #0071e3 (苹果蓝)
   强调悬停: #0077ED
   成功: #34C759
   错误: #FF3B30
   警告: #FF6B35
   信息: #0071e3
   选中/活跃: #e8f0fe
   ======================================== */

/* ---- 全局 ---- */
QWidget {
    background-color: #f5f5f7;
    color: #1d1d1f;
    font-family: -apple-system, "SF Pro Display", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 13px;
    selection-background-color: #e8f0fe;
    selection-color: #0071e3;
}

/* ---- 主窗口 ---- */
QMainWindow {
    background-color: #f5f5f7;
}

/* ---- 菜单栏 ---- */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e5ea;
    padding: 2px 8px;
    font-size: 13px;
}

QMenuBar::item {
    padding: 6px 16px;
    border-radius: 4px;
    background: transparent;
    color: #1d1d1f;
}

QMenuBar::item:selected {
    background-color: #f5f5f7;
    color: #1d1d1f;
}

/* ---- 下拉菜单 ---- */
QMenu {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 12px;
    border-radius: 4px;
    color: #1d1d1f;
}

QMenu::item:selected {
    background-color: #f5f5f7;
    color: #1d1d1f;
}

QMenu::separator {
    height: 1px;
    background: #e5e5ea;
    margin: 4px 8px;
}

/* ---- 工具栏 ---- */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e5ea;
    padding: 4px 8px;
    spacing: 2px;
}

QToolBar QToolButton {
    background-color: transparent;
    color: #1d1d1f;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
}

QToolBar QToolButton:hover {
    background-color: #f5f5f7;
    color: #1d1d1f;
}

QToolBar QToolButton:pressed {
    background-color: #e8e8ed;
    color: #1d1d1f;
}

QToolBar QToolButton:checked {
    background-color: #e8f0fe;
    color: #0071e3;
}

/* ---- 状态栏 ---- */
QStatusBar {
    background-color: #f5f5f7;
    border-top: 1px solid #e5e5ea;
    color: #86868b;
    font-size: 11px;
    padding: 2px 8px;
}

QStatusBar::item {
    border: none;
}

/* ---- 选项卡 ---- */
QTabWidget::pane {
    border: none;
    background-color: transparent;
}

QTabBar {
    background-color: transparent;
}

QTabBar::tab {
    background-color: transparent;
    color: #86868b;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    margin-right: 2px;
}

QTabBar::tab:hover {
    color: #1d1d1f;
}

QTabBar::tab:selected {
    color: #0071e3;
    border-bottom: 2px solid #0071e3;
    font-weight: bold;
}

/* ---- 分割器 ---- */
QSplitter::handle:horizontal {
    width: 1px;
    background-color: #e5e5ea;
}

QSplitter::handle:vertical {
    height: 1px;
    background-color: #e5e5ea;
}

/* ---- 分组框 ---- */
QGroupBox {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-size: 12px;
    font-weight: bold;
    color: #1d1d1f;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #1d1d1f;
    font-size: 12px;
    font-weight: bold;
    padding-bottom: 6px;
}

/* ---- 面板容器 ---- */
QWidget#panelContainer {
    background-color: #ffffff;
}

/* ---- 输入框 ---- */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 5px 10px;
    color: #1d1d1f;
    font-size: 13px;
    selection-background-color: #e8f0fe;
    selection-color: #0071e3;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #0071e3;
}

/* ---- 文本编辑区 ---- */
QTextEdit {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 5px 10px;
    color: #1d1d1f;
    font-size: 13px;
    outline: none;
    selection-background-color: #e8f0fe;
    selection-color: #0071e3;
}

QTextEdit:focus {
    border: 2px solid #0071e3;
}

/* ---- 下拉框 ---- */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 5px 10px;
    color: #1d1d1f;
    font-size: 13px;
    min-height: 28px;
}

QComboBox:hover {
    border-color: #b0b0b6;
}

QComboBox:focus {
    border: 2px solid #0071e3;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #86868b;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    color: #1d1d1f;
    selection-background-color: #e8f0fe;
    selection-color: #0071e3;
    padding: 4px;
    outline: none;
}

/* ---- 按钮（基础） ---- */
QPushButton {
    background-color: #f5f5f7;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    color: #1d1d1f;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #e8e8ed;
}

QPushButton:pressed {
    background-color: #d1d1d6;
}

QPushButton:disabled {
    background-color: #f5f5f7;
    color: #aeaeb2;
}

/* ---- 列表 ---- */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    font-size: 13px;
    color: #1d1d1f;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    color: #1d1d1f;
}

QListWidget::item:hover {
    background-color: #f5f5f7;
}

QListWidget::item:selected {
    background-color: #e8f0fe;
    color: #0071e3;
}

QListWidget::item:selected:hover {
    background-color: #d1e4ff;
    color: #0071e3;
}

/* ---- 树形控件 ---- */
QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    font-size: 13px;
    color: #1d1d1f;
    alternate-background-color: #fafafa;
}

QTreeWidget::item {
    padding: 4px 8px;
    border-radius: 4px;
    color: #1d1d1f;
}

QTreeWidget::item:hover {
    background-color: #f5f5f7;
}

QTreeWidget::item:selected {
    background-color: #e8f0fe;
    color: #0071e3;
}

QHeaderView::section {
    background-color: #f5f5f7;
    color: #86868b;
    border: none;
    border-bottom: 1px solid #e5e5ea;
    border-right: 1px solid #e5e5ea;
    padding: 6px 8px;
    font-size: 12px;
    font-weight: 600;
}

/* ---- 滚动条 ---- */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #c7c7cc;
    border-radius: 3px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #a1a1a6;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    border-radius: 3px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #c7c7cc;
    border-radius: 3px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background: #a1a1a6;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ---- 对话框 ---- */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #1d1d1f;
    font-size: 14px;
}

QMessageBox QPushButton {
    min-width: 80px;
}

QFileDialog {
    background-color: #ffffff;
}

/* ---- 工具提示 ---- */
QToolTip {
    background-color: #1d1d1f;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}

/* ---- 进度条 ---- */
QProgressBar {
    background-color: #e5e5ea;
    border: none;
    border-radius: 3px;
    height: 4px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #0071e3;
    border-radius: 3px;
}

/* ========================================
   ObjectName 选择器（组件级样式）
   ======================================== */

/* ---- 面板标题 ---- */
QLabel#panelTitle {
    font-size: 13px;
    font-weight: bold;
    color: #1d1d1f;
    padding: 6px 0px 2px 0px;
}

/* ---- 辅助文字 ---- */
QLabel#summaryLabel {
    color: #86868b;
    font-size: 12px;
    padding: 6px 8px;
    background-color: #f5f5f7;
    border-radius: 4px;
}

QLabel#hintLabel {
    color: #86868b;
    font-size: 12px;
    padding: 4px 0px;
    line-height: 1.5;
}

/* ---- 拖拽区域 ---- */
QLabel#dropZone {
    border: 2px dashed #d1d1d6;
    border-radius: 12px;
    background-color: transparent;
    color: #aeaeb2;
    padding: 24px;
    font-size: 13px;
    qproperty-alignment: AlignCenter;
}

QLabel#dropZone:hover {
    border-color: #0071e3;
    color: #0071e3;
    background-color: #e8f0fe;
}

/* ---- 详情视图 ---- */
QTextEdit#detailView {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    padding: 10px;
    color: #1d1d1f;
    font-size: 12px;
}

/* ---- 结果视图 ---- */
QTextEdit#resultView {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    padding: 10px;
    color: #1d1d1f;
    font-size: 12px;
    font-family: "Consolas", "SF Mono", "PingFang SC", "Microsoft YaHei", monospace;
}

/* ---- 主操作按钮（苹果蓝） ---- */
QPushButton#primaryBtn {
    background-color: #0071e3;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#primaryBtn:hover {
    background-color: #0077ED;
}

QPushButton#primaryBtn:pressed {
    background-color: #0062c4;
}

QPushButton#primaryBtn:disabled {
    background-color: #f5f5f7;
    color: #aeaeb2;
}

/* ---- 强调按钮（浅蓝底） ---- */
QPushButton#accentBtn {
    background-color: #e8f0fe;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    color: #0071e3;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#accentBtn:hover {
    background-color: #d1e4ff;
}

QPushButton#accentBtn:pressed {
    background-color: #b8d4f8;
}

/* ---- 紫色按钮 ---- */
QPushButton#purpleBtn {
    background-color: #f3e8ff;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    color: #8b5cf6;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#purpleBtn:hover {
    background-color: #e9d5ff;
}

QPushButton#purpleBtn:pressed {
    background-color: #d8b4fe;
}

/* ---- 橙色按钮 ---- */
QPushButton#orangeBtn {
    background-color: #fff3e0;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    color: #FF6B35;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#orangeBtn:hover {
    background-color: #ffe0b2;
}

QPushButton#orangeBtn:pressed {
    background-color: #ffcc80;
}
"""
