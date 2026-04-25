# -*- coding: utf-8 -*-
"""E2E cross-reference panel flow."""

from __future__ import annotations

import json

import pytest

from .conftest import upload_document


@pytest.mark.e2e
@pytest.mark.regression
def test_xref_flow(logged_in_page, sample_doc_path, e2e_artifact_dir):
    page = logged_in_page
    upload_document(page, sample_doc_path)

    page.locator("#btnXRef").click()
    page.locator("#rp-xref").wait_for(timeout=10000)
    page.locator("#xrefTargets").wait_for(timeout=10000)
    page.locator("#xrefTargetsBody").wait_for(state="attached", timeout=10000)

    payload = {
        "target_count_text": page.locator("#xrefTargets").inner_text(),
        "status_count_text": page.locator("#xrefStatus").inner_text() if page.locator("#xrefStatus").count() else "",
    }
    (e2e_artifact_dir / "xref_panel_snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    assert payload["target_count_text"] != ""

