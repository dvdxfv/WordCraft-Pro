from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import NamedTuple, Sequence


DEFAULT_ENDPOINT = "/auth/v1/health"
DEFAULT_TIMEOUT = 10
USER_AGENT = "wordcraft-pro-supabase-keepalive/1.0"


class KeepaliveResult(NamedTuple):
    ok: bool
    url: str
    status: int | None
    body: str
    error: str | None = None


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip()
    if not base_url:
        raise ValueError("Supabase URL is empty.")
    return base_url.rstrip("/")


def normalize_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if not endpoint:
        raise ValueError("Endpoint is empty.")
    return endpoint if endpoint.startswith("/") else f"/{endpoint}"


def build_keepalive_url(base_url: str, endpoint: str = DEFAULT_ENDPOINT) -> str:
    return f"{normalize_base_url(base_url)}{normalize_endpoint(endpoint)}"


def build_headers(anon_key: str) -> dict[str, str]:
    if not anon_key or not anon_key.strip():
        raise ValueError("Supabase anon key is empty.")
    token = anon_key.strip()
    return {
        "apikey": token,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": USER_AGENT,
    }


def perform_keepalive(
    base_url: str,
    anon_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
) -> KeepaliveResult:
    url = build_keepalive_url(base_url, endpoint)
    request = urllib.request.Request(url, headers=build_headers(anon_key), method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return KeepaliveResult(
                ok=True,
                url=url,
                status=getattr(response, "status", None),
                body=body,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return KeepaliveResult(
            ok=False,
            url=url,
            status=exc.code,
            body=body,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return KeepaliveResult(
            ok=False,
            url=url,
            status=None,
            body="",
            error=f"Network error: {reason}",
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return KeepaliveResult(
            ok=False,
            url=url,
            status=None,
            body="",
            error=str(exc),
        )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a minimal, manual Supabase keepalive request."
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("SUPABASE_URL", ""),
        help="Supabase project URL, e.g. https://xxx.supabase.co",
    )
    parser.add_argument(
        "--anon-key",
        default=os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_KEY", ""),
        help="Supabase anon key used as both apikey and Bearer token.",
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("SUPABASE_KEEPALIVE_ENDPOINT", DEFAULT_ENDPOINT),
        help=f"Request path to ping. Default: {DEFAULT_ENDPOINT}",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("SUPABASE_KEEPALIVE_TIMEOUT", DEFAULT_TIMEOUT)),
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human summary.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.url:
        print("Missing --url or SUPABASE_URL.", file=sys.stderr)
        return 2
    if not args.anon_key:
        print("Missing --anon-key or SUPABASE_ANON_KEY/SUPABASE_KEY.", file=sys.stderr)
        return 2

    result = perform_keepalive(
        base_url=args.url,
        anon_key=args.anon_key,
        endpoint=args.endpoint,
        timeout=args.timeout,
    )

    if args.json:
        payload = {
            "ok": result.ok,
            "url": result.url,
            "status": result.status,
            "body": result.body,
            "error": result.error,
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if result.ok:
            summary = f"OK {result.status or ''} {result.url}".rstrip()
            print(summary)
            if result.body:
                print(result.body)
        else:
            print(f"FAIL {result.url}", file=sys.stderr)
            if result.error:
                print(result.error, file=sys.stderr)
            if result.body:
                print(result.body, file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
