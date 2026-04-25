# -*- coding: utf-8 -*-
"""E2E AI QA flow with progress and interaction compatibility."""

from __future__ import annotations

import json

import pytest

from .conftest import upload_document


@pytest.mark.e2e
@pytest.mark.regression
def test_qa_ai_flow(logged_in_page, sample_doc_path, e2e_artifact_dir):
    page = logged_in_page
    upload_document(page, sample_doc_path)
    snippet = page.locator("#docPage").inner_text().strip()[:6] or "测试文本"

    ai_reply = (
        '{"issues":[{"severity":"warning","category":"format","title":"AI测试问题",'
        f'"description":"用于验证AI链路","location_text":"{snippet}","suggestion":"{snippet}"'
        "}]}",
    )[0]

    def handle_call_ai(route):
        body = {"content": ai_reply}
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(body, ensure_ascii=False),
        )

    page.route("**/api/callAI", handle_call_ai)

    page.locator("#btnQA").click()
    page.locator('[onclick="runAIQA()"]').click()
    page.locator("#issue-0").wait_for(timeout=30000)

    # AI thinking panel should have been shown at least once during processing.
    panel_seen = page.evaluate(
        """() => {
          const panel = document.getElementById('aiThinkingPanel');
          if (!panel) return false;
          const log = panel.querySelector('.ai-thinking-log');
          return !!log && (log.innerText || '').length > 0;
        }"""
    )
    assert panel_seen

    page.locator('#issue-0 .issue-btn.accept').click()
    assert page.locator("#issue-0").evaluate("el => el.classList.contains('accepted')")
    page.screenshot(path=str(e2e_artifact_dir / "qa_ai_flow.png"))

