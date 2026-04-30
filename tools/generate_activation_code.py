#!/usr/bin/env python3
"""Generate manual activation-code SQL for Batch 17A.

This script does not connect to Supabase.  It prints an INSERT statement that
can be pasted into the Supabase SQL editor after manual payment collection.
"""

from __future__ import annotations

import argparse
import json
import secrets
import string
from datetime import datetime, timedelta, timezone


ALPHABET = string.ascii_uppercase + string.digits


def generate_code(prefix: str = "PRO", groups: int = 3, group_size: int = 4) -> str:
    parts = []
    for _ in range(groups):
        parts.append("".join(secrets.choice(ALPHABET) for _ in range(group_size)))
    return f"{prefix}-" + "-".join(parts)


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_insert_sql(
    *,
    code: str,
    plan_tier: str,
    duration_days: int,
    max_redemptions: int,
    expires_at: str | None,
    note: str,
) -> str:
    expires_sql = "null" if not expires_at else sql_quote(expires_at)
    return (
        "insert into public.activation_codes "
        "(code, plan_tier, duration_days, max_redemptions, expires_at, meta) values "
        f"({sql_quote(code)}, {sql_quote(plan_tier)}, {duration_days}, "
        f"{max_redemptions}, {expires_sql}, "
        f"{sql_quote(json.dumps({'note': note}, ensure_ascii=False))}::jsonb);"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a WordCraft Pro activation code SQL row.")
    parser.add_argument("--tier", default="pro", choices=["pro", "team", "enterprise"])
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-redemptions", type=int, default=1)
    parser.add_argument("--prefix", default="PRO")
    parser.add_argument("--code", default="")
    parser.add_argument("--expires-days", type=int, default=30)
    parser.add_argument("--no-expiry", action="store_true")
    parser.add_argument("--note", default="manual")
    args = parser.parse_args()

    code = (args.code or generate_code(args.prefix)).upper()
    expires_at = None
    if not args.no_expiry:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=args.expires_days)).isoformat()
    print(build_insert_sql(
        code=code,
        plan_tier=args.tier,
        duration_days=args.days,
        max_redemptions=args.max_redemptions,
        expires_at=expires_at,
        note=args.note,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
