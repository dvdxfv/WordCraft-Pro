from pathlib import Path


DASHBOARD_HTML = Path(__file__).resolve().parents[1] / "web" / "dashboard.html"


def test_dashboard_uses_current_admin_stats_view_fields():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    assert 'select("total_users,new_users_7d,new_users_30d,total_tokens_used")' in html
    assert 'select("total_users,active_today,active_week,new_today")' not in html


def test_dashboard_uses_current_admin_token_view_fields():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    assert 'select("date,total_tokens,total_requests,active_users,purpose")' in html
    assert 'select("stat_date,total_tokens,user_count")' not in html


def test_dashboard_content_section_reflects_minimal_batch17b_progress_without_live_team_queries():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    assert "Batch 17B 已接入最小闭环" in html
    assert 'sb.from("teams")' not in html
    assert 'sb.from("team_members")' not in html


def test_dashboard_activation_submit_preserves_form_reference_after_await():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    assert "const formEl = event.currentTarget;" in html
    assert "const form = new FormData(formEl);" in html
    assert "formEl.reset();" in html
    assert "event.currentTarget.reset();" not in html


def test_dashboard_can_delete_only_unused_activation_codes():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    assert 'data-delete-code="${escapeHtml(item.code)}"' in html
    assert 'Number(item.redeemed_count || 0) === 0' in html
    assert '.from("activation_codes")' in html
    assert ".delete()" in html
    assert '.eq("redeemed_count", 0)' in html
    assert "已兑换的激活码不能删除" in html
