"""
文本规则解析器 (Text Rule Parser)

从排版要求文件（纯文本描述）中提取排版规则。
使用规则匹配 + 模式识别（暂不依赖 LLM，后续可扩展）。
"""

from __future__ import annotations

import re
from typing import Optional

from core.formatting_rules import FormattingRules, StyleRules, PageRules, CrossRefRules
from core.document_model import Alignment, LineSpacingType, PageNumberFormat
from core.template_parser.rule_normalizer import RuleNormalizer


class TextRuleParser:
    """从文本描述中提取排版规则"""

    def parse(self, text: str) -> FormattingRules:
        """解析排版要求文本，返回结构化规则"""
        rules = FormattingRules()

        # 提取各维度规则
        self._extract_page_rules(text, rules)
        self._extract_title_rules(text, rules)
        self._extract_heading_rules(text, rules)
        self._extract_body_rules(text, rules)
        self._extract_table_rules(text, rules)
        self._extract_figure_rules(text, rules)
        self._extract_reference_rules(text, rules)
        self._extract_header_footer_rules(text, rules)
        self._extract_numbering_rules(text, rules)
        self._extract_cross_ref_rules(text, rules)
        self._extract_special_rules(text, rules)

        # 填充默认值
        rules = RuleNormalizer.fill_defaults(rules)

        return rules

    # ---- 页面设置 ----

    def _extract_page_rules(self, text: str, rules: FormattingRules):
        """提取页面设置"""
        # 纸张
        if "A4" in text or "a4" in text.lower():
            rules.page.paper_size = "A4"
        elif "A3" in text:
            rules.page.paper_size = "A3"

        # 页边距 — 匹配 "上Xcm"、"上下Xcm" 等模式
        margin_patterns = [
            (r"上(?:边距)?[：:\s]*(\d+(?:\.\d+)?)\s*cm", "margin_top_cm"),
            (r"下(?:边距)?[：:\s]*(\d+(?:\.\d+)?)\s*cm", "margin_bottom_cm"),
            (r"左(?:边距)?[：:\s]*(\d+(?:\.\d+)?)\s*cm", "margin_left_cm"),
            (r"右(?:边距)?[：:\s]*(\d+(?:\.\d+)?)\s*cm", "margin_right_cm"),
            (r"左右[：:\s]*(\d+(?:\.\d+)?)\s*cm", "both_lr"),  # 左右统一
        ]
        for pattern, attr in margin_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if attr == "both_lr":
                    rules.page.margin_left_cm = value
                    rules.page.margin_right_cm = value
                elif attr:
                    setattr(rules.page, attr, value)

    # ---- 标题规则 ----

    def _extract_title_rules(self, text: str, rules: FormattingRules):
        """提取文档大标题规则"""
        # 匹配 "标题（...，字体，字号）" 模式
        patterns = [
            r"标题[（(]([^)）]+)[)）]",
            r"标题[：:]\s*([^。\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                desc = match.group(1)
                self._apply_style_from_description(desc, rules.title)
                break

    def _extract_heading_rules(self, text: str, rules: FormattingRules):
        """提取各级标题规则"""
        # 第一层标题
        self._extract_heading_level(text, rules, level=1,
            patterns=[
                r"第一层[：:\s]*([^。\n]+)",
                r"一级标题[：:\s]*([^。\n]+)",
                r"第一层[用用]([^。，；\n]+)字",
            ])
        # 第二层标题
        self._extract_heading_level(text, rules, level=2,
            patterns=[
                r"第二层[：:\s]*([^。\n]+)",
                r"二级标题[：:\s]*([^。\n]+)",
            ])
        # 第三层标题
        self._extract_heading_level(text, rules, level=3,
            patterns=[
                r"第三层[：:\s]*([^。\n]+)",
                r"三级标题[：:\s]*([^。\n]+)",
            ])
        # 第四层标题
        self._extract_heading_level(text, rules, level=4,
            patterns=[
                r"第四层[：:\s]*([^。\n]+)",
                r"四级标题[：:\s]*([^。\n]+)",
            ])

    def _extract_heading_level(self, text: str, rules: FormattingRules,
                                level: int, patterns: list[str]):
        """提取指定层级的标题规则"""
        style = rules.get_heading_style(level)
        if style is None:
            return

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                desc = match.group(1)
                self._apply_style_from_description(desc, style)
                break

    # ---- 正文规则 ----

    def _extract_body_rules(self, text: str, rules: FormattingRules):
        """提取正文规则"""
        patterns = [
            r"正文[（(]([^)）]+)[)）]",
            r"正文[：:]\s*([^。\n]+)",
            r"正文字体[：:\s]*([^。，\n]+)",
            r"正文[用用]([^。，；\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                desc = match.group(1)
                self._apply_style_from_description(desc, rules.body)
                break

        # 行距（全局）
        spacing_patterns = [
            r"行距[：:\s]*(\d+(?:\.\d+)?)\s*倍",
            r"行距[：:\s]*固定值\s*(\d+(?:\.\d+)?)\s*磅",
            r"(\d+(?:\.\d+)?)\s*倍行距",
        ]
        for pattern in spacing_patterns:
            match = re.search(pattern, text)
            if match:
                if "固定值" in pattern:
                    rules.body.line_spacing_type = LineSpacingType.EXACT
                    rules.body.line_spacing_value = float(match.group(1))
                else:
                    value = float(match.group(1))
                    if value == 1.5:
                        rules.body.line_spacing_type = LineSpacingType.ONE_POINT_FIVE
                    else:
                        rules.body.line_spacing_type = LineSpacingType.MULTIPLE
                    rules.body.line_spacing_value = value
                break

    # ---- 表格规则 ----

    def _extract_table_rules(self, text: str, rules: FormattingRules):
        """提取表格规则"""
        # 表名
        match = re.search(r"表名[（(]([^)）]+)[)）]", text)
        if match:
            self._apply_style_from_description(match.group(1), rules.table_caption)

        # 表内文字
        match = re.search(r"表内(?:文字|字体)[：:\s]*([^。，\n]+)", text)
        if match:
            self._apply_style_from_description(match.group(1), rules.table_body)

    # ---- 图片规则 ----

    def _extract_figure_rules(self, text: str, rules: FormattingRules):
        """提取图片规则"""
        match = re.search(r"图名[（(]([^)）]+)[)）]", text)
        if match:
            self._apply_style_from_description(match.group(1), rules.figure_caption)

    # ---- 参考文献规则 ----

    def _extract_reference_rules(self, text: str, rules: FormattingRules):
        """提取参考文献规则"""
        match = re.search(r"参考文献[（(]([^)）]+)[)）]", text)
        if match:
            self._apply_style_from_description(match.group(1), rules.reference)

    # ---- 页眉页脚 ----

    def _extract_header_footer_rules(self, text: str, rules: FormattingRules):
        """提取页眉页脚规则"""
        from core.formatting_rules import SectionRules

        # 页眉
        match = re.search(r"页眉[：:\s]*([^。\n]+)", text)
        if match:
            desc = match.group(1)
            section = SectionRules()
            section.header_text = desc
            # 尝试提取字体
            font_match = re.search(r"([\u4e00-\u9fff\w]+)[，,]\s*(\d+(?:\.\d+)?)[号pt磅]", desc)
            if font_match:
                section.header_font = font_match.group(1)
                section.header_size_pt = RuleNormalizer.cn_size_to_pt(font_match.group(2))
            rules.sections.append(section)

        # 页脚/页码
        match = re.search(r"页脚[：:\s]*([^。\n]+)", text)
        if match:
            desc = match.group(1)

    # ---- 编号规则 ----

    def _extract_numbering_rules(self, text: str, rules: FormattingRules):
        """提取标题编号格式"""
        # 按 heading level 分组，每组独立匹配
        numbering_groups = {
            "heading1_numbering": [
                r'第一层.{0,30}?[\u201c\"\u300c]([一二三四五六七八九十、]+)[\u201d\"\u300d]',
                r"第一层[^。]*?用([^。，；\n]+)字标注",
            ],
            "heading2_numbering": [
                r'第二层.{0,30}?[\u201c\"\u300c]([^\u201d\"\u300d]+)[\u201d\"\u300d]',
                r"第二层[^。]*?用([^。，；\n]+)字标注",
            ],
            "heading3_numbering": [
                r'第三层.{0,30}?[\u201c\"\u300c]([^\u201d\"\u300d]+)[\u201d\"\u300d]',
                r"第三层[^。]*?用([^。，；\n]+)字标注",
            ],
            "heading4_numbering": [
                r'第四层.{0,30}?[\u201c\"\u300c]([^\u201d\"\u300d]+)[\u201d\"\u300d]',
                r"第四层[^。]*?用([^。，；\n]+)字标注",
            ],
        }
        for attr, patterns in numbering_groups.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    setattr(rules, attr, match.group(1))
                    break  # 只 break 内层，继续下一个 heading level

    # ---- 交叉引用 ----

    def _extract_cross_ref_rules(self, text: str, rules: FormattingRules):
        """提取交叉引用相关规则"""
        if "交叉引用" in text or "引用" in text:
            rules.cross_reference.enabled = True

        # 图表编号模式
        match = re.search(r"图序号[：:\s]*([^。，\n]+)", text)
        if match:
            rules.cross_reference.figure_pattern = match.group(1)
        match = re.search(r"表序号[：:\s]*([^。，\n]+)", text)
        if match:
            rules.cross_reference.table_pattern = match.group(1)

    # ---- 特殊规则 ----

    def _extract_special_rules(self, text: str, rules: FormattingRules):
        """提取特殊排版规则"""
        special = {}

        # 标点符号
        if "中文输入" in text or "中文标点" in text:
            special["punctuation"] = "必须使用中文输入格式"

        # 数字格式
        if "千位分隔" in text:
            special["number_format"] = "千位分隔符"

        # 金额单位
        match = re.search(r"金额单位[：:\s]*([^。，\n]+)", text)
        if match:
            special["money_unit"] = match.group(1)

        # 禁止项
        forbidden = []
        if "禁止" in text or "不得" in text or "不能" in text:
            match = re.search(r"禁止使用[^。]*[：:]([^。]+)", text)
            if match:
                forbidden = [x.strip() for x in re.split(r"[、，,]", match.group(1))]
        if forbidden:
            special["forbidden"] = forbidden

        rules.special_rules = special

    # ---- 辅助方法 ----

    def _apply_style_from_description(self, desc: str, style: StyleRules):
        """从描述文本中提取样式并应用到 StyleRules"""
        desc = desc.strip()

        # 提取字体 — 匹配中文字体名
        cn_fonts = ["宋体", "黑体", "楷体", "仿宋GB2312", "仿宋", "微软雅黑",
                     "方正小标宋简体", "方正姚体", "华文中宋", "华文楷体",
                     "Times New Roman", "Arial", "Calibri"]
        for font in cn_fonts:
            if font in desc:
                if any(c in font for c in "宋体黑体楷体仿宋微软雅黑方正华文"):
                    style.font_name_cn = font
                else:
                    style.font_name_en = font
                break

        # 提取字号 — 匹配 "X号" 或 "Xpt"
        size_patterns = [
            r"(初号|小初|一号|小一|二号|小二|三号|小三|四号|小四|五号|小五|六号|小六|七号|八号)",
            r"(\d+(?:\.\d+)?)\s*[号pt磅]",
        ]
        for pattern in size_patterns:
            match = re.search(pattern, desc)
            if match:
                pt = RuleNormalizer.cn_size_to_pt(match.group(1))
                if pt is not None:
                    style.font_size_pt = pt
                break

        # 提取加粗
        if "加粗" in desc:
            style.bold = True

        # 提取对齐
        if "居中" in desc:
            style.alignment = Alignment.CENTER

        # 提取斜体
        if "斜体" in desc:
            style.italic = True
