from pathlib import Path


INDEX_HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


def _apply_highlights_source() -> str:
    html = INDEX_HTML.read_text(encoding="utf-8")
    start = html.index("function applyHighlights(items)")
    end = html.index("function showAnnoTip", start)
    return html[start:end]


def test_qa_highlight_prefers_backend_element_index_scope():
    src = _apply_highlights_source()
    compact = "".join(src.split())

    assert "item.elementIndex" in src
    assert "scopedBlock" in src
    assert "highlightInScope(scopedBlock)" in src
    assert "if(scopedBlock&&highlightInScope(scopedBlock))return;" in compact
    assert src.index("highlightInScope(scopedBlock)") < src.index("Pass 1")


def test_qa_highlight_fallback_scans_past_non_matching_text_nodes():
    src = _apply_highlights_source()

    assert "if(i<0)continue;" in "".join(src.split())
