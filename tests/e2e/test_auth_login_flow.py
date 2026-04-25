# -*- coding: utf-8 -*-
"""E2E auth login flow."""

from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.smoke
def test_auth_login_flow(logged_in_page, e2e_artifact_dir):
    page = logged_in_page
    title = page.title()
    assert "WordCraft Pro" in title
    assert page.url.endswith("index.html")
    page.screenshot(path=str(e2e_artifact_dir / "auth_login_ok.png"))

