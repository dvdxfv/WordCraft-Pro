from core.document_structure import classify_dicts


def _el(text, *, type_="p", size=12.0, align=None, bold=False, style="Normal", indent=0):
    return {
        "type": type_,
        "text": text,
        "fmt": {
            "style": style,
            "alignment": align,
            "first_line_indent_twips": indent,
        },
        "runs": [{"text": text, "font_size_pt": size, "bold": bold}],
    }


def test_toc_section_absorbs_named_entries_with_page_markers():
    elems = [
        _el("\u76ee\u5f55", type_="h1", size=16.0, bold=True),
        _el("\u6458\u8981    I"),
        _el("Abstract    II"),
        _el("\u4e00\u3001\u524d\u8a00   - 1 -"),
        _el("1.1 \u5173\u952e\u73af\u5883\u56e0\u5b50\u53ca\u5176\u5bf9\u5357\u6d77\u9e22\u4e4c\u8d3c\u5206\u5e03\u7684\u5f71\u54cd   - 2 -"),
        _el("\u53c2\u8003\u6587\u732e   - 7 -"),
        _el("\u6b63\u6587\u6bb5\u843d" * 10, indent=420),
    ]

    out = classify_dicts(elems)

    assert out[1]["metadata"]["structure_role"] == "toc"
    assert out[1]["metadata"]["section_kind"] == "toc_entry"
    assert out[2]["metadata"]["structure_role"] == "toc"
    assert out[5]["metadata"]["structure_role"] == "toc"
    assert out[6]["metadata"]["structure_role"] == "body"


def test_cover_continuation_absorbs_bare_author_name_after_title():
    elems = [
        _el("\u5357\u6d77\u9e22\u4e4c\u8d3c\u6355\u635e\u91cf\u667a\u80fd\u53cd\u6f14\u6587\u732e\u7efc\u8ff0", size=24.0, align="CENTER", bold=True),
        _el("\u9646\u5609\u6021", size=14.0, align="CENTER"),
        _el("\u76ee\u5f55", type_="h1", size=16.0, bold=True),
        _el("\u6458\u8981    I"),
    ]

    out = classify_dicts(elems)

    assert out[0]["metadata"]["structure_role"] == "cover"
    assert out[1]["metadata"]["structure_role"] == "cover"
    assert out[1]["metadata"]["exclude_from_format_body"] is True
    assert out[2]["metadata"]["section_kind"] == "toc_heading"
    assert out[3]["metadata"]["structure_role"] == "toc"


def test_cover_continuation_survives_blank_paragraphs_before_author():
    elems = [
        _el("Generic Research Report", size=24.0, align="CENTER", bold=True),
        _el("", size=12.0, align="CENTER"),
        _el("", size=12.0, align="CENTER"),
        _el("Ada Zhang", size=14.0, align="CENTER"),
        _el("Contents", type_="h1", size=16.0, bold=True),
        _el("Abstract    II"),
    ]

    out = classify_dicts(elems)

    assert out[0]["metadata"]["structure_role"] == "cover"
    assert out[3]["metadata"]["structure_role"] == "cover"
    assert out[3]["metadata"]["exclude_from_format_body"] is True
    assert out[4]["metadata"]["section_kind"] == "toc_heading"
    assert out[5]["metadata"]["structure_role"] == "toc"


def test_toc_page_marker_entries_are_not_promoted_to_real_headings():
    elems = [
        _el("Contents", type_="h1", size=16.0, bold=True),
        _el("Abstract    II"),
        _el("References   - 7 -"),
        _el("Appendix A   12"),
        _el("Chapter One", type_="h1", size=16.0, bold=True),
    ]

    out = classify_dicts(elems)

    assert out[1]["metadata"]["structure_role"] == "toc"
    assert out[1]["metadata"]["section_kind"] == "toc_entry"
    assert out[2]["metadata"]["structure_role"] == "toc"
    assert out[2]["metadata"]["section_kind"] == "toc_entry"
    assert out[3]["metadata"]["structure_role"] == "toc"
    assert out[4]["metadata"]["structure_role"] == "heading"
    assert out[4]["metadata"]["section_kind"] != "toc_entry"
