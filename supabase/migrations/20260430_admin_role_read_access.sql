-- Admin role support for dashboard reads and stats views.

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'token_logs'
      and policyname = 'admin_can_view_all_token_logs'
  ) then
    create policy admin_can_view_all_token_logs on public.token_logs
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'documents'
      and policyname = 'admin_can_view_all_documents'
  ) then
    create policy admin_can_view_all_documents on public.documents
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'templates'
      and policyname = 'admin_can_view_all_templates'
  ) then
    create policy admin_can_view_all_templates on public.templates
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'user_settings'
      and policyname = 'admin_can_view_all_user_settings'
  ) then
    create policy admin_can_view_all_user_settings on public.user_settings
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;
end $$;

grant select on table public.admin_user_stats to authenticated;
grant select on table public.admin_token_daily_stats to authenticated;
