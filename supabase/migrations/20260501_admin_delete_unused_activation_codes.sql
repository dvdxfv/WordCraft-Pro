-- Batch 17A follow-up: allow admins to delete unused activation codes.

drop policy if exists admin_can_delete_unused_activation_codes on public.activation_codes;

create policy admin_can_delete_unused_activation_codes on public.activation_codes
  for delete to authenticated
  using (
    (select coalesce(auth.jwt() -> 'app_metadata' ->> 'role', auth.jwt() ->> 'role')) = 'admin'
    and coalesce(redeemed_count, 0) = 0
  );
