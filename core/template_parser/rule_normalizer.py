"""
规则标准化器 (Rule Normalizer)

将各种来源的排版规则标准化为统一的 FormattingRules。
主要功能：中文字号→磅值转换、单位统一、默认值填充。
"""

from __future__ import annotations

import re
from typing import Optional

from core.formatting_rules import (
    FormattingRules, StyleRules, PageRules, SectionRules,
)
from core.document_model import Alignment, LineSpacingType, PageNumberFormat


# 中文字号 → 磅值映射
CN_SIZE_MAP = {
    "初号": 42, "小初": 36,
    "一号": 26, "小一": 24,
    "二号": 22, "小二": 18,
    "三号": 16, "小三": 15,
    "四号": 14, "小四": 12,
    "五号": 10.5, "小五": 9,
    "六号": 7.5, "小六": 6.5,
    "七号": 5.5, "八号": 5,
}

# 磅值 → 中文字号（反向映射，取最接近的）
PT_TO_CN = {v: k for k, v in CN_SIZE_MAP.items()}


class RuleNormalizer:
    """排版规则标准化器"""

    @staticmethod
    def cn_size_to_pt(size_str: str) -> Optional[float]:
        """将中文字号转换为磅值

        Args:
            size_str: 中文字号，如"三号"、"小四"、"12pt"、"12磅"

        Returns:
            磅值，如 16.0；无法识别返回 None
        """
        if not size_str:
            return None

        size_str = size_str.strip()

        # 直接匹配中文字号
        if size_str in CN_SIZE_MAP:
            return CN_SIZE_MAP[size_str]

        # 匹配带"号"的
        clean = re.sub(r"[字号]", "", size_str).strip()
        if clean in CN_SIZE_MAP:
            return CN_SIZE_MAP[clean]

        # 匹配磅值格式：12pt、12磅、12
        match = re.match(r"^(\d+(?:\.\d+)?)\s*(pt|磅|磅值)?$", size_str, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None

    @staticmethod
    def pt_to_cn_size(pt: float) -> Optional[str]:
        """将磅值转换为最接近的中文字号"""
        if pt in PT_TO_CN:
            return PT_TO_CN[pt]
        # 找最接近的
        closest = min(PT_TO_CN.keys(), key=lambda x: abs(x - pt))
        if abs(closest - pt) < 0.3:
            return PT_TO_CN[closest]
        return None

    @staticmethod
    def parse_alignment(text: str) -> Optional[Alignment]:
        """解析对齐方式文本"""
        if not text:
            return None
        text = text.strip().lower()
        mapping = {
            "左对齐": Alignment.LEFT, "left": Alignment.LEFT, "靠左": Alignment.LEFT,
            "居中": Alignment.CENTER, "center": Alignment.CENTER, "居中对齐": Alignment.CENTER,
            "右对齐": Alignment.RIGHT, "right": Alignment.RIGHT, "靠右": Alignment.RIGHT,
            "两端对齐": Alignment.JUSTIFY, "justify": Alignment.JUSTIFY, "两端": Alignment.JUSTIFY,
        }
        return mapping.get(text)

    @staticmethod
    def parse_line_spacing(text: str) -> tuple[Optional[LineSpacingType], Optional[float]]:
        """解析行距文本

        Returns:
            (行距类型, 行距值)
        """
        if not text:
            return None, None
        text = text.strip()

        # 固定值：固定值20磅、20磅、固定值 20
        match = re.match(r"固定值\s*(\d+(?:\.\d+)?)\s*磅?", text)
        if match:
            return LineSpacingType.EXACT, float(match.group(1))

        match = re.match(r"(\d+(?:\.\d+)?)\s*磅", text)
        if match:
            return LineSpacingType.EXACT, float(match.group(1))

        # 倍数：1.5倍、1.5倍行距、单倍行距、双倍行距
        if "单倍" in text:
            return LineSpacingType.SINGLE, 1.0
        if "双倍" in text:
            return LineSpacingType.DOUBLE, 2.0

        match = re.match(r"(\d+(?:\.\d+)?)\s*倍", text)
        if match:
            value = float(match.group(1))
            if value == 1.0:
                return LineSpacingType.SINGLE, 1.0
            elif value == 1.5:
                return LineSpacingType.ONE_POINT_FIVE, 1.5
            elif value == 2.0:
                return LineSpacingType.DOUBLE, 2.0
            else:
                return LineSpacingType.MULTIPLE, value

        return None, None

    @staticmethod
    def parse_page_number_format(text: str) -> Optional[PageNumberFormat]:
        """解析页码格式"""
        if not text:
            return None
        text = text.strip().lower()
        mapping = {
            "阿拉伯数字": PageNumberFormat.ARABIC, "arabic": PageNumberFormat.ARABIC,
            "数字": PageNumberFormat.ARABIC,
            "大写罗马": PageNumberFormat.UPPER_ROMAN, "upper_roman": PageNumberFormat.UPPER_ROMAN,
            "罗马数字": PageNumberFormat.UPPER_ROMAN,
            "小写罗马": PageNumberFormat.LOWER_ROMAN, "lower_roman": PageNumberFormat.LOWER_ROMAN,
        }
        return mapping.get(text)

    @staticmethod
    def parse_margin(text: str) -> Optional[float]:
        """解析边距值（如"2.54cm"、"25.4mm"）"""
        if not text:
            return None
        text = text.strip()

        match = re.match(r"(\d+(?:\.\d+)?)\s*(cm|毫米|mm)", text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            if unit in ("mm", "毫米"):
                return value / 10.0
            return value

        return None

    @staticmethod
    def normalize_style_rules(raw: dict) -> StyleRules:
        """将原始字典标准化为 StyleRules"""
        rules = StyleRules()

        # 字体
        if "font" in raw or "字体" in raw:
            font = raw.get("font") or raw.get("字体", "")
            if isinstance(font, str):
                # 尝试区分中英文字体
                if any(c in font for c in "宋体黑体楷体仿宋微软雅黑方正"):
                    rules.font_name_cn = font
                else:
                    rules.font_name_en = font

        if "font_cn" in raw or "中文字体" in raw:
            rules.font_name_cn = raw.get("font_cn") or raw.get("中文字体")
        if "font_en" in raw or "英文字体" in raw:
            rules.font_name_en = raw.get("font_en") or raw.get("英文字体")

        # 字号
        size_raw = raw.get("size") or raw.get("字号") or raw.get("font_size")
        if size_raw:
            pt = RuleNormalizer.cn_size_to_pt(str(size_raw))
            if pt is not None:
                rules.font_size_pt = pt

        # 加粗/斜体/下划线
        if raw.get("bold") or raw.get("加粗"):
            rules.bold = True
        if raw.get("italic") or raw.get("斜体"):
            rules.italic = True
        if raw.get("underline") or raw.get("下划线"):
            rules.underline = True

        # 对齐
        align_raw = raw.get("align") or raw.get("对齐") or raw.get("alignment")
        if align_raw:
            rules.alignment = RuleNormalizer.parse_alignment(str(align_raw))

        # 缩进
        indent = raw.get("first_indent") or raw.get("首行缩进")
        if indent is not None:
            if isinstance(indent, (int, float)):
                rules.first_indent_chars = float(indent)
            elif isinstance(indent, str):
                match = re.match(r"(\d+)\s*字符?", indent)
                if match:
                    rules.first_indent_chars = float(match.group(1))

        # 行距
        spacing_raw = raw.get("line_spacing") or raw.get("行距")
        if spacing_raw:
            ls_type, ls_value = RuleNormalizer.parse_line_spacing(str(spacing_raw))
            if ls_type:
                rules.line_spacing_type = ls_type
            if ls_value is not None:
                rules.line_spacing_value = ls_value

        # 段前段后
        if "space_before" in raw or "段前" in raw:
            val = raw.get("space_before") or raw.get("段前")
            rules.space_before_pt = float(val) if val else None
        if "space_after" in raw or "段后" in raw:
            val = raw.get("space_after") or raw.get("段后")
            rules.space_after_pt = float(val) if val else None

        return rules

    @staticmethod
    def fill_defaults(rules: FormattingRules) -> FormattingRules:
        """用合理默认值填充规则中的 None 项"""
        # 正文默认值
        if rules.body.font_name_cn is None:
            rules.body.font_name_cn = "宋体"
        if rules.body.font_name_en is None:
            rules.body.font_name_en = "Times New Roman"
        if rules.body.font_size_pt is None:
            rules.body.font_size_pt = 12.0
        if rules.body.first_indent_chars is None:
            rules.body.first_indent_chars = 2

        # 页面默认值
        if rules.page.paper_size is None:
            rules.page.paper_size = "A4"

        return rules
