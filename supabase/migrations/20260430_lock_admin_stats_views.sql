-- Security hardening: admin aggregate views must not bypass RLS for API roles.

alter view if exists public.admin_user_stats
  set (security_invoker = true);

alter view if exists public.admin_token_daily_stats
  set (security_invoker = true);

revoke all on table public.admin_user_stats from anon, authenticated;
revoke all on table public.admin_token_daily_stats from anon, authenticated;
