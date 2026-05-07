#!/usr/bin/env python3
"""
Supabase 客户端模块
封装 Supabase Python 客户端，提供用户认证、数据库操作、Storage 操作
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta, timezone


def _load_supabase_sdk():
    repo_root = Path(__file__).resolve().parents[1]
    original_sys_path = list(sys.path)
    try:
        filtered = []
        for entry in sys.path:
            current = Path(entry or os.getcwd()).resolve()
            if current == repo_root:
                continue
            filtered.append(entry)
        sys.path[:] = filtered
        from supabase import create_client, Client  # type: ignore
        return create_client, Client
    finally:
        sys.path[:] = original_sys_path


create_client, Client = _load_supabase_sdk()

logger = logging.getLogger(__name__)


class SupabaseClient:
    """封装 Supabase 客户端操作"""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or os.environ.get('SUPABASE_URL', '')
        self.key = key or os.environ.get('SUPABASE_KEY', '')
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL 和 SUPABASE_KEY 必须通过环境变量配置")
        
        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase 客户端初始化成功: %s", self.url)

    # ------------------------------------------------------------------
    #  用户认证
    # ------------------------------------------------------------------

    def sign_up(self, email: str, password: str) -> dict:
        """用户注册"""
        try:
            result = self.client.auth.sign_up({
                "email": email,
                "password": password,
            })
            if result.user:
                return {
                    "success": True,
                    "user_id": result.user.id,
                    "email": result.user.email,
                }
            return {"success": False, "error": "注册失败"}
        except Exception as e:
            logger.error("用户注册失败: %s", e)
            return {"success": False, "error": str(e)}

    def sign_in(self, email: str, password: str) -> dict:
        """用户登录"""
        try:
            result = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            if result.user:
                return {
                    "success": True,
                    "user_id": result.user.id,
                    "email": result.user.email,
                    "access_token": result.session.access_token if result.session else None,
                    "refresh_token": result.session.refresh_token if result.session else None,
                }
            return {"success": False, "error": "登录失败"}
        except Exception as e:
            logger.error("用户登录失败: %s", e)
            return {"success": False, "error": str(e)}

    def sign_out(self, access_token: Optional[str] = None) -> bool:
        """用户登出"""
        try:
            self.client.auth.sign_out()
            return True
        except Exception as e:
            logger.error("用户登出失败: %s", e)
            return False

    def get_user(self, access_token: Optional[str] = None) -> Optional[dict]:
        """获取当前用户信息"""
        try:
            if access_token:
                user = self.client.auth.get_user(access_token)
                if user.user:
                    return {
                        "id": user.user.id,
                        "email": user.user.email,
                        "nickname": user.user.user_metadata.get("nickname", user.user.email.split('@')[0] if user.user.email else ""),
                    }
            return None
        except Exception as e:
            logger.error("获取用户信息失败: %s", e)
            return None

    # ------------------------------------------------------------------
    #  Profiles 表操作
    # ------------------------------------------------------------------

    def get_profile(self, user_id: str, access_token: str | None = None) -> Optional[dict]:
        """获取用户档案"""
        try:
            if access_token:
                self.client.postgrest.auth(access_token)
            result = self.client.table("profiles").select("*").eq("id", user_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error("获取用户档案失败: %s", e)
            return None
        finally:
            if access_token:
                self.client.postgrest.auth(self.key)

    def update_profile(self, user_id: str, updates: dict) -> bool:
        """更新用户档案"""
        try:
            result = self.client.table("profiles").update(updates).eq("id", user_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error("更新用户档案失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  Token 管理
    # ------------------------------------------------------------------

    def get_user_plan(self, user_id: str, access_token: str | None = None) -> dict:
        profile = self.get_profile(user_id, access_token=access_token) or {}
        return {
            "plan_tier": profile.get("plan_tier") or "free",
            "plan_status": profile.get("plan_status") or "active",
            "plan_source": profile.get("plan_source") or "system",
            "current_period_start": profile.get("current_period_start"),
            "current_period_end": profile.get("current_period_end"),
            "team_id": profile.get("team_id"),
            "feature_flags": profile.get("feature_flags") or {},
            "token_quota": profile.get("token_quota", 100000),
            "token_used": profile.get("token_used", 0),
        }

    def get_or_create_usage_counter(self, user_id: str, period_key: str, day_key: str | None = None, access_token: str | None = None) -> dict:
        try:
            if access_token:
                self.client.postgrest.auth(access_token)
            result = (
                self.client.table("usage_counters")
                .select("*")
                .eq("user_id", user_id)
                .eq("period_key", period_key)
                .limit(1)
                .execute()
            )
            row = result.data[0] if result.data else None
            if row:
                if day_key and row.get("day_key") != day_key:
                    row = {**row, "day_key": day_key, "rule_check_used_today": 0}
                    self.client.table("usage_counters").update({
                        "day_key": day_key,
                        "rule_check_used_today": 0,
                    }).eq("id", row["id"]).execute()
                return row

            row = {
                "user_id": user_id,
                "period_key": period_key,
                "day_key": day_key,
                "ai_qa_used": 0,
                "ai_parse_used": 0,
                "rule_check_used_today": 0,
            }
            created = self.client.table("usage_counters").insert(row).execute()
            return created.data[0] if created.data else row
        except Exception as e:
            logger.error("获取使用计数失败: %s", e)
            return {
                "user_id": user_id,
                "period_key": period_key,
                "day_key": day_key,
                "ai_qa_used": 0,
                "ai_parse_used": 0,
                "rule_check_used_today": 0,
            }
        finally:
            if access_token:
                self.client.postgrest.auth(self.key)

    def increment_usage_counter(self, user_id: str, counter_name: str, amount: int = 1,
                                period_key: str | None = None, day_key: str | None = None,
                                access_token: str | None = None) -> dict:
        from core.entitlements import current_day_key, current_period_key

        allowed = {"ai_qa_used", "ai_parse_used", "rule_check_used_today"}
        if counter_name not in allowed:
            raise ValueError(f"Unsupported usage counter: {counter_name}")
        period_key = period_key or current_period_key()
        day_key = day_key or current_day_key()
        row = self.get_or_create_usage_counter(user_id, period_key, day_key, access_token=access_token)
        new_value = int(row.get(counter_name) or 0) + int(amount)
        updates = {counter_name: new_value, "updated_at": datetime.now(timezone.utc).isoformat()}
        if counter_name == "rule_check_used_today":
            updates["day_key"] = day_key
        try:
            if access_token:
                self.client.postgrest.auth(access_token)
            if row.get("id"):
                result = self.client.table("usage_counters").update(updates).eq("id", row["id"]).execute()
            else:
                result = self.client.table("usage_counters").upsert({
                    **row,
                    **updates,
                }, on_conflict="user_id,period_key").execute()
            return result.data[0] if result.data else {**row, **updates}
        except Exception as e:
            logger.error("更新使用计数失败: %s", e)
            return {**row, **updates}
        finally:
            if access_token:
                self.client.postgrest.auth(self.key)

    def get_user_entitlements(self, user_id: str, access_token: str | None = None) -> dict:
        from core.entitlements import build_entitlements, current_day_key, current_period_key

        profile = self.get_user_plan(user_id, access_token=access_token)
        usage = self.get_or_create_usage_counter(user_id, current_period_key(), current_day_key(), access_token=access_token)
        return build_entitlements(profile, usage)

    def get_team(self, team_id: str) -> Optional[dict]:
        try:
            result = self.client.table("teams").select("*").eq("id", team_id).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("获取团队失败: %s", e)
            return None

    def get_team_members(self, team_id: str) -> list:
        try:
            result = (
                self.client.table("team_members")
                .select("*")
                .eq("team_id", team_id)
                .order("joined_at")
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("获取团队成员失败: %s", e)
            return []

    def list_team_activities(self, team_id: str, limit: int = 20) -> list:
        try:
            result = (
                self.client.table("team_activity_logs")
                .select("*")
                .eq("team_id", team_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("获取团队活动失败: %s", e)
            return []

    def create_team_activity(self, row: dict) -> dict:
        try:
            result = self.client.table("team_activity_logs").insert(row).execute()
            return result.data[0] if result.data else row
        except Exception as e:
            logger.error("记录团队活动失败: %s", e)
            raise

    def list_team_batch_jobs(self, team_id: str, limit: int = 20) -> list:
        try:
            result = (
                self.client.table("team_batch_jobs")
                .select("*")
                .eq("team_id", team_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("获取团队任务失败: %s", e)
            return []

    def get_team_batch_job(self, job_id: str) -> Optional[dict]:
        try:
            result = self.client.table("team_batch_jobs").select("*").eq("id", job_id).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("获取团队任务详情失败: %s", e)
            return None

    def create_team_batch_job(self, row: dict) -> dict:
        try:
            result = self.client.table("team_batch_jobs").insert(row).execute()
            return result.data[0] if result.data else row
        except Exception as e:
            logger.error("创建团队任务失败: %s", e)
            raise

    def update_team_batch_job(self, job_id: str, row: dict) -> dict:
        updates = {
            "status": row.get("status"),
            "summary": row.get("summary"),
            "result_payload": row.get("result_payload"),
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "updated_at": row.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        }
        try:
            result = self.client.table("team_batch_jobs").update(updates).eq("id", job_id).execute()
            return result.data[0] if result.data else {**row, **updates}
        except Exception as e:
            logger.error("更新团队任务失败: %s", e)
            raise

    def get_pending_team_invitations(self, user_id: str) -> list:
        try:
            result = (
                self.client.table("team_members")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "pending")
                .order("invited_at")
                .execute()
            )
            invitations = result.data or []
            for item in invitations:
                team = self.get_team(item.get("team_id"))
                if team:
                    item["team"] = team
            return invitations
        except Exception as e:
            logger.error("获取待接受团队邀请失败: %s", e)
            return []

    def get_team_format_rules(self, team_id: str) -> dict:
        try:
            result = (
                self.client.table("team_format_rules")
                .select("rules_json, updated_at")
                .eq("team_id", team_id)
                .limit(1)
                .execute()
            )
            if result.data:
                return {"rules": result.data[0].get("rules_json"), "storage": "supabase"}
            return {"rules": None, "storage": "supabase"}
        except Exception as e:
            logger.error("读取团队规则库失败: %s", e)
            return {"rules": None, "storage": "supabase", "error": str(e)}

    def save_team_format_rules(self, team_id: str, updated_by: str, rules: dict) -> dict:
        try:
            self.client.table("team_format_rules").upsert({
                "team_id": team_id,
                "rules_json": rules,
                "updated_by": updated_by,
            }, on_conflict="team_id").execute()
            return {"success": True, "storage": "supabase"}
        except Exception as e:
            logger.error("保存团队规则库失败: %s", e)
            return {"success": False, "storage": "supabase", "error": str(e)}

    def get_user_team_workspace(self, user_id: str) -> dict:
        profile = self.get_profile(user_id) or {}
        team_id = profile.get("team_id")
        invitations = self.get_pending_team_invitations(user_id)
        if not team_id:
            return {"team": None, "members": [], "rules": None, "team_id": None, "invitations": invitations, "activities": [], "jobs": []}

        workspace = self.get_team_workspace_by_id(team_id)
        workspace["invitations"] = invitations
        return workspace

    def get_team_workspace_by_id(self, team_id: str) -> dict:
        team = self.get_team(team_id)
        members = self.get_team_members(team_id)
        rules = self.get_team_format_rules(team_id).get("rules")
        activities = self.list_team_activities(team_id, limit=20)
        jobs = self.list_team_batch_jobs(team_id, limit=20)
        return {
            "team": team,
            "members": members,
            "rules": rules,
            "team_id": team_id,
            "invitations": [],
            "activities": activities,
            "jobs": jobs,
        }

    def create_team_workspace(self, user_id: str, name: str, seat_limit: int = 5) -> dict:
        try:
            try:
                rpc_result = self.client.rpc("create_team_workspace", {
                    "p_name": name,
                    "p_seat_limit": int(seat_limit),
                }).execute()
                if rpc_result.data:
                    payload = rpc_result.data
                    if isinstance(payload, dict) and payload.get("success") is not False:
                        team_id = payload.get("team_id") or payload.get("id")
                        return {
                            "success": True,
                            "team": self.get_team(team_id) if team_id else payload.get("team"),
                            "members": self.get_team_members(team_id) if team_id else [],
                            "rules": None,
                            "team_id": team_id,
                        }
            except Exception as rpc_error:
                logger.warning("RPC 创建团队失败，尝试兼容路径: %s", rpc_error)

            result = self.client.table("teams").insert({
                "name": name,
                "owner_user_id": user_id,
                "seat_limit": int(seat_limit),
                "status": "active",
            }).execute()
            if not result.data:
                return {"success": False, "error": "创建团队失败"}
            team = result.data[0]
            team_id = team["id"]
            self.client.table("team_members").upsert({
                "team_id": team_id,
                "user_id": user_id,
                "role": "owner",
            }, on_conflict="team_id,user_id").execute()
            self.client.table("profiles").update({"team_id": team_id}).eq("id", user_id).execute()
            return {
                "success": True,
                "team": self.get_team(team_id) or team,
                "members": self.get_team_members(team_id),
                "rules": None,
                "team_id": team_id,
            }
        except Exception as e:
            logger.error("创建团队失败: %s", e)
            return {"success": False, "error": str(e)}

    def add_team_member_by_email(self, user_id: str, team_id: str, email: str, role: str = "member") -> dict:
        try:
            rpc_result = self.client.rpc("add_team_member_by_email", {
                "p_team_id": team_id,
                "p_email": email,
                "p_role": role,
            }).execute()
            payload = rpc_result.data
            if isinstance(payload, dict):
                return payload
            if payload:
                return {"success": True, "added_member": payload}
            return {"success": False, "error": "添加成员失败"}
        except Exception as e:
            logger.error("按邮箱添加团队成员失败: %s", e)
            return {"success": False, "error": str(e)}

    def accept_team_invite(self, user_id: str, team_id: str) -> dict:
        try:
            rpc_result = self.client.rpc("accept_team_invite", {
                "p_team_id": team_id,
            }).execute()
            payload = rpc_result.data
            if isinstance(payload, dict) and payload.get("success"):
                workspace = self.get_user_team_workspace(user_id)
                return {"success": True, **workspace}
            if isinstance(payload, dict):
                return payload
            return {"success": False, "error": "接受团队邀请失败"}
        except Exception as e:
            logger.error("接受团队邀请失败: %s", e)
            return {"success": False, "error": str(e)}

    def cancel_team_invite(self, user_id: str, team_id: str, email: str) -> dict:
        try:
            rpc_result = self.client.rpc("cancel_team_invite", {
                "p_team_id": team_id,
                "p_email": email,
            }).execute()
            payload = rpc_result.data
            if isinstance(payload, dict) and payload.get("success"):
                workspace = self.get_user_team_workspace(user_id)
                return {"success": True, **workspace}
            if isinstance(payload, dict):
                return payload
            return {"success": False, "error": "Pending invite was not found."}
        except Exception as e:
            logger.error("cancel team invite failed: %s", e)
            return {"success": False, "error": str(e)}

    def redeem_activation_code(self, user_id: str, code: str) -> dict:
        code = (code or "").strip().upper()
        if not code:
            return {"success": False, "error": "激活码不能为空", "error_code": "EMPTY_CODE"}
        try:
            try:
                rpc_result = self.client.rpc("redeem_activation_code", {"p_code": code}).execute()
                if rpc_result.data:
                    return rpc_result.data
            except Exception as rpc_error:
                logger.warning("RPC 兑换激活码失败，尝试兼容路径: %s", rpc_error)

            res = (
                self.client.table("activation_codes")
                .select("*")
                .eq("code", code)
                .limit(1)
                .execute()
            )
            if not res.data:
                return {"success": False, "error": "激活码不存在", "error_code": "CODE_NOT_FOUND"}
            row = res.data[0]
            expires_at = row.get("expires_at")
            if expires_at:
                exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if exp < datetime.now(timezone.utc):
                    return {"success": False, "error": "激活码已过期", "error_code": "CODE_EXPIRED"}
            max_redemptions = int(row.get("max_redemptions") or 1)
            redeemed_count = int(row.get("redeemed_count") or 0)
            if redeemed_count >= max_redemptions:
                return {"success": False, "error": "激活码已被用完", "error_code": "CODE_EXHAUSTED"}

            tier = row.get("plan_tier") or "pro"
            duration_days = int(row.get("duration_days") or 30)
            now = datetime.now(timezone.utc)
            ended_at = now + timedelta(days=duration_days)
            profile_updates = {
                "plan_tier": tier,
                "plan_status": "active",
                "plan_source": "activation_code",
                "current_period_start": now.isoformat(),
                "current_period_end": ended_at.isoformat(),
            }
            self.client.table("profiles").update(profile_updates).eq("id", user_id).execute()
            self.client.table("activation_codes").update({
                "redeemed_count": redeemed_count + 1,
                "updated_at": now.isoformat(),
            }).eq("code", code).execute()
            self.client.table("subscriptions").insert({
                "user_id": user_id,
                "plan_tier": tier,
                "status": "active",
                "source": "activation_code",
                "started_at": now.isoformat(),
                "ended_at": ended_at.isoformat(),
                "meta": {"activation_code": code},
            }).execute()
            return {
                "success": True,
                "plan_tier": tier,
                "current_period_end": ended_at.isoformat(),
            }
        except Exception as e:
            logger.error("兑换激活码失败: %s", e)
            return {"success": False, "error": str(e), "error_code": "REDEEM_FAILED"}

    def get_token_usage(self, user_id: str) -> dict:
        """获取用户 Token 用量"""
        try:
            # 获取配额
            profile = self.get_profile(user_id, access_token=access_token)
            quota = profile.get('token_quota', 100000) if profile else 100000
            used = profile.get('token_used', 0) if profile else 0
            
            # 查询今日用量
            import datetime
            today_start = datetime.datetime.now().strftime("%Y-%m-%dT00:00:00")
            today_logs = self.client.table("token_logs").select("usage_amount").eq("user_id", user_id).gte("created_at", today_start).execute()
            today_usage = sum(log['usage_amount'] for log in today_logs.data) if today_logs.data else 0
            
            remaining = quota - used
            usage_percentage = (used / quota * 100) if quota > 0 else 0
            
            return {
                "token_quota": quota,
                "token_used": used,
                "token_remaining": remaining,
                "usage_percentage": round(usage_percentage, 2),
                "today_usage": today_usage,
                "month_usage": used,
            }
        except Exception as e:
            logger.error("获取 Token 用量失败: %s", e)
            return {
                "token_quota": 100000,
                "token_used": 0,
                "token_remaining": 100000,
                "usage_percentage": 0,
                "today_usage": 0,
                "month_usage": 0,
            }

    def record_token_usage(self, user_id: str, amount: int, purpose: str,
                           model: str = "", prompt_tokens: int = 0, completion_tokens: int = 0,
                           access_token: str | None = None) -> bool:
        """记录 Token 使用"""
        try:
            # 插入使用记录
            if access_token:
                self.client.postgrest.auth(access_token)
            log_entry = {
                "user_id": user_id,
                "usage_amount": amount,
                "purpose": purpose,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
            self.client.table("token_logs").insert(log_entry).execute()
            
            # 更新用户档案中的已用量
            profile = self.get_profile(user_id, access_token=access_token)
            if profile:
                new_used = profile.get('token_used', 0) + amount
                self.client.table("profiles").update({"token_used": new_used}).eq("id", user_id).execute()
            
            return True
        except Exception as e:
            logger.error("记录 Token 使用失败: %s", e)
            return False
        finally:
            if access_token:
                self.client.postgrest.auth(self.key)

    # ------------------------------------------------------------------
    #  Templates 表操作
    # ------------------------------------------------------------------

    def get_user_templates(self, user_id: str) -> list:
        """获取用户模板列表"""
        try:
            result = self.client.table("templates").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error("获取用户模板失败: %s", e)
            return []

    def get_system_templates(self) -> list:
        """获取系统模板列表（is_system=true，所有用户可见）"""
        try:
            result = self.client.table("templates").select("*").eq("is_system", True).order("created_at").execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error("获取系统模板失败: %s", e)
            return []

    def insert_template(self, user_id: str, name: str, file_url: str = "", category: str = "custom", template_data: dict = None) -> Optional[dict]:
        """插入模板记录到 templates 表"""
        try:
            record = {
                "user_id": user_id,
                "name": name,
                "category": category,
                "file_url": file_url,
                "is_system": False,
            }
            if template_data:
                record["template_data"] = template_data
            result = self.client.table("templates").insert(record).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("插入模板失败: %s", e)
            return None

    def delete_template(self, template_id: str, user_id: str) -> bool:
        """删除模板"""
        try:
            # 先获取模板信息（包括文件 URL）
            result = self.client.table("templates").select("*").eq("id", template_id).eq("user_id", user_id).execute()
            if result.data:
                template = result.data[0]
                file_url = template.get('file_url')
                
                # 从 Storage 删除文件
                if file_url:
                    try:
                        file_path = file_url.split('/templates/')[-1]
                        self.client.storage.from_("templates").remove([file_path])
                    except Exception:
                        pass  # 文件删除失败不影响数据库操作
                
                # 从数据库删除记录
                self.client.table("templates").delete().eq("id", template_id).eq("user_id", user_id).execute()
                return True
            
            return False
        except Exception as e:
            logger.error("删除模板失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  user_settings 表操作
    # ------------------------------------------------------------------

    _DEFAULT_SETTINGS = {
        "theme": "light",
        "default_format": {
            "paper": "A4", "mt": 2.5, "mb": 2.5, "ml": 3.0, "mr": 2.5,
            "h1": "黑体", "h1s": 16, "h2": "黑体", "h2s": 14,
            "h3": "黑体", "h3s": 12, "bf": "宋体", "bs": 12,
            "indent": 2, "lh": 1.5,
        },
        "ai_model": "doubao-seed-1-6-251015",
    }

    def get_user_settings(self, user_id: str) -> dict:
        """读取用户设置，不存在时返回默认值"""
        try:
            result = self.client.table("user_settings").select("settings_data").eq("user_id", user_id).execute()
            if result.data:
                return result.data[0].get("settings_data") or self._DEFAULT_SETTINGS.copy()
            return self._DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error("读取用户设置失败: %s", e)
            return self._DEFAULT_SETTINGS.copy()

    def save_user_settings(self, user_id: str, settings_data: dict) -> bool:
        """保存用户设置（upsert，不存在则创建）"""
        try:
            self.client.table("user_settings").upsert({
                "user_id": user_id,
                "settings_data": settings_data,
            }, on_conflict="user_id").execute()
            return True
        except Exception as e:
            logger.error("保存用户设置失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  Storage 操作
    # ------------------------------------------------------------------

    def upload_template_file(self, user_id: str, file_path: str, file_name: str) -> Optional[str]:
        """上传模板文件到 Storage"""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            storage_path = f"{user_id}/{file_name}"
            result = self.client.storage.from_("templates").upload(storage_path, file_content, {
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            })
            
            # 获取公开 URL
            public_url = self.client.storage.from_("templates").get_public_url(storage_path)
            return public_url
        except Exception as e:
            logger.error("上传模板文件失败: %s", e)
            return None

    # ------------------------------------------------------------------
    #  Documents 表操作
    # ------------------------------------------------------------------

    def get_user_documents(self, user_id: str) -> list:
        """获取用户文档列表"""
        try:
            result = self.client.table("documents").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error("获取用户文档失败: %s", e)
            return []

    def save_document(self, user_id: str, title: str, content: dict, 
                     template_id: Optional[str] = None) -> Optional[str]:
        """保存文档"""
        try:
            doc_entry = {
                "user_id": user_id,
                "title": title,
                "content": content,
                "template_id": template_id,
            }
            result = self.client.table("documents").insert(doc_entry).execute()
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error("保存文档失败: %s", e)
            return None

    def load_document(self, doc_id: str, user_id: str) -> Optional[dict]:
        """加载文档"""
        try:
            result = self.client.table("documents").select("*").eq("id", doc_id).eq("user_id", user_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error("加载文档失败: %s", e)
            return None

    def update_document(self, doc_id: str, user_id: str, updates: dict) -> bool:
        """更新文档"""
        try:
            result = self.client.table("documents").update(updates).eq("id", doc_id).eq("user_id", user_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error("更新文档失败: %s", e)
            return False
