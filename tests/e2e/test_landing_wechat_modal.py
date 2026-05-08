# -*- coding: utf-8 -*-
"""No-login regressions for landing page WeChat contact flows."""

from __future__ import annotations

import pytest

try:
    from playwright.sync_api import Page
except ImportError:
    pytest.skip("Playwright not installed", allow_module_level=True)

from .conftest import FRONTEND_LOGIN_URL


@pytest.mark.e2e
@pytest.mark.no_login
class TestLandingWechatModal:
    def test_footer_contact_link_opens_qr_modal(self, page: Page) -> None:
        page.goto(FRONTEND_LOGIN_URL, wait_until="networkidle")
        page.locator("footer a", has_text="微信联系").click()

        modal = page.locator("#wechatModal")
        modal.wait_for(state="visible")
        title = page.locator("#wechatModalTitle")
        title.wait_for()
        assert "微信联系" in (title.text_content() or "")
        assert "扫码添加企业微信进行咨询" in (page.locator("#wechatModalSubtitle").text_content() or "")

        qr = page.locator("#wechatModalQrImage")
        assert qr.get_attribute("src") == "assets/wechat-contact-qr.jpg"
        assert qr.is_visible()
        assert not page.locator("#wechatModalMeta").is_visible()

    def test_pricing_buttons_render_real_qr_for_both_modes(self, page: Page) -> None:
        page.goto(FRONTEND_LOGIN_URL, wait_until="networkidle")

        page.get_by_role("button", name="微信咨询下单").click()
        page.locator("#wechatModal").wait_for(state="visible")
        assert "论文急诊包" in (page.locator("#wechatModalTitle").text_content() or "")
        assert "扫码添加客服" in (page.locator("#wechatModalSubtitle").text_content() or "")
        assert page.locator("#wechatModalQrImage").is_visible()
        assert page.locator("#wechatModalMeta").is_visible()
        assert "24h 内交付检查报告" in (page.locator("#wechatModalMeta").text_content() or "")
        assert "微信号" not in (page.locator("#wechatModalMeta").text_content() or "")
        page.get_by_role("button", name="关闭").click()

        page.get_by_role("button", name="微信咨询订阅").click()
        page.locator("#wechatModal").wait_for(state="visible")
        assert "Pro 订阅" in (page.locator("#wechatModalTitle").text_content() or "")
        assert page.locator("#wechatModalQrImage").is_visible()
        assert page.locator("#wechatModalMeta").is_visible()
        assert "6.9 / 月" in (page.locator("#wechatModalMeta").text_content() or "")
        assert "微信号" not in (page.locator("#wechatModalMeta").text_content() or "")
