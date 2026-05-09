"""
Stateless DOCX format-attribute fixer.

apply_format_fix(docx_b64, fix_payload) -> {"docx_b64": "..."} | {"error": "..."}

Supported attrs: font_size, font_name, line_spacing.
Decision A: rejects with error when para_fingerprint does not match.
"""
from __future__ import annotations

import base64
import io
from typing import Any

from lxml import etree

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _w(tag: str) -> str:
    return f"{{{_W_NS}}}{tag}"


def _get_or_create(parent: etree._Element, tag: str) -> etree._Element:
    child = parent.find(tag)
    if child is None:
        child = etree.SubElement(parent, tag)
    return child


def _para_text(p: etree._Element) -> str:
    return "".join(t.text or "" for t in p.iter(_w("t")))


def _find_para(
    body: etree._Element, fingerprint: str, hint_idx: int | None
) -> tuple[etree._Element | None, int]:
    """Locate paragraph by fingerprint, using hint_idx as first attempt."""
    all_paras = list(body.iter(_w("p")))

    if hint_idx is not None and 0 <= hint_idx < len(all_paras):
        p = all_paras[hint_idx]
        if _para_text(p)[:40].strip() == fingerprint:
            return p, hint_idx

    for i, p in enumerate(all_paras):
        if _para_text(p)[:40].strip() == fingerprint:
            return p, i

    return None, -1


def _apply_font_size(para_elem: etree._Element, pt_size: float) -> None:
    """Set font size (pt) on all runs.  B1: w:sz stores half-points.  B2: paragraph scope."""
    sz_val = str(int(pt_size * 2))

    pPr = para_elem.find(_w("pPr"))
    if pPr is not None:
        pRPr = pPr.find(_w("rPr"))
        if pRPr is not None:
            _get_or_create(pRPr, _w("sz")).set(_w("val"), sz_val)
            _get_or_create(pRPr, _w("szCs")).set(_w("val"), sz_val)

    for r in para_elem.findall(_w("r")):
        rPr = r.find(_w("rPr"))
        if rPr is None:
            rPr = etree.Element(_w("rPr"))
            r.insert(0, rPr)
        _get_or_create(rPr, _w("sz")).set(_w("val"), sz_val)
        _get_or_create(rPr, _w("szCs")).set(_w("val"), sz_val)


def _apply_font_name(para_elem: etree._Element, font_name: str) -> None:
    """Set east-Asian (and ASCII/hAnsi) font on all runs in the paragraph."""
    for r in para_elem.findall(_w("r")):
        rPr = r.find(_w("rPr"))
        if rPr is None:
            rPr = etree.Element(_w("rPr"))
            r.insert(0, rPr)
        rFonts = rPr.find(_w("rFonts"))
        if rFonts is None:
            rFonts = etree.Element(_w("rFonts"))
            rPr.insert(0, rFonts)
        rFonts.set(_w("eastAsia"), font_name)
        rFonts.set(_w("ascii"), font_name)
        rFonts.set(_w("hAnsi"), font_name)


def _apply_line_spacing(para_elem: etree._Element, mode: str, value: float) -> None:
    """Set paragraph line spacing.  mode: 'exact' (pt) or 'multiple' (multiplier)."""
    pPr = para_elem.find(_w("pPr"))
    if pPr is None:
        pPr = etree.Element(_w("pPr"))
        para_elem.insert(0, pPr)
    spacing = _get_or_create(pPr, _w("spacing"))

    if mode == "exact":
        spacing.set(_w("line"), str(int(value * 20)))
        spacing.set(_w("lineRule"), "exact")
    elif mode == "multiple":
        spacing.set(_w("line"), str(int(value * 240)))
        spacing.set(_w("lineRule"), "auto")
    else:
        raise ValueError(f"Unknown line_spacing mode: '{mode}'")


def apply_format_fix(docx_b64: str, fix_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Apply one format-attribute fix to a DOCX document.

    Stateless: caller sends the DOCX as base64, receives the modified DOCX as base64.
    Returns {"docx_b64": "..."} on success or {"error": "..."} on failure.
    Decision A: fingerprint mismatch → 400-style error, document not modified.
    """
    try:
        raw = base64.b64decode(docx_b64)
    except Exception as exc:
        return {"error": f"Invalid docx_b64: {exc}"}

    try:
        from docx import Document
        doc = Document(io.BytesIO(raw))
    except Exception as exc:
        return {"error": f"Cannot open DOCX: {exc}"}

    body = doc.element.body
    para_idx: int | None = fix_payload.get("para_idx")
    fingerprint: str = (fix_payload.get("para_fingerprint") or "").strip()
    attr: str = fix_payload.get("attr", "")
    value = fix_payload.get("value")
    mode: str = fix_payload.get("mode", "")

    para_elem, _ = _find_para(body, fingerprint, para_idx)
    if para_elem is None:
        return {
            "error": (
                f"Paragraph not found — fingerprint='{fingerprint}' hint_idx={para_idx}. "
                "The document may have been modified since the QA scan."
            )
        }

    try:
        if attr == "font_size":
            if value is None:
                return {"error": "fix_payload missing 'value' for font_size"}
            _apply_font_size(para_elem, float(value))
        elif attr == "font_name":
            if not value:
                return {"error": "fix_payload missing 'value' for font_name"}
            _apply_font_name(para_elem, str(value))
        elif attr == "line_spacing":
            if value is None:
                return {"error": "fix_payload missing 'value' for line_spacing"}
            _apply_line_spacing(para_elem, mode, float(value))
        else:
            return {"error": f"Unknown attr: '{attr}'"}
    except Exception as exc:
        return {"error": f"Failed to apply {attr!r}: {exc}"}

    buf = io.BytesIO()
    try:
        doc.save(buf)
    except Exception as exc:
        return {"error": f"Cannot serialize DOCX: {exc}"}

    return {"docx_b64": base64.b64encode(buf.getvalue()).decode()}
