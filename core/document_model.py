"""
统一文档模型 (Document Model)

所有文件解析器的输出统一转换为此模型，排版引擎和质量检查引擎均基于此模型工作。
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ============================================================
# 枚举类型
# ============================================================

class ElementType(Enum):
    """文档元素类型"""
    HEADING = "heading"           # 标题
    PARAGRAPH = "paragraph"       # 段落
    TABLE = "table"               # 表格
    LIST = "list"                 # 列表
    LIST_ITEM = "list_item"       # 列表项
    IMAGE = "image"               # 图片
    CODE_BLOCK = "code_block"     # 代码块
    PAGE_BREAK = "page_break"     # 分页符
    SECTION_BREAK = "section_break"  # 分节符
    TOC = "toc"                   # 目录
    HEADER = "header"             # 页眉
    FOOTER = "footer"             # 页脚
    CAPTION = "caption"           # 题注（图题/表题）
    EQUATION = "equation"         # 公式
    REFERENCE = "reference"       # 参考文献条目
    BOOKMARK = "bookmark"         # 书签
    CROSS_REF = "cross_ref"       # 交叉引用


class Alignment(Enum):
    """对齐方式"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class LineSpacingType(Enum):
    """行距类型"""
    SINGLE = "single"             # 单倍行距
    ONE_POINT_FIVE = "1.5"        # 1.5倍行距
    DOUBLE = "double"             # 双倍行距
    EXACT = "exact"               # 固定值（磅）
    AT_LEAST = "at_least"         # 最小值（磅）
    MULTIPLE = "multiple"         # 多倍行距


class NumberingType(Enum):
    """编号类型"""
    DECIMAL = "decimal"           # 1, 2, 3...
    CHINESE_UPPER = "chinese_upper"  # 一、二、三...
    CHINESE_LOWER = "chinese_lower"  # （一）（二）...
    LOWER_LETTER = "lower_letter"    # a, b, c...
    UPPER_LETTER = "upper_letter"    # A, B, C...
    LOWER_ROMAN = "lower_roman"      # i, ii, iii...
    UPPER_ROMAN = "upper_roman"      # I, II, III...
    BULLET = "bullet"             # 项目符号


class PageNumberFormat(Enum):
    """页码格式"""
    ARABIC = "arabic"             # 1, 2, 3...
    UPPER_ROMAN = "upper_roman"   # I, II, III...
    LOWER_ROMAN = "lower_roman"   # i, ii, iii...
    UPPER_LETTER = "upper_letter" # A, B, C...
    LOWER_LETTER = "lower_letter" # a, b, c...
    CIRCLED_NUMBER = "circled"    # ①②③...


# ============================================================
# 样式数据类
# ============================================================

@dataclass
class FontStyle:
    """字体样式"""
    font_name_cn: str = ""         # 中文字体（如"宋体"）
    font_name_en: str = ""         # 英文字体（如"Times New Roman"）
    font_size_pt: float = 0.0      # 字号（磅）
    bold: bool = False             # 加粗
    italic: bool = False           # 斜体
    underline: bool = False        # 下划线
    strike_through: bool = False   # 删除线
    color: str = ""                # 颜色（十六进制，如"FF0000"）
    super_script: bool = False     # 上标
    sub_script: bool = False       # 下标

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "font_name_cn": self.font_name_cn,
            "font_name_en": self.font_name_en,
            "font_size_pt": self.font_size_pt,
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "strike_through": self.strike_through,
            "color": self.color,
            "super_script": self.super_script,
            "sub_script": self.sub_script,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FontStyle:
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ParagraphStyle:
    """段落样式"""
    alignment: Alignment = Alignment.JUSTIFY
    first_indent_chars: float = 0.0    # 首行缩进（字符数）
    first_indent_cm: float = 0.0       # 首行缩进（厘米）
    left_indent_cm: float = 0.0        # 左缩进（厘米）
    right_indent_cm: float = 0.0       # 右缩进（厘米）
    line_spacing_type: LineSpacingType = LineSpacingType.SINGLE
    line_spacing_value: float = 1.0    # 行距值（倍数或磅值）
    space_before_pt: float = 0.0       # 段前间距（磅）
    space_after_pt: float = 0.0        # 段后间距（磅）
    keep_with_next: bool = False       # 段前分页
    keep_lines_together: bool = False  # 段中不分页
    page_break_before: bool = False    # 段前分页

    def to_dict(self) -> dict:
        return {
            "alignment": self.alignment.value if isinstance(self.alignment, Alignment) else self.alignment,
            "first_indent_chars": self.first_indent_chars,
            "first_indent_cm": self.first_indent_cm,
            "left_indent_cm": self.left_indent_cm,
            "right_indent_cm": self.right_indent_cm,
            "line_spacing_type": self.line_spacing_type.value if isinstance(self.line_spacing_type, LineSpacingType) else self.line_spacing_type,
            "line_spacing_value": self.line_spacing_value,
            "space_before_pt": self.space_before_pt,
            "space_after_pt": self.space_after_pt,
            "keep_with_next": self.keep_with_next,
            "keep_lines_together": self.keep_lines_together,
            "page_break_before": self.page_break_before,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ParagraphStyle:
        d = copy.deepcopy(data)
        if "alignment" in d and isinstance(d["alignment"], str):
            d["alignment"] = Alignment(d["alignment"])
        if "line_spacing_type" in d and isinstance(d["line_spacing_type"], str):
            d["line_spacing_type"] = LineSpacingType(d["line_spacing_type"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ============================================================
# 文档元素
# ============================================================

@dataclass
class DocElement:
    """文档元素（统一文档模型的核心单元）"""
    element_type: ElementType
    content: str = ""                       # 文本内容
    level: int = 0                          # 标题层级 (1-6)，0表示非标题
    font_style: FontStyle = field(default_factory=FontStyle)
    paragraph_style: ParagraphStyle = field(default_factory=ParagraphStyle)
    style_name: str = ""                    # 原始样式名（来自docx等）
    numbering_type: Optional[NumberingType] = None  # 编号类型
    numbering_text: str = ""                # 编号文本（如"一、""1."）
    children: list[DocElement] = field(default_factory=list)  # 子元素
    metadata: dict = field(default_factory=dict)  # 额外信息

    # 内部标识
    _id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """递归转换为字典"""
        result = {
            "id": self._id,
            "element_type": self.element_type.value,
            "content": self.content,
            "level": self.level,
            "font_style": self.font_style.to_dict(),
            "paragraph_style": self.paragraph_style.to_dict(),
            "style_name": self.style_name,
            "numbering_type": self.numbering_type.value if self.numbering_type else None,
            "numbering_text": self.numbering_text,
            "metadata": self.metadata,
        }
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> DocElement:
        """从字典创建"""
        d = copy.deepcopy(data)
        d["element_type"] = ElementType(d["element_type"])
        if d.get("numbering_type"):
            d["numbering_type"] = NumberingType(d["numbering_type"])
        d["font_style"] = FontStyle.from_dict(d.get("font_style", {}))
        d["paragraph_style"] = ParagraphStyle.from_dict(d.get("paragraph_style", {}))
        d["children"] = [cls.from_dict(c) for c in d.get("children", [])]
        d["_id"] = d.pop("id", str(uuid.uuid4())[:8])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def get_text(self) -> str:
        """获取元素及其所有子元素的纯文本"""
        parts = [self.content]
        for child in self.children:
            parts.append(child.get_text())
        return "".join(parts)

    def find_elements(self, element_type: ElementType) -> list[DocElement]:
        """递归查找指定类型的所有元素"""
        results = []
        if self.element_type == element_type:
            results.append(self)
        for child in self.children:
            results.extend(child.find_elements(element_type))
        return results


# ============================================================
# 表格模型
# ============================================================

@dataclass
class TableCell:
    """表格单元格"""
    content: str = ""
    font_style: FontStyle = field(default_factory=FontStyle)
    paragraph_style: ParagraphStyle = field(default_factory=ParagraphStyle)
    row_span: int = 1        # 行合并
    col_span: int = 1        # 列合并
    is_header: bool = False  # 是否为表头单元格
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "font_style": self.font_style.to_dict(),
            "paragraph_style": self.paragraph_style.to_dict(),
            "row_span": self.row_span,
            "col_span": self.col_span,
            "is_header": self.is_header,
            "metadata": self.metadata,
        }


@dataclass
class TableData:
    """表格数据"""
    rows: list[list[TableCell]] = field(default_factory=list)
    caption: str = ""           # 表题
    caption_position: str = "above"  # "above" 或 "below"
    numbering: str = ""         # 表序号（如"表2-1"）
    alignment: Alignment = Alignment.CENTER
    border_visible: bool = True
    repeat_header: bool = True  # 跨页重复表头
    metadata: dict = field(default_factory=dict)

    @property
    def num_rows(self) -> int:
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        return max((len(row) for row in self.rows), default=0)

    def to_dict(self) -> dict:
        return {
            "rows": [[cell.to_dict() for cell in row] for row in self.rows],
            "caption": self.caption,
            "caption_position": self.caption_position,
            "numbering": self.numbering,
            "alignment": self.alignment.value,
            "border_visible": self.border_visible,
            "repeat_header": self.repeat_header,
            "metadata": self.metadata,
        }


# ============================================================
# 图片模型
# ============================================================

@dataclass
class ImageData:
    """图片数据"""
    caption: str = ""           # 图题
    caption_position: str = "below"  # "above" 或 "below"
    numbering: str = ""         # 图序号（如"图2-1"）
    file_path: str = ""         # 图片文件路径
    width_cm: float = 0.0       # 宽度（厘米）
    height_cm: float = 0.0      # 高度（厘米）
    alignment: Alignment = Alignment.CENTER
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "caption": self.caption,
            "caption_position": self.caption_position,
            "numbering": self.numbering,
            "file_path": self.file_path,
            "width_cm": self.width_cm,
            "height_cm": self.height_cm,
            "alignment": self.alignment.value,
            "metadata": self.metadata,
        }


# ============================================================
# 页面设置
# ============================================================

@dataclass
class PageSetup:
    """页面设置"""
    paper_size: str = "A4"              # 纸张大小
    orientation: str = "portrait"       # 方向：portrait / landscape
    margin_top_cm: float = 2.54
    margin_bottom_cm: float = 2.54
    margin_left_cm: float = 3.17
    margin_right_cm: float = 3.17
    gutter_cm: float = 0.0              # 装订线
    header_distance_cm: float = 1.5     # 页眉距边界
    footer_distance_cm: float = 1.75    # 页脚距边界

    def to_dict(self) -> dict:
        return {
            "paper_size": self.paper_size,
            "orientation": self.orientation,
            "margin_top_cm": self.margin_top_cm,
            "margin_bottom_cm": self.margin_bottom_cm,
            "margin_left_cm": self.margin_left_cm,
            "margin_right_cm": self.margin_right_cm,
            "gutter_cm": self.gutter_cm,
            "header_distance_cm": self.header_distance_cm,
            "footer_distance_cm": self.footer_distance_cm,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PageSetup:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================
# 节配置（多节页眉页脚）
# ============================================================

@dataclass
class HeaderFooterConfig:
    """页眉页脚配置"""
    text: str = ""
    font_name: str = ""
    font_size_pt: float = 10.5
    bold: bool = False
    alignment: Alignment = Alignment.CENTER

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "font_name": self.font_name,
            "font_size_pt": self.font_size_pt,
            "bold": self.bold,
            "alignment": self.alignment.value if isinstance(self.alignment, Alignment) else self.alignment,
        }


@dataclass
class PageNumberConfig:
    """页码配置"""
    enabled: bool = True
    format: str = "{num}"                # 格式模板，如"－ {num} －"
    number_format: PageNumberFormat = PageNumberFormat.ARABIC
    start_from: Optional[int] = None     # 起始页码（None表示续前节）
    font_name: str = ""
    font_size_pt: float = 10.5
    alignment: Alignment = Alignment.CENTER

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "format": self.format,
            "number_format": self.number_format.value if isinstance(self.number_format, PageNumberFormat) else self.number_format,
            "start_from": self.start_from,
            "font_name": self.font_name,
            "font_size_pt": self.font_size_pt,
            "alignment": self.alignment.value if isinstance(self.alignment, Alignment) else self.alignment,
        }


@dataclass
class SectionConfig:
    """节配置（每个分节符对应的页眉页脚设置）"""
    name: str = ""                       # 节名称（如"封面""正文"）
    first_page_different: bool = False   # 首页不同
    header: Optional[HeaderFooterConfig] = None       # 默认页眉
    first_page_header: Optional[HeaderFooterConfig] = None  # 首页页眉
    footer: Optional[HeaderFooterConfig] = None       # 默认页脚
    first_page_footer: Optional[HeaderFooterConfig] = None  # 首页页脚
    page_number: PageNumberConfig = field(default_factory=PageNumberConfig)

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "first_page_different": self.first_page_different,
            "header": self.header.to_dict() if self.header else None,
            "first_page_header": self.first_page_header.to_dict() if self.first_page_header else None,
            "footer": self.footer.to_dict() if self.footer else None,
            "first_page_footer": self.first_page_footer.to_dict() if self.first_page_footer else None,
            "page_number": self.page_number.to_dict(),
        }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> SectionConfig:
        """从字典创建"""
        d = copy.deepcopy(data)
        # 反序列化嵌套的 HeaderFooterConfig
        for key in ("header", "first_page_header", "footer", "first_page_footer"):
            if d.get(key) is not None and isinstance(d[key], dict):
                d[key] = HeaderFooterConfig(**{k: v for k, v in d[key].items() if k in HeaderFooterConfig.__dataclass_fields__})
        # 反序列化 PageNumberConfig
        if "page_number" in d and isinstance(d["page_number"], dict):
            pn = d["page_number"]
            if "number_format" in pn and isinstance(pn["number_format"], str):
                pn["number_format"] = PageNumberFormat(pn["number_format"])
            if "alignment" in pn and isinstance(pn["alignment"], str):
                pn["alignment"] = Alignment(pn["alignment"])
            d["page_number"] = PageNumberConfig(**{k: v for k, v in pn.items() if k in PageNumberConfig.__dataclass_fields__})
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ============================================================
# 文档模型（顶层）
# ============================================================

@dataclass
class DocumentModel:
    """统一文档模型 — 所有解析器的输出、排版引擎和质量检查引擎的输入"""
    # 元数据
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    created_date: str = ""
    source_file: str = ""          # 来源文件路径
    source_format: str = ""        # 来源格式（docx/pdf/xlsx/txt/md）

    # 文档内容
    elements: list[DocElement] = field(default_factory=list)

    # 表格数据（独立存储，便于表格操作）
    tables: list[TableData] = field(default_factory=list)

    # 图片数据（独立存储）
    images: list[ImageData] = field(default_factory=list)

    # 页面设置
    page_setup: PageSetup = field(default_factory=PageSetup)

    # 多节配置（页眉页脚）
    sections: list[SectionConfig] = field(default_factory=list)

    # 额外元数据
    metadata: dict = field(default_factory=dict)

    # ---- 便捷方法 ----

    def get_all_text(self) -> str:
        """获取文档全部纯文本"""
        parts = []
        for elem in self.elements:
            parts.append(elem.get_text())
        return "\n".join(parts)

    def find_elements(self, element_type: ElementType) -> list[DocElement]:
        """在所有元素中递归查找指定类型"""
        results = []
        for elem in self.elements:
            results.extend(elem.find_elements(element_type))
        return results

    def get_headings(self, max_level: int = 0) -> list[DocElement]:
        """获取所有标题，可限制最大层级"""
        headings = self.find_elements(ElementType.HEADING)
        if max_level > 0:
            headings = [h for h in headings if h.level <= max_level]
        return headings

    def get_paragraphs(self) -> list[DocElement]:
        """获取所有正文段落"""
        return self.find_elements(ElementType.PARAGRAPH)

    def get_references(self) -> list[DocElement]:
        """获取所有参考文献条目"""
        return self.find_elements(ElementType.REFERENCE)

    def get_equations(self) -> list[DocElement]:
        """获取所有公式"""
        return self.find_elements(ElementType.EQUATION)

    def get_captions(self) -> list[DocElement]:
        """获取所有题注"""
        return self.find_elements(ElementType.CAPTION)

    def get_cross_refs(self) -> list[DocElement]:
        """获取所有交叉引用"""
        return self.find_elements(ElementType.CROSS_REF)

    def element_count(self) -> dict[str, int]:
        """统计各类型元素数量"""
        counts: dict[str, int] = {}
        for elem in self.elements:
            self._count_recursive(elem, counts)
        return counts

    def _count_recursive(self, elem: DocElement, counts: dict[str, int]):
        t = elem.element_type.value
        counts[t] = counts.get(t, 0) + 1
        for child in elem.children:
            self._count_recursive(child, counts)

    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "keywords": self.keywords,
            "created_date": self.created_date,
            "source_file": self.source_file,
            "source_format": self.source_format,
            "elements": [e.to_dict() for e in self.elements],
            "tables": [t.to_dict() for t in self.tables],
            "images": [i.to_dict() for i in self.images],
            "page_setup": self.page_setup.to_dict(),
            "sections": [s.to_dict() for s in self.sections],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocumentModel:
        """从字典创建（用于反序列化）"""
        d = copy.deepcopy(data)
        d["elements"] = [DocElement.from_dict(e) for e in d.get("elements", [])]
        d["tables"] = [TableData(**{k: v for k, v in t.items() if k in TableData.__dataclass_fields__}) for t in d.get("tables", [])]
        d["images"] = [ImageData(**{k: v for k, v in i.items() if k in ImageData.__dataclass_fields__}) for i in d.get("images", [])]
        d["page_setup"] = PageSetup.from_dict(d.get("page_setup", {}))
        d["sections"] = [SectionConfig.from_dict(s) for s in d.get("sections", [])]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        """序列化为JSON字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> DocumentModel:
        """从JSON字符串反序列化"""
        import json
        return cls.from_dict(json.loads(json_str))
