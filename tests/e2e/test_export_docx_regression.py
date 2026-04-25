# -*- coding: utf-8 -*-
"""Issue-5 export format regression gate."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from docx.oxml.ns import qn

from .conftest import upload_document


@dataclass
class ParagraphSig:
    text: str
    style: str | None
    alignment: str | None
    first_line_indent: int | None
    left_indent: int | None
    right_indent: int | None
    space_before: int | None
    space_after: int | None
    line_spacing_rule: str | None
    line_spacing: float | None
    runs: list[dict[str, Any]]


def _run_rfonts(run) -> dict[str, str | None]:
    r_pr = getattr(run._element, "rPr", None)
    if r_pr is None or getattr(r_pr, "rFonts", None) is None:
        return {"ascii": None, "hAnsi": None, "eastAsia": None, "cs": None}
    r_fonts = r_pr.rFonts
    return {
        "ascii": r_fonts.get(qn("w:ascii")),
        "hAnsi": r_fonts.get(qn("w:hAnsi")),
        "eastAsia": r_fonts.get(qn("w:eastAsia")),
        "cs": r_fonts.get(qn("w:cs")),
    }


def _paragraph_signature(paragraph) -> ParagraphSig:
    fmt = paragraph.paragraph_format
    runs: list[dict[str, Any]] = []
    for r in paragraph.runs:
        r_fonts = _run_rfonts(r)
        runs.append(
            {
                "text": r.text or "",
                "font_name": r.font.name,
                "font_size": int(r.font.size.pt * 2) if r.font.size else None,
                "bold": bool(r.bold) if r.bold is not None else None,
                "italic": bool(r.italic) if r.italic is not None else None,
                "underline": bool(r.underline) if r.underline is not None else None,
                "font_ascii": r_fonts["ascii"],
                "font_hansi": r_fonts["hAnsi"],
                "font_eastasia": r_fonts["eastAsia"],
                "font_cs": r_fonts["cs"],
            }
        )
    return ParagraphSig(
        text=paragraph.text or "",
        style=paragraph.style.name if paragraph.style else None,
        alignment=str(paragraph.alignment) if paragraph.alignment is not None else None,
        first_line_indent=int(fmt.first_line_indent) if fmt.first_line_indent is not None else None,
        left_indent=int(fmt.left_indent) if fmt.left_indent is not None else None,
        right_indent=int(fmt.right_indent) if fmt.right_indent is not None else None,
        space_before=int(fmt.space_before) if fmt.space_before is not None else None,
        space_after=int(fmt.space_after) if fmt.space_after is not None else None,
        line_spacing_rule=str(fmt.line_spacing_rule) if fmt.line_spacing_rule is not None else None,
        line_spacing=float(fmt.line_spacing) if fmt.line_spacing is not None else None,
        runs=runs,
    )


def _style_signature(doc: Document) -> dict[str, Any]:
    def _style_rfonts(style) -> dict[str, str | None]:
        r_pr = style.element.find(qn("w:rPr"))
        if r_pr is None:
            return {"ascii": None, "hAnsi": None, "eastAsia": None, "cs": None}
        r_fonts = r_pr.find(qn("w:rFonts"))
        if r_fonts is None:
            return {"ascii": None, "hAnsi": None, "eastAsia": None, "cs": None}
        return {
            "ascii": r_fonts.get(qn("w:ascii")),
            "hAnsi": r_fonts.get(qn("w:hAnsi")),
            "eastAsia": r_fonts.get(qn("w:eastAsia")),
            "cs": r_fonts.get(qn("w:cs")),
        }

    tracked_names = {"Normal", "Heading 1", "Heading 2", "Heading 3"}
    style_map: dict[str, Any] = {}
    for s in doc.styles:
        if s.type != 1:  # WD_STYLE_TYPE.PARAGRAPH
            continue
        if s.name not in tracked_names:
            continue
        style_map[s.name] = {
            "font_name": s.font.name,
            "font_size": int(s.font.size.pt * 2) if s.font.size else None,
            "bold": bool(s.font.bold) if s.font.bold is not None else None,
            "italic": bool(s.font.italic) if s.font.italic is not None else None,
            "underline": bool(s.font.underline) if s.font.underline is not None else None,
            "rfonts": _style_rfonts(s),
        }
    return style_map


def _doc_signature(path: Path) -> dict[str, Any]:
    doc = Document(str(path))
    sections = []
    for s in doc.sections:
        sections.append(
            {
                "page_width": int(s.page_width) if s.page_width else None,
                "page_height": int(s.page_height) if s.page_height else None,
                "left_margin": int(s.left_margin) if s.left_margin else None,
                "right_margin": int(s.right_margin) if s.right_margin else None,
                "top_margin": int(s.top_margin) if s.top_margin else None,
                "bottom_margin": int(s.bottom_margin) if s.bottom_margin else None,
            }
        )
    paragraphs = [asdict(_paragraph_signature(p)) for p in doc.paragraphs]
    return {
        "section_count": len(doc.sections),
        "sections": sections,
        "paragraph_count": len(paragraphs),
        "non_empty_paragraph_count": sum(1 for p in paragraphs if p["text"].strip()),
        "paragraphs": paragraphs,
        "styles": _style_signature(doc),
    }


def _compare_signature(base: dict[str, Any], exported: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    if base["section_count"] != exported["section_count"]:
        mismatches.append({"type": "section_count", "base": base["section_count"], "exported": exported["section_count"]})
    sec_len = min(len(base["sections"]), len(exported["sections"]))
    for i in range(sec_len):
        if base["sections"][i] != exported["sections"][i]:
            mismatches.append({"type": "section_format", "index": i, "base": base["sections"][i], "exported": exported["sections"][i]})
    if base["paragraph_count"] != exported["paragraph_count"]:
        mismatches.append({"type": "paragraph_count", "base": base["paragraph_count"], "exported": exported["paragraph_count"]})
    if base["non_empty_paragraph_count"] != exported["non_empty_paragraph_count"]:
        mismatches.append(
            {
                "type": "non_empty_paragraph_count",
                "base": base["non_empty_paragraph_count"],
                "exported": exported["non_empty_paragraph_count"],
            }
        )
    if base["styles"] != exported["styles"]:
        mismatches.append({"type": "style_format", "base": base["styles"], "exported": exported["styles"]})
    p_len = min(base["paragraph_count"], exported["paragraph_count"])
    for i in range(p_len):
        b = base["paragraphs"][i]
        e = exported["paragraphs"][i]
        if b != e:
            mismatches.append(
                {
                    "type": "paragraph_format",
                    "index": i,
                    "base_text": b["text"][:60],
                    "exported_text": e["text"][:60],
                    "base": b,
                    "exported": e,
                }
            )
            if len(mismatches) >= 50:
                break
    return {"all_equal": len(mismatches) == 0, "mismatch_count": len(mismatches), "mismatches": mismatches}


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.regression
def test_export_docx_regression(logged_in_page, sample_doc_path: Path, e2e_artifact_dir: Path):
    page = logged_in_page
    upload_document(page, sample_doc_path)
    page.wait_for_timeout(1200)
    meta = page.evaluate(
        """() => {
            try {
                const tab = openTabs[activeTabIdx];
                if (!tab) return { error: "no active tab" };
                const content = docContents[tab.name] || [];
                const fmtCount = content.filter(it => !!(it && it.fmt)).length;
                const secCount = (docSections[tab.name] || []).length;
                return {
                    tab_name: tab.name,
                    tab_type: tab.type,
                    content_count: content.length,
                    fmt_count: fmtCount,
                    section_count: secCount,
                };
            } catch (e) {
                return { error: String(e) };
            }
        }"""
    )
    assert not meta.get("error"), f"页面元数据检查失败: {meta}"
    assert meta["tab_type"] in {"docx", "doc"}, f"unexpected tab type: {meta}"
    assert meta["content_count"] > 0, f"empty parsed content: {meta}"
    assert meta["fmt_count"] == meta["content_count"], f"missing paragraph fmt metadata: {meta}"
    assert meta["section_count"] > 0, f"missing section metadata: {meta}"

    export_btn = page.locator('button.tbtn[onclick="exportDoc()"]')
    export_btn.wait_for(timeout=30000)
    exported_file = e2e_artifact_dir / "phase5_exported.docx"

    with page.expect_download(timeout=90000) as dl_info:
        export_btn.click()
    dl_info.value.save_as(str(exported_file))

    assert exported_file.exists(), "no downloaded export file"

    base_sig = _doc_signature(sample_doc_path)
    exported_sig = _doc_signature(exported_file)
    compare = _compare_signature(base_sig, exported_sig)

    report = {
        "sample_doc": str(sample_doc_path),
        "exported_doc": str(exported_file),
        "result": compare,
        "base_summary": {"section_count": base_sig["section_count"], "paragraph_count": base_sig["paragraph_count"]},
        "exported_summary": {
            "section_count": exported_sig["section_count"],
            "paragraph_count": exported_sig["paragraph_count"],
        },
    }
    report_file = e2e_artifact_dir / "phase5_export_compare_report.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    assert compare["all_equal"], f"导出排版与原文不一致，mismatch_count={compare['mismatch_count']}，详见: {report_file}"

