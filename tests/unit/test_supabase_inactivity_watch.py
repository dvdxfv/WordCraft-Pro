from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock, patch
import os


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "supabase_inactivity_watch.py"
SPEC = importlib.util.spec_from_file_location("supabase_inactivity_watch", MODULE_PATH)
assert SPEC and SPEC.loader
supabase_inactivity_watch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supabase_inactivity_watch)


class _Response:
    def __init__(self, body: str, status: int = 200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body.encode("utf-8")


def test_parse_iso_timestamp_handles_z_suffix():
    dt = supabase_inactivity_watch._parse_iso_timestamp("2026-04-27T12:30:00Z")
    assert dt is not None
    assert dt.isoformat() == "2026-04-27T12:30:00+00:00"


def test_build_message_warning():
    activity = supabase_inactivity_watch.TableActivity(
        table="documents",
        timestamp_field="updated_at",
        timestamp=supabase_inactivity_watch.datetime(2026, 4, 20, tzinfo=supabase_inactivity_watch.timezone.utc),
        row={"updated_at": "2026-04-20T00:00:00Z"},
    )
    msg = supabase_inactivity_watch.build_message(activity, 6.2, 6.0, 6.9, "https://example.supabase.co")
    assert "warning" in msg
    assert "documents.updated_at" in msg


def test_collect_latest_activity_prefers_latest_timestamp():
    payloads = {
        "token_logs": '[{"created_at":"2026-04-20T00:00:00Z"}]',
        "documents": '[{"updated_at":"2026-04-27T00:00:00Z"}]',
        "templates": "[]",
        "profiles": "[]",
        "user_settings": "[]",
    }

    def fake_urlopen(request, timeout=0):
        url = request.full_url
        for table, body in payloads.items():
            if f"/{table}?" in url:
                return _Response(body)
        raise AssertionError(f"Unexpected URL: {url}")

    with patch.object(supabase_inactivity_watch.urllib.request, "urlopen", side_effect=fake_urlopen):
        activities = supabase_inactivity_watch.collect_latest_activity(
            "https://example.supabase.co",
            "service-role-key",
            12,
        )

    assert len(activities) == 2
    latest = max(activities, key=lambda x: x.timestamp)
    assert latest.table == "documents"


def test_notify_webhook_posts_json_payload():
    response = _Response("ok")
    with patch.object(supabase_inactivity_watch.urllib.request, "urlopen", return_value=response) as mocked:
        supabase_inactivity_watch.notify_webhook("https://hooks.example.test", "hello", "warning", 12)

    req = mocked.call_args.args[0]
    body = json.loads(req.data.decode("utf-8"))
    assert body["text"] == "hello"
    assert body["severity"] == "warning"


def test_send_alert_formats_feishu_payload_and_signature():
    response = _Response("ok")
    with patch.object(supabase_inactivity_watch.urllib.request, "urlopen", return_value=response) as mocked:
        supabase_inactivity_watch.send_alert(
            "https://open.feishu.cn/open-apis/bot/v2/hook/abc",
            "hello",
            "warning",
            12,
            platform="feishu",
            feishu_secret="secret",
        )

    req = mocked.call_args.args[0]
    assert "timestamp=" in req.full_url
    assert "sign=" in req.full_url
    body = json.loads(req.data.decode("utf-8"))
    assert body["msg_type"] == "text"
    assert body["content"]["text"] == "hello"


def test_main_without_url_exits_with_error():
    code = supabase_inactivity_watch.main(["--key", "k"])
    assert code == 2


def test_parse_args_accepts_feishu_webhook_env():
    with patch.dict(os.environ, {"FEISHU_BOT_WEBHOOK": "https://open.feishu.cn/open-apis/bot/v2/hook/abc"}, clear=False):
        args = supabase_inactivity_watch._parse_args([])
    assert args.webhook_url == "https://open.feishu.cn/open-apis/bot/v2/hook/abc"
