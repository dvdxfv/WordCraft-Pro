#!/usr/bin/env python3
"""
WordCraft Pro - API 核心层（Web 版业务逻辑）
"""

import json
import logging
import os
import re
import sys
import time
from functools import wraps

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


def cached_response(ttl_seconds: int = 300):
    def decorator(func):
        cache = {}
        cache_time = {}

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            now = time.time()
            if cache_key in cache and (now - cache_time.get(cache_key, 0)) < ttl_seconds:
                return cache[cache_key]
            result = func(self, *args, **kwargs)
            cache[cache_key] = result
            cache_time[cache_key] = now
            return result

        return wrapper
    return decorator


class Api:
    def __init__(self, supabase_enabled: bool = True) -> None:
        self._session = {}
        self._supabase = None
        self._supabase_enabled = supabase_enabled
        self._supabase_initialized = False

    def _ensure_supabase_initialized(self):
        if not self._supabase_initialized and self._supabase_enabled:
            self._init_supabase()
            self._supabase_initialized = True

    def _init_supabase(self):
        try:
            from core.supabase_client import SupabaseClient
            self._supabase = SupabaseClient()
        except Exception as e:
            logger.warning("Supabase 初始化失败，使用本地模式: %s", e)
            self._supabase = None

    # ------------------------------------------------------------------
    #  文件操作
    # ------------------------------------------------------------------

    def openFile(self, file_content: str = None, file_name: str = None) -> str:
        if not file_content or not file_name:
            return json.dumps({"cancelled": True, "error": "请提供文件内容和文件名"})

        import tempfile, base64
        ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else 'docx'
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            # 支持 base64 编码内容（二进制文件）
            try:
                decoded = base64.b64decode(file_content)
                tmp.write(decoded)
            except Exception:
                tmp.write(file_content.encode('utf-8') if isinstance(file_content, str) else file_content)
            path = tmp.name

        name = file_name

        if not os.path.exists(path):
            return json.dumps({"success": False, "error": f"文件不存在: {path}", "error_code": "FILE_NOT_FOUND"})
        if not os.access(path, os.R_OK):
            return json.dumps({"success": False, "error": "无权限读取文件", "error_code": "PERMISSION_DENIED"})

        try:
            size = os.path.getsize(path)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "error_code": "SIZE_ERROR"})

        if size > 100 * 1024 * 1024:
            return json.dumps({"success": False, "error": "文件过大（超过100MB）", "error_code": "FILE_TOO_LARGE"})

        try:
            if ext == "docx":
                elements = self._parse_docx(path)
            elif ext in ("txt", "md"):
                elements = self._parse_text(path)
            else:
                try:
                    elements = self._parse_text(path)
                except Exception:
                    elements = self._parse_docx(path)

            if not elements:
                return json.dumps({"success": False, "error": "文件为空或无可解析内容", "error_code": "EMPTY_FILE"})
        except Exception as exc:
            error_msg = str(exc)
            error_code = "PARSE_ERROR"
            if "not a valid zip file" in error_msg.lower():
                error_msg = "文件不是有效的Word文档(.docx)"
                error_code = "INVALID_DOCX"
            elif "encoding" in error_msg.lower() or "decode" in error_msg.lower():
                error_msg = "文件编码错误"
                error_code = "ENCODING_ERROR"
            try:
                os.unlink(path)
            except Exception:
                pass
            return json.dumps({"success": False, "error": f"文件解析失败: {error_msg}", "error_code": error_code})

        try:
            os.unlink(path)
        except Exception:
            pass

        return json.dumps({
            "success": True, "name": name, "size": size,
            "type": ext, "elements": elements, "element_count": len(elements)
        }, ensure_ascii=False)

    def saveFile(self, content: str, file_name: str = "document.html") -> str:
        try:
            return json.dumps({"success": True, "content": content, "file_name": file_name}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def exportDocx(self, content: str, format_params: str = "{}", file_name: str = "document.docx") -> str:
        try:
            import tempfile, base64
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                temp_path = tmp.name
            params = json.loads(format_params) if format_params else {}
            self._write_docx(temp_path, content, params)
            with open(temp_path, "rb") as f:
                docx_content = base64.b64encode(f.read()).decode('utf-8')
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return json.dumps({"success": True, "content": docx_content, "file_name": file_name}, ensure_ascii=False)
        except Exception as exc:
            logger.error("导出失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    @cached_response(ttl_seconds=600)
    def getSystemInfo(self) -> str:
        return json.dumps({"version": APP_VERSION, "platform": sys.platform, "python": sys.version.split()[0]})

    # ------------------------------------------------------------------
    #  用户认证
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> str:
        try:
            self._ensure_supabase_initialized()
            if self._supabase:
                result = self._supabase.sign_in(email, password)
                if result.get("success"):
                    profile = self._supabase.get_profile(result["user_id"])
                    user_info = {
                        "id": result["user_id"], "email": result["email"],
                        "nickname": profile.get("nickname", email.split("@")[0]) if profile else email.split("@")[0],
                        "avatar_url": profile.get("avatar_url", "") if profile else "",
                        "token_quota": profile.get("token_quota", 100000) if profile else 100000,
                        "token_used": profile.get("token_used", 0) if profile else 0,
                    }
                    self._session = {"user_id": result["user_id"], "access_token": result.get("access_token"), "user_info": user_info}
                    return json.dumps({"success": True, "user": user_info, "token": result.get("access_token")}, ensure_ascii=False)
                else:
                    return json.dumps({"success": False, "error": result.get("error", "登录失败")}, ensure_ascii=False)
            else:
                mock_user = {"id": "mock-user-001", "email": email, "nickname": email.split("@")[0],
                             "avatar_url": "", "token_quota": 100000, "token_used": 12345}
                self._session = {"user_id": "mock-user-001", "user_info": mock_user}
                return json.dumps({"success": True, "user": mock_user, "token": "mock-jwt-token"}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def logout(self) -> str:
        try:
            self._ensure_supabase_initialized()
            if self._supabase and self._session.get("access_token"):
                self._supabase.sign_out(self._session.get("access_token"))
            self._session = {}
            return json.dumps({"success": True})
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  Token 管理
    # ------------------------------------------------------------------

    def getTokenUsage(self) -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                usage = self._supabase.get_token_usage(self._session["user_id"])
                return json.dumps(usage, ensure_ascii=False)
            else:
                from core.token_tracker import TokenTracker
                usage = TokenTracker().get_quota()
                return json.dumps({
                    "token_quota": usage.get('quota', 100000), "token_used": usage.get('used', 0),
                    "token_remaining": usage.get('remaining', 100000),
                    "usage_percentage": usage.get('usage_percentage', 0),
                    "today_usage": 0, "month_usage": usage.get('used', 0),
                }, ensure_ascii=False)
        except Exception:
            return json.dumps({"token_quota": 100000, "token_used": 0, "token_remaining": 100000,
                               "usage_percentage": 0, "today_usage": 0, "month_usage": 0}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  模板管理
    # ------------------------------------------------------------------

    def getUserTemplates(self) -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                templates = self._supabase.get_user_templates(self._session["user_id"])
                return json.dumps({"success": True, "templates": templates}, ensure_ascii=False)
            else:
                mock = [
                    {"id": "template-001", "name": "广东海洋大学毕业论文", "category": "thesis", "file_url": "", "created_at": "2026-04-15"},
                    {"id": "template-002", "name": "尖草坪区绩效评价报告", "category": "gov", "file_url": "", "created_at": "2026-04-16"},
                ]
                return json.dumps({"success": True, "templates": mock}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def uploadTemplate(self, file_path: str, name: str) -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                user_id = self._session["user_id"]
                file_url = self._supabase.upload_template_file(user_id, file_path, name)
                if file_url:
                    record = self._supabase.insert_template(user_id, name, file_url, "custom")
                    return json.dumps({"success": True, "template_id": record.get("id", "") if record else "", "name": name, "file_url": file_url}, ensure_ascii=False)
                return json.dumps({"success": False, "error": "上传失败"})
            else:
                if not os.path.exists(file_path):
                    return json.dumps({"success": False, "error": "文件不存在"})
                return json.dumps({"success": True, "template_id": "template-new-001", "name": name}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def saveTemplateSettings(self, name: str, template_data: str) -> str:
        try:
            data = json.loads(template_data) if isinstance(template_data, str) else template_data
            if self._supabase and self._session.get("user_id"):
                record = self._supabase.insert_template(self._session["user_id"], name, "", "custom", data)
                return json.dumps({"success": True, "template_id": record.get("id", "") if record else "", "name": name}, ensure_ascii=False)
            return json.dumps({"success": True, "template_id": "local-" + name, "name": name}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def deleteTemplate(self, template_id: str) -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                success = self._supabase.delete_template(template_id, self._session["user_id"])
                return json.dumps({"success": success})
            return json.dumps({"success": True})
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  用户设置
    # ------------------------------------------------------------------

    def getUserSettings(self) -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                settings = self._supabase.get_user_settings(self._session["user_id"])
                return json.dumps({"success": True, "settings": settings}, ensure_ascii=False)
            else:
                from core.supabase_client import SupabaseClient
                return json.dumps({"success": True, "settings": SupabaseClient._DEFAULT_SETTINGS.copy()}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def saveUserSettings(self, settings_str: str) -> str:
        try:
            settings = json.loads(settings_str) if isinstance(settings_str, str) else settings_str
            if self._supabase and self._session.get("user_id"):
                ok = self._supabase.save_user_settings(self._session["user_id"], settings)
                return json.dumps({"success": ok}, ensure_ascii=False)
            return json.dumps({"success": True}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  质量检查
    # ------------------------------------------------------------------

    def runQA(self, content: str, categories_str: str = '["typo", "consistency", "logic"]') -> str:
        try:
            from core.qa_engine import QAEngine
            from core.document_model import DocumentModel
            doc = DocumentModel(title="检查文档", source_format="html")
            categories = json.loads(categories_str)
            engine = QAEngine()
            report = engine.check(doc, categories)
            return json.dumps({
                "success": True,
                "issues": [
                    {"id": i.id,
                     "category": i.category.value if hasattr(i.category, 'value') else str(i.category),
                     "severity": i.severity.value if hasattr(i.severity, 'value') else str(i.severity),
                     "title": i.title, "description": i.description,
                     "suggestion": i.suggestion, "confidence": i.confidence}
                    for i in report.issues
                ],
                "stats": {
                    "total": len(report.issues),
                    "errors": len([i for i in report.issues if i.severity.value == "error"]),
                    "warnings": len([i for i in report.issues if i.severity.value == "warning"]),
                    "infos": len([i for i in report.issues if i.severity.value == "info"]),
                },
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    def acceptSuggestion(self, content: str, issue_id: str, original_text: str, suggested_text: str) -> str:
        try:
            corrected = content.replace(original_text, suggested_text, 1)
            if corrected != content:
                return json.dumps({"success": True, "corrected_content": corrected,
                                   "message": f"已将 '{original_text}' 改为 '{suggested_text}'"}, ensure_ascii=False)
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                for string in soup.find_all(string=True):
                    if original_text in string:
                        string.replace_with(string.replace(original_text, suggested_text, 1))
                        return json.dumps({"success": True, "corrected_content": str(soup),
                                           "message": f"已将 '{original_text}' 改为 '{suggested_text}'"}, ensure_ascii=False)
            except ImportError:
                pass
            return json.dumps({"success": False, "error": f"未找到待替换文本: {original_text}"})
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    # ------------------------------------------------------------------
    #  交叉引用
    # ------------------------------------------------------------------

    def runXRef(self, content: str) -> str:
        try:
            targets_found = []
            references_found = []

            for match in re.finditer(r'<h([1-3])>([^<]+)</h\1>', content):
                targets_found.append({"type": f"heading_{match.group(1)}", "text": match.group(2), "label": match.group(2)})

            for match in re.finditer(r'表\s*(\d+)[\-\.]?(\d*)\s*([^<\n]*)', content):
                label = f"表{match.group(1)}" + (f"-{match.group(2)}" if match.group(2) else "")
                targets_found.append({"type": "table", "text": label, "label": f"{label} {match.group(3).strip()}".strip()})

            for match in re.finditer(r'图\s*(\d+)[\-\.]?(\d*)\s*([^<\n]*)', content):
                label = f"图{match.group(1)}" + (f"-{match.group(2)}" if match.group(2) else "")
                targets_found.append({"type": "figure", "text": label, "label": f"{label} {match.group(3).strip()}".strip()})

            for match in re.finditer(r'(如图|见表|查看图|参见表|图|表)\s*(\d+)[\-\.]?(\d*)', content):
                ref_type = match.group(1)
                ref_text = match.group(2) + (f"-{match.group(3)}" if match.group(3) else "")
                references_found.append({"type": "图" if "图" in ref_type else "表",
                                          "text": ref_text, "full_text": match.group(0), "location": match.start()})

            matches = []
            for ref in references_found:
                found = any(
                    (ref["type"] == "图" and "figure" in t["type"] and ref["text"] in t["label"]) or
                    (ref["type"] == "表" and "table" in t["type"] and ref["text"] in t["label"])
                    for t in targets_found
                )
                if found:
                    matches.append({"status": "valid", "reference": ref["full_text"], "message": "匹配成功"})
                else:
                    matches.append({"status": "dangling", "reference": ref["full_text"],
                                    "message": f"找不到{ref['type']}{ref['text']}的定义"})

            return json.dumps({
                "success": True, "targets": targets_found, "references": references_found, "matches": matches,
                "summary": {"total_targets": len(targets_found), "total_references": len(references_found),
                             "valid_matches": len([m for m in matches if m["status"] == "valid"]),
                             "dangling_references": len([m for m in matches if m["status"] == "dangling"])},
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    # ------------------------------------------------------------------
    #  排版
    # ------------------------------------------------------------------

    def applyFormat(self, content: str, rules_str: str = "{}") -> str:
        try:
            rules = json.loads(rules_str) if rules_str else {}
            styles = {
                "h1": {"font-family": rules.get("heading1_font", "宋体"), "font-size": f"{rules.get('heading1_size', '16')}pt", "line-height": rules.get("line_height", "1.5")},
                "h2": {"font-family": rules.get("heading2_font", "宋体"), "font-size": f"{rules.get('heading2_size', '14')}pt", "line-height": rules.get("line_height", "1.5")},
                "h3": {"font-family": rules.get("heading3_font", "宋体"), "font-size": f"{rules.get('heading3_size', '12')}pt", "line-height": rules.get("line_height", "1.5")},
                "p":  {"font-family": rules.get("body_font", "宋体"), "font-size": f"{rules.get('body_size', '10.5')}pt", "line-height": rules.get("line_height", "1.5")},
            }
            styled = self._apply_css_styles(content, styles)
            return json.dumps({"success": True, "message": "排版规则已应用", "rules_applied": len(rules), "formatted_content": styled}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    def _apply_css_styles(self, html_content: str, styles: dict) -> str:
        result = html_content
        for tag, tag_styles in styles.items():
            style_str = "; ".join(f"{k}: {v}" for k, v in tag_styles.items())
            def merge_styles(match, _tag=tag, _style=style_str):
                existing = match.group(1)
                if 'style=' in existing:
                    existing = re.sub(r'style="([^"]*)"', f'style="\\1; {_style}"', existing)
                    return f"<{_tag}{existing}>"
                return f'<{_tag}{existing} style="{_style}">'
            result = re.sub(f"<{tag}([^>]*)>", merge_styles, result, flags=re.IGNORECASE)
        return result

    # ------------------------------------------------------------------
    #  文档管理
    # ------------------------------------------------------------------

    def saveDocument(self, content: str, title: str = "未命名文档") -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                doc_id = self._supabase.save_document(self._session["user_id"], title, {"html_content": content})
                if doc_id:
                    return json.dumps({"success": True, "message": "文档已保存到云端", "doc_id": doc_id}, ensure_ascii=False)
                return json.dumps({"success": False, "error": "保存失败"})
            else:
                import tempfile
                cache_dir = os.path.join(tempfile.gettempdir(), "wordcraft-cache")
                os.makedirs(cache_dir, exist_ok=True)
                doc_file = os.path.join(cache_dir, "current_doc.json")
                with open(doc_file, "w", encoding="utf-8") as f:
                    json.dump({"title": title, "content": content}, f, ensure_ascii=False)
                return json.dumps({"success": True, "message": "文档已保存到本地", "path": doc_file}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def loadDocument(self, doc_id: str = "current") -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                doc = self._supabase.load_document(doc_id, self._session["user_id"])
                if doc:
                    return json.dumps({"success": True, "document": doc}, ensure_ascii=False)
                return json.dumps({"success": False, "error": "未找到文档"}, ensure_ascii=False)
            else:
                import tempfile
                doc_file = os.path.join(tempfile.gettempdir(), "wordcraft-cache", "current_doc.json")
                if os.path.exists(doc_file):
                    with open(doc_file, "r", encoding="utf-8") as f:
                        return json.dumps({"success": True, "document": json.load(f)}, ensure_ascii=False)
                return json.dumps({"success": False, "error": "未找到保存的文档"}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def updateDocument(self, doc_id: str, content: str, title: str = "未命名文档") -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                ok = self._supabase.update_document(doc_id, self._session["user_id"],
                                                     {"content": {"html_content": content}, "title": title})
                return json.dumps({"success": ok, "doc_id": doc_id}, ensure_ascii=False)
            return json.dumps({"success": True, "doc_id": doc_id}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def getDocumentList(self) -> str:
        try:
            if self._supabase and self._session.get("user_id"):
                docs = self._supabase.get_user_documents(self._session["user_id"])
                return json.dumps({"success": True, "documents": docs}, ensure_ascii=False)
            else:
                return json.dumps({"success": True, "documents": [
                    {"id": "doc-001", "title": "益海嘉里项目综合效益评价", "updated_at": "2026-04-18 10:30", "word_count": 5678}
                ]}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  AI 调用
    # ------------------------------------------------------------------

    def callAI(self, system_prompt: str, user_message: str, config_str: str = "{}") -> str:
        import urllib.request, urllib.error

        config = {}
        if config_str:
            try:
                config = json.loads(config_str) if isinstance(config_str, str) else config_str
            except Exception:
                pass

        model = config.get("model", "doubao-seed-1-6-251015")
        temperature = config.get("temperature", 0.3)

        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": 2048,
        }).encode("utf-8")

        # 通道1: Supabase Edge Function 代理
        supabase_url = "https://nzujajuefdsheggulpze.supabase.co"
        supabase_anon = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im56dWphanVlZmRzaGVnZ3VscHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyNDY0MDMsImV4cCI6MjA5MTgyMjQwM30.N3jsg3tIi6ezlmp_MvQYvbUo41SzR5kEBECawel5KDE"
        proxy_endpoint = f"{supabase_url}/functions/v1/ai-proxy"

        try:
            req = urllib.request.Request(
                proxy_endpoint, data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {supabase_anon}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or data.get("content", "")
                return json.dumps({"content": content, "usage": data.get("usage", {})}, ensure_ascii=False)
        except Exception as proxy_err:
            # 通道2: 直接调用豆包 API
            direct_endpoint = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
            api_key = "d9523eb2-f741-4122-ab0f-e6ed95ce59f2"
            req = urllib.request.Request(
                direct_endpoint, data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return json.dumps({"content": content, "usage": data.get("usage", {})}, ensure_ascii=False)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                try:
                    msg = json.loads(body).get("error", {}).get("message", f"HTTP {e.code}")
                except Exception:
                    msg = f"HTTP {e.code}: {body[:200]}"
                return json.dumps({"error": msg}, ensure_ascii=False)
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  文件解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_docx(path: str) -> list:
        from docx import Document
        doc = Document(path)
        elements = []

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                from docx.text.paragraph import Paragraph
                para = Paragraph(element, doc)
                text = para.text.strip()
                if not text:
                    continue
                style_name = ((para.style.name if para.style else "") or "").lower()
                elem_type = "p"
                if style_name in ("heading 1", "标题 1", "title") or style_name.startswith("heading 1 "):
                    elem_type = "h1"
                elif style_name in ("heading 2", "标题 2") or style_name.startswith("heading 2 "):
                    elem_type = "h2"
                elif style_name in ("heading 3", "标题 3", "heading 4", "标题 4") or re.match(r"^heading [34]", style_name):
                    elem_type = "h3"
                elif re.match(r"^heading [5-9]", style_name):
                    elem_type = "h3"
                elif style_name in ("caption", "题注") or "题注" in style_name:
                    elem_type = "caption"
                elif "list bullet" in style_name or "无序列表" in style_name:
                    elem_type = "li"
                    text = "• " + text
                elif "list number" in style_name or "有序列表" in style_name:
                    elem_type = "li"
                elif re.match(r"^\[\d+\]", text):
                    elem_type = "ref"
                elements.append({"type": elem_type, "text": text})

            elif tag == "tbl":
                from docx.table import Table
                try:
                    table = Table(element, doc)
                    rows = [[cell.text.strip().replace("\n", " ") for cell in row.cells] for row in table.rows]
                    if rows:
                        html = "<table>" + "".join(
                            "<tr>" + "".join(f"<{'th' if i==0 else 'td'}>{c}</{'th' if i==0 else 'td'}>" for c in row) + "</tr>"
                            for i, row in enumerate(rows)
                        ) + "</table>"
                        elements.append({"type": "table", "text": html})
                except Exception:
                    pass

        if not elements:
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    elements.append({"type": "p", "text": text})

        return elements

    @staticmethod
    def _parse_text(path: str) -> list:
        content = None
        for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as fh:
                    content = fh.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if content is None:
            raise RuntimeError(f"无法解码文件: {path}")

        elements = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if line.startswith("#### ") or line.startswith("### "):
                elements.append({"type": "h3", "text": line.lstrip("#").strip()})
            elif line.startswith("## "):
                elements.append({"type": "h2", "text": line[3:].strip()})
            elif line.startswith("# "):
                elements.append({"type": "h1", "text": line[2:].strip()})
            elif re.match(r"^[\-\*]\s+", line):
                elements.append({"type": "li", "text": "• " + re.sub(r"^[\-\*]\s+", "", line)})
            elif re.match(r"^\d+\.\s+", line):
                elements.append({"type": "li", "text": line})
            elif re.match(r"^\[\d+\]", line):
                elements.append({"type": "ref", "text": line})
            elif re.match(r"^(图|表|Figure|Table)\s*\d", line):
                elements.append({"type": "caption", "text": line})
            else:
                elements.append({"type": "p", "text": line})
            i += 1
        return elements

    # ------------------------------------------------------------------
    #  Word 导出（修复：安全设置中文字体）
    # ------------------------------------------------------------------

    @staticmethod
    def _set_run_font(run, cn_font: str, en_font: str, size_pt: float) -> None:
        """安全设置 run 的中英文字体和字号，避免 rPr 为 None 导致乱码。"""
        from docx.shared import Pt
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        run.font.name = en_font
        run.font.size = Pt(size_pt)

        rPr = run._element.get_or_add_rPr()
        # 移除已有 rFonts，重新构造，保证覆盖
        existing = rPr.find(qn('w:rFonts'))
        if existing is not None:
            rPr.remove(existing)
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:ascii'), en_font)
        rFonts.set(qn('w:hAnsi'), en_font)
        rFonts.set(qn('w:eastAsia'), cn_font)
        rFonts.set(qn('w:cs'), cn_font)
        rPr.insert(0, rFonts)

    @staticmethod
    def _write_docx(path: str, html_content: str, format_params: dict = None) -> None:
        from docx import Document
        from docx.shared import Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        fp = format_params or {}
        h1_font  = fp.get("h1Font",   "黑体");  h1_size  = float(fp.get("h1Size",  16))
        h2_font  = fp.get("h2Font",   "黑体");  h2_size  = float(fp.get("h2Size",  14))
        h3_font  = fp.get("h3Font",   "黑体");  h3_size  = float(fp.get("h3Size",  12))
        body_font= fp.get("bodyFont", "宋体");  body_size= float(fp.get("bodySize", 12))
        west_font= fp.get("westFont", "Times New Roman")
        indent   = float(fp.get("indent",     2))
        line_h   = float(fp.get("lineHeight", 1.5))
        align    = fp.get("align", "justify")
        margin_t = float(fp.get("marginTop",    2.5))
        margin_b = float(fp.get("marginBottom", 2.5))
        margin_l = float(fp.get("marginLeft",   3.0))
        margin_r = float(fp.get("marginRight",  2.5))

        doc = Document()
        sec = doc.sections[0]
        sec.page_width    = Cm(21);   sec.page_height     = Cm(29.7)
        sec.top_margin    = Cm(margin_t); sec.bottom_margin = Cm(margin_b)
        sec.left_margin   = Cm(margin_l); sec.right_margin  = Cm(margin_r)

        set_font = Api._set_run_font  # 使用安全字体设置方法

        for elem in Api._html_to_elements(html_content):
            t, text = elem["type"], elem["text"]

            if t in ("h1", "h2", "h3"):
                level = int(t[1])
                p = doc.add_heading(text, level=level)
                cn = h1_font if t == "h1" else (h2_font if t == "h2" else h3_font)
                sz = h1_size if t == "h1" else (h2_size if t == "h2" else h3_size)
                for run in p.runs:
                    set_font(run, cn, west_font, sz)

            elif t == "table":
                from html.parser import HTMLParser

                class _TableParser(HTMLParser):
                    def __init__(self):
                        super().__init__(); self.rows = []; self._row = []; self._cell = ""; self._in = False
                    def handle_starttag(self, tag, attrs):
                        if tag in ("th", "td"): self._in = True; self._cell = ""
                    def handle_endtag(self, tag):
                        if tag in ("th", "td"): self._row.append(self._cell); self._in = False
                        elif tag == "tr": self.rows.append(self._row); self._row = []
                    def handle_data(self, data):
                        if self._in: self._cell += data

                tp = _TableParser(); tp.feed(text)
                if tp.rows:
                    tbl = doc.add_table(rows=len(tp.rows), cols=len(tp.rows[0]))
                    tbl.style = "Table Grid"
                    for ri, row_data in enumerate(tp.rows):
                        for ci, cell_text in enumerate(row_data):
                            if ci < len(tbl.rows[ri].cells):
                                tbl.rows[ri].cells[ci].text = cell_text

            elif t == "ref":
                p = doc.add_paragraph(text)
                for run in p.runs:
                    set_font(run, body_font, west_font, 10.5)

            elif t == "caption":
                p = doc.add_paragraph(text)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    set_font(run, h3_font, west_font, 10.5)

            elif t == "li":
                p = doc.add_paragraph(text, style="List Bullet")
                p.paragraph_format.line_spacing = line_h
                for run in p.runs:
                    set_font(run, body_font, west_font, body_size)

            else:
                p = doc.add_paragraph(text)
                p.paragraph_format.first_line_indent = Cm(indent * 0.35 * body_size / 12)
                p.paragraph_format.line_spacing = line_h
                align_map = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                             "center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT}
                p.alignment = align_map.get(align, WD_ALIGN_PARAGRAPH.JUSTIFY)
                for run in p.runs:
                    set_font(run, body_font, west_font, body_size)

        doc.save(path)

    @staticmethod
    def _html_to_elements(html: str) -> list:
        cleaned = re.sub(r"<br\s*/?>", "\n", html)
        pattern = re.compile(r"<(h[1-6]|p|div|caption|li)[^>]*>(.*?)</\1>|(<table>.*?</table>)",
                              re.DOTALL | re.IGNORECASE)
        elements = []
        for match in pattern.finditer(cleaned):
            if match.group(3):
                elements.append({"type": "table", "text": match.group(3)})
                continue
            tag = match.group(1)
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if not text:
                continue
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                elements.append({"type": tag if tag in ("h1","h2","h3") else "h3", "text": text})
            elif tag == "caption":
                elements.append({"type": "caption", "text": text})
            elif tag == "li":
                elements.append({"type": "li", "text": text})
            else:
                elements.append({"type": "p", "text": text})
        return elements
