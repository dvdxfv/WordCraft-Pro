"""
文档结构识别层 (Document Structure Classifier)

为每个段落级元素打上 ``metadata.structure_role``、``structure_confidence``、
``structure_reason``、``exclude_from_format_body``、``exclude_from_xref_targets``，
让 FormatChecker / CrossRefEngine 等下游消费方知道哪些段落属于封面、目录、参考
文献等区域，从而避免把它们当成正文标题或正文段落来检查。

设计要点：

- 纯规则、零 AI、不引入新依赖。
- 双入口函数：``classify_dicts`` (app.py._parse_docx 路径，元素是 dict)
  与 ``classify_elements`` (parsers/docx_parser.py 路径，元素是 DocElement)，
  内部共享同一套启发式，避免两套分类长期分叉。
- 原地写入 metadata；不复制元素列表，方便上游链路保持引用相同对象。
- 每条元素都会被打上 role + confidence + reason，由消费方决定阈值。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from core.document_model import DocElement, ElementType


# ============================================================
# 公共常量
# ============================================================

DEFAULT_FORMAT_THRESHOLD = 0.6
"""confidence >= 此值时，结构性区域 (cover/toc/reference/caption/table) 会被
设置 ``exclude_from_format_body=True``，FormatChecker 会跳过它们。"""

DEFAULT_XREF_THRESHOLD = 0.7
"""confidence >= 此值时，cover/toc 元素会被设置 ``exclude_from_xref_targets
=True``，TargetScanner 跳过它们以避免把目录章节当作真章节。"""


_BODY_ROLE = "body"
_KNOWN_ROLES = (
    "cover",
    "toc",
    "title",
    "heading",
    "body",
    "abstract",
    "reference",
    "caption",
    "table",
    "unknown",
)


# ============================================================
# 内部启发式
# ============================================================

# TOC 行尾"......15"或制表符 + 页码模式（点导符 / dotted leader）
_TOC_DOTTED_LEADER_RE = re.compile(r"[\.…·•]{3,}\s*\d+\s*$")
_TOC_TAB_PAGE_RE = re.compile(r"\t+\d+\s*$")

# 章节级标题（无 Word 样式时仅靠正文文本识别）
_CHAPTER_RE = re.compile(r"^第\s*[一二三四五六七八九十百零〇\d]+\s*[章节篇部回卷]")
_NUMBERED_RE = re.compile(r"^\d+(?:\.\d+){0,3}(?:[\.?])?\s*\S")
_CHINESE_NUM_RE = re.compile(r"^[一二三四五六七八九十]+\s*[、．\.]\s*\S")
_SECTION_NAME_RE = re.compile(
    r"^(摘\s*要|abstract|引\s*言|绪\s*论|结\s*论|参考文献|references?|bibliography|"
    r"致\s*谢|附\s*录|关键词|keywords?)\s*$",
    re.IGNORECASE,
)

# 参考文献条目（编号引导）
_REF_ITEM_RE = re.compile(r"^\s*\[\d+\]")

# 题注
_CAPTION_RE = re.compile(r"^\s*(图|表|Figure|Table)\s*\d")

# 中文/英文 TOC 节标题（"目录" / "Contents" / "Table of Contents"）
_TOC_HEADING_RE = re.compile(
    r"^(目\s*录|contents?|table of contents)\s*$", re.IGNORECASE
)

# Word 自带的 TOC 样式名前缀
_TOC_STYLE_PREFIXES = ("toc ", "toc1", "toc2", "toc3", "toc4", "toc5", "toc6")

# 题注 / 参考文献样式名
_CAPTION_STYLE_TOKENS = ("caption", "题注")
_REF_STYLE_TOKENS = ("bibliography", "参考", "reference")

# 默认 cover 区域上限：在没有 section break 信号时，最多扫描前 N 个段落寻找封面候选
_COVER_MAX_INDEX = 8

_HEADING_DECIMAL_RE = re.compile(r"^(\d+(?:\.\d+){0,3})[\.\u3001]?\s*\S")
_HEADING_NAMED_LEVEL1_RE = re.compile(
    r"^(\u6458\s*\u8981|abstract|\u5f15\s*\u8a00|\u7eea\s*\u8bba|\u524d\s*\u8a00|\u7ed3\s*\u8bba|"
    r"\u53c2\u8003\u6587\u732e|references?|bibliography|\u76ee\s*\u5f55|contents?)\s*$",
    re.IGNORECASE,
)
_KEYWORDS_RE = re.compile(r"^(\u5173\u952e\u8bcd|keywords?)\s*[:\uff1a]", re.IGNORECASE)


@dataclass
class _ElementView:
    """归一化的元素视图：屏蔽 dict / DocElement 形态差异，仅暴露分类启发式需要的字段。"""

    index: int
    text: str
    style_name: str            # lowercase
    type_hint: str             # "h1" | "h2" | "h3" | "p" | "li" | "caption" | "ref" | "table" | ""
    font_size_pt: float        # 0.0 if unknown
    alignment: str             # "left" | "center" | "right" | "justify" | ""
    first_indent_twips: float  # 0.0 if unknown / not applicable
    bold: bool
    is_section_break: bool


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _normalize_align(v: Any) -> str:
    """无论传入是 'CENTER' / Alignment.CENTER / 'center'，统一小写 keyword。"""
    if v is None:
        return ""
    s = _coerce_str(v).lower()
    # python-docx 的 WD_ALIGN_PARAGRAPH 字符串化形如 "CENTER (1)" → 取首词
    return s.split()[0] if s else ""


def _to_view_from_dict(idx: int, el: dict) -> _ElementView:
    """app.py._parse_docx 返回的 dict 形态 → ElementView。"""
    t = _coerce_str(el.get("type") or "p").lower()
    text = _coerce_str(el.get("text"))
    fmt = el.get("fmt") or {}
    runs = el.get("runs") or []

    style = _coerce_str(fmt.get("style")).lower()
    align = _normalize_align(fmt.get("alignment"))
    first_indent = fmt.get("first_line_indent_twips") or 0
    try:
        first_indent_f = float(first_indent or 0)
    except (TypeError, ValueError):
        first_indent_f = 0.0

    # 取 runs 中字符数最多的一段为主导字号 / 加粗
    size_pt = 0.0
    bold = False
    if runs:
        size_w: dict[float, int] = {}
        bold_chars = 0
        total_chars = 0
        for r in runs:
            rtxt = _coerce_str(r.get("text"))
            rlen = len(rtxt.strip())
            if rlen <= 0:
                continue
            total_chars += rlen
            sz = r.get("font_size_pt")
            if sz:
                try:
                    size_w[float(sz)] = size_w.get(float(sz), 0) + rlen
                except (TypeError, ValueError):
                    pass
            if r.get("bold"):
                bold_chars += rlen
        if size_w:
            size_pt = max(size_w, key=size_w.get)
        if total_chars > 0 and bold_chars / total_chars >= 0.6:
            bold = True

    return _ElementView(
        index=idx,
        text=text,
        style_name=style,
        type_hint=t,
        font_size_pt=size_pt,
        alignment=align,
        first_indent_twips=first_indent_f,
        bold=bold,
        is_section_break=bool(el.get("section_break")),
    )


def _to_view_from_doc_element(idx: int, elem: DocElement) -> _ElementView:
    """DocumentModel.elements 中的 DocElement → ElementView。"""
    et = elem.element_type
    type_hint = ""
    if et == ElementType.HEADING:
        lvl = elem.level if 1 <= (elem.level or 0) <= 3 else 3
        type_hint = f"h{lvl}"
    elif et == ElementType.PARAGRAPH:
        type_hint = "p"
    elif et == ElementType.LIST_ITEM:
        type_hint = "li"
    elif et == ElementType.CAPTION:
        type_hint = "caption"
    elif et == ElementType.REFERENCE:
        type_hint = "ref"
    elif et == ElementType.TABLE:
        type_hint = "table"
    elif et == ElementType.SECTION_BREAK:
        type_hint = ""

    fs = elem.font_style
    ps = elem.paragraph_style
    align = ""
    if ps and getattr(ps, "alignment", None) is not None:
        align = _normalize_align(getattr(ps.alignment, "value", ps.alignment))

    # DocElement 用厘米记录首行缩进；本批次不需要精确单位，只判断是否为 0
    first_indent_cm = float(getattr(ps, "first_indent_cm", 0.0) or 0.0)
    first_indent_twips = first_indent_cm * 567.0  # 1 cm ≈ 567 twips（仅作非零信号）

    return _ElementView(
        index=idx,
        text=_coerce_str(elem.content),
        style_name=_coerce_str(elem.style_name).lower(),
        type_hint=type_hint,
        font_size_pt=float(getattr(fs, "font_size_pt", 0.0) or 0.0),
        alignment=align,
        first_indent_twips=first_indent_twips,
        bold=bool(getattr(fs, "bold", False)),
        is_section_break=(et == ElementType.SECTION_BREAK),
    )


# ============================================================
# 启发式：基线 + 单元素分类
# ============================================================


@dataclass
class _Baseline:
    body_size_pt: float = 0.0
    body_align: str = ""
    cover_boundary: int = 0  # 第一个 section break 的索引；无则等于 _COVER_MAX_INDEX


def _infer_baseline(views: list[_ElementView]) -> _Baseline:
    """从视图列表推断正文基线（字号众数、主导对齐、封面区上限）。"""
    if not views:
        return _Baseline(cover_boundary=_COVER_MAX_INDEX)

    size_counts: dict[float, int] = {}
    align_counts: dict[str, int] = {}
    cover_boundary = _COVER_MAX_INDEX

    for v in views:
        if v.is_section_break and v.index < cover_boundary:
            cover_boundary = v.index
            break  # 仅认第一个分节符
    for v in views:
        # 仅在普通段落 (type=p / li) 上推断基线，避免标题/题注污染
        if v.type_hint not in ("p", "li"):
            continue
        text_len = len(v.text.strip())
        if text_len < 4:
            continue
        if v.font_size_pt > 0:
            size_counts[v.font_size_pt] = size_counts.get(v.font_size_pt, 0) + text_len
        if v.alignment:
            align_counts[v.alignment] = align_counts.get(v.alignment, 0) + 1

    body_size = max(size_counts, key=size_counts.get) if size_counts else 0.0
    body_align = max(align_counts, key=align_counts.get) if align_counts else ""

    return _Baseline(body_size_pt=body_size, body_align=body_align, cover_boundary=cover_boundary)


def _classify_one(
    view: _ElementView,
    baseline: _Baseline,
    in_ref_section: bool,
) -> tuple[str, float, str]:
    """单个元素 → (role, confidence, reason)。所有阈值与启发式集中在此。"""
    text = view.text.strip()
    if not text:
        return (_BODY_ROLE, 0.3, "empty_text")

    style = view.style_name

    # 1. TOC：样式名 / 节标题 / 行尾点导符
    if any(style.startswith(p) for p in _TOC_STYLE_PREFIXES) or style in (
        "table of contents", "目录"
    ):
        return ("toc", 0.95, "style:toc")
    if _TOC_HEADING_RE.match(text) and view.index < _COVER_MAX_INDEX * 2:
        return ("heading", 0.85, "section_name:toc_heading")
    if _TOC_DOTTED_LEADER_RE.search(text) or _TOC_TAB_PAGE_RE.search(text):
        return ("toc", 0.85, "dotted_leader")

    # 2. 参考文献节：进入 ref_section 后所有 paragraph / ref 视为 reference 条目
    if in_ref_section:
        if view.type_hint in ("p", "li", "ref") and text:
            return ("reference", 0.9, "in_reference_section")

    # 3. 参考文献条目（独立判断，覆盖 ref_section 没识别到的兜底）
    if style.startswith(_REF_STYLE_TOKENS) or any(tok in style for tok in _REF_STYLE_TOKENS):
        return ("reference", 0.9, f"style:{style[:20]}")
    if _REF_ITEM_RE.match(text):
        return ("reference", 0.8, "ref_item_pattern")

    # 4. 题注
    if any(tok in style for tok in _CAPTION_STYLE_TOKENS):
        return ("caption", 0.95, "style:caption")
    if _CAPTION_RE.match(text):
        return ("caption", 0.85, "caption_pattern")

    # 5. 表格类型直接归类
    if view.type_hint == "table":
        return ("table", 0.95, "type:table")

    # 6. 已经是 Word HEADING 样式：保留 heading；并尝试识别"摘要 / 引言 / 参考文献"等节标题
    if view.type_hint in ("h1", "h2", "h3"):
        if _SECTION_NAME_RE.match(text):
            return ("heading", 0.95, "section_name")
        return ("heading", 0.9, f"style:{view.type_hint}")

    # 7. 封面：只在文档前若干段考虑；居中 + 显著大于正文字号 + 无首行缩进
    if view.index < baseline.cover_boundary:
        if (
            view.alignment == "center"
            and view.font_size_pt > 0
            and baseline.body_size_pt > 0
            and view.font_size_pt >= baseline.body_size_pt * 1.3
            and view.first_indent_twips <= 1.0
        ):
            return ("cover", 0.85, "cover_first_page_centered_large")
        # 兜底：很短的居中行，前 3 个段
        if (
            view.index < 3
            and view.alignment == "center"
            and len(text) <= 30
            and view.first_indent_twips <= 1.0
        ):
            return ("cover", 0.7, "cover_short_centered")

    # 8. 节标题（独立段，非 heading 样式但文字命中关键节名）
    if _SECTION_NAME_RE.match(text) and len(text) <= 12:
        return ("heading", 0.85, "section_name")

    # 9. 编号标题（无 Word 样式但命中编号模式 + 字号大于正文）
    text_short = len(text) <= 60
    looks_numbered = bool(
        _CHAPTER_RE.match(text) or _NUMBERED_RE.match(text) or _CHINESE_NUM_RE.match(text)
    )
    if looks_numbered and text_short:
        bigger = (
            view.font_size_pt > 0
            and baseline.body_size_pt > 0
            and view.font_size_pt > baseline.body_size_pt + 0.5
        )
        if bigger or view.bold or view.alignment == "center":
            return ("heading", 0.75, "numbered_heading")
        # 字号信息缺失（HTML 路径）：编号 + 短文本仍降级识别为标题，confidence 较低
        if view.font_size_pt == 0:
            return ("heading", 0.6, "numbered_heading_no_size")

    # 10. 兜底：正文
    return (_BODY_ROLE, 0.5, "default")


# ============================================================
# 公共入口
# ============================================================


def _is_ref_section_heading(role: str, reason: str, text: str) -> bool:
    """判定一段是否为'参考文献'区段的节标题。"""
    if role != "heading":
        return False
    if "参考文献" in text or text.lower().strip() in ("references", "reference", "bibliography"):
        return True
    return False


def _build_views_and_classify(
    views: list[_ElementView],
) -> list[tuple[str, float, str]]:
    """对一组视图执行分类，返回与 views 等长的 (role, conf, reason) 列表。"""
    baseline = _infer_baseline(views)
    results: list[tuple[str, float, str]] = []
    in_ref_section = False

    for v in views:
        # 一旦遇到 section break，认定封面区已结束（更新 baseline.cover_boundary 下限）
        # 但 cover_boundary 已在 baseline 中固定，仅在分类逻辑里短路即可。
        role, conf, reason = _classify_one(v, baseline, in_ref_section)
        results.append((role, conf, reason))
        # 检查是否进入 / 退出参考文献区段
        if _is_ref_section_heading(role, reason, v.text.strip()):
            in_ref_section = True
        elif role == "heading" and in_ref_section:
            # 进入新章节 → 退出参考文献区段
            if not _is_ref_section_heading(role, reason, v.text.strip()):
                in_ref_section = False

    return results


def _compose_metadata(role: str, confidence: float, reason: str) -> dict:
    """根据分类结果构造 metadata 增量字段。"""
    role = role if role in _KNOWN_ROLES else "unknown"
    conf = max(0.0, min(1.0, float(confidence)))
    excl_format = role in ("cover", "toc", "reference", "caption", "table") and conf >= DEFAULT_FORMAT_THRESHOLD
    excl_xref = role in ("cover", "toc") and conf >= DEFAULT_XREF_THRESHOLD
    return {
        "structure_role": role,
        "structure_confidence": round(conf, 3),
        "structure_reason": reason,
        "exclude_from_format_body": bool(excl_format),
        "exclude_from_xref_targets": bool(excl_xref),
    }


def _infer_heading_level(view: _ElementView, role: str) -> Optional[int]:
    """为 role=heading 的元素推断层级；目录/封面/正文返回 None。"""
    if role != "heading":
        return None

    if view.type_hint == "h1":
        return 1
    if view.type_hint == "h2":
        return 2
    if view.type_hint == "h3":
        return 3

    text = view.text.strip()
    if not text:
        return None

    if _HEADING_NAMED_LEVEL1_RE.match(text) or _CHAPTER_RE.match(text) or _CHINESE_NUM_RE.match(text):
        return 1

    m = _HEADING_DECIMAL_RE.match(text)
    if m:
        token = m.group(1)
        return token.count(".") + 2

    return None


def _infer_section_kind(view: _ElementView, role: str) -> Optional[str]:
    """补充更细的结构类型，供前端/QA 消费。"""
    text = view.text.strip()
    if not text:
        return None

    lower = text.lower()
    compact = re.sub(r"\s+", "", lower)

    if role == "toc":
        return "toc_entry"
    if role == "reference":
        return "reference_item"
    if role == "caption":
        return "caption"
    if role == "cover":
        return "cover"

    if compact in ("目录", "contents", "tableofcontents"):
        return "toc_heading"
    if compact == "摘要":
        return "abstract_heading_zh"
    if compact == "abstract":
        return "abstract_heading_en"
    if compact in ("参考文献", "references", "reference", "bibliography"):
        return "references_heading"
    if _KEYWORDS_RE.match(text):
        return "keywords"

    if role == "heading":
        level = _infer_heading_level(view, role)
        if level is not None:
            return f"heading_{level}"
        return "heading"

    return None


def classify_dicts(elems: list[dict]) -> list[dict]:
    """app.py._parse_docx 路径：原地写入 ``el['metadata']``，返回同一列表。"""
    if not elems:
        return elems
    views = [_to_view_from_dict(i, el) for i, el in enumerate(elems)]
    results = _build_views_and_classify(views)
    for el, view, (role, conf, reason) in zip(elems, views, results):
        meta = el.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        meta.update(_compose_metadata(role, conf, reason))
        heading_level = _infer_heading_level(view, role)
        if heading_level is not None:
            meta["heading_level"] = heading_level
        else:
            meta.pop("heading_level", None)
        section_kind = _infer_section_kind(view, role)
        if section_kind:
            meta["section_kind"] = section_kind
        else:
            meta.pop("section_kind", None)
        el["metadata"] = meta
    return elems


def classify_elements(elems: list[DocElement]) -> list[DocElement]:
    """parsers/docx_parser.py 路径：原地写入 ``elem.metadata``，返回同一列表。"""
    if not elems:
        return elems
    views = [_to_view_from_doc_element(i, e) for i, e in enumerate(elems)]
    results = _build_views_and_classify(views)
    for elem, view, (role, conf, reason) in zip(elems, views, results):
        if not isinstance(elem.metadata, dict):
            elem.metadata = {}
        elem.metadata.update(_compose_metadata(role, conf, reason))
        heading_level = _infer_heading_level(view, role)
        if heading_level is not None:
            elem.metadata["heading_level"] = heading_level
        else:
            elem.metadata.pop("heading_level", None)
        section_kind = _infer_section_kind(view, role)
        if section_kind:
            elem.metadata["section_kind"] = section_kind
        else:
            elem.metadata.pop("section_kind", None)
    return elems


__all__ = [
    "DEFAULT_FORMAT_THRESHOLD",
    "DEFAULT_XREF_THRESHOLD",
    "classify_dicts",
    "classify_elements",
]
