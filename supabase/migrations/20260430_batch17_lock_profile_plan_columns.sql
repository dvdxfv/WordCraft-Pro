-- Batch 17A hardening: users may edit profile basics, not plan/quota fields.

revoke update on public.profiles from anon, authenticated;

grant update (
  email,
  phone,
  nickname,
  avatar_url,
  updated_at
) on public.profiles to authenticated;
