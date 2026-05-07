import base64
import json
import sys
import time
from types import ModuleType, SimpleNamespace

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


def test_call_ai_records_token_usage_for_dashboard_stats(monkeypatch):
    class _FakeUsage:
        @staticmethod
        def model_dump():
            return {"total_tokens": 321, "prompt_tokens": 123, "completion_tokens": 198}

    class _FakeCompletions:
        @staticmethod
        def create(**_kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                usage=_FakeUsage(),
            )

    class _FakeOpenAI:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    class _FakeSupabase:
        def __init__(self):
            self.logged = []
            self.usage_counter_calls = []

        @staticmethod
        def get_user_entitlements(_user_id, access_token=None):
            del access_token
            return {
                "tier": "free",
                "status": "active",
                "source": "system",
                "usage": {
                    "ai_qa_used": 0,
                    "ai_parse_used": 0,
                    "rule_check_used_today": 0,
                },
                "limits": {
                    "ai_qa_per_period": 3,
                    "ai_parse_per_period": 3,
                    "rule_checks_per_day": 10,
                },
                "features": {
                    "ai_qa": True,
                    "ai_parse": True,
                    "deep_xref": False,
                    "personal_rule_library": False,
                    "team_rule_share": False,
                    "batch_check": False,
                },
            }

        def record_token_usage(self, user_id, amount, purpose, model="", prompt_tokens=0, completion_tokens=0, access_token=None):
            self.logged.append({
                "user_id": user_id,
                "amount": amount,
                "purpose": purpose,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "access_token": access_token,
            })
            return True

        def increment_usage_counter(self, user_id, counter_name, amount, access_token=None):
            self.usage_counter_calls.append((user_id, counter_name, amount, access_token))
            return {"user_id": user_id, counter_name: amount}

    fake_openai = ModuleType("openai")
    fake_openai.OpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    api = Api(supabase_enabled=False)
    api._supabase = _FakeSupabase()
    api._session = {
        "user_id": "user-123",
        "access_token": "token-123",
        "user_info": {
            "id": "user-123",
            "email": "user@example.com",
            "plan_tier": "free",
            "plan_status": "active",
            "plan_source": "system",
            "feature_flags": {},
        },
    }

    data = _json(api.callAI("system", "user", {"purpose": "ai_parse", "model": "deepseek-v4-flash"}))

    assert data["content"] == "ok"
    assert data["usage"]["total_tokens"] == 321
    assert api._supabase.logged == [{
        "user_id": "user-123",
        "amount": 321,
        "purpose": "ai_parse",
        "model": "deepseek-v4-flash",
        "prompt_tokens": 123,
        "completion_tokens": 198,
        "access_token": "token-123",
    }]
    assert api._supabase.usage_counter_calls == [("user-123", "ai_parse_used", 1, "token-123")]


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
    assert created["plan"]["tier"] == "team"
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
    assert data["added_member"]["status"] == "pending"
    assert len(data["members"]) == 2


def test_invited_local_member_can_accept_team_invite():
    owner_api = Api(supabase_enabled=False)
    owner_api._session = {
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
    created = _json(owner_api.createTeamWorkspace("编辑部", 2))
    team_id = created["team"]["id"]
    _json(owner_api.addTeamMemberByEmail("member@example.com"))

    invited_api = Api(supabase_enabled=False)
    invited_api._local_teams = owner_api._local_teams
    invited_api._local_team_rules = owner_api._local_team_rules
    invited_api._local_known_users = owner_api._local_known_users
    invited_api._session = {
        "user_id": "team-member-001",
        "user_info": {
            "id": "team-member-001",
            "email": "member@example.com",
            "plan_tier": "free",
            "plan_status": "active",
            "plan_source": "system",
            "feature_flags": {},
        },
    }

    workspace = _json(invited_api.getTeamWorkspace())
    accepted = _json(invited_api.acceptTeamInvite(team_id))
    plan = _json(invited_api.getCurrentPlan())

    assert workspace["success"] is True
    assert workspace["plan"]["tier"] == "free"
    assert len(workspace["invitations"]) == 1
    assert workspace["invitations"][0]["status"] == "pending"
    assert accepted["success"] is True
    assert accepted["team"]["id"] == team_id
    assert accepted["members"][1]["status"] == "active"
    assert accepted["plan"]["tier"] == "team"
    assert plan["plan"]["tier"] == "team"


def test_team_owner_can_cancel_pending_invite_locally():
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
    created = _json(api.createTeamWorkspace("团队空间", 2))
    team_id = created["team"]["id"]
    _json(api.addTeamMemberByEmail("member@example.com"))

    canceled = _json(api.cancelTeamInvite(team_id, "member@example.com"))
    readded = _json(api.addTeamMemberByEmail("member@example.com"))

    assert canceled["success"] is True
    assert len(canceled["members"]) == 1
    assert readded["success"] is True
    assert readded["added_member"]["status"] == "pending"


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


def test_team_owner_can_send_formal_invite_email_locally():
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
    _json(api.addTeamMemberByEmail("member@example.com"))
    api._deliver_team_invite_email = lambda email, payload: {  # type: ignore[method-assign]
        "success": True,
        "provider": "mock",
        "response": {"to": email, "subject": payload["subject"]},
    }

    data = _json(api.sendTeamInviteEmail("team-local-001", "member@example.com", "member"))

    assert data["success"] is True
    assert data["delivery"]["provider"] == "mock"
    assert data["activities"][0]["event_type"] == "team_invite_email_sent"


def test_team_user_can_start_batch_job_and_read_history():
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
    api.runQA = lambda content, categories_str='[]', elements_json=None: json.dumps({  # type: ignore[method-assign]
        "success": True,
        "issues": [{"severity": "warn", "message": "示例问题"}],
    }, ensure_ascii=False)

    started = _json(api.startTeamBatchQA(json.dumps([
        {"name": "a.docx", "content": "<p>A</p>"},
    ])))
    job_id = started["job"]["id"]
    for _ in range(20):
        jobs = _json(api.getTeamBatchJobs())
        job = next((item for item in jobs["jobs"] if item["id"] == job_id), None)
        if job and job["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    jobs = _json(api.getTeamBatchJobs())
    job = next(item for item in jobs["jobs"] if item["id"] == job_id)

    assert started["success"] is True
    assert job["status"] == "completed"
    assert job["result_payload"]["issues"] == 1
