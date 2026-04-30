from core.entitlements import (
    build_entitlements,
    check_feature_access,
    check_file_size_allowed,
    check_quota_available,
)


def test_free_plan_has_expected_limits_and_locked_features():
    entitlements = build_entitlements(
        {"plan_tier": "free", "plan_status": "active"},
        {"ai_qa_used": 1, "ai_parse_used": 2, "rule_check_used_today": 4},
    )

    assert entitlements["tier"] == "free"
    assert entitlements["limits"]["file_size_mb"] == 5
    assert entitlements["limits"]["ai_qa_per_month"] == 3
    assert entitlements["features"]["ai_parse"] is True
    assert entitlements["features"]["deep_xref"] is False
    assert entitlements["features"]["personal_rule_library"] is False


def test_free_quota_denies_after_monthly_ai_parse_limit():
    entitlements = build_entitlements(
        {"plan_tier": "free", "plan_status": "active"},
        {"ai_parse_used": 3},
    )

    gate = check_quota_available(entitlements, "ai_parse")

    assert gate["allowed"] is False
    assert gate["reason_code"] == "QUOTA_EXCEEDED"
    assert gate["upgrade_target"] == "pro"


def test_pro_plan_removes_ai_and_rule_check_quotas():
    entitlements = build_entitlements(
        {"plan_tier": "pro", "plan_status": "active"},
        {"ai_qa_used": 999, "ai_parse_used": 999, "rule_check_used_today": 999},
    )

    assert check_quota_available(entitlements, "ai_qa")["allowed"] is True
    assert check_quota_available(entitlements, "ai_parse")["allowed"] is True
    assert check_quota_available(entitlements, "rule_check")["allowed"] is True
    assert check_feature_access(entitlements, "personal_rule_library")["allowed"] is True


def test_expired_paid_plan_falls_back_to_free():
    entitlements = build_entitlements(
        {
            "plan_tier": "pro",
            "plan_status": "active",
            "current_period_end": "2000-01-01T00:00:00+00:00",
        },
        {},
    )

    assert entitlements["tier"] == "free"
    assert entitlements["status"] == "expired"
    assert check_feature_access(entitlements, "deep_xref")["allowed"] is False


def test_file_size_gate_uses_current_plan_limit():
    free = build_entitlements({"plan_tier": "free"}, {})
    pro = build_entitlements({"plan_tier": "pro"}, {})

    assert check_file_size_allowed(free, 6 * 1024 * 1024)["allowed"] is False
    assert check_file_size_allowed(pro, 6 * 1024 * 1024)["allowed"] is True
