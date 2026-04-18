"""
Phase 1 单元测试

测试统一文档模型和排版规则的创建、序列化、反序列化、查询功能。
"""

import json
import sys
import os

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import (
    ElementType, Alignment, LineSpacingType, NumberingType, PageNumberFormat,
    FontStyle, ParagraphStyle,
    DocElement, TableCell, TableData, ImageData,
    PageSetup, HeaderFooterConfig, PageNumberConfig, SectionConfig,
    DocumentModel,
)
from core.formatting_rules import (
    StyleRules, PageRules, SectionRules, CrossRefRules, FormattingRules,
)


# ============================================================
# 测试枚举类型
# ============================================================

class TestEnums:
    """测试枚举类型的值"""

    def test_element_type_values(self):
        assert ElementType.HEADING.value == "heading"
        assert ElementType.PARAGRAPH.value == "paragraph"
        assert ElementType.TABLE.value == "table"
        assert ElementType.CROSS_REF.value == "cross_ref"

    def test_alignment_values(self):
        assert Alignment.LEFT.value == "left"
        assert Alignment.CENTER.value == "center"
        assert Alignment.JUSTIFY.value == "justify"

    def test_line_spacing_type_values(self):
        assert LineSpacingType.SINGLE.value == "single"
        assert LineSpacingType.EXACT.value == "exact"
        assert LineSpacingType.ONE_POINT_FIVE.value == "1.5"

    def test_page_number_format_values(self):
        assert PageNumberFormat.ARABIC.value == "arabic"
        assert PageNumberFormat.UPPER_ROMAN.value == "upper_roman"


# ============================================================
# 测试样式数据类
# ============================================================

class TestFontStyle:
    """测试字体样式"""

    def test_default_values(self):
        style = FontStyle()
        assert style.font_name_cn == ""
        assert style.bold is False
        assert style.font_size_pt == 0.0

    def test_custom_values(self):
        style = FontStyle(font_name_cn="宋体", font_size_pt=10.5, bold=True)
        assert style.font_name_cn == "宋体"
        assert style.font_size_pt == 10.5
        assert style.bold is True

    def test_to_dict(self):
        style = FontStyle(font_name_cn="黑体", font_size_pt=12, bold=True, italic=True)
        d = style.to_dict()
        assert d["font_name_cn"] == "黑体"
        assert d["font_size_pt"] == 12
        assert d["bold"] is True
        assert d["italic"] is True

    def test_from_dict(self):
        d = {"font_name_cn": "宋体", "font_size_pt": 10.5, "bold": True}
        style = FontStyle.from_dict(d)
        assert style.font_name_cn == "宋体"
        assert style.font_size_pt == 10.5
        assert style.bold is True

    def test_from_dict_ignores_unknown_keys(self):
        d = {"font_name_cn": "宋体", "unknown_key": "value"}
        style = FontStyle.from_dict(d)
        assert style.font_name_cn == "宋体"
        assert not hasattr(style, "unknown_key")


class TestParagraphStyle:
    """测试段落样式"""

    def test_default_values(self):
        style = ParagraphStyle()
        assert style.alignment == Alignment.JUSTIFY
        assert style.first_indent_chars == 0.0
        assert style.line_spacing_type == LineSpacingType.SINGLE

    def test_custom_values(self):
        style = ParagraphStyle(
            alignment=Alignment.CENTER,
            first_indent_chars=2,
            line_spacing_type=LineSpacingType.EXACT,
            line_spacing_value=20,
        )
        assert style.alignment == Alignment.CENTER
        assert style.first_indent_chars == 2
        assert style.line_spacing_type == LineSpacingType.EXACT

    def test_to_dict_and_from_dict(self):
        style = ParagraphStyle(
            alignment=Alignment.CENTER,
            first_indent_chars=2,
            line_spacing_type=LineSpacingType.EXACT,
            line_spacing_value=20,
            space_before_pt=6,
        )
        d = style.to_dict()
        restored = ParagraphStyle.from_dict(d)
        assert restored.alignment == Alignment.CENTER
        assert restored.first_indent_chars == 2
        assert restored.line_spacing_type == LineSpacingType.EXACT
        assert restored.line_spacing_value == 20
        assert restored.space_before_pt == 6


# ============================================================
# 测试文档元素
# ============================================================

class TestDocElement:
    """测试文档元素"""

    def test_create_heading(self):
        elem = DocElement(
            element_type=ElementType.HEADING,
            content="第一章 绪论",
            level=1,
            font_style=FontStyle(font_name_cn="黑体", font_size_pt=12, bold=True),
        )
        assert elem.element_type == ElementType.HEADING
        assert elem.content == "第一章 绪论"
        assert elem.level == 1
        assert elem.font_style.bold is True

    def test_create_paragraph(self):
        elem = DocElement(
            element_type=ElementType.PARAGRAPH,
            content="这是一段正文内容。",
            paragraph_style=ParagraphStyle(first_indent_chars=2),
        )
        assert elem.element_type == ElementType.PARAGRAPH
        assert elem.paragraph_style.first_indent_chars == 2

    def test_create_with_children(self):
        parent = DocElement(
            element_type=ElementType.LIST,
            children=[
                DocElement(element_type=ElementType.LIST_ITEM, content="项目一"),
                DocElement(element_type=ElementType.LIST_ITEM, content="项目二"),
            ]
        )
        assert len(parent.children) == 2
        assert parent.children[0].content == "项目一"

    def test_get_text(self):
        elem = DocElement(
            element_type=ElementType.HEADING,
            content="标题",
            children=[
                DocElement(element_type=ElementType.PARAGRAPH, content="子内容"),
            ]
        )
        text = elem.get_text()
        assert "标题" in text
        assert "子内容" in text

    def test_find_elements(self):
        root = DocElement(
            element_type=ElementType.HEADING,
            content="根",
            children=[
                DocElement(element_type=ElementType.HEADING, content="子标题1", level=2),
                DocElement(element_type=ElementType.PARAGRAPH, content="段落"),
                DocElement(element_type=ElementType.HEADING, content="子标题2", level=2),
            ]
        )
        headings = root.find_elements(ElementType.HEADING)
        assert len(headings) == 3  # 包含自身

    def test_to_dict_and_from_dict(self):
        elem = DocElement(
            element_type=ElementType.HEADING,
            content="测试标题",
            level=2,
            font_style=FontStyle(font_name_cn="黑体", font_size_pt=12),
            paragraph_style=ParagraphStyle(alignment=Alignment.CENTER),
        )
        d = elem.to_dict()
        assert d["element_type"] == "heading"
        assert d["content"] == "测试标题"
        assert d["level"] == 2

        restored = DocElement.from_dict(d)
        assert restored.element_type == ElementType.HEADING
        assert restored.content == "测试标题"
        assert restored.level == 2
        assert restored.font_style.font_name_cn == "黑体"
        assert restored.paragraph_style.alignment == Alignment.CENTER

    def test_unique_id(self):
        elem1 = DocElement(element_type=ElementType.PARAGRAPH)
        elem2 = DocElement(element_type=ElementType.PARAGRAPH)
        assert elem1.id != elem2.id


# ============================================================
# 测试表格和图片
# ============================================================

class TestTableData:
    """测试表格数据"""

    def test_create_table(self):
        table = TableData(
            caption="表1-1 测试数据",
            numbering="表1-1",
            rows=[
                [TableCell(content="姓名", is_header=True), TableCell(content="年龄", is_header=True)],
                [TableCell(content="张三"), TableCell(content="25")],
                [TableCell(content="李四"), TableCell(content="30")],
            ]
        )
        assert table.num_rows == 3
        assert table.num_cols == 2
        assert table.caption == "表1-1 测试数据"

    def test_empty_table(self):
        table = TableData()
        assert table.num_rows == 0
        assert table.num_cols == 0

    def test_to_dict(self):
        table = TableData(
            caption="表1-1",
            rows=[[TableCell(content="A", is_header=True)]]
        )
        d = table.to_dict()
        assert d["caption"] == "表1-1"
        assert len(d["rows"]) == 1
        assert d["rows"][0][0]["is_header"] is True


class TestImageData:
    """测试图片数据"""

    def test_create_image(self):
        img = ImageData(
            caption="图1-1 系统架构",
            numbering="图1-1",
            file_path="/path/to/image.png",
            width_cm=15.0,
        )
        assert img.caption == "图1-1 系统架构"
        assert img.width_cm == 15.0


# ============================================================
# 测试页面设置和节配置
# ============================================================

class TestPageSetup:
    """测试页面设置"""

    def test_default_a4(self):
        setup = PageSetup()
        assert setup.paper_size == "A4"
        assert setup.orientation == "portrait"

    def test_custom(self):
        setup = PageSetup(
            paper_size="A4",
            margin_top_cm=2.5,
            margin_left_cm=2.5,
            margin_right_cm=2.0,
            gutter_cm=0.5,
        )
        d = setup.to_dict()
        assert d["gutter_cm"] == 0.5
        assert d["margin_right_cm"] == 2.0

    def test_from_dict(self):
        d = {"paper_size": "A4", "margin_top_cm": 3.7, "gutter_cm": 0.5}
        setup = PageSetup.from_dict(d)
        assert setup.margin_top_cm == 3.7
        assert setup.gutter_cm == 0.5


class TestSectionConfig:
    """测试节配置"""

    def test_section_with_header_and_page_number(self):
        section = SectionConfig(
            name="正文",
            header=HeaderFooterConfig(text="广东海洋大学2024届本科生毕业设计"),
            page_number=PageNumberConfig(
                format="－ {num} －",
                number_format=PageNumberFormat.ARABIC,
                start_from=1,
            ),
        )
        assert section.name == "正文"
        assert section.header.text == "广东海洋大学2024届本科生毕业设计"
        assert section.page_number.start_from == 1

    def test_section_to_dict(self):
        section = SectionConfig(
            name="封面",
            first_page_different=True,
            first_page_header=HeaderFooterConfig(text="2024届本科生毕业设计", bold=True),
        )
        d = section.to_dict()
        assert d["name"] == "封面"
        assert d["first_page_different"] is True
        assert d["first_page_header"]["bold"] is True


# ============================================================
# 测试文档模型（顶层）
# ============================================================

class TestDocumentModel:
    """测试文档模型"""

    def _create_sample_doc(self) -> DocumentModel:
        """创建示例文档"""
        doc = DocumentModel(
            title="测试论文",
            author="张三",
            source_format="demo",
            page_setup=PageSetup(paper_size="A4"),
            sections=[
                SectionConfig(name="正文", header=HeaderFooterConfig(text="测试文档")),
            ],
        )
        doc.elements.extend([
            DocElement(element_type=ElementType.HEADING, content="第一章 绪论", level=1),
            DocElement(element_type=ElementType.HEADING, content="1.1 研究背景", level=2),
            DocElement(element_type=ElementType.PARAGRAPH, content="这是第一段正文。"),
            DocElement(element_type=ElementType.PARAGRAPH, content="这是第二段正文。"),
            DocElement(element_type=ElementType.HEADING, content="第二章 方法", level=1),
            DocElement(element_type=ElementType.PARAGRAPH, content="这是方法部分的正文。"),
        ])
        doc.tables.append(TableData(
            caption="表1-1 实验数据",
            rows=[
                [TableCell(content="指标", is_header=True), TableCell(content="值", is_header=True)],
                [TableCell(content="准确率"), TableCell(content="95%")],
            ]
        ))
        return doc

    def test_create_and_query(self):
        doc = self._create_sample_doc()
        assert doc.title == "测试论文"
        assert len(doc.elements) == 6

    def test_get_all_text(self):
        doc = self._create_sample_doc()
        text = doc.get_all_text()
        assert "第一章 绪论" in text
        assert "这是第一段正文" in text

    def test_find_headings(self):
        doc = self._create_sample_doc()
        headings = doc.get_headings()
        assert len(headings) == 3
        headings_l1 = doc.get_headings(max_level=1)
        assert len(headings_l1) == 2

    def test_get_paragraphs(self):
        doc = self._create_sample_doc()
        paras = doc.get_paragraphs()
        assert len(paras) == 3

    def test_element_count(self):
        doc = self._create_sample_doc()
        counts = doc.element_count()
        assert counts["heading"] == 3
        assert counts["paragraph"] == 3

    def test_to_dict_and_from_dict(self):
        doc = self._create_sample_doc()
        d = doc.to_dict()
        assert d["title"] == "测试论文"
        assert len(d["elements"]) == 6
        assert len(d["tables"]) == 1
        assert d["sections"][0]["name"] == "正文"

        restored = DocumentModel.from_dict(d)
        assert restored.title == "测试论文"
        assert len(restored.elements) == 6
        assert restored.elements[0].content == "第一章 绪论"
        assert len(restored.tables) == 1
        assert restored.tables[0].caption == "表1-1 实验数据"
        assert restored.sections[0].header.text == "测试文档"

    def test_json_serialization(self):
        doc = self._create_sample_doc()
        json_str = doc.to_json()
        assert "测试论文" in json_str

        restored = DocumentModel.from_json(json_str)
        assert restored.title == "测试论文"
        assert len(restored.elements) == 6

    def test_empty_document(self):
        doc = DocumentModel()
        assert doc.title == ""
        assert doc.elements == []
        assert doc.get_all_text() == ""
        assert doc.element_count() == {}


# ============================================================
# 测试排版规则
# ============================================================

class TestStyleRules:
    """测试样式规则"""

    def test_default(self):
        rules = StyleRules()
        assert rules.font_name_cn is None
        assert rules.bold is None

    def test_merge(self):
        base = StyleRules(font_name_cn="宋体", font_size_pt=10.5)
        override = StyleRules(font_size_pt=12, bold=True)
        merged = base.merge(override)
        assert merged.font_name_cn == "宋体"  # 保留
        assert merged.font_size_pt == 12       # 覆盖
        assert merged.bold is True             # 新增

    def test_to_dict_omits_none(self):
        rules = StyleRules(font_name_cn="宋体")
        d = rules.to_dict()
        assert "font_name_cn" in d
        assert "bold" not in d


class TestFormattingRules:
    """测试排版规则"""

    def _create_sample_rules(self) -> FormattingRules:
        return FormattingRules(
            template_name="海大毕业论文",
            template_type="thesis",
            page=PageRules(paper_size="A4", margin_top_cm=2.5, margin_bottom_cm=2.5),
            heading1=StyleRules(font_name_cn="黑体", font_size_pt=12, bold=True, alignment=Alignment.CENTER),
            heading2=StyleRules(font_name_cn="黑体", font_size_pt=12, bold=True),
            body=StyleRules(font_name_cn="宋体", font_size_pt=10.5, first_indent_chars=2),
            table_caption=StyleRules(font_name_cn="黑体", font_size_pt=14, alignment=Alignment.CENTER),
            heading1_numbering="1. 2. 3. ...",
            heading2_numbering="1.1 1.2 1.3 ...",
        )

    def test_create(self):
        rules = self._create_sample_rules()
        assert rules.template_name == "海大毕业论文"
        assert rules.heading1.font_name_cn == "黑体"

    def test_get_heading_style(self):
        rules = self._create_sample_rules()
        h1 = rules.get_heading_style(1)
        assert h1.font_name_cn == "黑体"
        h5 = rules.get_heading_style(5)
        assert h5 is None

    def test_get_heading_numbering(self):
        rules = self._create_sample_rules()
        assert rules.get_heading_numbering(1) == "1. 2. 3. ..."
        assert rules.get_heading_numbering(3) == ""

    def test_to_dict_and_from_dict(self):
        rules = self._create_sample_rules()
        d = rules.to_dict()
        assert d["template_name"] == "海大毕业论文"
        assert d["heading1"]["font_name_cn"] == "黑体"

        restored = FormattingRules.from_dict(d)
        assert restored.template_name == "海大毕业论文"
        assert restored.heading1.font_name_cn == "黑体"
        assert restored.body.first_indent_chars == 2

    def test_yaml_serialization(self):
        rules = self._create_sample_rules()
        yaml_str = rules.to_yaml()
        assert "海大毕业论文" in yaml_str
        assert "黑体" in yaml_str

        restored = FormattingRules.from_yaml(yaml_str)
        assert restored.template_name == "海大毕业论文"
        assert restored.heading1.font_size_pt == 12

    def test_json_serialization(self):
        rules = self._create_sample_rules()
        json_str = rules.to_json()
        assert "海大毕业论文" in json_str

        restored = FormattingRules.from_json(json_str)
        assert restored.template_type == "thesis"

    def test_cross_reference_rules(self):
        rules = FormattingRules(
            cross_reference=CrossRefRules(
                enabled=True,
                figure_pattern="图{chapter}-{seq}",
                table_pattern="表{chapter}-{seq}",
            )
        )
        assert rules.cross_reference.enabled is True
        assert rules.cross_reference.figure_pattern == "图{chapter}-{seq}"


# ============================================================
# 测试真实模板规则
# ============================================================

class TestRealTemplateRules:
    """测试从真实模板提取的排版规则"""

    def test_thesis_template_rules(self):
        """测试海大毕业论文排版规则"""
        rules = FormattingRules(
            template_name="广东海洋大学本科毕业论文",
            template_type="thesis",
            page=PageRules(
                paper_size="A4",
                margin_top_cm=2.5,
                margin_bottom_cm=2.5,
                margin_left_cm=2.5,
                margin_right_cm=2.0,
                gutter_cm=0.5,
                header_distance_cm=1.7,
                footer_distance_cm=1.7,
            ),
            heading1=StyleRules(
                font_name_cn="黑体", font_size_pt=12, bold=True,
                alignment=Alignment.CENTER,
                line_spacing_type=LineSpacingType.EXACT, line_spacing_value=20,
            ),
            heading2=StyleRules(
                font_name_cn="黑体", font_size_pt=12, bold=True,
                alignment=Alignment.LEFT,
                line_spacing_type=LineSpacingType.EXACT, line_spacing_value=20,
            ),
            body=StyleRules(
                font_name_cn="宋体", font_size_pt=10.5,
                first_indent_chars=2,
                line_spacing_type=LineSpacingType.EXACT, line_spacing_value=20,
            ),
            reference=StyleRules(
                font_name_cn="宋体", font_size_pt=9,
                line_spacing_type=LineSpacingType.EXACT, line_spacing_value=16,
            ),
        )

        # 验证序列化
        yaml_str = rules.to_yaml()
        assert "装订线" not in yaml_str  # gutter_cm 不在 yaml key 中
        assert "0.5" in yaml_str

        # 验证反序列化
        restored = FormattingRules.from_yaml(yaml_str)
        assert restored.page.gutter_cm == 0.5
        assert restored.heading1.font_size_pt == 12

    def test_gov_report_template_rules(self):
        """测试公文排版规则"""
        rules = FormattingRules(
            template_name="太原市尖草坪区绩效评价报告",
            template_type="gov_doc",
            page=PageRules(
                paper_size="A4",
                margin_top_cm=3.7,
                margin_bottom_cm=3.5,
                margin_left_cm=2.7,
                margin_right_cm=2.7,
            ),
            title=StyleRules(
                font_name_cn="方正小标宋简体", font_size_pt=22,
                bold=True, alignment=Alignment.CENTER,
            ),
            heading1=StyleRules(
                font_name_cn="黑体", font_size_pt=16, bold=True,
            ),
            heading2=StyleRules(
                font_name_cn="楷体", font_size_pt=16,
            ),
            heading3=StyleRules(
                font_name_cn="仿宋GB2312", font_size_pt=16, bold=True,
            ),
            body=StyleRules(
                font_name_cn="仿宋GB2312", font_size_pt=16,
                font_name_en="Times New Roman",
            ),
            heading1_numbering="一、二、三、...",
            heading2_numbering="（一）（二）...",
            heading3_numbering="1. 2. 3. ...",
            heading4_numbering="（1）（2）...",
        )

        # 验证
        assert rules.heading1_numbering == "一、二、三、..."
        assert rules.body.font_name_en == "Times New Roman"

        json_str = rules.to_json()
        restored = FormattingRules.from_json(json_str)
        assert restored.heading2.font_name_cn == "楷体"
        assert restored.page.margin_top_cm == 3.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
