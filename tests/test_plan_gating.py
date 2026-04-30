import base64
import json
from types import SimpleNamespace

from app import Api


def _json(result: str) -> dict:
    return json.loads(result)


def test_get_current_plan_defaults_to_free_in_local_mode():
    api = Api(supabase_enabled=False)

    data = _json(api.getCurrentPlan())

    assert data["success"] is True
    assert data["plan"]["tier"] == "free"
    assert data["plan"]["limits"]["rule_checks_per_day"] == 10


def test_free_user_cannot_use_deep_xref_by_direct_api_call():
    api = Api(supabase_enabled=False)

    data = _json(api.runXRef("<h1>第1章 绪论</h1><p>见第1章。</p>", deep=True))

    assert data["success"] is False
    assert data["entitlement_denied"] is True
    assert data["error_code"] == "FEATURE_LOCKED"
    assert data["upgrade_target"] == "pro"


def test_local_activation_code_upgrades_to_pro_and_unlocks_xref():
    api = Api(supabase_enabled=False)

    redeemed = _json(api.redeemActivationCode("PRO-LOCAL"))
    plan = _json(api.getCurrentPlan())
    xref = _json(api.runXRef("<h1>第1章 绪论</h1><p>见第1章。</p>", deep=True))

    assert redeemed["success"] is True
    assert plan["plan"]["tier"] == "pro"
    assert xref["success"] is True


def test_ai_parse_quota_blocks_fourth_direct_call_before_network():
    api = Api(supabase_enabled=False)
    api._local_usage_counters["mock-user-001:2099-01"] = {
        "user_id": "mock-user-001",
        "period_key": "2099-01",
        "day_key": "2099-01-01",
        "ai_qa_used": 0,
        "ai_parse_used": 3,
        "rule_check_used_today": 0,
    }

    # Force the current usage row through the public helper so the test is not
    # coupled to the real calendar month.
    row = api._get_usage_counter()
    row["ai_parse_used"] = 3

    data = _json(api.callAI("system", "user", {"purpose": "ai_parse"}))

    assert data["success"] is False
    assert data["entitlement_denied"] is True
    assert data["error_code"] == "QUOTA_EXCEEDED"


def test_ai_qa_chunk_can_skip_quota_charge_after_first_chunk():
    api = Api(supabase_enabled=False)
    row = api._get_usage_counter()
    row["ai_qa_used"] = 3

    data = _json(api.callAI("system", "user", {"purpose": "ai_qa", "charge_quota": False}))

    assert data.get("entitlement_denied") is not True
    assert data.get("error_code") != "QUOTA_EXCEEDED"


def test_free_user_cannot_save_personal_format_rules():
    api = Api(supabase_enabled=False)

    data = _json(api.saveFormatRequirements(json.dumps({"h1Font": "黑体"})))

    assert data["success"] is False
    assert data["entitlement_denied"] is True
    assert data["feature"] == "personal_rule_library"


def test_pro_user_cannot_save_team_format_rules():
    api = Api(supabase_enabled=False)
    api._session = {
        "user_id": "pro-user-001",
        "user_info": {
            "id": "pro-user-001",
            "email": "pro@example.com",
            "plan_tier": "pro",
            "plan_status": "active",
            "plan_source": "admin",
            "feature_flags": {},
        },
    }

    data = _json(api.saveFormatRequirements(json.dumps({"h1Font": "黑体"}), "team"))

    assert data["success"] is False
    assert data["entitlement_denied"] is True
    assert data["feature"] == "team_rule_share"
    assert data["upgrade_target"] == "team"


def test_team_user_can_create_workspace_and_save_team_rules_locally():
    api = Api(supabase_enabled=False)
    api._session = {
        "user_id": "team-user-001",
        "user_info": {
            "id": "team-user-001",
            "email": "team@example.com",
            "plan_tier": "team",
            "plan_status": "active",
            "plan_source": "admin",
            "feature_flags": {},
        },
    }

    created = _json(api.createTeamWorkspace("编辑部"))
    saved = _json(api.saveFormatRequirements(json.dumps({"h1Font": "黑体"}), "team"))
    loaded = _json(api.loadFormatRequirements("team"))

    assert created["success"] is True
    assert created["team"]["name"] == "编辑部"
    assert saved["success"] is True
    assert saved["scope"] == "team"
    assert loaded["success"] is True
    assert loaded["scope"] == "team"
    assert loaded["rules"]["h1Font"] == "黑体"


def test_team_owner_can_add_member_by_email_locally():
    api = Api(supabase_enabled=False)
    api._session = {
        "user_id": "team-user-001",
        "user_info": {
            "id": "team-user-001",
            "email": "team@example.com",
            "plan_tier": "team",
            "plan_status": "active",
            "plan_source": "admin",
            "feature_flags": {},
        },
    }
    _json(api.createTeamWorkspace("编辑部", 2))

    data = _json(api.addTeamMemberByEmail("member@example.com"))

    assert data["success"] is True
    assert data["added_member"]["email"] == "member@example.com"
    assert len(data["members"]) == 2


def test_team_member_add_respects_local_seat_limit():
    api = Api(supabase_enabled=False)
    api._session = {
        "user_id": "team-user-001",
        "user_info": {
            "id": "team-user-001",
            "email": "team@example.com",
            "plan_tier": "team",
            "plan_status": "active",
            "plan_source": "admin",
            "feature_flags": {},
        },
    }
    _json(api.createTeamWorkspace("编辑部", 1))

    data = _json(api.addTeamMemberByEmail("member@example.com"))

    assert data["success"] is False
    assert data["error_code"] == "TEAM_SEAT_LIMIT_REACHED"


def test_free_file_size_gate_rejects_large_upload_before_parse():
    api = Api(supabase_enabled=False)
    raw = b"x" * (6 * 1024 * 1024)

    data = _json(api.openFile(base64.b64encode(raw).decode("ascii"), "large.txt"))

    assert data["success"] is False
    assert data["entitlement_denied"] is True
    assert data["error_code"] == "FILE_TOO_LARGE_FOR_PLAN"


def test_login_carries_admin_role_from_auth_metadata():
    class _FakeAuth:
        @staticmethod
        def get_user(_token):
            user = SimpleNamespace(app_metadata={"role": "admin"}, raw_app_meta_data={"role": "admin"})
            return SimpleNamespace(user=user)

    class _FakeSupabase:
        client = SimpleNamespace(auth=_FakeAuth())

        @staticmethod
        def sign_in(email, _password):
            return {
                "success": True,
                "user_id": "user-1",
                "email": email,
                "access_token": "token-1",
            }

        @staticmethod
        def get_profile(_user_id):
            return {
                "nickname": "admin",
                "avatar_url": "",
                "token_quota": 100000,
                "token_used": 0,
                "plan_tier": "free",
                "plan_status": "active",
                "plan_source": "system",
                "feature_flags": {},
            }

    api = Api(supabase_enabled=False)
    api._supabase = _FakeSupabase()

    data = _json(api.login("admin@wordcraft.com", "password"))

    assert data["success"] is True
    assert data["user"]["role"] == "admin"
    assert api._session["user_info"]["role"] == "admin"


def test_free_user_cannot_run_batch_qa():
    api = Api(supabase_enabled=False)

    data = _json(api.runBatchQA(json.dumps([{"name": "a.docx", "content": "<p>test</p>"}])))

    assert data["success"] is False
    assert data["entitlement_denied"] is True
    assert data["feature"] == "batch_check"


def test_team_user_batch_qa_aggregates_results():
    api = Api(supabase_enabled=False)
    api._session = {
        "user_id": "team-user-001",
        "user_info": {
            "id": "team-user-001",
            "email": "team@example.com",
            "plan_tier": "team",
            "plan_status": "active",
            "plan_source": "admin",
            "feature_flags": {},
        },
    }
    api.runQA = lambda content, categories_str='[]', elements_json=None: json.dumps({  # type: ignore[method-assign]
        "success": True,
        "issues": [],
        "content_echo": content,
    }, ensure_ascii=False)

    data = _json(api.runBatchQA(json.dumps([
        {"name": "a.docx", "content": "<p>A</p>"},
        {"name": "b.docx", "content": "<p>B</p>"},
    ])))

    assert data["success"] is True
    assert data["count"] == 2
    assert data["results"][0]["name"] == "a.docx"
    assert data["results"][1]["result"]["success"] is True
