-- Batch 17A hardening: only signed-in users may call activation redemption.

revoke execute on function public.redeem_activation_code(text) from public, anon;
grant execute on function public.redeem_activation_code(text) to authenticated;
