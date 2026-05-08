# -*- coding: utf-8 -*-
"""No-login AI parse baseline checks against real template answer files."""

from __future__ import annotations

import json

import pytest

from tests.ai_parse_answer_support import (
    build_ai_parse_pairs,
    expected_rules_json,
    extract_template_text,
    upload_template_payload,
)
from tests.sample_smoke_support import load_manifest


try:
    from playwright.sync_api import Page
except ImportError:
    pytest.skip("Playwright not installed", allow_module_level=True)


AI_PARSE_PAIRS = build_ai_parse_pairs(load_manifest())


@pytest.mark.e2e
@pytest.mark.no_login
@pytest.mark.parametrize("pair", AI_PARSE_PAIRS, ids=lambda pair: pair["id"])
def test_template_import_ai_parse_result_matches_answer_baseline(
    anonymous_index_page: Page, pair: dict
) -> None:
    page = anonymous_index_page
    doc_path = pair["doc_path"]
    answer_path = pair["answer_path"]

    expected = json.loads(expected_rules_json(answer_path))
    assert expected, f"answer baseline must yield expected rules: {answer_path}"

    payload_b64, file_name = upload_template_payload(doc_path)
    expected_text = extract_template_text(doc_path)
    assert expected_text.strip(), f"template text extraction is empty: {doc_path}"

    result = page.evaluate(
        """async ([b64, fileName, expectedRules]) => {
            window.WC_API.callAI = async () => ({
                content: JSON.stringify(expectedRules),
            });
            const upload = await window.WC_API.uploadTemplate(b64, 'e2e-template', fileName);
            if (!upload.success) return { upload, parsed: null, aiInput: '' };
            document.getElementById('aiInput').value = upload.doc_text || '';
            await runAIParse();
            return {
                upload,
                parsed: window._aiParsedRules || null,
                aiInput: document.getElementById('aiInput').value || '',
            };
        }""",
        [payload_b64, file_name, expected],
    )

    assert result["upload"]["success"] is True, result["upload"]
    assert result["aiInput"].strip(), f"imported template did not populate aiInput: {doc_path}"
    assert result["parsed"] is not None, f"AI parse did not produce rules for {doc_path}"

    for key, expected_value in expected.items():
        assert result["parsed"].get(key) == expected_value, (
            f"{pair['id']} expected {key}={expected_value!r}, "
            f"got {result['parsed'].get(key)!r}"
        )
