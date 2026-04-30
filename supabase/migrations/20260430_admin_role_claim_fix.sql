-- Fix admin RLS policies to read the custom admin role from JWT app_metadata.

drop policy if exists admin_can_view_all_token_logs on public.token_logs;
create policy admin_can_view_all_token_logs on public.token_logs
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_all_documents on public.documents;
create policy admin_can_view_all_documents on public.documents
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_all_templates on public.templates;
create policy admin_can_view_all_templates on public.templates
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_all_user_settings on public.user_settings;
create policy admin_can_view_all_user_settings on public.user_settings
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_all_profiles on public.profiles;
create policy admin_can_view_all_profiles on public.profiles
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_all_usage_counters on public.usage_counters;
create policy admin_can_view_all_usage_counters on public.usage_counters
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_all_subscriptions on public.subscriptions;
create policy admin_can_view_all_subscriptions on public.subscriptions
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_activation_codes on public.activation_codes;
create policy admin_can_view_activation_codes on public.activation_codes
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_insert_activation_codes on public.activation_codes;
create policy admin_can_insert_activation_codes on public.activation_codes
  for insert to authenticated
  with check (
    (select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin'
    and created_by = auth.uid()
  );

drop policy if exists admin_can_view_all_teams on public.teams;
create policy admin_can_view_all_teams on public.teams
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists admin_can_view_all_team_members on public.team_members;
create policy admin_can_view_all_team_members on public.team_members
  for select to authenticated
  using ((select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin');

drop policy if exists team_members_select_own_team on public.team_members;
create policy team_members_select_own_team on public.team_members
  for select to public
  using (
    user_id = auth.uid()
    or (select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin'
  );
