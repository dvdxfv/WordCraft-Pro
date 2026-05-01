-- Batch 17B: pending team invites and member-side acceptance flow.

alter table public.team_members
  add column if not exists status text not null default 'active',
  add column if not exists invite_email text,
  add column if not exists invited_by uuid references auth.users(id) on delete set null,
  add column if not exists invited_at timestamptz not null default now(),
  add column if not exists accepted_at timestamptz;

update public.team_members
set status = 'active',
    accepted_at = coalesce(accepted_at, joined_at),
    invite_email = coalesce(invite_email, lower(trim((
      select email from auth.users u where u.id = team_members.user_id
    ))))
where coalesce(status, '') = '' or accepted_at is null or invite_email is null;

create index if not exists idx_team_members_user_status
  on public.team_members(user_id, status);

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_members'
      and policyname = 'team_members_accept_own_pending_invite'
  ) then
    create policy team_members_accept_own_pending_invite on public.team_members
      for update to authenticated
      using (
        user_id = auth.uid()
        and status = 'pending'
      )
      with check (
        user_id = auth.uid()
      );
  end if;
end $$;

create or replace function public.add_team_member_by_email(
  p_team_id uuid,
  p_email text,
  p_role text default 'member'
)
returns jsonb
language plpgsql
security invoker
set search_path = public, auth
as $$
declare
  v_actor_id uuid := auth.uid();
  v_target_user_id uuid;
  v_team public.teams%rowtype;
  v_member_role text := case when lower(coalesce(p_role, 'member')) = 'owner' then 'owner' else 'member' end;
  v_member_count integer;
  v_email text := lower(trim(p_email));
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
    where lower(email) = v_email
    limit 1;

  if v_target_user_id is null then
    return jsonb_build_object('success', false, 'error_code', 'USER_NOT_FOUND', 'error', 'User with this email was not found.');
  end if;

  if exists (
    select 1 from public.team_members
    where team_id = p_team_id and user_id = v_target_user_id
  ) then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_MEMBER_EXISTS', 'error', 'User is already invited or already a team member.');
  end if;

  select count(*)
    into v_member_count
    from public.team_members
    where team_id = p_team_id;

  if v_member_count >= coalesce(v_team.seat_limit, 0) then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_SEAT_LIMIT_REACHED', 'error', 'Team seat limit has been reached.');
  end if;

  insert into public.team_members (
    team_id, user_id, role, status, invite_email, invited_by, invited_at
  )
  values (
    p_team_id, v_target_user_id, v_member_role, 'pending', v_email, v_actor_id, now()
  );

  return jsonb_build_object(
    'success', true,
    'added_member', jsonb_build_object(
      'team_id', p_team_id,
      'user_id', v_target_user_id,
      'email', v_email,
      'role', v_member_role,
      'status', 'pending'
    )
  );
end;
$$;

create or replace function public.accept_team_invite(
  p_team_id uuid
)
returns jsonb
language plpgsql
security invoker
set search_path = public, auth
as $$
declare
  v_user_id uuid := auth.uid();
  v_team public.teams%rowtype;
begin
  if v_user_id is null then
    return jsonb_build_object('success', false, 'error_code', 'NOT_AUTHENTICATED', 'error', 'User is not authenticated.');
  end if;

  select *
    into v_team
    from public.teams
    where id = p_team_id;

  if not found then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_NOT_FOUND', 'error', 'Team was not found.');
  end if;

  if not exists (
    select 1 from public.team_members
    where team_id = p_team_id and user_id = v_user_id and status = 'pending'
  ) then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_INVITE_NOT_FOUND', 'error', 'Pending invite was not found.');
  end if;

  update public.team_members
    set status = 'active',
        accepted_at = now(),
        joined_at = coalesce(joined_at, now())
    where team_id = p_team_id and user_id = v_user_id and status = 'pending';

  update public.profiles
    set team_id = p_team_id,
        plan_tier = 'team',
        plan_status = 'active',
        plan_source = 'team_invite'
    where id = v_user_id;

  return jsonb_build_object('success', true, 'team_id', p_team_id);
end;
$$;

revoke execute on function public.accept_team_invite(uuid) from public, anon;
grant execute on function public.accept_team_invite(uuid) to authenticated;
