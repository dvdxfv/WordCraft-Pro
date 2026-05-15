from __future__ import annotations

import argparse
import json
import base64
import hashlib
import hmac
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Iterable, NamedTuple, Sequence


DEFAULT_WARN_DAYS = 6.0
DEFAULT_CRITICAL_DAYS = 6.9
DEFAULT_TIMEOUT = 12
DEFAULT_TABLES = (
    ("token_logs", ("created_at",)),
    ("documents", ("updated_at", "created_at")),
    ("templates", ("updated_at", "created_at")),
    ("profiles", ("updated_at", "created_at")),
    ("user_settings", ("updated_at", "created_at")),
)
USER_AGENT = "wordcraft-pro-supabase-inactivity-watch/1.0"


class TableActivity(NamedTuple):
    table: str
    timestamp_field: str
    timestamp: datetime
    row: dict


def _normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip()
    if not base_url:
        raise ValueError("Supabase URL is empty.")
    return base_url.rstrip("/")


def _get_auth_key() -> str:
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_KEY")
        or ""
    )
    return key.strip()


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _build_rest_url(base_url: str, table: str, timestamp_fields: Iterable[str]) -> str:
    table = table.strip()
    fields = list(timestamp_fields)
    if not fields:
        raise ValueError(f"No timestamp fields configured for table {table}.")

    query = urllib.parse.urlencode(
        {
            "select": ",".join(fields),
            "order": f"{fields[0]}.desc",
            "limit": "1",
        }
    )
    return f"{_normalize_base_url(base_url)}/rest/v1/{table}?{query}"


def _request_json(url: str, key: str, timeout: int) -> list[dict]:
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": USER_AGENT,
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body or "[]")
        return data if isinstance(data, list) else []


def _query_latest_row(
    base_url: str,
    key: str,
    table: str,
    timestamp_fields: Sequence[str],
    timeout: int,
) -> TableActivity | None:
    last_error: str | None = None
    for ts_field in timestamp_fields:
        url = _build_rest_url(base_url, table, [ts_field])
        try:
            rows = _request_json(url, key, timeout)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            last_error = f"HTTP {exc.code}: {body or exc.reason}"
            continue
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error while querying {table}: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON returned by {table}: {exc}") from exc

        if not rows:
            continue
        row = rows[0]
        candidate = _parse_iso_timestamp(str(row.get(ts_field) or ""))
        if candidate is None:
            for alt_field in timestamp_fields:
                if alt_field == ts_field:
                    continue
                candidate = _parse_iso_timestamp(str(row.get(alt_field) or ""))
                if candidate is not None:
                    ts_field = alt_field
                    break
        if candidate is not None:
            return TableActivity(table=table, timestamp_field=ts_field, timestamp=candidate, row=row)

    if last_error:
        raise RuntimeError(f"Failed to query {table}: {last_error}")
    return None


def collect_latest_activity(
    base_url: str,
    key: str,
    timeout: int,
) -> list[TableActivity]:
    activities: list[TableActivity] = []
    for table, timestamp_fields in DEFAULT_TABLES:
        activity = _query_latest_row(base_url, key, table, timestamp_fields, timeout)
        if activity is not None:
            activities.append(activity)
    return activities


def build_message(
    latest: TableActivity | None,
    age_days: float | None,
    warn_days: float,
    critical_days: float,
    base_url: str,
) -> str:
    if latest is None or age_days is None:
        return (
            f"Supabase inactivity watch: no activity found in monitored tables for {base_url}. "
            f"Please verify the project before the Free Plan inactivity window."
        )

    severity = "warning" if age_days >= warn_days else "ok"
    if age_days >= critical_days:
        severity = "critical"

    return (
        f"Supabase inactivity watch [{severity}]: latest activity in {latest.table}.{latest.timestamp_field} "
        f"was at {latest.timestamp.isoformat()}. Age: {age_days:.2f} days. "
        f"Warn at {warn_days:.1f} days, critical at {critical_days:.1f} days."
    )


def notify_webhook(webhook_url: str, message: str, severity: str, timeout: int) -> None:
    payload = json.dumps(
        {
            "text": message,
            "severity": severity,
            "source": "wordcraft-pro",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as _resp:
        _resp.read()


def _sign_feishu_webhook(webhook_url: str, secret: str, timestamp: int | None = None) -> str:
    secret = secret.strip()
    if not secret:
        return webhook_url
    ts = timestamp or int(datetime.now(timezone.utc).timestamp())
    string_to_sign = f"{ts}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(digest).decode("utf-8")
    separator = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{separator}timestamp={ts}&sign={urllib.parse.quote(sign)}"


def send_alert(
    webhook_url: str,
    message: str,
    severity: str,
    timeout: int,
    platform: str = "generic",
    feishu_secret: str = "",
) -> None:
    platform = (platform or "generic").strip().lower()
    if platform == "feishu" or "open.feishu.cn" in webhook_url:
        signed_url = _sign_feishu_webhook(webhook_url, feishu_secret)
        payload = {
            "msg_type": "text",
            "content": {
                "text": message,
            },
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            signed_url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as _resp:
            _resp.read()
        return

    notify_webhook(webhook_url, message, severity, timeout)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warn before Supabase inactivity pause risk.")
    parser.add_argument(
        "--url",
        default=os.environ.get("SUPABASE_URL", ""),
        help="Supabase project URL.",
    )
    parser.add_argument(
        "--key",
        default=_get_auth_key(),
        help="Supabase service role key preferred; anon key fallback.",
    )
    parser.add_argument(
        "--warn-days",
        type=float,
        default=float(os.environ.get("SUPABASE_INACTIVITY_WARN_DAYS", DEFAULT_WARN_DAYS)),
        help="Warn when latest activity is older than this many days.",
    )
    parser.add_argument(
        "--critical-days",
        type=float,
        default=float(os.environ.get("SUPABASE_INACTIVITY_CRITICAL_DAYS", DEFAULT_CRITICAL_DAYS)),
        help="Mark critical when latest activity is older than this many days.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("SUPABASE_INACTIVITY_TIMEOUT", DEFAULT_TIMEOUT)),
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--webhook-url",
        default=(
            os.environ.get("ALERT_WEBHOOK_URL", "")
            or os.environ.get("FEISHU_BOT_WEBHOOK", "")
        ),
        help="Optional alert webhook URL. If omitted, the workflow still fails on warning.",
    )
    parser.add_argument(
        "--platform",
        default=os.environ.get("ALERT_PLATFORM", "") or os.environ.get("FEISHU_BOT_PLATFORM", ""),
        help="Alert platform, e.g. feishu. Auto-detects Feishu URLs when omitted.",
    )
    parser.add_argument(
        "--feishu-secret",
        default=os.environ.get("FEISHU_BOT_SECRET", "") or os.environ.get("ALERT_WEBHOOK_SECRET", ""),
        help="Optional Feishu bot secret for signed webhooks.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON summary instead of human-readable text.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.url:
        print("Missing --url or SUPABASE_URL.", file=sys.stderr)
        return 2
    if not args.key:
        print("Missing --key or SUPABASE_SERVICE_ROLE_KEY/SUPABASE_ANON_KEY/SUPABASE_KEY.", file=sys.stderr)
        return 2

    try:
        activities = collect_latest_activity(args.url, args.key, args.timeout)
    except Exception as exc:
        payload = {"ok": False, "severity": "error", "error": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    latest = max(activities, key=lambda item: item.timestamp, default=None)
    if latest is None:
        age_days = None
        severity = "critical"
        message = build_message(None, None, args.warn_days, args.critical_days, args.url)
    else:
        now = datetime.now(timezone.utc)
        age_days = (now - latest.timestamp).total_seconds() / 86400.0
        if age_days >= args.critical_days:
            severity = "critical"
        elif age_days >= args.warn_days:
            severity = "warning"
        else:
            severity = "ok"
        message = build_message(latest, age_days, args.warn_days, args.critical_days, args.url)

    if severity in {"warning", "critical"} and args.webhook_url:
        try:
            send_alert(
                args.webhook_url,
                message,
                severity,
                args.timeout,
                platform=args.platform,
                feishu_secret=args.feishu_secret,
            )
        except Exception as exc:
            # Alerting failure should still surface in the workflow output.
            if args.json:
                print(json.dumps({"ok": False, "severity": "error", "error": f"webhook: {exc}"}, ensure_ascii=False))
            else:
                print(f"Webhook delivery failed: {exc}", file=sys.stderr)
            return 2

    result = {
        "ok": severity == "ok",
        "severity": severity,
        "latest": None
        if latest is None
        else {
            "table": latest.table,
            "timestamp_field": latest.timestamp_field,
            "timestamp": latest.timestamp.isoformat(),
        },
        "age_days": age_days,
        "warn_days": args.warn_days,
        "critical_days": args.critical_days,
        "message": message,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(message)

    return 0 if severity == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
