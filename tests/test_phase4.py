"""
Phase 4 单元测试

测试质量检查引擎：错别字、数据一致性、逻辑检查。
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import (
    DocumentModel, DocElement, ElementType, FontStyle, ParagraphStyle,
    Alignment, PageSetup, SectionConfig, HeaderFooterConfig, PageNumberConfig, PageNumberFormat,
    TableData, TableCell,
)
from core.qa_models import QAIssue, QAReport, IssueCategory, IssueSeverity, IssueStatus
from core.typo_checker import TypoChecker
from core.consistency_checker import ConsistencyChecker
from core.logic_checker import LogicChecker
from core.qa_engine import QAEngine
from core.formatter import Formatter
from core.exporter import Exporter
from core.formatting_rules import FormattingRules, StyleRules, PageRules


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


# ============================================================
# 测试 QA 结果模型
# ============================================================

class TestQAModels:

    def test_create_issue(self):
        issue = QAIssue(
            category=IssueCategory.TYPO,
            severity=IssueSeverity.WARNING,
            title="测试问题",
            description="测试描述",
            suggestion="修改建议",
            confidence=0.8,
        )
        assert issue.category == IssueCategory.TYPO
        assert issue.severity == IssueSeverity.WARNING
        assert issue.status == IssueStatus.PENDING

    def test_issue_serialization(self):
        issue = QAIssue(
            category=IssueCategory.INCONSISTENCY,
            severity=IssueSeverity.ERROR,
            title="数据不一致",
            confidence=0.9,
        )
        d = issue.to_dict()
        assert d["category"] == "inconsistency"
        assert d["severity"] == "error"

        restored = QAIssue.from_dict(d)
        assert restored.category == IssueCategory.INCONSISTENCY
        assert restored.confidence == 0.9

    def test_qa_report(self):
        report = QAReport()
        report.add_issue(QAIssue(category=IssueCategory.TYPO, severity=IssueSeverity.ERROR))
        report.add_issue(QAIssue(category=IssueCategory.TYPO, severity=IssueSeverity.WARNING))
        report.add_issue(QAIssue(category=IssueCategory.INCONSISTENCY, severity=IssueSeverity.WARNING))
        report.add_issue(QAIssue(category=IssueCategory.LOGIC, severity=IssueSeverity.INFO))

        assert report.total == 4
        assert report.error_count == 1
        assert report.warning_count == 2
        assert report.info_count == 1
        assert report.typo_count == 2
        assert report.inconsistency_count == 1
        assert report.logic_count == 1

    def test_report_filter(self):
        report = QAReport()
        report.add_issue(QAIssue(category=IssueCategory.TYPO, severity=IssueSeverity.ERROR))
        report.add_issue(QAIssue(category=IssueCategory.LOGIC, severity=IssueSeverity.INFO))

        typos = report.get_issues_by_category(IssueCategory.TYPO)
        assert len(typos) == 1

        errors = report.get_issues_by_severity(IssueSeverity.ERROR)
        assert len(errors) == 1

    def test_report_summary(self):
        report = QAReport()
        report.add_issue(QAIssue(category=IssueCategory.TYPO, severity=IssueSeverity.WARNING))
        text = report.summary_text()
        assert "1" in text
        assert "错别字" in text


# ============================================================
# 测试错别字检查器
# ============================================================

class TestTypoChecker:

    def test_detect_common_typo(self):
        doc = _make_doc(_p("请输入正确的帐号和密码"))
        report = TypoChecker().check(doc)
        assert report.total >= 1
        assert any("帐号" in i.title or "账号" in i.suggestion for i in report.issues)

    def test_detect_multiple_typos(self):
        doc = _make_doc(
            _p("既使遇到了困难，也要按装好设备。"),
        )
        report = TypoChecker().check(doc)
        # 应该检测到"既使"和"按装"
        assert report.total >= 2

    def test_no_false_positive(self):
        doc = _make_doc(_p("这是一个正常的段落，没有错别字。"))
        report = TypoChecker().check(doc)
        # 正确文本不应产生高置信度问题
        high_confidence = [i for i in report.issues if i.confidence >= 0.7]
        assert len(high_confidence) == 0

    def test_de_di_de_check(self):
        doc = _make_doc(_p("他认真的完成了任务"))
        report = TypoChecker().check(doc)
        # "认真的完成" 可能应改为 "认真地完成"
        de_issues = [i for i in report.issues if "的地得" in i.title]
        assert len(de_issues) >= 1

    def test_skip_de_di_de_for_valid_usage(self):
        doc = _make_doc(_p("这是我的目的，我要实现它"))
        report = TypoChecker().check(doc)
        # "我的目的" 是正确用法，不应报错
        de_issues = [i for i in report.issues if "目的" in i.location_text]
        assert len(de_issues) == 0


# ============================================================
# 测试数据一致性检查器
# ============================================================

class TestConsistencyChecker:

    def test_number_format_inconsistency(self):
        doc = _make_doc(
            _p("项目总投资为 1,000 万元"),
            _p("第二期投资为1000万元"),
        )
        report = ConsistencyChecker().check(doc)
        assert report.total >= 1
        assert any("数字格式不一致" in i.title for i in report.issues)

    def test_consistent_numbers(self):
        doc = _make_doc(
            _p("投资金额为 1,000 万元"),
            _p("回报率为 1,000 万元"),
        )
        report = ConsistencyChecker().check(doc)
        # 相同格式不应报错
        format_issues = [i for i in report.issues if "格式不一致" in i.title]
        assert len(format_issues) == 0

    def test_date_format_inconsistency(self):
        doc = _make_doc(
            _p("报告日期为 2024年3月15日"),
            _p("截止日期为 2024-03-15"),
        )
        report = ConsistencyChecker().check(doc)
        assert report.total >= 1
        assert any("日期格式不一致" in i.title for i in report.issues)

    def test_proper_noun_similarity(self):
        doc = _make_doc(
            _p("本项目由清华大学负责"),
            _p("清华太学提供了技术支持"),
            _p("北京研究院承担了开发工作"),
            _p("北京究研院负责测试"),
        )
        report = ConsistencyChecker().check(doc)
        assert report.total >= 1
        assert any("专有名词" in i.title for i in report.issues)

    def test_edit_distance(self):
        assert ConsistencyChecker._edit_distance("abc", "abc") == 0
        assert ConsistencyChecker._edit_distance("abc", "abd") == 1
        assert ConsistencyChecker._edit_distance("abc", "axc") == 1
        assert ConsistencyChecker._edit_distance("kitten", "sitting") == 3


# ============================================================
# 测试逻辑检查器
# ============================================================

class TestLogicChecker:

    def test_empty_section(self):
        doc = _make_doc(
            _h("第三章 研究方法", level=1),
            _h("第四章 结果分析", level=1),
        )
        report = LogicChecker().check(doc)
        assert report.total >= 1
        assert any("内容为空" in i.title for i in report.issues)

    def test_non_empty_section(self):
        doc = _make_doc(
            _h("第三章 研究方法", level=1),
            _p("本章介绍了研究方法。"),
            _h("第四章 结果分析", level=1),
        )
        report = LogicChecker().check(doc)
        empty_issues = [i for i in report.issues if "内容为空" in i.title]
        assert len(empty_issues) == 0

    def test_contradiction_detection(self):
        doc = _make_doc(
            _p("实验结果显著增加，但是最终数据却减少了"),
        )
        report = LogicChecker().check(doc)
        assert any("矛盾" in i.title for i in report.issues)

    def test_timeline_check(self):
        doc = _make_doc(
            _p("项目于2023年启动"),
            _p("经过一年发展"),
            _p("在2020年取得了重大突破"),
        )
        report = LogicChecker().check(doc)
        assert any("时间线" in i.title for i in report.issues)

    def test_conclusion_without_data(self):
        doc = _make_doc(
            _p("综上所述，本项目取得了良好的效果。"),
        )
        report = LogicChecker().check(doc)
        assert any("数据支撑" in i.title for i in report.issues)

    def test_conclusion_with_data(self):
        doc = _make_doc(
            _p("综上所述，实验数据显示准确率提升了15.3%。"),
        )
        report = LogicChecker().check(doc)
        data_issues = [i for i in report.issues if "数据支撑" in i.title]
        assert len(data_issues) == 0


# ============================================================
# 测试 QA 引擎
# ============================================================

class TestQAEngine:

    def test_full_check(self):
        doc = _make_doc(
            _h("第一章 绪论", level=1),
            _p("本项目由清华大学负责，资金为 1,000 万元。"),
            _p("清华太学提供了技术支持，资金为1000万元。"),
            _h("第二章 方法", level=1),
            _p("请输入正确的帐号进行登录。"),
        )
        engine = QAEngine()
        report = engine.check(doc)

        # 应该检测到多种问题
        assert report.total >= 1  # 至少有错别字
        assert report.typo_count >= 1
        assert report.inconsistency_count >= 1

    def test_partial_check(self):
        doc = _make_doc(
            _p("请输入正确的帐号进行登录。"),
            _p("清华太学提供了技术支持。"),
        )
        engine = QAEngine()
        report = engine.check(doc, categories=["typo"])
        assert report.typo_count >= 1
        assert report.inconsistency_count == 0

    def test_check_typo_only(self):
        doc = _make_doc(_p("既使困难也要坚持。"))
        report = QAEngine().check_typo_only(doc)
        assert report.typo_count >= 1

    def test_empty_document(self):
        doc = DocumentModel()
        report = QAEngine().check(doc)
        assert report.total == 0


# ============================================================
# 测试 QA + 排版 + 导出 端到端
# ============================================================

class TestQAEndToEnd:

    def test_qa_then_export(self):
        """QA检查 → 排版 → 导出（含批注）"""
        doc = _make_doc(
            _h("第一章 绪论", level=1),
            _p("本项目由清华大学负责。"),
            _p("清华太学提供了技术支持。"),
            _p("请输入正确的帐号进行登录。"),
            _h("第二章 方法", level=1),  # 空章节
        )

        # 1. QA 检查
        engine = QAEngine()
        report = engine.check(doc)
        assert report.total >= 1

        # 2. 排版
        rules = FormattingRules(
            heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True),
            body=StyleRules(font_name_cn="宋体", font_size_pt=12),
        )
        formatted = Formatter(rules).apply(doc)

        # 3. 导出（含批注）
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            Exporter().export(formatted, path, qa_report=report)
            assert os.path.isfile(path)
            assert os.path.getsize(path) > 1000
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_full_pipeline_qa_format_export(self):
        """完整管线：解析 → QA → 排版 → 导出"""
        from parsers.dispatcher import parse_file

        # 创建测试 TXT 文件
        import tempfile
        fd, txt_path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("项目概况\n\n本项目由北京大学负责。\n\n")
                f.write("北京太学提供了技术支持。\n\n")
                f.write("投资金额为 1,000 万元。\n\n")
                f.write("第二期投资为1000万元。\n\n")
                f.write("请输入正确的帐号。\n\n")
                f.write("第三章 结论\n\n第四章 总结\n")

            # 1. 解析
            doc = parse_file(txt_path)
            assert doc.source_format == "txt"

            # 2. QA 检查
            report = QAEngine().check(doc)
            assert report.total >= 2

            # 3. 排版
            rules = FormattingRules(
                heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True),
                body=StyleRules(font_name_cn="宋体", font_size_pt=12),
            )
            formatted = Formatter(rules).apply(doc)

            # 4. 导出
            fd2, docx_path = tempfile.mkstemp(suffix=".docx")
            os.close(fd2)
            try:
                Exporter().export(formatted, docx_path, qa_report=report)
                assert os.path.isfile(docx_path)

                # 5. 重新解析验证
                reparsed = parse_file(docx_path)
                text = reparsed.get_all_text()
                assert "北京大学" in text or "项目" in text
            finally:
                if os.path.exists(docx_path):
                    os.unlink(docx_path)
        finally:
            if os.path.exists(txt_path):
                os.unlink(txt_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
