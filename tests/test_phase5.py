"""
Phase 5 单元测试

测试交叉引用引擎：目标扫描、引用点扫描、匹配校验、域代码执行。
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import (
    DocumentModel, DocElement, ElementType, FontStyle, ParagraphStyle,
    Alignment,
)
from core.crossref_models import (
    RefTarget, RefPoint, CrossRefMatch, CrossRefReport,
    RefTargetType, CrossRefStatus,
)
from core.crossref_engine import (
    TargetScanner, RefPointScanner, CrossRefMatcher, CrossRefEngine,
)
from core.crossref_executor import CrossRefExecutor
from core.formatting_rules import CrossRefRules, FormattingRules, StyleRules
from core.exporter import Exporter


# ============================================================
# 辅助函数
# ============================================================

def _make_doc(*elements) -> DocumentModel:
    """快速创建文档模型"""
    doc = DocumentModel(title="测试文档")
    doc.elements.extend(elements)
    return doc


def _p(content: str, **kwargs) -> DocElement:
    """快速创建段落元素"""
    return DocElement(element_type=ElementType.PARAGRAPH, content=content, **kwargs)


def _h(content: str, level: int = 1, **kwargs) -> DocElement:
    """快速创建标题元素"""
    return DocElement(element_type=ElementType.HEADING, content=content, level=level, **kwargs)


def _cap(content: str, **kwargs) -> DocElement:
    """快速创建题注元素"""
    return DocElement(element_type=ElementType.CAPTION, content=content, **kwargs)


def _ref(content: str, **kwargs) -> DocElement:
    """快速创建参考文献元素"""
    return DocElement(element_type=ElementType.REFERENCE, content=content, **kwargs)


# ============================================================
# 测试数据模型
# ============================================================

class TestCrossRefModels:

    def test_ref_target_creation(self):
        t = RefTarget(
            target_type=RefTargetType.FIGURE,
            number="3-1",
            label="图3-1 实验结果",
            title="实验结果",
            element_index=5,
            chapter_num=3,
            seq_num=1,
            bookmark_name="_fig_3_1",
        )
        assert t.target_type == RefTargetType.FIGURE
        assert t.number == "3-1"
        assert t.bookmark_name == "_fig_3_1"

    def test_ref_target_serialization(self):
        t = RefTarget(
            target_type=RefTargetType.TABLE,
            number="2-1",
            label="表2-1 数据统计",
        )
        d = t.to_dict()
        assert d["target_type"] == "table"
        assert d["number"] == "2-1"

        restored = RefTarget.from_dict(d)
        assert restored.target_type == RefTargetType.TABLE
        assert restored.number == "2-1"

    def test_ref_point_creation(self):
        rp = RefPoint(
            ref_text="图3-1",
            target_type=RefTargetType.FIGURE,
            target_number="3-1",
            context="如图3-1所示",
            element_index=10,
        )
        assert rp.ref_text == "图3-1"
        assert rp.target_number == "3-1"

    def test_cross_ref_report(self):
        report = CrossRefReport()
        report.targets.append(RefTarget(
            target_type=RefTargetType.FIGURE, number="1-1", label="图1-1"
        ))
        report.targets.append(RefTarget(
            target_type=RefTargetType.TABLE, number="1-1", label="表1-1"
        ))
        assert report.target_count == 2
        assert len(report.get_targets_by_type(RefTargetType.FIGURE)) == 1

    def test_report_summary(self):
        report = CrossRefReport()
        text = report.summary_text()
        assert "交叉引用检查报告" in text
        assert "引用目标总数：0" in text


# ============================================================
# 测试目标扫描器
# ============================================================

class TestTargetScanner:

    def test_scan_figures(self):
        doc = _make_doc(
            _h("第三章 实验结果", level=1),
            _cap("图3-1 实验数据对比"),
            _cap("图3-2 误差分析"),
        )
        targets = TargetScanner().scan(doc)
        figures = [t for t in targets if t.target_type == RefTargetType.FIGURE]
        assert len(figures) == 2
        assert figures[0].number == "3-1"
        assert figures[0].chapter_num == 3
        assert figures[0].seq_num == 1
        assert figures[1].number == "3-2"

    def test_scan_tables(self):
        doc = _make_doc(
            _h("第二章 数据分析", level=1),
            _cap("表2-1 样本统计"),
            _cap("表2-2 回归结果"),
        )
        targets = TargetScanner().scan(doc)
        tables = [t for t in targets if t.target_type == RefTargetType.TABLE]
        assert len(tables) == 2
        assert tables[0].number == "2-1"
        assert tables[1].number == "2-2"

    def test_scan_equations(self):
        doc = _make_doc(
            _h("第二章 理论推导", level=1),
            _p("根据牛顿第二定律，F=ma (2-1)"),
            _p("代入数据可得 v=at (2-2)"),
        )
        targets = TargetScanner().scan(doc)
        equations = [t for t in targets if t.target_type == RefTargetType.EQUATION]
        assert len(equations) == 2
        assert equations[0].number == "2-1"
        assert equations[1].number == "2-2"

    def test_scan_chapters(self):
        doc = _make_doc(
            _h("第一章 绪论", level=1),
            _p("这是绪论内容。"),
            _h("第二章 文献综述", level=1),
            _p("这是综述内容。"),
            _h("第三章 研究方法", level=1),
        )
        targets = TargetScanner().scan(doc)
        chapters = [t for t in targets if t.target_type == RefTargetType.CHAPTER]
        assert len(chapters) == 3
        assert chapters[0].number == "1"
        assert chapters[0].title == "绪论"
        assert chapters[1].number == "2"
        assert chapters[2].number == "3"

    def test_scan_references(self):
        doc = _make_doc(
            _ref("[1] 张三, 李四. 某研究方法[J]. 期刊名, 2024."),
            _ref("[2] Wang J, et al. A method[J]. Journal, 2023."),
            _ref("[3] 刘五. 另一种方法[M]. 出版社, 2022."),
        )
        targets = TargetScanner().scan(doc)
        refs = [t for t in targets if t.target_type == RefTargetType.REFERENCE]
        assert len(refs) == 3
        assert refs[0].number == "1"
        assert refs[1].number == "2"
        assert refs[2].number == "3"

    def test_scan_mixed_targets(self):
        """混合目标扫描"""
        doc = _make_doc(
            _h("第一章 绪论", level=1),
            _p("背景介绍。"),
            _h("第二章 方法", level=1),
            _cap("图2-1 系统架构"),
            _p("核心公式如下：E=mc^2 (2-1)"),
            _cap("表2-1 参数设置"),
        )
        targets = TargetScanner().scan(doc)
        assert len([t for t in targets if t.target_type == RefTargetType.CHAPTER]) == 2
        assert len([t for t in targets if t.target_type == RefTargetType.FIGURE]) == 1
        assert len([t for t in targets if t.target_type == RefTargetType.TABLE]) == 1
        assert len([t for t in targets if t.target_type == RefTargetType.EQUATION]) == 1

    def test_bookmark_names(self):
        """书签名称生成"""
        doc = _make_doc(
            _h("第三章 实验", level=1),
            _cap("图3-1 结果"),
        )
        targets = TargetScanner().scan(doc)
        fig = [t for t in targets if t.target_type == RefTargetType.FIGURE][0]
        assert fig.bookmark_name == "_fig_3_1"
        ch = [t for t in targets if t.target_type == RefTargetType.CHAPTER][0]
        assert ch.bookmark_name == "_chapter_3"


# ============================================================
# 测试引用点扫描器
# ============================================================

class TestRefPointScanner:

    def test_scan_figure_refs(self):
        doc = _make_doc(
            _p("如图3-1所示，实验结果符合预期。"),
            _p("从图3-2可以看出，误差在可接受范围内。"),
        )
        refs = RefPointScanner().scan(doc)
        fig_refs = [r for r in refs if r.target_type == RefTargetType.FIGURE]
        assert len(fig_refs) == 2
        assert fig_refs[0].target_number == "3-1"
        assert fig_refs[1].target_number == "3-2"

    def test_scan_table_refs(self):
        doc = _make_doc(
            _p("如表2-1所示，数据呈现正态分布。"),
            _p("由表2-2可知，两组数据差异显著。"),
        )
        refs = RefPointScanner().scan(doc)
        tbl_refs = [r for r in refs if r.target_type == RefTargetType.TABLE]
        assert len(tbl_refs) == 2
        assert tbl_refs[0].target_number == "2-1"

    def test_scan_equation_refs(self):
        doc = _make_doc(
            _p("根据公式(2-1)可得以下结论。"),
            _p("将式3-1代入式3-2中。"),
        )
        refs = RefPointScanner().scan(doc)
        eq_refs = [r for r in refs if r.target_type == RefTargetType.EQUATION]
        assert len(eq_refs) >= 2

    def test_scan_chapter_refs(self):
        doc = _make_doc(
            _p("如第三章所述，本研究采用实验方法。"),
            _p("详见第二章文献综述部分。"),
        )
        refs = RefPointScanner().scan(doc)
        ch_refs = [r for r in refs if r.target_type == RefTargetType.CHAPTER]
        assert len(ch_refs) >= 2

    def test_scan_reference_refs(self):
        doc = _make_doc(
            _p("根据文献[1]的研究结果。"),
            _p("参考文献[2,3]表明该方法有效。"),
        )
        refs = RefPointScanner().scan(doc)
        # 单引用
        single_refs = [r for r in refs if r.target_type == RefTargetType.REFERENCE
                       and r.target_number == "1"]
        assert len(single_refs) >= 1

    def test_scan_multi_references(self):
        """多参考文献引用"""
        doc = _make_doc(
            _p("参考文献[1,3,5]表明该方法有效。"),
            _p("如文献[2，4]所示。"),
        )
        multi_refs = RefPointScanner().scan_multi_references(doc)
        assert len(multi_refs) == 5  # [1], [3], [5], [2], [4]
        numbers = [r.target_number for r in multi_refs]
        assert "1" in numbers
        assert "3" in numbers
        assert "5" in numbers
        assert "2" in numbers
        assert "4" in numbers

    def test_skip_heading_as_ref(self):
        """标题不应作为引用点"""
        doc = _make_doc(
            _h("图3-1 实验结果", level=2),  # 这是标题，不是引用
            _p("如图3-1所示。"),  # 这才是引用
        )
        refs = RefPointScanner().scan(doc)
        fig_refs = [r for r in refs if r.target_type == RefTargetType.FIGURE]
        assert len(fig_refs) == 1
        assert fig_refs[0].element_index == 1  # 第二个元素


# ============================================================
# 测试匹配与校验器
# ============================================================

class TestCrossRefMatcher:

    def test_valid_match(self):
        targets = [
            RefTarget(target_type=RefTargetType.FIGURE, number="3-1",
                      label="图3-1 实验结果"),
        ]
        ref_points = [
            RefPoint(ref_text="图3-1", target_type=RefTargetType.FIGURE,
                     target_number="3-1"),
        ]
        report = CrossRefMatcher().match(targets, ref_points)
        assert report.valid_count == 1
        assert report.dangling_count == 0

    def test_dangling_ref(self):
        """悬空引用"""
        targets = [
            RefTarget(target_type=RefTargetType.FIGURE, number="3-1",
                      label="图3-1 实验结果"),
        ]
        ref_points = [
            RefPoint(ref_text="图3-2", target_type=RefTargetType.FIGURE,
                     target_number="3-2"),  # 不存在
        ]
        report = CrossRefMatcher().match(targets, ref_points)
        assert report.dangling_count == 1
        assert report.valid_count == 0

    def test_unreferenced_target(self):
        """未被引用的目标"""
        targets = [
            RefTarget(target_type=RefTargetType.TABLE, number="2-1",
                      label="表2-1 数据"),
            RefTarget(target_type=RefTargetType.TABLE, number="2-2",
                      label="表2-2 结果"),
        ]
        ref_points = [
            RefPoint(ref_text="表2-1", target_type=RefTargetType.TABLE,
                     target_number="2-1"),
        ]
        report = CrossRefMatcher().match(targets, ref_points)
        assert report.unreferenced_count == 1
        assert report.valid_count == 1

    def test_duplicate_targets(self):
        """重复编号"""
        targets = [
            RefTarget(target_type=RefTargetType.FIGURE, number="3-1",
                      label="图3-1 结果A", element_index=5),
            RefTarget(target_type=RefTargetType.FIGURE, number="3-1",
                      label="图3-1 结果B", element_index=10),
        ]
        report = CrossRefMatcher().match(targets, [])
        # 应该有 1 个重复报告
        dup_matches = [m for m in report.matches
                       if m.status == CrossRefStatus.DUPLICATE]
        assert len(dup_matches) == 1

    def test_mixed_types_no_cross_match(self):
        """不同类型不交叉匹配"""
        targets = [
            RefTarget(target_type=RefTargetType.FIGURE, number="2-1",
                      label="图2-1"),
        ]
        ref_points = [
            RefPoint(ref_text="表2-1", target_type=RefTargetType.TABLE,
                     target_number="2-1"),
        ]
        report = CrossRefMatcher().match(targets, ref_points)
        assert report.dangling_count == 1  # 表2-1 找不到目标


# ============================================================
# 测试交叉引用引擎（完整流程）
# ============================================================

class TestCrossRefEngine:

    def test_full_check_valid(self):
        """完整检查 — 全部有效"""
        doc = _make_doc(
            _h("第三章 实验结果", level=1),
            _cap("图3-1 实验数据对比"),
            _p("如图3-1所示，实验结果符合预期。"),
        )
        rules = CrossRefRules(enabled=True)
        report = CrossRefEngine(rules).check(doc)
        assert report.target_count >= 2  # 章节 + 图
        assert report.ref_point_count >= 1
        assert report.valid_count >= 1

    def test_full_check_with_dangling(self):
        """完整检查 — 含悬空引用"""
        doc = _make_doc(
            _h("第三章 实验结果", level=1),
            _cap("图3-1 实验数据对比"),
            _p("如图3-2所示，实验结果符合预期。"),  # 3-2 不存在
        )
        rules = CrossRefRules(enabled=True)
        report = CrossRefEngine(rules).check(doc)
        assert report.dangling_count >= 1

    def test_full_check_complex(self):
        """复杂文档检查"""
        doc = _make_doc(
            _h("第一章 绪论", level=1),
            _p("如第二章所述，本研究具有重要意义。"),
            _h("第二章 文献综述", level=1),
            _p("根据文献[1]的研究。"),
            _p("参考文献[2,3]表明。"),
            _cap("图2-1 相关研究趋势"),
            _p("由图2-1可知趋势明显。"),
            _cap("表2-1 数据汇总"),
            _p("核心公式：y=ax+b (2-1)"),
            _p("根据公式(2-1)可推导。"),
            _ref("[1] 张三. 研究方法[J]. 期刊, 2024."),
            _ref("[2] 李四. 另一种方法[J]. 期刊, 2023."),
            _ref("[3] 王五. 第三种方法[J]. 期刊, 2022."),
        )
        rules = CrossRefRules(enabled=True)
        report = CrossRefEngine(rules).check(doc)
        assert report.target_count >= 6
        assert report.ref_point_count >= 5
        assert report.valid_count >= 3

    def test_disabled_rules(self):
        """禁用时返回空报告"""
        doc = _make_doc(
            _h("第三章 实验", level=1),
            _cap("图3-1 结果"),
            _p("如图3-1所示。"),
        )
        rules = CrossRefRules(enabled=False)
        report = CrossRefEngine(rules).check(doc)
        assert report.target_count == 0
        assert report.ref_point_count == 0

    def test_interactive_suggestions(self):
        """交互建议生成"""
        doc = _make_doc(
            _h("第三章 实验", level=1),
            _cap("图3-1 结果"),
            _p("如图3-2所示。"),  # 悬空
            _cap("图3-3 未引用"),  # 未引用
        )
        rules = CrossRefRules(enabled=True)
        report = CrossRefEngine(rules).check(doc)
        suggestions = CrossRefEngine(rules).get_interactive_suggestions(report)
        assert len(suggestions) >= 2
        types = [s["type"] for s in suggestions]
        assert "dangling" in types
        assert "unreferenced" in types

    def test_report_summary(self):
        """报告摘要"""
        doc = _make_doc(
            _h("第三章 实验", level=1),
            _cap("图3-1 结果"),
            _p("如图3-1所示。"),
        )
        rules = CrossRefRules(enabled=True)
        report = CrossRefEngine(rules).check(doc)
        text = report.summary_text()
        assert "交叉引用检查报告" in text
        assert "图" in text


# ============================================================
# 测试端到端（含导出）
# ============================================================

class TestCrossRefEndToEnd:

    def test_export_with_crossref(self):
        """导出含交叉引用的文档"""
        doc = _make_doc(
            _h("第三章 实验结果", level=1),
            _cap("图3-1 实验数据对比"),
            _p("如图3-1所示，实验结果符合预期。"),
        )

        # 交叉引用检查
        rules = CrossRefRules(enabled=True)
        report = CrossRefEngine(rules).check(doc)

        # 导出
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            Exporter().export(doc, path, crossref_report=report)
            assert os.path.isfile(path)
            assert os.path.getsize(path) > 500
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_full_pipeline_with_crossref(self):
        """完整管线：解析 → 交叉引用 → 排版 → 导出"""
        from parsers.dispatcher import parse_file

        # 创建测试 TXT
        fd, txt_path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("第三章 实验结果\n\n")
                f.write("图3-1 实验数据对比\n\n")
                f.write("如图3-1所示，实验结果符合预期。\n\n")
                f.write("表3-1 参数设置\n\n")
                f.write("如表3-1所示，参数设置合理。\n\n")
                f.write("核心公式如下：E=mc^2 (3-1)\n\n")
                f.write("根据公式(3-1)可得结论。\n\n")

            # 1. 解析
            doc = parse_file(txt_path)
            assert doc.source_format == "txt"

            # 2. 交叉引用检查
            rules = CrossRefRules(enabled=True)
            report = CrossRefEngine(rules).check(doc)
            assert report.target_count >= 1
            assert report.ref_point_count >= 1

            # 3. 排版
            from core.formatter import Formatter
            from core.formatting_rules import FormattingRules, StyleRules
            fmt_rules = FormattingRules(
                heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True),
                body=StyleRules(font_name_cn="宋体", font_size_pt=12),
            )
            formatted = Formatter(fmt_rules).apply(doc)

            # 4. 导出
            fd2, docx_path = tempfile.mkstemp(suffix=".docx")
            os.close(fd2)
            try:
                Exporter().export(formatted, docx_path, crossref_report=report)
                assert os.path.isfile(docx_path)
                assert os.path.getsize(docx_path) > 1000
            finally:
                if os.path.exists(docx_path):
                    os.unlink(docx_path)
        finally:
            if os.path.exists(txt_path):
                os.unlink(txt_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
