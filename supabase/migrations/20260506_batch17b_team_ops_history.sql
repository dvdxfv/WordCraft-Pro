-- Batch 17B: formal invite delivery history and team batch task history.

create table if not exists public.team_activity_logs (
  id text primary key,
  team_id uuid not null references public.teams(id) on delete cascade,
  actor_user_id uuid references auth.users(id) on delete set null,
  event_type text not null,
  status text not null default 'completed',
  target_email text,
  target_user_id uuid references auth.users(id) on delete set null,
  batch_job_id text,
  summary text not null default '',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_team_activity_logs_team_created
  on public.team_activity_logs(team_id, created_at desc);

alter table public.team_activity_logs enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_activity_logs'
      and policyname = 'team_activity_logs_select_member'
  ) then
    create policy team_activity_logs_select_member on public.team_activity_logs
      for select to authenticated
      using (
        exists (
          select 1 from public.team_members tm
          where tm.team_id = team_activity_logs.team_id
            and tm.user_id = auth.uid()
        )
      );
  end if;
end $$;

create table if not exists public.team_batch_jobs (
  id text primary key,
  team_id uuid not null references public.teams(id) on delete cascade,
  created_by uuid references auth.users(id) on delete set null,
  job_type text not null default 'batch_qa',
  status text not null default 'queued',
  file_count integer not null default 0,
  categories jsonb not null default '[]'::jsonb,
  request_payload jsonb not null default '{}'::jsonb,
  result_payload jsonb,
  summary text not null default '',
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_team_batch_jobs_team_created
  on public.team_batch_jobs(team_id, created_at desc);

alter table public.team_batch_jobs enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'team_batch_jobs'
      and policyname = 'team_batch_jobs_select_member'
  ) then
    create policy team_batch_jobs_select_member on public.team_batch_jobs
      for select to authenticated
      using (
        exists (
          select 1 from public.team_members tm
          where tm.team_id = team_batch_jobs.team_id
            and tm.user_id = auth.uid()
        )
      );
  end if;
end $$;
