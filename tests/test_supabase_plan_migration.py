from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[1] / "supabase" / "migrations" / "20260429_batch17_user_plans.sql"
PROFILE_LOCK_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260430_batch17_lock_profile_plan_columns.sql"
)
RPC_LOCK_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260430_batch17_restrict_activation_rpc.sql"
)
ADMIN_VIEW_LOCK_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260430_lock_admin_stats_views.sql"
)
ADMIN_ROLE_ACCESS_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260430_admin_role_read_access.sql"
)
ADMIN_DASHBOARD_FIX_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260430_admin_dashboard_policy_fixes.sql"
)
ADMIN_ROLE_CLAIM_FIX_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260430_admin_role_claim_fix.sql"
)
TEAM_WORKSPACE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260501_batch17b_team_workspace.sql"
)
TEAM_INVOKER_HARDENING_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260501_batch17b_invoker_hardening.sql"
)
ADMIN_DELETE_UNUSED_CODES_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260501_admin_delete_unused_activation_codes.sql"
)
TEAM_INVITES_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260502_batch17b_team_invites.sql"
)
TEAM_INVITE_CANCEL_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260502_batch17b_cancel_team_invite.sql"
)


def test_plan_migration_uses_rpc_for_activation_redemption():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "create or replace function public.redeem_activation_code" in sql
    assert "security definer" in sql.lower()
    assert "revoke execute on function public.redeem_activation_code(text) from public, anon" in sql
    assert "grant execute on function public.redeem_activation_code(text) to authenticated" in sql


def test_plan_migration_does_not_allow_users_to_update_profiles_directly():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "profiles_update_own" not in sql
    assert "activation_codes_read_unexpired" not in sql
    assert "activation_codes_update_redeemable" not in sql


def test_plan_migration_rpc_error_messages_are_valid_sql_strings():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "'User is not authenticated.'" in sql
    assert "'Activation code was not found.'" in sql
    assert "'Activation code has expired.'" in sql
    assert "'Activation code has been fully redeemed.'" in sql


def test_profile_lock_migration_removes_direct_plan_updates():
    sql = PROFILE_LOCK_MIGRATION.read_text(encoding="utf-8").lower()

    assert "revoke update on public.profiles from anon, authenticated" in sql
    assert "grant update (" in sql
    assert "plan_tier" not in sql
    assert "plan_status" not in sql
    assert "token_quota" not in sql
    assert "feature_flags" not in sql


def test_rpc_lock_migration_removes_anon_execute():
    sql = RPC_LOCK_MIGRATION.read_text(encoding="utf-8").lower()

    assert "revoke execute on function public.redeem_activation_code(text) from public, anon" in sql
    assert "grant execute on function public.redeem_activation_code(text) to authenticated" in sql


def test_admin_stats_views_do_not_bypass_rls_for_api_roles():
    sql = ADMIN_VIEW_LOCK_MIGRATION.read_text(encoding="utf-8").lower()

    assert "set (security_invoker = true)" in sql
    assert "revoke all on table public.admin_user_stats from anon, authenticated" in sql
    assert "revoke all on table public.admin_token_daily_stats from anon, authenticated" in sql


def test_admin_role_access_migration_restores_dashboard_reads_for_admins():
    sql = ADMIN_ROLE_ACCESS_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create policy admin_can_view_all_token_logs" in sql
    assert "create policy admin_can_view_all_documents" in sql
    assert "create policy admin_can_view_all_templates" in sql
    assert "create policy admin_can_view_all_user_settings" in sql
    assert "grant select on table public.admin_user_stats to authenticated" in sql
    assert "grant select on table public.admin_token_daily_stats to authenticated" in sql


def test_admin_dashboard_fix_migration_adds_missing_admin_read_paths():
    sql = ADMIN_DASHBOARD_FIX_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create policy admin_can_view_all_profiles" in sql
    assert "create policy admin_can_view_all_usage_counters" in sql
    assert "create policy admin_can_view_all_subscriptions" in sql
    assert "create policy admin_can_view_activation_codes" in sql
    assert "create policy admin_can_insert_activation_codes" in sql
    assert "create policy admin_can_view_all_teams" in sql
    assert "create policy admin_can_view_all_team_members" in sql


def test_admin_dashboard_fix_migration_breaks_team_policy_recursion():
    sql = ADMIN_DASHBOARD_FIX_MIGRATION.read_text(encoding="utf-8").lower()

    assert "drop policy if exists team_members_select_own_team on public.team_members" in sql
    assert "create policy team_members_select_own_team on public.team_members" in sql
    assert "user_id = auth.uid()" in sql
    assert "select 1 from public.teams" not in sql


def test_admin_role_claim_fix_uses_app_metadata_role():
    sql = ADMIN_ROLE_CLAIM_FIX_MIGRATION.read_text(encoding="utf-8").lower()

    assert "coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')" in sql
    assert "drop policy if exists admin_can_view_all_token_logs on public.token_logs" in sql
    assert "drop policy if exists admin_can_view_all_profiles on public.profiles" in sql
    assert "drop policy if exists admin_can_insert_activation_codes on public.activation_codes" in sql
    assert "created_by = auth.uid()" in sql


def test_team_workspace_migration_creates_shared_rules_table_and_rls():
    sql = TEAM_WORKSPACE_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.team_format_rules" in sql
    assert "alter table public.team_format_rules enable row level security" in sql
    assert "create policy team_format_rules_select_member" in sql
    assert "create policy team_format_rules_upsert_owner" in sql


def test_team_workspace_migration_exposes_authenticated_team_creation_rpc():
    sql = TEAM_WORKSPACE_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function public.create_team_workspace" in sql
    assert "security definer" in sql
    assert "insert into public.team_members" in sql
    assert "update public.profiles" in sql
    assert "revoke execute on function public.create_team_workspace(text, integer) from public, anon" in sql
    assert "grant execute on function public.create_team_workspace(text, integer) to authenticated" in sql


def test_team_workspace_migration_exposes_add_member_rpc():
    sql = TEAM_WORKSPACE_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function public.add_team_member_by_email" in sql
    assert "only the team owner can add members." in sql
    assert "team seat limit has been reached." in sql
    assert "update public.profiles" in sql
    assert "revoke execute on function public.add_team_member_by_email(uuid, text, text) from public, anon" in sql
    assert "grant execute on function public.add_team_member_by_email(uuid, text, text) to authenticated" in sql


def test_team_invoker_hardening_migration_adds_precise_update_and_insert_policies():
    sql = TEAM_INVOKER_HARDENING_MIGRATION.read_text(encoding="utf-8").lower()

    assert "grant update (" in sql
    assert "team_id" in sql
    assert "profiles_update_own_team_membership" in sql
    assert "profiles_update_team_membership_by_team_owner" in sql
    assert "team_members_insert_by_team_owner" in sql


def test_team_invoker_hardening_migration_switches_team_rpcs_to_security_invoker():
    sql = TEAM_INVOKER_HARDENING_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function public.create_team_workspace" in sql
    assert "create or replace function public.add_team_member_by_email" in sql
    assert "security invoker" in sql
    assert "only the team owner can add members." in sql


def test_admin_delete_unused_codes_migration_limits_delete_to_unused_codes_for_admins():
    sql = ADMIN_DELETE_UNUSED_CODES_MIGRATION.read_text(encoding="utf-8").lower()

    assert "drop policy if exists admin_can_delete_unused_activation_codes on public.activation_codes" in sql
    assert "create policy admin_can_delete_unused_activation_codes on public.activation_codes" in sql
    assert "for delete to authenticated" in sql
    assert "coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')" in sql
    assert "coalesce(redeemed_count, 0) = 0" in sql


def test_team_invites_migration_adds_pending_invite_columns_and_index():
    sql = TEAM_INVITES_MIGRATION.read_text(encoding="utf-8").lower()

    assert "alter table public.team_members" in sql
    assert "add column if not exists status text not null default 'active'" in sql
    assert "add column if not exists invite_email text" in sql
    assert "add column if not exists invited_by uuid" in sql
    assert "add column if not exists invited_at timestamptz not null default now()" in sql
    assert "add column if not exists accepted_at timestamptz" in sql
    assert "create index if not exists idx_team_members_user_status" in sql


def test_team_invites_migration_adds_member_accept_policy_and_rpc():
    sql = TEAM_INVITES_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create policy team_members_accept_own_pending_invite" in sql
    assert "status = 'pending'" in sql
    assert "create or replace function public.accept_team_invite" in sql
    assert "pending invite was not found." in sql
    assert "plan_tier = 'team'" in sql
    assert "plan_source = 'team_invite'" in sql
    assert "revoke execute on function public.accept_team_invite(uuid) from public, anon" in sql
    assert "grant execute on function public.accept_team_invite(uuid) to authenticated" in sql


def test_team_invites_migration_switches_add_member_to_pending_invites():
    sql = TEAM_INVITES_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function public.add_team_member_by_email" in sql
    assert "'user is already invited or already a team member.'" in sql
    assert "'pending'" in sql
    assert "invite_email" in sql
    assert "invited_by" in sql
    assert "update public.profiles" not in sql.split("create or replace function public.add_team_member_by_email", 1)[1].split("create or replace function public.accept_team_invite", 1)[0]


def test_team_invite_cancel_migration_adds_owner_delete_policy_and_rpc():
    sql = TEAM_INVITE_CANCEL_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create policy team_members_delete_pending_invite_by_team_owner" in sql
    assert "for delete to authenticated" in sql
    assert "status = 'pending'" in sql
    assert "create or replace function public.cancel_team_invite" in sql
    assert "only the team owner can cancel pending invites." in sql
    assert "pending invite was not found." in sql
    assert "delete from public.team_members" in sql
    assert "revoke execute on function public.cancel_team_invite(uuid, text) from public, anon" in sql
    assert "grant execute on function public.cancel_team_invite(uuid, text) to authenticated" in sql
