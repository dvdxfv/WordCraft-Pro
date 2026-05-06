from pathlib import Path


INDEX_HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


def test_activation_button_and_modal_exist_in_toolbar_flow():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="btnActivationCode"' in html
    assert 'onclick="openActivationRedeemModal()"' in html
    assert 'id="activationRedeemModal"' in html
    assert 'id="activationCodeInput"' in html
    assert 'id="btnSubmitActivationRedeem"' in html


def test_activation_redeem_uses_supabase_rpc_and_updates_badge():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "async function submitActivationRedeem()" in html
    assert ".rpc('redeem_activation_code', { p_code: code })" in html
    assert "await loadCurrentPlanBadge();" in html
    assert "el.onclick=openActivationRedeemModal;" in html
    assert "async getUsageAndPlan() { return this._request('getUsageAndPlan', {}); }" in html
