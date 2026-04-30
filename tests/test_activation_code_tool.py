import re

from tools.generate_activation_code import build_insert_sql, generate_code


def test_generate_code_uses_prefix_and_grouped_uppercase_token():
    code = generate_code(prefix="PRO", groups=2, group_size=4)

    assert re.fullmatch(r"PRO-[A-Z0-9]{4}-[A-Z0-9]{4}", code)


def test_build_insert_sql_escapes_note_as_jsonb():
    sql = build_insert_sql(
        code="PRO-TEST",
        plan_tier="pro",
        duration_days=30,
        max_redemptions=1,
        expires_at=None,
        note="manual user's payment",
    )

    assert "insert into public.activation_codes" in sql
    assert "'PRO-TEST'" in sql
    assert "'pro'" in sql
    assert "::jsonb" in sql
    assert "manual user''s payment" in sql
