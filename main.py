"""
WordCraft Pro - 应用入口

智能Word排版桌面应用的主入口文件。
"""

import sys
import os


def main():
    """应用主入口"""
    # 确保项目根目录在 sys.path 中
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 启动模式
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "--test":
            os.system(f"{sys.executable} -m pytest tests/ -v")
        elif mode == "--demo":
            _run_demo()
        elif mode == "--gui":
            _launch_gui()
        else:
            print(f"未知参数: {mode}")
            _print_usage()
    else:
        # 默认启动 GUI
        _launch_gui()


def _launch_gui():
    """启动图形界面"""
    from ui.main_window import launch
    launch()


def _run_demo():
    """运行功能演示"""
    from core.document_model import (
        DocumentModel, DocElement, ElementType, FontStyle,
        ParagraphStyle, Alignment, LineSpacingType,
        PageSetup, SectionConfig, HeaderFooterConfig, PageNumberConfig,
        PageNumberFormat, TableData, TableCell
    )
    from core.formatting_rules import FormattingRules, StyleRules, PageRules

    print("=" * 60)
    print("  WordCraft Pro - 功能演示")
    print("=" * 60)

    doc = DocumentModel(
        title="WordCraft Pro 功能演示",
        author="系统",
        source_format="demo",
        page_setup=PageSetup(
            paper_size="A4",
            margin_top_cm=2.5, margin_bottom_cm=2.5,
            margin_left_cm=2.5, margin_right_cm=2.0,
        ),
    )

    doc.elements.append(DocElement(
        element_type=ElementType.HEADING,
        content="第一章 绪论",
        level=1,
        font_style=FontStyle(font_name_cn="黑体", font_size_pt=12, bold=True),
    ))

    doc.elements.append(DocElement(
        element_type=ElementType.PARAGRAPH,
        content="本文介绍了一种基于自然语言处理的智能排版方法。",
        font_style=FontStyle(font_name_cn="宋体", font_size_pt=10.5),
    ))

    rules = FormattingRules(
        template_name="演示模板",
        template_type="thesis",
        heading1=StyleRules(font_name_cn="黑体", font_size_pt=12, bold=True),
        body=StyleRules(font_name_cn="宋体", font_size_pt=10.5),
    )

    print(f"\n文档元素: {sum(doc.element_count().values())}")
    print(f"排版规则: {rules.template_name}")
    print("\n[OK] 演示完成")


def _print_usage():
    print("WordCraft Pro - 智能Word排版桌面应用")
    print("用法: python main.py [选项]")
    print("  (无参数)  启动图形界面")
    print("  --gui     启动图形界面")
    print("  --test    运行单元测试")
    print("  --demo    运行功能演示")


if __name__ == "__main__":
    main()
