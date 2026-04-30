-- Batch 17B: minimal team workspace for shared format rules.

create table if not exists public.team_format_rules (
  team_id uuid primary key references public.teams(id) on delete cascade,
  rules_json jsonb not null default '{}'::jsonb,
  updated_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default now()
);

alter table public.team_format_rules enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_format_rules'
      and policyname = 'team_format_rules_select_member'
  ) then
    create policy team_format_rules_select_member on public.team_format_rules
      for select using (
        exists (
          select 1 from public.team_members tm
          where tm.team_id = team_format_rules.team_id and tm.user_id = auth.uid()
        )
        or exists (
          select 1 from public.teams t
          where t.id = team_format_rules.team_id and t.owner_user_id = auth.uid()
        )
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_format_rules'
      and policyname = 'team_format_rules_upsert_owner'
  ) then
    create policy team_format_rules_upsert_owner on public.team_format_rules
      for all using (
        exists (
          select 1 from public.teams t
          where t.id = team_format_rules.team_id and t.owner_user_id = auth.uid()
        )
      )
      with check (
        exists (
          select 1 from public.teams t
          where t.id = team_format_rules.team_id and t.owner_user_id = auth.uid()
        )
      );
  end if;
end $$;

create or replace function public.create_team_workspace(p_name text, p_seat_limit integer default 5)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid := auth.uid();
  v_team_id uuid;
begin
  if v_user_id is null then
    return jsonb_build_object('success', false, 'error_code', 'NOT_AUTHENTICATED', 'error', 'User is not authenticated.');
  end if;

  insert into public.teams (name, owner_user_id, seat_limit, status)
  values (p_name, v_user_id, greatest(coalesce(p_seat_limit, 5), 1), 'active')
  returning id into v_team_id;

  insert into public.team_members (team_id, user_id, role)
  values (v_team_id, v_user_id, 'owner')
  on conflict (team_id, user_id) do update set role = excluded.role;

  update public.profiles
    set team_id = v_team_id
    where id = v_user_id;

  return jsonb_build_object('success', true, 'team_id', v_team_id);
end;
$$;

revoke execute on function public.create_team_workspace(text, integer) from public, anon;
grant execute on function public.create_team_workspace(text, integer) to authenticated;

create or replace function public.add_team_member_by_email(
  p_team_id uuid,
  p_email text,
  p_role text default 'member'
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_actor_id uuid := auth.uid();
  v_target_user_id uuid;
  v_team public.teams%rowtype;
  v_member_role text := case when lower(coalesce(p_role, 'member')) = 'owner' then 'owner' else 'member' end;
  v_member_count integer;
begin
  if v_actor_id is null then
    return jsonb_build_object('success', false, 'error_code', 'NOT_AUTHENTICATED', 'error', 'User is not authenticated.');
  end if;

  select *
    into v_team
    from public.teams
    where id = p_team_id;

  if not found then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_NOT_FOUND', 'error', 'Team was not found.');
  end if;

  if v_team.owner_user_id <> v_actor_id then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_OWNER_REQUIRED', 'error', 'Only the team owner can add members.');
  end if;

  select id
    into v_target_user_id
    from auth.users
    where lower(email) = lower(trim(p_email))
    limit 1;

  if v_target_user_id is null then
    return jsonb_build_object('success', false, 'error_code', 'USER_NOT_FOUND', 'error', 'User with this email was not found.');
  end if;

  if exists (
    select 1 from public.team_members
    where team_id = p_team_id and user_id = v_target_user_id
  ) then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_MEMBER_EXISTS', 'error', 'User is already a team member.');
  end if;

  select count(*)
    into v_member_count
    from public.team_members
    where team_id = p_team_id;

  if v_member_count >= coalesce(v_team.seat_limit, 0) then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_SEAT_LIMIT_REACHED', 'error', 'Team seat limit has been reached.');
  end if;

  insert into public.team_members (team_id, user_id, role)
  values (p_team_id, v_target_user_id, v_member_role);

  update public.profiles
    set team_id = p_team_id
    where id = v_target_user_id;

  return jsonb_build_object(
    'success', true,
    'added_member', jsonb_build_object(
      'team_id', p_team_id,
      'user_id', v_target_user_id,
      'email', lower(trim(p_email)),
      'role', v_member_role
    )
  );
end;
$$;

revoke execute on function public.add_team_member_by_email(uuid, text, text) from public, anon;
grant execute on function public.add_team_member_by_email(uuid, text, text) to authenticated;
