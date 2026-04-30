from pathlib import Path


LANDING_HTML = Path(__file__).resolve().parents[1] / "web" / "wordcraft_landing.html"


def test_landing_register_entrypoint_is_bound():
    html = LANDING_HTML.read_text(encoding="utf-8")

    assert "setAuthMode('register'); return false;" in html
    assert "function register()" in html
    assert "window.supabaseClient.auth.signUp" in html


def test_landing_uses_single_modal_for_login_and_register():
    html = LANDING_HTML.read_text(encoding="utf-8")

    assert "function handleAuthSubmit()" in html
    assert "const isRegister = authMode === 'register';" in html
    assert "confirmPasswordWrap" in html
