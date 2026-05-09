"""
Stateless DOCX cross-reference fixer.

apply_xref_fix(docx_b64, fix_payload) -> {"docx_b64": "..."} | {"error": "..."}

For single-number citations [n]: inserts REF field + superscript, after ensuring
a bookmark exists in the reference paragraph.

For multi-number citations [n,m,...]: applies superscript formatting only
(full REF field insertion for ranges/sets is deferred).

Decision B6: if reference paragraph cannot be located, falls back to
superscript-only rather than corrupting the document.
"""
from __future__ import annotations

import base64
import io
import re
from typing import Any

from lxml import etree

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML_NS = "http://www.w3.org/XML/1998/namespace"

_REF_SECTION_RE = re.compile(r"参考文献|references?\b|bibliography", re.IGNORECASE)
_REF_ENTRY_RE = re.compile(r"^\s*\[(\d+)\]")


def _w(tag: str) -> str:
    return f"{{{_W_NS}}}{tag}"


def _xspace() -> str:
    return f"{{{_XML_NS}}}space"


def _para_text(p: etree._Element) -> str:
    return "".join(t.text or "" for t in p.iter(_w("t")))


def _find_para(
    body: etree._Element, fingerprint: str, hint_idx: int | None
) -> tuple[etree._Element | None, int]:
    all_paras = list(body.iter(_w("p")))
    if hint_idx is not None and 0 <= hint_idx < len(all_paras):
        p = all_paras[hint_idx]
        if _para_text(p)[:40].strip() == fingerprint:
            return p, hint_idx
    for i, p in enumerate(all_paras):
        if _para_text(p)[:40].strip() == fingerprint:
            return p, i
    return None, -1


def _find_ref_paragraph(body: etree._Element, ref_num: int) -> etree._Element | None:
    """Find the reference entry paragraph '[n] ...' after the 参考文献 heading."""
    paras = list(body.iter(_w("p")))
    in_ref_section = False
    for p in paras:
        text = _para_text(p).strip()
        if not in_ref_section:
            if _REF_SECTION_RE.search(text):
                in_ref_section = True
            continue
        m = _REF_ENTRY_RE.match(text)
        if m and int(m.group(1)) == ref_num:
            return p
    return None


def _ensure_bookmark(para_elem: etree._Element, ref_num: int, doc_body: etree._Element) -> str:
    """
    Return existing bookmark name for this paragraph, or create one.
    Does not overwrite existing bookmarks (B6 decision: stable IDs).
    """
    for bm in para_elem.findall(_w("bookmarkStart")):
        name = bm.get(_w("name"), "")
        if name:
            return name

    all_ids = [
        int(b.get(_w("id"), "-1"))
        for b in doc_body.iter(_w("bookmarkStart"))
        if (b.get(_w("id"), "") or "").lstrip("-").isdigit()
    ]
    new_id = str((max(all_ids) + 1) if all_ids else 1)
    bm_name = f"_WCRef_{ref_num}"

    bm_start = etree.Element(_w("bookmarkStart"))
    bm_start.set(_w("id"), new_id)
    bm_start.set(_w("name"), bm_name)

    bm_end = etree.Element(_w("bookmarkEnd"))
    bm_end.set(_w("id"), new_id)

    pPr = para_elem.find(_w("pPr"))
    insert_pos = (list(para_elem).index(pPr) + 1) if pPr is not None else 0
    para_elem.insert(insert_pos, bm_start)
    para_elem.append(bm_end)

    return bm_name


def _clone_rPr(run_elem: etree._Element) -> etree._Element | None:
    rPr = run_elem.find(_w("rPr"))
    if rPr is None:
        return None
    return etree.fromstring(etree.tostring(rPr))


def _make_superscript_rPr(base_rPr: etree._Element | None) -> etree._Element:
    """Return an rPr element with superscript added (based on base_rPr)."""
    if base_rPr is not None:
        rPr = etree.fromstring(etree.tostring(base_rPr))
    else:
        rPr = etree.Element(_w("rPr"))
    existing = rPr.find(_w("vertAlign"))
    if existing is not None:
        rPr.remove(existing)
    va = etree.SubElement(rPr, _w("vertAlign"))
    va.set(_w("val"), "superscript")
    return rPr


def _make_run(rPr: etree._Element | None, child: etree._Element) -> etree._Element:
    r = etree.Element(_w("r"))
    if rPr is not None:
        r.append(rPr)
    r.append(child)
    return r


def _build_ref_field_runs(
    citation_text: str, bookmark_name: str, base_rPr: etree._Element | None
) -> list[etree._Element]:
    """Build the 5-run REF field: begin + instrText + separate + display + end."""
    sup_rPr = _make_superscript_rPr(base_rPr)

    def _sup_run(child: etree._Element) -> etree._Element:
        rPr_copy = etree.fromstring(etree.tostring(sup_rPr))
        return _make_run(rPr_copy, child)

    fc_begin = etree.Element(_w("fldChar"))
    fc_begin.set(_w("fldCharType"), "begin")

    instr = etree.Element(_w("instrText"))
    instr.set(_xspace(), "preserve")
    instr.text = f" REF {bookmark_name} \\r \\h "

    fc_sep = etree.Element(_w("fldChar"))
    fc_sep.set(_w("fldCharType"), "separate")

    t_display = etree.Element(_w("t"))
    t_display.text = citation_text

    fc_end = etree.Element(_w("fldChar"))
    fc_end.set(_w("fldCharType"), "end")

    return [
        _sup_run(fc_begin),
        _sup_run(instr),
        _sup_run(fc_sep),
        _sup_run(t_display),
        _sup_run(fc_end),
    ]


def _replace_text_span_in_para(
    para_elem: etree._Element,
    target_text: str,
    replacement_runs: list[etree._Element],
) -> bool:
    """
    Find target_text within a single run's <w:t>, split that run, and replace
    the span with replacement_runs.  Returns True on success.

    Only handles the case where target_text falls entirely within one <w:t>.
    This covers the common case for hand-typed [n] citations.
    """
    children = list(para_elem)
    for run_elem in para_elem.findall(_w("r")):
        for t_elem in run_elem.findall(_w("t")):
            t_text = t_elem.text or ""
            pos = t_text.find(target_text)
            if pos == -1:
                continue

            before = t_text[:pos]
            after = t_text[pos + len(target_text):]
            orig_rPr = _clone_rPr(run_elem)
            run_idx = children.index(run_elem)

            new_nodes: list[etree._Element] = []

            if before:
                r_b = etree.Element(_w("r"))
                if orig_rPr is not None:
                    r_b.append(etree.fromstring(etree.tostring(orig_rPr)))
                t_b = etree.SubElement(r_b, _w("t"))
                t_b.set(_xspace(), "preserve")
                t_b.text = before
                new_nodes.append(r_b)

            new_nodes.extend(replacement_runs)

            if after:
                r_a = etree.Element(_w("r"))
                if orig_rPr is not None:
                    r_a.append(etree.fromstring(etree.tostring(orig_rPr)))
                t_a = etree.SubElement(r_a, _w("t"))
                t_a.set(_xspace(), "preserve")
                t_a.text = after
                new_nodes.append(r_a)

            para_elem.remove(run_elem)
            for j, node in enumerate(new_nodes):
                para_elem.insert(run_idx + j, node)
            return True

    return False


def _apply_superscript_only(para_elem: etree._Element, citation_text: str) -> bool:
    """Fallback: apply superscript to citation_text without a REF field."""
    for run_elem in para_elem.findall(_w("r")):
        for t_elem in run_elem.findall(_w("t")):
            t_text = t_elem.text or ""
            pos = t_text.find(citation_text)
            if pos == -1:
                continue

            before = t_text[:pos]
            after = t_text[pos + len(citation_text):]
            orig_rPr = _clone_rPr(run_elem)
            children = list(para_elem)
            run_idx = children.index(run_elem)

            new_nodes: list[etree._Element] = []

            if before:
                r_b = etree.Element(_w("r"))
                if orig_rPr is not None:
                    r_b.append(etree.fromstring(etree.tostring(orig_rPr)))
                t_b = etree.SubElement(r_b, _w("t"))
                t_b.set(_xspace(), "preserve")
                t_b.text = before
                new_nodes.append(r_b)

            r_mid = etree.Element(_w("r"))
            rPr_mid = etree.SubElement(r_mid, _w("rPr"))
            va = etree.SubElement(rPr_mid, _w("vertAlign"))
            va.set(_w("val"), "superscript")
            t_mid = etree.SubElement(r_mid, _w("t"))
            t_mid.text = citation_text
            new_nodes.append(r_mid)

            if after:
                r_a = etree.Element(_w("r"))
                if orig_rPr is not None:
                    r_a.append(etree.fromstring(etree.tostring(orig_rPr)))
                t_a = etree.SubElement(r_a, _w("t"))
                t_a.set(_xspace(), "preserve")
                t_a.text = after
                new_nodes.append(r_a)

            para_elem.remove(run_elem)
            for j, node in enumerate(new_nodes):
                para_elem.insert(run_idx + j, node)
            return True

    return False


def apply_xref_fix(docx_b64: str, fix_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Fix a plain-text citation [n] in a DOCX paragraph.

    Strategy:
      Single-number [n]: find/create bookmark in reference paragraph, insert REF field + superscript.
      Multi-number [n,m,...]: apply superscript formatting only.
      Fallback (ref section not found): apply superscript formatting only (B6).
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
    fingerprint = (fix_payload.get("para_fingerprint") or "").strip()
    para_idx: int | None = fix_payload.get("para_idx")
    citation_text: str = fix_payload.get("citation_text", "")
    ref_numbers: list[int] = fix_payload.get("ref_numbers", [])

    if not citation_text:
        return {"error": "Missing citation_text in fix_payload"}

    body_para, _ = _find_para(body, fingerprint, para_idx)
    if body_para is None:
        return {
            "error": (
                f"Body paragraph not found — fingerprint='{fingerprint}' hint_idx={para_idx}. "
                "The document may have changed since the QA scan."
            )
        }

    fixed = False

    if len(ref_numbers) == 1:
        ref_num = ref_numbers[0]
        ref_para = _find_ref_paragraph(body, ref_num)
        if ref_para is not None:
            bookmark_name = _ensure_bookmark(ref_para, ref_num, body)
            orig_rPr_hint = _clone_rPr(
                next(iter(body_para.findall(_w("r"))), etree.Element(_w("r")))
            )
            ref_runs = _build_ref_field_runs(citation_text, bookmark_name, orig_rPr_hint)
            fixed = _replace_text_span_in_para(body_para, citation_text, ref_runs)

    if not fixed:
        # B6: ref para not found or multi-number → superscript only
        fixed = _apply_superscript_only(body_para, citation_text)

    if not fixed:
        return {"error": f"Citation '{citation_text}' not found in paragraph"}

    buf = io.BytesIO()
    try:
        doc.save(buf)
    except Exception as exc:
        return {"error": f"Cannot serialize DOCX: {exc}"}

    return {"docx_b64": base64.b64encode(buf.getvalue()).decode()}
