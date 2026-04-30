-- Batch 17A: user plan, quota, activation-code foundation.

alter table if exists public.profiles
  add column if not exists plan_tier text not null default 'free',
  add column if not exists plan_status text not null default 'active',
  add column if not exists plan_source text not null default 'system',
  add column if not exists current_period_start timestamptz,
  add column if not exists current_period_end timestamptz,
  add column if not exists team_id uuid,
  add column if not exists feature_flags jsonb not null default '{}'::jsonb;

create table if not exists public.usage_counters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  period_key text not null,
  day_key text,
  ai_qa_used integer not null default 0,
  ai_parse_used integer not null default 0,
  rule_check_used_today integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, period_key)
);

create table if not exists public.activation_codes (
  code text primary key,
  plan_tier text not null default 'pro',
  duration_days integer not null default 30,
  max_redemptions integer not null default 1,
  redeemed_count integer not null default 0,
  expires_at timestamptz,
  created_by uuid references auth.users(id) on delete set null,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  plan_tier text not null,
  status text not null default 'active',
  source text not null default 'manual',
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  external_order_id text,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  seat_limit integer not null default 5,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table if not exists public.team_members (
  team_id uuid not null references public.teams(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member',
  joined_at timestamptz not null default now(),
  primary key (team_id, user_id)
);

create index if not exists idx_usage_counters_user_period
  on public.usage_counters(user_id, period_key);

create index if not exists idx_subscriptions_user
  on public.subscriptions(user_id, started_at desc);

create index if not exists idx_team_members_user
  on public.team_members(user_id);

alter table public.usage_counters enable row level security;
alter table public.activation_codes enable row level security;
alter table public.subscriptions enable row level security;
alter table public.teams enable row level security;
alter table public.team_members enable row level security;
alter table public.profiles enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'profiles'
      and policyname = 'profiles_select_own'
  ) then
    create policy profiles_select_own on public.profiles
      for select using (auth.uid() = id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'usage_counters'
      and policyname = 'usage_counters_select_own'
  ) then
    create policy usage_counters_select_own on public.usage_counters
      for select using (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'usage_counters'
      and policyname = 'usage_counters_insert_own'
  ) then
    create policy usage_counters_insert_own on public.usage_counters
      for insert with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'usage_counters'
      and policyname = 'usage_counters_update_own'
  ) then
    create policy usage_counters_update_own on public.usage_counters
      for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'subscriptions'
      and policyname = 'subscriptions_select_own'
  ) then
    create policy subscriptions_select_own on public.subscriptions
      for select using (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'subscriptions'
      and policyname = 'subscriptions_insert_own'
  ) then
    create policy subscriptions_insert_own on public.subscriptions
      for insert with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'teams'
      and policyname = 'teams_select_member'
  ) then
    create policy teams_select_member on public.teams
      for select using (
        owner_user_id = auth.uid()
        or exists (
          select 1 from public.team_members tm
          where tm.team_id = id and tm.user_id = auth.uid()
        )
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'teams'
      and policyname = 'teams_insert_owner'
  ) then
    create policy teams_insert_owner on public.teams
      for insert with check (owner_user_id = auth.uid());
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_members'
      and policyname = 'team_members_select_own_team'
  ) then
    create policy team_members_select_own_team on public.team_members
      for select using (
        user_id = auth.uid()
        or exists (
          select 1 from public.teams t
          where t.id = team_id and t.owner_user_id = auth.uid()
        )
      );
  end if;
end $$;

create or replace function public.redeem_activation_code(p_code text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid := auth.uid();
  v_code public.activation_codes%rowtype;
  v_started_at timestamptz := now();
  v_ended_at timestamptz;
begin
  if v_user_id is null then
    return jsonb_build_object('success', false, 'error_code', 'NOT_AUTHENTICATED', 'error', 'User is not authenticated.');
  end if;

  select *
    into v_code
    from public.activation_codes
    where code = p_code
    for update;

  if not found then
    return jsonb_build_object('success', false, 'error_code', 'CODE_NOT_FOUND', 'error', 'Activation code was not found.');
  end if;

  if v_code.expires_at is not null and v_code.expires_at < now() then
    return jsonb_build_object('success', false, 'error_code', 'CODE_EXPIRED', 'error', 'Activation code has expired.');
  end if;

  if v_code.redeemed_count >= v_code.max_redemptions then
    return jsonb_build_object('success', false, 'error_code', 'CODE_EXHAUSTED', 'error', 'Activation code has been fully redeemed.');
  end if;

  v_ended_at := v_started_at + make_interval(days => v_code.duration_days);

  update public.activation_codes
    set redeemed_count = redeemed_count + 1,
        updated_at = v_started_at
    where code = p_code;

  update public.profiles
    set plan_tier = v_code.plan_tier,
        plan_status = 'active',
        plan_source = 'activation_code',
        current_period_start = v_started_at,
        current_period_end = v_ended_at
    where id = v_user_id;

  insert into public.subscriptions
    (user_id, plan_tier, status, source, started_at, ended_at, meta)
  values
    (v_user_id, v_code.plan_tier, 'active', 'activation_code', v_started_at, v_ended_at,
     jsonb_build_object('activation_code', p_code));

  return jsonb_build_object(
    'success', true,
    'plan_tier', v_code.plan_tier,
    'current_period_end', v_ended_at
  );
end;
$$;

revoke execute on function public.redeem_activation_code(text) from public, anon;
grant execute on function public.redeem_activation_code(text) to authenticated;
