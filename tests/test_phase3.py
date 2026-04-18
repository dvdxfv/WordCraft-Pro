"""
Phase 3 单元测试

测试规则标准化、模板解析、排版引擎、导出引擎、模板管理器。
包含端到端验证：解析文件 → 提取规则 → 应用排版 → 导出 .docx。
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import (
    DocumentModel, DocElement, ElementType, FontStyle, ParagraphStyle,
    Alignment, LineSpacingType, TableData, TableCell,
    PageSetup, SectionConfig, HeaderFooterConfig, PageNumberConfig, PageNumberFormat,
)
from core.formatting_rules import FormattingRules, StyleRules, PageRules
from core.template_parser.rule_normalizer import RuleNormalizer
from core.template_parser.text_rule_parser import TextRuleParser
from core.template_parser.docx_style_parser import DocxStyleParser
from core.formatter import Formatter
from core.exporter import Exporter
from core.template_manager import TemplateManager
from parsers.dispatcher import parse_file


# ============================================================
# 测试规则标准化器
# ============================================================

class TestRuleNormalizer:
    """测试规则标准化"""

    def test_cn_size_to_pt(self):
        assert RuleNormalizer.cn_size_to_pt("三号") == 16
        assert RuleNormalizer.cn_size_to_pt("小四") == 12
        assert RuleNormalizer.cn_size_to_pt("二号") == 22
        assert RuleNormalizer.cn_size_to_pt("五号") == 10.5
        assert RuleNormalizer.cn_size_to_pt("小五") == 9

    def test_pt_notation(self):
        assert RuleNormalizer.cn_size_to_pt("12pt") == 12
        assert RuleNormalizer.cn_size_to_pt("14磅") == 14
        assert RuleNormalizer.cn_size_to_pt("10.5") == 10.5

    def test_cn_size_unknown(self):
        assert RuleNormalizer.cn_size_to_pt("未知") is None
        assert RuleNormalizer.cn_size_to_pt("") is None

    def test_pt_to_cn_size(self):
        assert RuleNormalizer.pt_to_cn_size(16) == "三号"
        assert RuleNormalizer.pt_to_cn_size(12) == "小四"
        assert RuleNormalizer.pt_to_cn_size(22) == "二号"

    def test_parse_alignment(self):
        assert RuleNormalizer.parse_alignment("居中") == Alignment.CENTER
        assert RuleNormalizer.parse_alignment("左对齐") == Alignment.LEFT
        assert RuleNormalizer.parse_alignment("两端对齐") == Alignment.JUSTIFY
        assert RuleNormalizer.parse_alignment("center") == Alignment.CENTER

    def test_parse_line_spacing(self):
        ls_type, ls_val = RuleNormalizer.parse_line_spacing("固定值20磅")
        assert ls_type == LineSpacingType.EXACT
        assert ls_val == 20

        ls_type, ls_val = RuleNormalizer.parse_line_spacing("1.5倍")
        assert ls_type == LineSpacingType.ONE_POINT_FIVE
        assert ls_val == 1.5

        ls_type, ls_val = RuleNormalizer.parse_line_spacing("单倍行距")
        assert ls_type == LineSpacingType.SINGLE

    def test_parse_margin(self):
        assert RuleNormalizer.parse_margin("2.54cm") == 2.54
        assert RuleNormalizer.parse_margin("25.4mm") == 2.54

    def test_normalize_style_rules(self):
        raw = {"字体": "宋体", "字号": "小四", "加粗": True, "对齐": "居中"}
        style = RuleNormalizer.normalize_style_rules(raw)
        assert style.font_name_cn == "宋体"
        assert style.font_size_pt == 12
        assert style.bold is True
        assert style.alignment == Alignment.CENTER

    def test_fill_defaults(self):
        rules = FormattingRules()
        rules = RuleNormalizer.fill_defaults(rules)
        assert rules.body.font_name_cn == "宋体"
        assert rules.body.font_size_pt == 12
        assert rules.body.first_indent_chars == 2
        assert rules.page.paper_size == "A4"


# ============================================================
# 测试文本规则解析器
# ============================================================

class TestTextRuleParser:
    """测试文本规则解析"""

    def test_parse_gov_report_requirements(self):
        """测试解析公文排版要求"""
        text = """
        正文中标题的格式
        1．标题（居中，方正小标宋简体，二号）。
        2．文中结构层次序数依次可以用"一"、"（一）"、"1."、"（1）"标注；
        一般第一层用黑体字、第二层用楷体字、第三层（加粗）和第四层用仿宋GB2312体字标注。
        3．原则上不要超过三级标题，最多不能超过四级。
        正文（仿宋GB2312，三号，1.5倍行距）。
        页眉：项目名称，仿宋GB2312，小五号字。
        """
        parser = TextRuleParser()
        rules = parser.parse(text)

        # 验证标题规则
        assert rules.title.font_name_cn == "方正小标宋简体"
        assert rules.title.font_size_pt == 22
        assert rules.title.alignment == Alignment.CENTER

        # 验证正文规则
        assert "仿宋" in (rules.body.font_name_cn or "")  # 可能匹配到"仿宋"或"仿宋GB2312"
        assert rules.body.font_size_pt == 16
        assert rules.body.line_spacing_type == LineSpacingType.ONE_POINT_FIVE

    def test_parse_page_margins(self):
        text = "页面设置为A4纸，上3.7cm，下3.5cm，左右2.7cm。"
        rules = TextRuleParser().parse(text)
        assert rules.page.paper_size == "A4"
        assert rules.page.margin_top_cm == 3.7
        assert rules.page.margin_bottom_cm == 3.5
        assert rules.page.margin_left_cm == 2.7

    def test_parse_numbering(self):
        text = '第一层用"一、二、三、"标注，第二层用"（一）（二）"标注，第三层用"1."标注。'
        rules = TextRuleParser().parse(text)
        assert "一" in rules.heading1_numbering
        assert "（一）" in rules.heading2_numbering
        assert "1." in rules.heading3_numbering


# ============================================================
# 测试 DOCX 样式解析器
# ============================================================

class TestDocxStyleParser:
    """测试 DOCX 样式解析"""

    DOCX_FILE = "/workspace/.uploads/c0b6893f-cf16-4263-be25-6a16d93da746_附件7：太原市尖草坪区绩效评价报告基本排版要求.docx"

    def test_parse_real_docx_styles(self):
        if not os.path.exists(self.DOCX_FILE):
            pytest.skip("真实 DOCX 文件不存在")

        parser = DocxStyleParser()
        rules = parser.parse(self.DOCX_FILE)

        # 基本验证
        assert rules.page.paper_size == "A4"
        assert rules.page.margin_top_cm > 0

        # 应该提取到一些字体信息
        has_any_font = any([
            rules.body.font_name_cn,
            rules.heading1.font_name_cn,
            rules.title.font_name_cn,
        ])
        assert has_any_font, "应该从真实文件中提取到字体信息"

        # 序列化验证
        yaml_str = rules.to_yaml()
        assert len(yaml_str) > 50

    def test_parse_real_docx_page_setup(self):
        if not os.path.exists(self.DOCX_FILE):
            pytest.skip("真实 DOCX 文件不存在")

        rules = DocxStyleParser().parse(self.DOCX_FILE)
        # 尖草坪区要求：上3.7cm
        assert abs(rules.page.margin_top_cm - 3.7) < 0.5


# ============================================================
# 测试排版引擎
# ============================================================

class TestFormatter:
    """测试排版引擎"""

    def _create_sample_doc(self) -> DocumentModel:
        doc = DocumentModel(title="测试文档")
        doc.elements.extend([
            DocElement(element_type=ElementType.HEADING, content="第一章 绪论", level=1),
            DocElement(element_type=ElementType.HEADING, content="1.1 研究背景", level=2),
            DocElement(element_type=ElementType.PARAGRAPH, content="这是正文段落。"),
            DocElement(element_type=ElementType.PARAGRAPH, content="这是第二段。"),
        ])
        return doc

    def _create_sample_rules(self) -> FormattingRules:
        return FormattingRules(
            template_name="测试模板",
            heading1=StyleRules(font_name_cn="黑体", font_size_pt=16, bold=True, alignment=Alignment.CENTER),
            heading2=StyleRules(font_name_cn="黑体", font_size_pt=14, bold=True),
            body=StyleRules(font_name_cn="宋体", font_size_pt=12, first_indent_chars=2),
            page=PageRules(paper_size="A4", margin_top_cm=2.5),
        )

    def test_apply_heading_style(self):
        doc = self._create_sample_doc()
        rules = self._create_sample_rules()
        formatter = Formatter(rules)
        result = formatter.apply(doc)

        # 验证标题样式已应用
        h1 = result.elements[0]
        assert h1.font_style.font_name_cn == "黑体"
        assert h1.font_style.font_size_pt == 16
        assert h1.font_style.bold is True
        assert h1.paragraph_style.alignment == Alignment.CENTER

        h2 = result.elements[1]
        assert h2.font_style.font_name_cn == "黑体"
        assert h2.font_style.font_size_pt == 14

    def test_apply_body_style(self):
        doc = self._create_sample_doc()
        rules = self._create_sample_rules()
        formatter = Formatter(rules)
        result = formatter.apply(doc)

        body = result.elements[2]
        assert body.font_style.font_name_cn == "宋体"
        assert body.font_style.font_size_pt == 12
        assert body.paragraph_style.first_indent_chars == 2

    def test_apply_page_setup(self):
        doc = self._create_sample_doc()
        rules = self._create_sample_rules()
        formatter = Formatter(rules)
        result = formatter.apply(doc)

        assert result.page_setup.paper_size == "A4"
        assert result.page_setup.margin_top_cm == 2.5

    def test_apply_preserves_content(self):
        doc = self._create_sample_doc()
        rules = self._create_sample_rules()
        formatter = Formatter(rules)
        result = formatter.apply(doc)

        assert result.elements[0].content == "第一章 绪论"
        assert result.elements[2].content == "这是正文段落。"
        assert len(result.elements) == 4

    def test_apply_with_sections(self):
        doc = self._create_sample_doc()
        rules = FormattingRules(
            sections=[],
            body=StyleRules(font_name_cn="宋体", font_size_pt=12),
        )
        from core.formatting_rules import SectionRules
        rules.sections.append(SectionRules(
            name="正文",
            header_text="测试页眉",
            header_font="宋体",
            page_number_enabled=True,
            page_number_format="－ {num} －",
        ))
        formatter = Formatter(rules)
        result = formatter.apply(doc)

        assert len(result.sections) == 1
        assert result.sections[0].header.text == "测试页眉"
        assert result.sections[0].page_number.enabled is True


# ============================================================
# 测试导出引擎
# ============================================================

class TestExporter:
    """测试导出引擎"""

    def _create_formatted_doc(self) -> DocumentModel:
        doc = DocumentModel(
            title="导出测试",
            page_setup=PageSetup(paper_size="A4", margin_top_cm=2.5, margin_bottom_cm=2.5),
            sections=[
                SectionConfig(
                    name="正文",
                    header=HeaderFooterConfig(text="测试页眉", font_name="宋体", font_size_pt=10.5),
                    page_number=PageNumberConfig(enabled=True, format="－ {num} －", start_from=1),
                )
            ],
        )
        doc.elements.extend([
            DocElement(
                element_type=ElementType.HEADING, content="第一章 绪论", level=1,
                font_style=FontStyle(font_name_cn="黑体", font_size_pt=16, bold=True),
                paragraph_style=ParagraphStyle(alignment=Alignment.CENTER),
            ),
            DocElement(
                element_type=ElementType.PARAGRAPH, content="这是排版后的正文段落。",
                font_style=FontStyle(font_name_cn="宋体", font_size_pt=12),
                paragraph_style=ParagraphStyle(first_indent_chars=2),
            ),
        ])
        doc.tables.append(TableData(
            caption="表1-1 测试表格",
            rows=[
                [TableCell(content="姓名", is_header=True), TableCell(content="年龄", is_header=True)],
                [TableCell(content="张三"), TableCell(content="25")],
            ]
        ))
        return doc

    def test_export_creates_file(self):
        doc = self._create_formatted_doc()
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            exporter = Exporter()
            result_path = exporter.export(doc, path)
            assert os.path.isfile(result_path)
            assert os.path.getsize(result_path) > 1000  # 文件应该有一定大小
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_and_reparse(self):
        """导出后重新解析，验证内容完整性"""
        doc = self._create_formatted_doc()
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            # 导出
            Exporter().export(doc, path)

            # 重新解析
            reparsed = parse_file(path)
            text = reparsed.get_all_text()

            assert "第一章 绪论" in text
            assert "正文段落" in text
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ============================================================
# 测试模板管理器
# ============================================================

class TestTemplateManager:
    """测试模板管理器"""

    def test_list_templates(self):
        mgr = TemplateManager()
        templates = mgr.list_templates()
        assert len(templates) >= 2  # 至少有预设的两个模板

        names = [t["name"] for t in templates]
        assert any("海大" in n or "毕业论文" in n for n in names)
        assert any("尖草坪" in n or "绩效" in n for n in names)

    def test_load_preset_template(self):
        mgr = TemplateManager()
        template = mgr.load_template("广东海洋大学本科毕业论文")
        assert template is not None
        assert template.template_type == "thesis"
        assert template.heading1.font_name_cn == "黑体"
        assert template.body.font_name_cn == "宋体"

    def test_load_gov_template(self):
        mgr = TemplateManager()
        template = mgr.load_template("太原市尖草坪区绩效评价报告")
        assert template is not None
        assert template.template_type == "gov_doc"
        assert template.title.font_name_cn == "方正小标宋简体"

    def test_save_and_load_custom(self):
        mgr = TemplateManager()
        rules = FormattingRules(
            template_name="自定义测试模板",
            template_type="custom",
            body=StyleRules(font_name_cn="宋体", font_size_pt=12),
        )
        path = mgr.save_template(rules, "test_custom.yaml")
        try:
            loaded = mgr.load_template("自定义测试模板")
            assert loaded is not None
            assert loaded.template_name == "自定义测试模板"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_delete_custom_template(self):
        mgr = TemplateManager()
        rules = FormattingRules(template_name="待删除模板")
        path = mgr.save_template(rules, "to_delete.yaml")
        try:
            result = mgr.delete_template("待删除模板")
            assert result is True
            assert mgr.load_template("待删除模板") is None
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ============================================================
# 端到端测试：完整链路
# ============================================================

class TestEndToEnd:
    """端到端测试：解析文件 → 提取规则 → 应用排版 → 导出"""

    DOCX_FILE = "/workspace/.uploads/c0b6893f-cf16-4263-be25-6a16d93da746_附件7：太原市尖草坪区绩效评价报告基本排版要求.docx"

    def test_full_pipeline_with_template(self):
        """完整链路：加载预设模板 → 创建文档 → 排版 → 导出"""
        # 1. 加载模板
        mgr = TemplateManager()
        rules = mgr.load_template("太原市尖草坪区绩效评价报告")
        assert rules is not None

        # 2. 创建文档模型
        doc = DocumentModel(title="绩效评价报告测试")
        doc.elements.extend([
            DocElement(element_type=ElementType.HEADING, content="项目基本情况", level=1),
            DocElement(element_type=ElementType.HEADING, content="（一）项目背景", level=2),
            DocElement(element_type=ElementType.PARAGRAPH, content="本项目旨在提升公共服务质量。"),
            DocElement(element_type=ElementType.PARAGRAPH, content="通过多种方式进行评价。"),
        ])

        # 3. 应用排版
        formatter = Formatter(rules)
        formatted = formatter.apply(doc)

        # 验证排版已应用
        assert formatted.elements[0].font_style.font_name_cn == "黑体"
        assert formatted.elements[2].font_style.font_name_cn == "仿宋GB2312"

        # 4. 导出
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            Exporter().export(formatted, path)
            assert os.path.isfile(path)
            assert os.path.getsize(path) > 1000

            # 5. 重新解析验证
            reparsed = parse_file(path)
            text = reparsed.get_all_text()
            assert "项目基本情况" in text
            assert "公共服务质量" in text
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_parse_docx_extract_rules_and_format(self):
        """从真实 DOCX 提取规则 → 应用到新文档 → 导出"""
        if not os.path.exists(self.DOCX_FILE):
            pytest.skip("真实 DOCX 文件不存在")

        # 1. 解析文件
        source_doc = parse_file(self.DOCX_FILE)
        assert len(source_doc.elements) > 0

        # 2. 从文件提取样式规则
        style_parser = DocxStyleParser()
        rules = style_parser.parse(self.DOCX_FILE)

        # 3. 创建新文档并排版
        new_doc = DocumentModel(title="格式化输出测试")
        new_doc.elements.append(
            DocElement(element_type=ElementType.HEADING, content="测试标题", level=1)
        )
        new_doc.elements.append(
            DocElement(element_type=ElementType.PARAGRAPH, content="测试正文内容。")
        )

        formatter = Formatter(rules)
        formatted = formatter.apply(new_doc)

        # 4. 导出
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            Exporter().export(formatted, path)
            assert os.path.isfile(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_text_rules_to_formatted_docx(self):
        """文本规则 → FormattingRules → 排版 → 导出"""
        text = """
        页面设置为A4纸，上2.5cm，下2.5cm，左右3cm。
        标题（居中，黑体，三号）。
        正文（宋体，五号，固定值20磅行距，首行缩进2字符）。
        """
        parser = TextRuleParser()
        rules = parser.parse(text)

        doc = DocumentModel()
        doc.elements.extend([
            DocElement(element_type=ElementType.HEADING, content="测试标题", level=0),  # 大标题用 level=0
            DocElement(element_type=ElementType.PARAGRAPH, content="测试正文。"),
        ])

        formatter = Formatter(rules)
        formatted = formatter.apply(doc)

        # 标题(level=0)会尝试 heading1，如果没有则用 body
        # 但 title 规则只用于文档大标题，heading 规则用于各级标题
        # 这里我们验证 body 样式已正确应用
        assert formatted.elements[1].font_style.font_name_cn == "宋体"
        assert formatted.elements[1].font_style.font_size_pt == 10.5

        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            Exporter().export(formatted, path)
            assert os.path.isfile(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
