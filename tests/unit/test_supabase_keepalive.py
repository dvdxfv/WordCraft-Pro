from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "supabase_keepalive.py"
SPEC = importlib.util.spec_from_file_location("supabase_keepalive", MODULE_PATH)
assert SPEC and SPEC.loader
supabase_keepalive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supabase_keepalive)


def test_build_keepalive_url_normalizes_slashes():
    url = supabase_keepalive.build_keepalive_url(
        "https://example.supabase.co/",
        "auth/v1/health",
    )
    assert url == "https://example.supabase.co/auth/v1/health"


def test_build_headers_includes_auth_headers():
    headers = supabase_keepalive.build_headers("anon-key")
    assert headers["apikey"] == "anon-key"
    assert headers["Authorization"] == "Bearer anon-key"
    assert headers["User-Agent"] == "wordcraft-pro-supabase-keepalive/1.0"


def test_perform_keepalive_success():
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.status = 200
    response.read.return_value = b'{"ok":true}'

    with patch.object(supabase_keepalive.urllib.request, "urlopen", return_value=response):
        result = supabase_keepalive.perform_keepalive(
            base_url="https://example.supabase.co",
            anon_key="anon-key",
        )

    assert result.ok is True
    assert result.status == 200
    assert result.body == '{"ok":true}'
    assert result.url == "https://example.supabase.co/auth/v1/health"


def test_main_missing_url_exits_cleanly():
    exit_code = supabase_keepalive.main(["--anon-key", "anon-key"])
    assert exit_code == 2
