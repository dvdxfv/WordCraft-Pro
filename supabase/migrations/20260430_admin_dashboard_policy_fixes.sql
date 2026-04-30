-- Fix admin dashboard read/write access for Batch 17A live verification.

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'profiles'
      and policyname = 'admin_can_view_all_profiles'
  ) then
    create policy admin_can_view_all_profiles on public.profiles
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'usage_counters'
      and policyname = 'admin_can_view_all_usage_counters'
  ) then
    create policy admin_can_view_all_usage_counters on public.usage_counters
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'subscriptions'
      and policyname = 'admin_can_view_all_subscriptions'
  ) then
    create policy admin_can_view_all_subscriptions on public.subscriptions
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'activation_codes'
      and policyname = 'admin_can_view_activation_codes'
  ) then
    create policy admin_can_view_activation_codes on public.activation_codes
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'activation_codes'
      and policyname = 'admin_can_insert_activation_codes'
  ) then
    create policy admin_can_insert_activation_codes on public.activation_codes
      for insert to authenticated
      with check (
        (select auth.jwt() ->> 'role') = 'admin'
        and created_by = auth.uid()
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'teams'
      and policyname = 'admin_can_view_all_teams'
  ) then
    create policy admin_can_view_all_teams on public.teams
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_members'
      and policyname = 'admin_can_view_all_team_members'
  ) then
    create policy admin_can_view_all_team_members on public.team_members
      for select to authenticated
      using ((select auth.jwt() ->> 'role') = 'admin');
  end if;
end $$;

drop policy if exists team_members_select_own_team on public.team_members;

create policy team_members_select_own_team on public.team_members
  for select to public
  using (
    user_id = auth.uid()
    or (select auth.jwt() ->> 'role') = 'admin'
  );
