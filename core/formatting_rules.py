"""
排版规则模型 (Formatting Rules)

从模板文件或用户需求中解析出的结构化排版规则，排版引擎据此对文档进行格式化。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Optional

from .document_model import Alignment, LineSpacingType, PageNumberFormat


# ============================================================
# 排版规则 — 各维度
# ============================================================

@dataclass
class PageRules:
    """页面排版规则"""
    paper_size: str = "A4"
    orientation: str = "portrait"
    margin_top_cm: Optional[float] = None
    margin_bottom_cm: Optional[float] = None
    margin_left_cm: Optional[float] = None
    margin_right_cm: Optional[float] = None
    gutter_cm: Optional[float] = None
    header_distance_cm: Optional[float] = None
    footer_distance_cm: Optional[float] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> PageRules:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StyleRules:
    """元素样式规则"""
    font_name_cn: Optional[str] = None       # 中文字体
    font_name_en: Optional[str] = None       # 英文字体
    font_size_pt: Optional[float] = None     # 字号（磅）
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    color: Optional[str] = None
    alignment: Optional[Alignment] = None
    first_indent_chars: Optional[float] = None
    first_indent_cm: Optional[float] = None
    left_indent_cm: Optional[float] = None
    right_indent_cm: Optional[float] = None
    line_spacing_type: Optional[LineSpacingType] = None
    line_spacing_value: Optional[float] = None
    space_before_pt: Optional[float] = None
    space_after_pt: Optional[float] = None
    keep_with_next: Optional[bool] = None
    keep_lines_together: Optional[bool] = None

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if isinstance(v, Alignment):
                d[k] = v.value
            elif isinstance(v, LineSpacingType):
                d[k] = v.value
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: dict) -> StyleRules:
        d = copy.deepcopy(data)
        if "alignment" in d and isinstance(d["alignment"], str):
            d["alignment"] = Alignment(d["alignment"])
        if "line_spacing_type" in d and isinstance(d["line_spacing_type"], str):
            d["line_spacing_type"] = LineSpacingType(d["line_spacing_type"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def merge(self, other: StyleRules) -> StyleRules:
        """合并另一组规则（other中的非None值覆盖self）"""
        merged = copy.deepcopy(self)
        for k, v in other.__dict__.items():
            if v is not None:
                setattr(merged, k, v)
        return merged


@dataclass
class SectionRules:
    """节规则（页眉页脚）"""
    name: str = ""
    first_page_different: Optional[bool] = None
    header_text: Optional[str] = None
    header_font: Optional[str] = None
    header_size_pt: Optional[float] = None
    header_bold: Optional[bool] = None
    header_alignment: Optional[Alignment] = None
    first_page_header_text: Optional[str] = None
    first_page_header_font: Optional[str] = None
    first_page_header_size_pt: Optional[float] = None
    first_page_header_bold: Optional[bool] = None
    page_number_enabled: Optional[bool] = None
    page_number_format: Optional[str] = None       # 格式模板
    page_number_type: Optional[PageNumberFormat] = None
    page_number_start_from: Optional[int] = None
    page_number_font: Optional[str] = None
    page_number_size_pt: Optional[float] = None
    page_number_alignment: Optional[Alignment] = None

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if isinstance(v, (Alignment, PageNumberFormat)):
                d[k] = v.value
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: dict) -> SectionRules:
        d = copy.deepcopy(data)
        if "header_alignment" in d and isinstance(d["header_alignment"], str):
            d["header_alignment"] = Alignment(d["header_alignment"])
        if "page_number_type" in d and isinstance(d["page_number_type"], str):
            d["page_number_type"] = PageNumberFormat(d["page_number_type"])
        if "page_number_alignment" in d and isinstance(d["page_number_alignment"], str):
            d["page_number_alignment"] = Alignment(d["page_number_alignment"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CrossRefRules:
    """交叉引用规则"""
    enabled: bool = False
    figure_pattern: str = "图{chapter}-{seq}"       # 图编号模式
    table_pattern: str = "表{chapter}-{seq}"         # 表编号模式
    equation_pattern: str = "({chapter}-{seq})"      # 公式编号模式
    reference_pattern: str = "[{seq}]"               # 参考文献编号模式
    auto_scan: bool = True                           # 自动扫描引用点
    interact_confirm: bool = True                    # 交互确认

    def to_dict(self) -> dict:
        return self.__dict__.copy()


# ============================================================
# 排版规则 — 顶层
# ============================================================

@dataclass
class FormattingRules:
    """排版规则（顶层）— 从模板或需求解析而来"""
    template_name: str = ""
    template_type: str = ""  # thesis / report / gov_doc / custom

    # 页面规则
    page: PageRules = field(default_factory=PageRules)

    # 各元素样式规则
    title: StyleRules = field(default_factory=StyleRules)
    heading1: StyleRules = field(default_factory=StyleRules)
    heading2: StyleRules = field(default_factory=StyleRules)
    heading3: StyleRules = field(default_factory=StyleRules)
    heading4: StyleRules = field(default_factory=StyleRules)
    body: StyleRules = field(default_factory=StyleRules)
    table_caption: StyleRules = field(default_factory=StyleRules)
    figure_caption: StyleRules = field(default_factory=StyleRules)
    table_body: StyleRules = field(default_factory=StyleRules)
    reference: StyleRules = field(default_factory=StyleRules)
    toc: StyleRules = field(default_factory=StyleRules)

    # 多节配置
    sections: list[SectionRules] = field(default_factory=list)

    # 交叉引用
    cross_reference: CrossRefRules = field(default_factory=CrossRefRules)

    # 标题编号格式
    heading1_numbering: str = ""     # 如 "一、二、三、..."
    heading2_numbering: str = ""     # 如 "（一）（二）..."
    heading3_numbering: str = ""     # 如 "1. 2. 3. ..."
    heading4_numbering: str = ""     # 如 "（1）（2）..."

    # 特殊规则
    special_rules: dict = field(default_factory=dict)

    def get_heading_style(self, level: int) -> Optional[StyleRules]:
        """根据标题层级获取对应的样式规则"""
        mapping = {1: self.heading1, 2: self.heading2, 3: self.heading3, 4: self.heading4}
        return mapping.get(level)

    def get_heading_numbering(self, level: int) -> str:
        """根据标题层级获取编号格式"""
        mapping = {1: self.heading1_numbering, 2: self.heading2_numbering,
                   3: self.heading3_numbering, 4: self.heading4_numbering}
        return mapping.get(level, "")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "template_name": self.template_name,
            "template_type": self.template_type,
            "page": self.page.to_dict(),
            "title": self.title.to_dict(),
            "heading1": self.heading1.to_dict(),
            "heading2": self.heading2.to_dict(),
            "heading3": self.heading3.to_dict(),
            "heading4": self.heading4.to_dict(),
            "body": self.body.to_dict(),
            "table_caption": self.table_caption.to_dict(),
            "figure_caption": self.figure_caption.to_dict(),
            "table_body": self.table_body.to_dict(),
            "reference": self.reference.to_dict(),
            "toc": self.toc.to_dict(),
            "sections": [s.to_dict() for s in self.sections],
            "cross_reference": self.cross_reference.to_dict(),
            "heading1_numbering": self.heading1_numbering,
            "heading2_numbering": self.heading2_numbering,
            "heading3_numbering": self.heading3_numbering,
            "heading4_numbering": self.heading4_numbering,
            "special_rules": self.special_rules,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FormattingRules:
        """从字典创建"""
        d = copy.deepcopy(data)
        d["page"] = PageRules.from_dict(d.get("page", {}))
        for key in ["title", "heading1", "heading2", "heading3", "heading4",
                     "body", "table_caption", "figure_caption", "table_body",
                     "reference", "toc"]:
            d[key] = StyleRules.from_dict(d.get(key, {}))
        d["sections"] = [SectionRules.from_dict(s) for s in d.get("sections", [])]
        d["cross_reference"] = CrossRefRules(**d.get("cross_reference", {}))
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_yaml(self) -> str:
        """序列化为YAML"""
        try:
            import yaml
            return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")

    @classmethod
    def from_yaml(cls, yaml_str: str) -> FormattingRules:
        """从YAML反序列化"""
        try:
            import yaml
            data = yaml.safe_load(yaml_str)
            return cls.from_dict(data)
        except ImportError:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")

    def to_json(self) -> str:
        """序列化为JSON"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> FormattingRules:
        """从JSON反序列化"""
        import json
        return cls.from_dict(json.loads(json_str))
