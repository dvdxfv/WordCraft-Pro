# Supabase 现状同步（通俗版）

> 更新时间：2026-05-01
> 本文用于说明当前项目里 Supabase 实际承担的职责，以及今天已经落地到真实项目的状态。

## 一句话总结

Supabase 现在不只是“已经接入”，而是已经承载：

- 认证与会话
- 用户档案与套餐
- 文档/模板/用户设置存储
- Token 使用统计
- Batch 17A 的套餐、额度、激活码和团队基础 schema

## 今天新增落地

### 1. Batch 17A schema 已落到真实 Supabase

`profiles` 已新增：

- `plan_tier`
- `plan_status`
- `plan_source`
- `current_period_start`
- `current_period_end`
- `team_id`
- `feature_flags`

已新增新表：

- `usage_counters`
- `activation_codes`
- `subscriptions`
- `teams`
- `team_members`

### 2. 激活码兑换 RPC 已上线

- `public.redeem_activation_code(text)` 已存在
- 该函数为 `SECURITY DEFINER`
- `anon` 已不能执行该函数
- `authenticated` 可以执行该函数

### 3. 套餐字段安全收口已完成

- 普通登录用户已不能直接更新 `profiles.plan_tier`
- `profiles` 的可更新列已收紧到基础档案字段：
  - `email`
  - `phone`
  - `nickname`
  - `avatar_url`
  - `updated_at`

### 4. 两个 admin 统计 view 的 Critical 已消除

已处理对象：

- `public.admin_user_stats`
- `public.admin_token_daily_stats`

处理结果：

- 两个 view 都已改为 `security_invoker=true`
- 已去掉对 `anon/authenticated` 的宽放行
- Supabase Advisor 里之前这两个 `Security Definer View` Critical 已消失

### 5. 管理员读路径已补齐

已新增 admin 只读策略，使带有 `auth.jwt()->>'role' = 'admin'` 的登录用户可读取管理看板需要的全局统计路径。

当前已补齐的 admin 全局读取对象包括：

- `profiles`
- `usage_counters`
- `activation_codes`
- `subscriptions`
- `teams`
- `team_members`
- `token_logs`
- `documents`
- `templates`
- `user_settings`
- `admin_user_stats`
- `admin_token_daily_stats`

其中，Batch 19 补充的真实迁移文件为：

- `supabase/migrations/20260501_admin_role_read_plan_tables.sql`

该迁移同时补齐了 `activation_codes` 的 admin `insert` 策略，用于后台直接生成激活码。

## 当前两账号状态

### 开发者账号

- 邮箱：`13513645422@163.com`
- 当前 `plan_tier = enterprise`
- 当前 `plan_source = admin`
- 用途：开发者全功能账号，直接拥有全部产品能力

### 管理员账号

- 邮箱：`admin@wordcraft.com`
- `auth.users.raw_app_meta_data.role = admin`
- 当前 `profiles.plan_tier = free`
- 用途：管理员模式账号，重点是后台/管理权限，不与产品套餐强耦合

## 当前代码与 Supabase 的关系

### 已经真实依赖 Supabase 的能力

- 登录/注册：Supabase Auth
- 用户 session：前端和后端都在用
- 用户文档：`documents`
- 模板：`templates` + Storage `templates` bucket
- 用户设置：`user_settings`
- Token 统计：`profiles` + `token_logs`
- AI 代理：Supabase Edge Function 通道
- Batch 17A 套餐能力：`profiles` + `usage_counters` + `subscriptions` + `activation_codes`

### 当前仍保留的兜底

当 Supabase 不可用时，后端仍保留本地 fallback，应用不会直接崩溃。但套餐、激活码、管理员权限的真实行为现在应以 Supabase 项目状态为准。

## 已完成验收

### 1. 真实激活码链路验收已完成

已完成真实链路确认：

`admin 后台生成激活码 -> 普通账号兑换 -> 套餐升级/权益刷新 -> dashboard redeemed_count +1`

### 2. 管理员 UI 最终实登验收已完成

已确认：

- `admin@wordcraft.com` 可正常进入管理页
- 管理页各分区可正常读取 Supabase 统计与业务数据
- 新增 admin RLS 迁移在真实环境已应用生效

## 仍未完成

### 1. Team 闭环仍未最终收口

`teams / team_members`、`team_format_rules`、团队活动/任务历史表以及团队工作区相关 RPC 已落地，17B 已从“最小工作区”推进到“带正式邮件发送和任务历史的完整可用版”。

当前未完成的是：

- 真实团队账号端到端验收
- 真实环境中的正式邮件投递验收
- 多管理员、团队审计日志、复杂角色等延后能力

## 备注

- 文档中不再保留明文密码或长期有效 key
- 真实安全边界现在重点看：RLS、列级权限、RPC 执行权限、JWT 角色透传
## 2026-05-01 补充同步：Batch 17B 邀请链路

- 已新增 `accept_team_invite` / `cancel_team_invite` RPC，并补齐对应 migration。
- `add_team_member_by_email` 现在创建 `pending` 邀请，不再直接把成员写成 active。
- 前端团队工作区现提供待接受邀请入口，以及 `发送正式邮件`、`复制文案`、`邮件草稿`、`重新发送`、`撤销邀请`。
- 已新增团队活动历史与批量任务历史，批量检查改为任务创建 + 轮询收口。
- 当前仍未完成的是：真实团队账号端到端验收、真实环境邮件投递验收、多管理员、团队审计日志、复杂权限角色。
