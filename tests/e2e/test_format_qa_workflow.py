# -*- coding: utf-8 -*-
"""E2E format rules save/load and QA workflow."""

from __future__ import annotations

import json
import pytest

from .conftest import upload_document


@pytest.mark.e2e
@pytest.mark.regression
def test_format_qa_happy_path(logged_in_page, sample_doc_path, e2e_artifact_dir):
    """Happy path: save format rules → load on page → apply in QA check."""
    page = logged_in_page

    # 1. Set format rules in the panel (using select_option for dropdowns, fill for numbers)
    page.locator("#fH1Font").select_option("黑体")
    page.locator("#fH1Size").fill("16")
    page.locator("#fH2Font").select_option("黑体")
    page.locator("#fH2Size").fill("14")
    page.locator("#fH3Font").select_option("黑体")
    page.locator("#fH3Size").fill("12")
    page.locator("#fBFont").select_option("宋体")
    page.locator("#fBSize").fill("12")

    # 2. Click save button
    page.locator("#btnSaveFormatRules").click()

    # Verify localStorage is set
    local_rules = page.evaluate("localStorage.getItem('wc_format_rules')")
    assert local_rules, "Rules should be saved in localStorage"
    rules_obj = json.loads(local_rules)
    assert rules_obj["h1Font"] == "黑体"
    assert rules_obj["h1Size"] == 16.0

    # 3. Mock backend save API to succeed
    def handle_save(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success":true,"storage":"supabase"}',
        )
    page.route("**/api/saveFormatRequirements", handle_save)

    # 4. Upload a document
    upload_document(page, sample_doc_path)

    # 5. Mock QA response with format issues
    def handle_runqa(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"success":true,"issues":['
                '{"severity":"warning","category":"format",'
                '"title":"一级标题字体不符规范","description":"规范要求 黑体，实际为 宋体",'
                '"suggestion":"将标题改为黑体","location_text":"示例标题","element_index":0,'
                '"rule_id":"format_font_heading_1","rule_source":"format_rule"}'
                ']}'
            ),
        )
    page.route("**/api/runQA", handle_runqa)

    # 6. Run QA check
    page.locator("#btnQA").click()
    page.locator('[onclick="runQA()"]').click()
    page.locator("#issue-0").wait_for(timeout=15000)

    # 7. Verify format issue is displayed
    issue_title = page.locator("#issue-0 .issue-title").inner_text()
    assert "字体不符规范" in issue_title or "格式" in issue_title

    page.screenshot(path=str(e2e_artifact_dir / "format_qa_happy_path.png"))


@pytest.mark.e2e
@pytest.mark.regression
def test_format_qa_supabase_fallback(logged_in_page, sample_doc_path, e2e_artifact_dir):
    """Supabase fallback: rules save to localStorage and persist in memory."""
    page = logged_in_page

    # 1. Set and save rules
    page.locator("#fH1Font").select_option("微软雅黑")
    page.locator("#fH1Size").fill("18")
    page.locator("#fBFont").select_option("微软雅黑")
    page.locator("#fBSize").fill("11")

    # Mock backend save to return success (simulating Supabase working)
    def handle_save(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success":true,"storage":"supabase"}',
        )
    page.route("**/api/saveFormatRequirements", handle_save)

    page.locator("#btnSaveFormatRules").click()
    page.wait_for_timeout(1000)

    # 2. Verify localStorage has the rules (fallback storage)
    local_rules = page.evaluate("localStorage.getItem('wc_format_rules')")
    assert local_rules, "Rules should be persisted in localStorage"
    rules_obj = json.loads(local_rules)
    assert rules_obj["h1Font"] == "微软雅黑", f"Expected h1Font=微软雅黑, got {rules_obj.get('h1Font')}"
    assert rules_obj["h1Size"] == 18.0
    assert rules_obj["bFont"] == "微软雅黑"
    assert rules_obj["bSize"] == 11.0

    # 3. Upload document and run QA - should use the cached rules
    upload_document(page, sample_doc_path)

    def handle_runqa(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success":true,"issues":[]}',
        )
    page.route("**/api/runQA", handle_runqa)

    page.locator("#btnQA").click()
    page.locator('[onclick="runQA()"]').click()
    page.wait_for_timeout(2000)

    # Rules should still be available and used for QA
    page.screenshot(path=str(e2e_artifact_dir / "format_qa_fallback.png"))


@pytest.mark.e2e
@pytest.mark.regression
def test_format_qa_partial_rules(logged_in_page, sample_doc_path, e2e_artifact_dir):
    """Partial rules: template missing some format fields, app handles gracefully."""
    page = logged_in_page

    # 1. Set only h1 font/size (leave h2, h3, body at defaults)
    page.locator("#fH1Font").select_option("黑体")
    page.locator("#fH1Size").fill("16")
    # Don't set h2, h3, body font/size - they stay at defaults

    # 2. Save partial rules
    def handle_save(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success":true,"storage":"local"}',
        )
    page.route("**/api/saveFormatRequirements", handle_save)

    page.locator("#btnSaveFormatRules").click()
    page.wait_for_timeout(500)

    # 3. Verify partial rules in localStorage
    local_rules = page.evaluate("localStorage.getItem('wc_format_rules')")
    rules_obj = json.loads(local_rules)
    assert rules_obj["h1Font"] == "黑体"
    assert rules_obj["h1Size"] == 16.0
    # h2, h3 should be default (empty string or 0)

    # 4. Upload document
    upload_document(page, sample_doc_path)

    # 5. Run QA - should only check h1, not fail on missing h2/h3/body
    def handle_runqa(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"success":true,"issues":['
                '{"severity":"warning","category":"format",'
                '"title":"一级标题字体不符规范","description":"规范要求 黑体，实际为 宋体",'
                '"suggestion":"改为黑体","location_text":"标题","element_index":0,'
                '"rule_id":"format_font_heading_1"}'
                ']}'
            ),
        )
    page.route("**/api/runQA", handle_runqa)

    page.locator("#btnQA").click()
    page.locator('[onclick="runQA()"]').click()
    page.locator("#issue-0").wait_for(timeout=15000)

    # 6. Verify format issue is shown (only for h1, not h2/h3)
    issue_count = page.locator("#issue-0").count()
    assert issue_count >= 1, "Should have at least one format issue"

    page.screenshot(path=str(e2e_artifact_dir / "format_qa_partial_rules.png"))
