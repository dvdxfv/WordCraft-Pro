# -*- coding: utf-8 -*-
"""E2E upload and preview flow."""

from __future__ import annotations

import pytest

from .conftest import upload_document


@pytest.mark.e2e
@pytest.mark.smoke
def test_upload_preview_flow(logged_in_page, sample_doc_path, e2e_artifact_dir):
    page = logged_in_page
    upload_document(page, sample_doc_path)

    # Preview container should have loaded content after upload.
    doc_page = page.locator("#docPage")
    text = doc_page.inner_text().strip()
    assert len(text) > 20
    page.screenshot(path=str(e2e_artifact_dir / "upload_preview_ok.png"))

