# -*- coding: utf-8 -*-
"""E2E rule QA interaction flow with locate/accept/reject."""

from __future__ import annotations

import pytest

from .conftest import upload_document


@pytest.mark.e2e
@pytest.mark.regression
def test_qa_rule_flow(logged_in_page, sample_doc_path, e2e_artifact_dir):
    page = logged_in_page
    upload_document(page, sample_doc_path)

    snippet = page.locator("#docPage").inner_text().strip()[:6] or "测试文本"

    def handle_runqa(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"success":true,"issues":[{"severity":"warning","category":"format",'
                f'"title":"规则测试问题","description":"用于回归验证","suggestion":"{snippet}",'
                f'"location_text":"{snippet}"'
                "}]}"),
        )

    page.route("**/api/runQA", handle_runqa)

    page.locator("#btnQA").click()
    page.locator('[onclick="runQA()"]').click()
    page.locator("#issue-0").wait_for(timeout=15000)

    page.locator('#issue-0 .issue-btn.locate').click()
    page.locator('#issue-0 .issue-btn.accept').click()
    assert page.locator("#issue-0").evaluate("el => el.classList.contains('accepted')")

    # Produce another issue and verify reject path.
    page.locator('[onclick="runQA()"]').click()
    page.locator("#issue-0").wait_for(timeout=15000)
    page.locator('#issue-0 .issue-btn.reject').click()
    assert page.locator("#issue-0").evaluate("el => el.classList.contains('rejected')")

    page.screenshot(path=str(e2e_artifact_dir / "qa_rule_flow.png"))

