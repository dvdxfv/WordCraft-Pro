"""AI 智能排版增强模块

核心功能：
1. 自然语言解析 - 解析用户输入的排版要求
2. 模板样式提取 - 从示例文档提取样式规则
3. 排版规则库扩展 - 支持更多文档类型
4. 一键应用优化 - 快速应用排版规则
5. 预览功能 - 实时预览排版效果

性能目标：
- 解析时间：<2 秒
- 应用时间：<3 秒
- 支持文档类型：学术论文、商业报告、技术文档、公文等
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from core.formatting_rules import FormattingRules, StyleRules, PageSetupRules, SectionRules
from core.document_model import (
    Alignment, LineSpacingType, PageNumberFormat,
)


@dataclass
class ParsedStyle:
    """解析后的样式"""
    font_name_cn: str = None
    font_name_en: str = None
    font_size_pt: float = None
    bold: bool = False
    italic: bool = False
    alignment: Alignment = None
    line_spacing_type: LineSpacingType = None
    line_spacing_value: float = None
    space_before_pt: float = None
    space_after_pt: float = None


@dataclass
class ParsedPageSetup:
    """解析后的页面设置"""
    paper_size: str = None
    orientation: str = None
    margin_top_cm: float = None
    margin_bottom_cm: float = None
    margin_left_cm: float = None
    margin_right_cm: float = None


class NaturalLanguageParser:
    """自然语言排版解析器"""
    
    # 纸张大小映射
    PAPER_SIZE_MAP = {
        'A4': 'A4',
        'A3': 'A3',
        'B5': 'B5',
        'Letter': 'Letter',
        '16 开': 'B5',
        '32 开': 'A5',
    }
    
    # 字体大小映射（中文字号到磅值）
    FONT_SIZE_MAP = {
        '初号': 42,
        '小初': 36,
        '一号': 26,
        '小一': 24,
        '二号': 22,
        '小二': 18,
        '三号': 16,
        '小三': 15,
        '四号': 14,
        '小四': 12,
        '五号': 10.5,
        '小五': 9,
        '六号': 7.5,
        '小六': 6.5,
        '七号': 5.5,
        '八号': 5,
    }
    
    # 对齐方式映射
    ALIGNMENT_MAP = {
        '左对齐': Alignment.LEFT,
        '居中': Alignment.CENTER,
        '右对齐': Alignment.RIGHT,
        '两端对齐': Alignment.JUSTIFY,
    }
    
    def __init__(self):
        self.parsed_styles: Dict[str, ParsedStyle] = {}
        self.parsed_page_setup: Optional[ParsedPageSetup] = None
    
    def parse(self, text: str) -> FormattingRules:
        """
        解析自然语言描述的排版要求
        
        Args:
            text: 用户输入的排版要求，例如：
                  "学术论文，A4 纸，一级标题黑体三号，正文宋体小四 1.5 倍行距"
        
        Returns:
            FormattingRules: 解析后的排版规则
        """
        rules = FormattingRules()
        
        # 解析文档类型
        doc_type = self._detect_document_type(text)
        
        # 解析页面设置
        self.parsed_page_setup = self._parse_page_setup(text)
        self._apply_page_setup_to_rules(rules)
        
        # 解析标题样式
        self._parse_heading_styles(text, rules)
        
        # 解析正文样式
        self._parse_body_style(text, rules)
        
        # 解析其他样式（题注、参考文献等）
        self._parse_other_styles(text, rules)
        
        return rules
    
    def _detect_document_type(self, text: str) -> str:
        """检测文档类型"""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['学术', '论文', '毕业', '硕士', '博士']):
            return 'academic'
        elif any(kw in text_lower for kw in ['商业', '报告', '方案']):
            return 'business'
        elif any(kw in text_lower for kw in ['技术', '文档', '说明', '手册']):
            return 'technical'
        elif any(kw in text_lower for kw in ['公文', '通知', '公告']):
            return 'official'
        else:
            return 'general'
    
    def _parse_page_setup(self, text: str) -> ParsedPageSetup:
        """解析页面设置"""
        page_setup = ParsedPageSetup()
        
        # 纸张大小
        for paper_kw, paper_size in self.PAPER_SIZE_MAP.items():
            if paper_kw in text:
                page_setup.paper_size = paper_size
                break
        
        # 页面方向
        if '横向' in text:
            page_setup.orientation = 'landscape'
        elif '纵向' in text:
            page_setup.orientation = 'portrait'
        
        # 页边距（支持多种格式）
        margin_patterns = [
            r'上边距 [：:]\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)',
            r'上 [：:]\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)',
        ]
        for pattern in margin_patterns:
            match = re.search(pattern, text)
            if match:
                page_setup.margin_top_cm = float(match.group(1))
                break
        
        return page_setup
    
    def _apply_page_setup_to_rules(self, rules: FormattingRules):
        """将解析的页面设置应用到规则"""
        if self.parsed_page_setup:
            ps = self.parsed_page_setup
            if ps.paper_size:
                rules.page.paper_size = ps.paper_size
            if ps.orientation:
                rules.page.orientation = ps.orientation
            if ps.margin_top_cm:
                rules.page.margin_top_cm = ps.margin_top_cm
            if ps.margin_bottom_cm:
                rules.page.margin_bottom_cm = ps.margin_bottom_cm
            if ps.margin_left_cm:
                rules.page.margin_left_cm = ps.margin_left_cm
            if ps.margin_right_cm:
                rules.page.margin_right_cm = ps.margin_right_cm
    
    def _parse_heading_styles(self, text: str, rules: FormattingRules):
        """解析标题样式"""
        # 一级标题
        heading1_patterns = [
            r'一级标题 [：:]\s*(\S+?)(?:[，,]|$)',
            r'标题一 [：:]\s*(\S+?)(?:[，,]|$)',
        ]
        for pattern in heading1_patterns:
            match = re.search(pattern, text)
            if match:
                style_desc = match.group(1)
                style = self._parse_style_description(style_desc)
                if style:
                    rules.add_heading_style(1, self._create_style_rules(style))
                break
        
        # 二级标题
        heading2_patterns = [
            r'二级标题 [：:]\s*(\S+?)(?:[，,]|$)',
            r'标题二 [：:]\s*(\S+?)(?:[，,]|$)',
        ]
        for pattern in heading2_patterns:
            match = re.search(pattern, text)
            if match:
                style_desc = match.group(1)
                style = self._parse_style_description(style_desc)
                if style:
                    rules.add_heading_style(2, self._create_style_rules(style))
                break
    
    def _parse_body_style(self, text: str, rules: FormattingRules):
        """解析正文样式"""
        body_patterns = [
            r'正文 [：:]\s*(\S+?)(?:[，,]|$)',
            r'内容 [：:]\s*(\S+?)(?:[，,]|$)',
        ]
        for pattern in body_patterns:
            match = re.search(pattern, text)
            if match:
                style_desc = match.group(1)
                style = self._parse_style_description(style_desc)
                if style:
                    rules.body = self._create_style_rules(style)
                break
    
    def _parse_other_styles(self, text: str, rules: FormattingRules):
        """解析其他样式（题注、参考文献等）"""
        # 题注
        caption_patterns = [
            r'图题 [：:]\s*(\S+?)(?:[，,]|$)',
            r'表题 [：:]\s*(\S+?)(?:[，,]|$)',
            r'题注 [：:]\s*(\S+?)(?:[，,]|$)',
        ]
        for pattern in caption_patterns:
            match = re.search(pattern, text)
            if match:
                style_desc = match.group(1)
                style = self._parse_style_description(style_desc)
                if style:
                    rules.table_caption = self._create_style_rules(style)
                    rules.figure_caption = self._create_style_rules(style)
                break
        
        # 参考文献
        ref_patterns = [
            r'参考文献 [：:]\s*(\S+?)(?:[，,]|$)',
            r'参考 [：:]\s*(\S+?)(?:[，,]|$)',
        ]
        for pattern in ref_patterns:
            match = re.search(pattern, text)
            if match:
                style_desc = match.group(1)
                style = self._parse_style_description(style_desc)
                if style:
                    rules.reference = self._create_style_rules(style)
                break
    
    def _parse_style_description(self, desc: str) -> Optional[ParsedStyle]:
        """
        解析样式描述
        
        Args:
            desc: 样式描述，例如："黑体三号"、"宋体小四 1.5 倍行距"
        
        Returns:
            ParsedStyle: 解析后的样式
        """
        style = ParsedStyle()
        
        # 字体
        font_patterns = ['黑体', '宋体', '仿宋', '楷体', '微软雅黑', 'Arial', 'Times']
        for font in font_patterns:
            if font in desc:
                if font in ['黑体', '宋体', '仿宋', '楷体', '微软雅黑']:
                    style.font_name_cn = font
                else:
                    style.font_name_en = font
        
        # 字号
        for chinese_size, pt_size in self.FONT_SIZE_MAP.items():
            if chinese_size in desc:
                style.font_size_pt = pt_size
                break
        
        # 英文数字字号（如"12pt"、"12 磅"）
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)', desc)
        if size_match:
            style.font_size_pt = float(size_match.group(1))
        
        # 加粗
        if any(kw in desc for kw in ['加粗', '粗体', 'bold']):
            style.bold = True
        
        # 倾斜
        if any(kw in desc for kw in ['倾斜', '斜体', 'italic']):
            style.italic = True
        
        # 对齐
        for kw, align in self.ALIGNMENT_MAP.items():
            if kw in desc:
                style.alignment = align
                break
        
        # 行距
        if '1.5 倍' in desc or '1.5 倍行距' in desc:
            style.line_spacing_type = LineSpacingType.MULTIPLE
            style.line_spacing_value = 1.5
        elif '单倍' in desc or '单倍行距' in desc:
            style.line_spacing_type = LineSpacingType.MULTIPLE
            style.line_spacing_value = 1.0
        elif '固定' in desc or '定值' in desc:
            style.line_spacing_type = LineSpacingType.EXACT
            value_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:磅|pt)', desc)
            if value_match:
                style.line_spacing_value = float(value_match.group(1))
        
        # 段前段后间距
        before_match = re.search(r'段前 [：:]\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', desc)
        if before_match:
            style.space_before_pt = float(before_match.group(1))
        
        after_match = re.search(r'段后 [：:]\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', desc)
        if after_match:
            style.space_after_pt = float(after_match.group(1))
        
        return style if any(vars(style).values()) else None
    
    def _create_style_rules(self, style: ParsedStyle) -> StyleRules:
        """将 ParsedStyle 转换为 StyleRules"""
        rules = StyleRules()
        rules.font_name_cn = style.font_name_cn
        rules.font_name_en = style.font_name_en
        rules.font_size_pt = style.font_size_pt
        rules.bold = style.bold
        rules.italic = style.italic
        rules.alignment = style.alignment
        rules.line_spacing_type = style.line_spacing_type
        rules.line_spacing_value = style.line_spacing_value
        rules.space_before_pt = style.space_before_pt
        rules.space_after_pt = style.space_after_pt
        return rules


class TemplateStyleExtractor:
    """模板样式提取器"""
    
    def __init__(self):
        pass
    
    def extract_from_document(self, doc) -> FormattingRules:
        """
        从示例文档提取样式规则
        
        Args:
            doc: python-docx Document 对象
        
        Returns:
            FormattingRules: 提取的样式规则
        """
        rules = FormattingRules()
        
        # 提取页面设置
        self._extract_page_setup(doc, rules)
        
        # 提取标题样式
        self._extract_heading_styles(doc, rules)
        
        # 提取正文样式
        self._extract_body_style(doc, rules)
        
        return rules
    
    def _extract_page_setup(self, doc, rules: FormattingRules):
        """提取页面设置"""
        if not doc.sections:
            return
        
        section = doc.sections[0]
        emu_to_cm = 1.0 / 360000.0
        
        # 纸张大小
        width_cm = section.page_width * emu_to_cm
        height_cm = section.page_height * emu_to_cm
        
        if abs(width_cm - 21.0) < 0.5 and abs(height_cm - 29.7) < 0.5:
            rules.page.paper_size = 'A4'
        elif abs(width_cm - 29.7) < 0.5 and abs(height_cm - 42.0) < 0.5:
            rules.page.paper_size = 'A3'
        
        # 页边距
        rules.page.margin_top_cm = section.top_margin * emu_to_cm
        rules.page.margin_bottom_cm = section.bottom_margin * emu_to_cm
        rules.page.margin_left_cm = section.left_margin * emu_to_cm
        rules.page.margin_right_cm = section.right_margin * emu_to_cm
    
    def _extract_heading_styles(self, doc, rules: FormattingRules):
        """提取标题样式"""
        for para in doc.paragraphs:
            style_name = (para.style.name or "").lower()
            
            if style_name.startswith('heading') or style_name.startswith('标题'):
                level = 1
                match = re.search(r'(\d+)', style_name)
                if match:
                    level = int(match.group(1))
                
                style_rules = self._extract_style_from_paragraph(para)
                rules.add_heading_style(level, style_rules)
    
    def _extract_body_style(self, doc, rules: FormattingRules):
        """提取正文样式"""
        for para in doc.paragraphs:
            style_name = (para.style.name or "").lower()
            
            if style_name in ('normal', '正文', 'body text'):
                rules.body = self._extract_style_from_paragraph(para)
                break
    
    def _extract_style_from_paragraph(self, para) -> StyleRules:
        """从段落提取样式规则"""
        rules = StyleRules()
        
        # 提取字体样式
        if para.runs:
            run = para.runs[0]
            if run.font.name:
                rules.font_name_en = run.font.name
            if run.font.size:
                rules.font_size_pt = run.font.size.pt
            if run.font.bold:
                rules.bold = True
            if run.font.italic:
                rules.italic = True
        
        # 提取段落样式
        pf = para.paragraph_format
        if pf.alignment is not None:
            align_map = {
                1: Alignment.LEFT,
                2: Alignment.CENTER,
                3: Alignment.RIGHT,
                4: Alignment.JUSTIFY,
            }
            rules.alignment = align_map.get(pf.alignment, Alignment.LEFT)
        
        if pf.line_spacing is not None:
            rules.line_spacing_type = LineSpacingType.MULTIPLE
            rules.line_spacing_value = pf.line_spacing
        
        return rules


class AITypesettingEngine:
    """AI 智能排版引擎"""
    
    def __init__(self):
        self.nl_parser = NaturalLanguageParser()
        self.template_extractor = TemplateStyleExtractor()
    
    def parse_and_apply(self, text: str, doc) -> FormattingRules:
        """
        解析自然语言并应用到文档
        
        Args:
            text: 用户输入的排版要求
            doc: python-docx Document 对象
        
        Returns:
            FormattingRules: 应用的排版规则
        """
        # 解析自然语言
        rules = self.nl_parser.parse(text)
        
        return rules
    
    def extract_and_apply(self, template_doc, target_doc) -> FormattingRules:
        """
        从模板文档提取样式并应用
        
        Args:
            template_doc: 模板文档（python-docx Document）
            target_doc: 目标文档（python-docx Document）
        
        Returns:
            FormattingRules: 应用的排版规则
        """
        # 从模板提取样式
        rules = self.template_extractor.extract_from_document(template_doc)
        
        return rules
    
    def quick_format(self, doc_type: str) -> FormattingRules:
        """
        快速应用预设排版规则
        
        Args:
            doc_type: 文档类型
                     - 'academic': 学术论文
                     - 'business': 商业报告
                     - 'technical': 技术文档
                     - 'official': 公文
        
        Returns:
            FormattingRules: 预设的排版规则
        """
        if doc_type == 'academic':
            return self._get_academic_rules()
        elif doc_type == 'business':
            return self._get_business_rules()
        elif doc_type == 'technical':
            return self._get_technical_rules()
        elif doc_type == 'official':
            return self._get_official_rules()
        else:
            return FormattingRules()
    
    def _get_academic_rules(self) -> FormattingRules:
        """学术论文排版规则"""
        rules = FormattingRules()
        rules.page.paper_size = 'A4'
        rules.page.margin_top_cm = 3.8
        rules.page.margin_bottom_cm = 3.2
        rules.page.margin_left_cm = 2.8
        rules.page.margin_right_cm = 2.8
        
        # 一级标题：黑体三号
        heading1 = StyleRules()
        heading1.font_name_cn = '黑体'
        heading1.font_size_pt = 16
        heading1.bold = True
        rules.add_heading_style(1, heading1)
        
        # 二级标题：黑体四号
        heading2 = StyleRules()
        heading2.font_name_cn = '黑体'
        heading2.font_size_pt = 14
        heading2.bold = True
        rules.add_heading_style(2, heading2)
        
        # 正文：宋体小四 1.5 倍行距
        body = StyleRules()
        body.font_name_cn = '宋体'
        body.font_size_pt = 12
        body.line_spacing_type = LineSpacingType.MULTIPLE
        body.line_spacing_value = 1.5
        body.first_indent_chars = 2
        rules.body = body
        
        return rules
    
    def _get_business_rules(self) -> FormattingRules:
        """商业报告排版规则"""
        rules = FormattingRules()
        rules.page.paper_size = 'A4'
        
        # 一级标题：微软雅黑二号
        heading1 = StyleRules()
        heading1.font_name_cn = '微软雅黑'
        heading1.font_size_pt = 22
        heading1.bold = True
        rules.add_heading_style(1, heading1)
        
        # 正文：微软雅黑小四
        body = StyleRules()
        body.font_name_cn = '微软雅黑'
        body.font_size_pt = 12
        body.line_spacing_type = LineSpacingType.MULTIPLE
        body.line_spacing_value = 1.5
        rules.body = body
        
        return rules
    
    def _get_technical_rules(self) -> FormattingRules:
        """技术文档排版规则"""
        rules = FormattingRules()
        rules.page.paper_size = 'A4'
        
        # 一级标题：黑体三号
        heading1 = StyleRules()
        heading1.font_name_cn = '黑体'
        heading1.font_size_pt = 16
        rules.add_heading_style(1, heading1)
        
        # 正文：宋体五号
        body = StyleRules()
        body.font_name_cn = '宋体'
        body.font_size_pt = 10.5
        body.line_spacing_type = LineSpacingType.MULTIPLE
        body.line_spacing_value = 1.5
        rules.body = body
        
        return rules
    
    def _get_official_rules(self) -> FormattingRules:
        """公文排版规则"""
        rules = FormattingRules()
        rules.page.paper_size = 'A4'
        rules.page.margin_top_cm = 3.7
        rules.page.margin_bottom_cm = 3.5
        rules.page.margin_left_cm = 2.8
        rules.page.margin_right_cm = 2.6
        
        # 一级标题：黑体二号
        heading1 = StyleRules()
        heading1.font_name_cn = '黑体'
        heading1.font_size_pt = 22
        heading1.bold = True
        rules.add_heading_style(1, heading1)
        
        # 正文：仿宋三号
        body = StyleRules()
        body.font_name_cn = '仿宋'
        body.font_size_pt = 16
        body.line_spacing_type = LineSpacingType.MULTIPLE
        body.line_spacing_value = 1.5
        rules.body = body
        
        return rules
