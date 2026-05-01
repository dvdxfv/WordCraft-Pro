-- Batch 17B: owner-side pending invite cancellation.

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_members'
      and policyname = 'team_members_delete_pending_invite_by_team_owner'
  ) then
    create policy team_members_delete_pending_invite_by_team_owner on public.team_members
      for delete to authenticated
      using (
        status = 'pending'
        and exists (
          select 1 from public.teams t
          where t.id = team_members.team_id
            and t.owner_user_id = auth.uid()
        )
      );
  end if;
end $$;

create or replace function public.cancel_team_invite(
  p_team_id uuid,
  p_email text
)
returns jsonb
language plpgsql
security invoker
set search_path = public, auth
as $$
declare
  v_actor_id uuid := auth.uid();
  v_team public.teams%rowtype;
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
    return jsonb_build_object('success', false, 'error_code', 'TEAM_OWNER_REQUIRED', 'error', 'Only the team owner can cancel pending invites.');
  end if;

  if not exists (
    select 1 from public.team_members
    where team_id = p_team_id
      and status = 'pending'
      and lower(coalesce(invite_email, '')) = v_email
  ) then
    return jsonb_build_object('success', false, 'error_code', 'TEAM_INVITE_NOT_FOUND', 'error', 'Pending invite was not found.');
  end if;

  delete from public.team_members
    where team_id = p_team_id
      and status = 'pending'
      and lower(coalesce(invite_email, '')) = v_email;

  return jsonb_build_object('success', true, 'team_id', p_team_id, 'invite_email', v_email);
end;
$$;

revoke execute on function public.cancel_team_invite(uuid, text) from public, anon;
grant execute on function public.cancel_team_invite(uuid, text) to authenticated;
