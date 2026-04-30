"""Plan entitlement and quota helpers for WordCraft Pro.

The rules in this module are intentionally pure and storage-agnostic.  API
layers pass a profile plus usage counters in, then enforce the returned
contract at the feature boundary.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


PLAN_TIERS = ("free", "pro", "team", "enterprise")

PLAN_DEFINITIONS: dict[str, dict[str, Any]] = {
    "free": {
        "label": "免费版",
        "limits": {
            "file_size_mb": 5,
            "rule_checks_per_day": 10,
            "ai_qa_per_month": 3,
            "ai_parse_per_month": 3,
        },
        "features": {
            "ai_qa": True,
            "ai_parse": True,
            "deep_xref": False,
            "personal_rule_library": False,
            "team_rule_share": False,
            "batch_check": False,
        },
    },
    "pro": {
        "label": "专业版",
        "limits": {
            "file_size_mb": 30,
            "rule_checks_per_day": None,
            "ai_qa_per_month": None,
            "ai_parse_per_month": None,
        },
        "features": {
            "ai_qa": True,
            "ai_parse": True,
            "deep_xref": True,
            "personal_rule_library": True,
            "team_rule_share": False,
            "batch_check": False,
        },
    },
    "team": {
        "label": "团队版",
        "limits": {
            "file_size_mb": 100,
            "rule_checks_per_day": None,
            "ai_qa_per_month": None,
            "ai_parse_per_month": None,
        },
        "features": {
            "ai_qa": True,
            "ai_parse": True,
            "deep_xref": True,
            "personal_rule_library": True,
            "team_rule_share": True,
            "batch_check": True,
        },
    },
    "enterprise": {
        "label": "机构版",
        "limits": {
            "file_size_mb": None,
            "rule_checks_per_day": None,
            "ai_qa_per_month": None,
            "ai_parse_per_month": None,
        },
        "features": {
            "ai_qa": True,
            "ai_parse": True,
            "deep_xref": True,
            "personal_rule_library": True,
            "team_rule_share": True,
            "batch_check": True,
        },
    },
}

USAGE_LIMIT_KEYS = {
    "ai_qa": ("ai_qa_used", "ai_qa_per_month"),
    "ai_parse": ("ai_parse_used", "ai_parse_per_month"),
    "rule_check": ("rule_check_used_today", "rule_checks_per_day"),
}

FEATURE_UPGRADE_TARGET = {
    "ai_qa": "pro",
    "ai_parse": "pro",
    "deep_xref": "pro",
    "personal_rule_library": "pro",
    "team_rule_share": "team",
    "batch_check": "team",
}


def current_period_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def current_day_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d")


def normalize_tier(tier: Any) -> str:
    tier = str(tier or "free").strip().lower()
    return tier if tier in PLAN_DEFINITIONS else "free"


def normalize_status(status: Any) -> str:
    status = str(status or "active").strip().lower()
    return status or "active"


def is_active_plan(profile: dict[str, Any] | None, now: datetime | None = None) -> bool:
    profile = profile or {}
    status = normalize_status(profile.get("plan_status"))
    if status not in ("active", "trialing"):
        return False
    period_end = profile.get("current_period_end")
    if not period_end:
        return True
    try:
        if isinstance(period_end, str):
            period_end_dt = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
        else:
            period_end_dt = period_end
        return period_end_dt >= (now or datetime.now(timezone.utc))
    except Exception:
        return True


def build_entitlements(
    profile: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    profile = profile or {}
    usage = usage or {}
    tier = normalize_tier(profile.get("plan_tier"))
    status = normalize_status(profile.get("plan_status"))
    if not is_active_plan(profile, now=now):
        tier = "free"
        status = "expired"

    plan = deepcopy(PLAN_DEFINITIONS[tier])
    feature_flags = profile.get("feature_flags") or {}
    if isinstance(feature_flags, dict):
        plan["features"].update({k: bool(v) for k, v in feature_flags.items()})

    normalized_usage = {
        "ai_qa_used": int(usage.get("ai_qa_used") or 0),
        "ai_parse_used": int(usage.get("ai_parse_used") or 0),
        "rule_check_used_today": int(usage.get("rule_check_used_today") or 0),
    }
    return {
        "tier": tier,
        "label": plan["label"],
        "status": status,
        "source": profile.get("plan_source") or "system",
        "current_period_start": profile.get("current_period_start"),
        "current_period_end": profile.get("current_period_end"),
        "limits": plan["limits"],
        "features": plan["features"],
        "usage": normalized_usage,
    }


def _deny(reason_code: str, feature: str, message: str, upgrade_target: str | None = None) -> dict[str, Any]:
    return {
        "allowed": False,
        "reason_code": reason_code,
        "feature": feature,
        "upgrade_target": upgrade_target or FEATURE_UPGRADE_TARGET.get(feature, "pro"),
        "message": message,
    }


def allow(feature: str) -> dict[str, Any]:
    return {
        "allowed": True,
        "reason_code": "OK",
        "feature": feature,
        "upgrade_target": None,
        "message": "",
    }


def check_feature_access(entitlements: dict[str, Any], feature: str) -> dict[str, Any]:
    if entitlements.get("features", {}).get(feature, False):
        return allow(feature)
    target = FEATURE_UPGRADE_TARGET.get(feature, "pro")
    return _deny(
        "FEATURE_LOCKED",
        feature,
        f"当前套餐不可使用该功能，请升级到 {target}。",
        target,
    )


def check_quota_available(entitlements: dict[str, Any], usage_name: str) -> dict[str, Any]:
    if usage_name not in USAGE_LIMIT_KEYS:
        return allow(usage_name)
    used_key, limit_key = USAGE_LIMIT_KEYS[usage_name]
    limit = entitlements.get("limits", {}).get(limit_key)
    if limit is None:
        return allow(usage_name)
    used = int(entitlements.get("usage", {}).get(used_key) or 0)
    if used < int(limit):
        return allow(usage_name)
    return _deny(
        "QUOTA_EXCEEDED",
        usage_name,
        f"本周期 {usage_name} 配额已用完，请升级套餐或等待额度恢复。",
        FEATURE_UPGRADE_TARGET.get(usage_name, "pro"),
    )


def check_file_size_allowed(entitlements: dict[str, Any], size_bytes: int) -> dict[str, Any]:
    limit_mb = entitlements.get("limits", {}).get("file_size_mb")
    if limit_mb is None:
        return allow("file_size")
    limit_bytes = int(float(limit_mb) * 1024 * 1024)
    if size_bytes <= limit_bytes:
        return allow("file_size")
    return _deny(
        "FILE_TOO_LARGE_FOR_PLAN",
        "file_size",
        f"当前套餐单文件上限为 {limit_mb}MB，请升级后上传更大的文件。",
        "pro",
    )
