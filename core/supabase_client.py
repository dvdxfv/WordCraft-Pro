#!/usr/bin/env python3
"""
Supabase 客户端模块
封装 Supabase Python 客户端，提供用户认证、数据库操作、Storage 操作
"""

import os
import json
import logging
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseClient:
    """封装 Supabase 客户端操作"""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or os.environ.get('SUPABASE_URL', 'https://nzujajuefdsheggulpze.supabase.co')
        self.key = key or os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im56dWphanVlZmRzaGVnZ3VscHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyNDY0MDMsImV4cCI6MjA5MTgyMjQwM30.N3jsg3tIi6ezlmp_MvQYvbUo41SzR5kEBECawel5KDE')
        
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

    def get_profile(self, user_id: str) -> Optional[dict]:
        """获取用户档案"""
        try:
            result = self.client.table("profiles").select("*").eq("id", user_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error("获取用户档案失败: %s", e)
            return None

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

    def get_token_usage(self, user_id: str) -> dict:
        """获取用户 Token 用量"""
        try:
            # 获取配额
            profile = self.get_profile(user_id)
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
                           model: str = "", prompt_tokens: int = 0, completion_tokens: int = 0) -> bool:
        """记录 Token 使用"""
        try:
            # 插入使用记录
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
            profile = self.get_profile(user_id)
            if profile:
                new_used = profile.get('token_used', 0) + amount
                self.client.table("profiles").update({"token_used": new_used}).eq("id", user_id).execute()
            
            return True
        except Exception as e:
            logger.error("记录 Token 使用失败: %s", e)
            return False

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
