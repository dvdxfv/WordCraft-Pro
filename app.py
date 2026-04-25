#!/usr/bin/env python3
"""
WordCraft Pro - API 核心层（Web 版业务逻辑）
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
import zipfile
from urllib.request import urlretrieve
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
        self._qa_health: dict = {}
        self._qa_runtime_config: dict = {}
        self._qa_autofix_attempted = False
        self._qa_autofix_attempted_at = 0
        self._qa_last_aggressive_retry_at = 0
        self._qa_install_state: dict = {
            "status": "idle",
            "message": "",
            "updated_at": int(time.time()),
        }
        self._warmup_qa_capabilities(force=True)

    def _load_runtime_config(self) -> dict:
        cfg = {}
        try:
            import yaml
            cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
        except Exception as exc:
            logger.warning("读取 config.yaml 失败: %s", exc)
        return cfg

    def _probe_autocorrect(self) -> dict:
        result = {"enabled": False, "available": False, "detail": "", "command": ""}
        qa_cfg = (self._qa_runtime_config.get("qa") or {})
        ac_cfg = qa_cfg.get("autocorrect_check") or {}
        enabled = bool(ac_cfg.get("enabled", True))
        cmd = str(ac_cfg.get("command", "autocorrect"))
        result["enabled"] = enabled
        result["command"] = cmd
        if not enabled:
            result["detail"] = "disabled by config"
            return result
        try:
            proc = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            if proc.returncode == 0:
                result["available"] = True
                result["detail"] = (proc.stdout or proc.stderr).strip() or "ok"
            else:
                result["detail"] = (proc.stderr or proc.stdout).strip() or f"exit={proc.returncode}"
        except Exception as exc:
            result["detail"] = f"exec failed: {exc}"
        return result

    def _get_autocorrect_target_command(self) -> str:
        """返回项目内推荐 autocorrect 可执行路径。"""
        exe = "autocorrect.exe" if sys.platform == "win32" else "autocorrect"
        return os.path.join(os.path.dirname(__file__), "tools", "autocorrect", exe)

    def _ensure_autocorrect_command(self):
        """若配置缺失 command，自动填充项目内命令路径。"""
        qa_cfg = self._qa_runtime_config.setdefault("qa", {})
        ac_cfg = qa_cfg.setdefault("autocorrect_check", {})
        if not ac_cfg.get("command"):
            ac_cfg["command"] = self._get_autocorrect_target_command()

    def _auto_install_autocorrect(self) -> tuple[bool, str]:
        """自动安装 autocorrect（当前优先 Windows 二进制分发）。"""
        try:
            cmd = self._get_autocorrect_target_command()
            if os.path.isfile(cmd):
                return True, "binary already exists"

            if sys.platform != "win32":
                return False, "auto-install autocorrect currently supports win32 only"

            tools_dir = os.path.dirname(cmd)
            os.makedirs(tools_dir, exist_ok=True)
            zip_path = os.path.join(os.path.dirname(__file__), "tools", "autocorrect-windows-amd64.zip")
            url = "https://github.com/huacnlee/autocorrect/releases/download/v2.16.3/autocorrect-windows-amd64.zip"
            urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tools_dir)
            if os.path.isfile(cmd):
                return True, "downloaded autocorrect binary"
            return False, "download finished but binary missing"
        except Exception as exc:
            return False, f"autocorrect install failed: {exc}"

    def _auto_fix_qa_dependencies(self, ac: dict, ignore_cooldown: bool = False) -> dict:
        """autocorrect 依赖自动修复（带冷却重试，避免频繁安装）。"""
        autofix = {"attempted": False, "actions": []}
        qa_cfg = self._qa_runtime_config.get("qa") or {}
        auto_install_enabled = bool(qa_cfg.get("auto_install_dependencies", True))
        retry_interval = int(qa_cfg.get("auto_install_retry_seconds", 300))
        if not auto_install_enabled:
            autofix["actions"].append({"name": "autofix", "ok": False, "detail": "disabled by config"})
            self._qa_install_state = {
                "status": "disabled",
                "message": "auto install disabled",
                "updated_at": int(time.time()),
            }
            return autofix
        if (not ignore_cooldown) and self._qa_autofix_attempted and (time.time() - self._qa_autofix_attempted_at) < retry_interval:
            autofix["actions"].append({"name": "autofix", "ok": False, "detail": "cooldown"})
            self._qa_install_state = {
                "status": "cooldown",
                "message": f"next retry in <= {retry_interval}s",
                "updated_at": int(time.time()),
            }
            return autofix

        self._qa_autofix_attempted = True
        self._qa_autofix_attempted_at = int(time.time())
        autofix["attempted"] = True
        self._qa_install_state = {
            "status": "installing",
            "message": "starting dependency auto-install" if not ignore_cooldown else "retrying dependency auto-install now",
            "updated_at": int(time.time()),
        }

        if ac.get("enabled") and not ac.get("available"):
            self._qa_install_state = {
                "status": "installing",
                "message": "installing autocorrect",
                "updated_at": int(time.time()),
            }
            ok, detail = self._auto_install_autocorrect()
            autofix["actions"].append({"name": "autocorrect", "ok": ok, "detail": detail})
            self._ensure_autocorrect_command()

        self._qa_install_state = {
            "status": "verifying",
            "message": "verifying capabilities",
            "updated_at": int(time.time()),
        }
        return autofix

    def _warmup_qa_capabilities(self, force: bool = False, aggressive_retry: bool = False) -> dict:
        if self._qa_health and not force:
            return self._qa_health

        self._qa_runtime_config = self._load_runtime_config()
        self._ensure_autocorrect_command()
        ac = self._probe_autocorrect()

        # 首次发现缺依赖时尝试自动修复，再重探测一次。
        autofix = self._auto_fix_qa_dependencies(ac, ignore_cooldown=aggressive_retry)
        if autofix.get("attempted"):
            ac = self._probe_autocorrect()

        # 硬门禁：启用的能力必须全部可用。
        required = []
        if ac["enabled"]:
            required.append(("autocorrect", ac["available"]))
        missing = [name for name, ok in required if not ok]

        self._qa_health = {
            "ready": len(missing) == 0,
            "checked_at": int(time.time()),
            "missing": missing,
            "autofix": autofix,
            "install_state": {
                **self._qa_install_state,
                "completed": len(missing) == 0,
            },
            "capabilities": {
                "autocorrect": ac,
            },
        }
        if len(missing) == 0:
            self._qa_install_state = {
                "status": "completed",
                "message": "qa dependencies ready",
                "updated_at": int(time.time()),
            }
            self._qa_health["install_state"] = {
                **self._qa_install_state,
                "completed": True,
            }
        elif self._qa_install_state.get("status") in ("idle", "verifying", "completed"):
            self._qa_install_state = {
                "status": "pending",
                "message": "waiting for dependencies",
                "updated_at": int(time.time()),
            }
            self._qa_health["install_state"] = {
                **self._qa_install_state,
                "completed": False,
            }
        return self._qa_health

    def getQAHealth(self) -> str:
        health = self._warmup_qa_capabilities(force=True)
        # 纯网页场景下，前端主要靠 health 轮询；这里按节流自动触发一次“立即重试安装”。
        if not health.get("ready", False):
            now_ts = int(time.time())
            qa_cfg = self._qa_runtime_config.get("qa") or {}
            aggressive_interval = int(qa_cfg.get("auto_install_aggressive_retry_seconds", 20))
            if (now_ts - self._qa_last_aggressive_retry_at) >= aggressive_interval:
                self._qa_last_aggressive_retry_at = now_ts
                health = self._warmup_qa_capabilities(force=True, aggressive_retry=True)
        return json.dumps({"success": True, **health}, ensure_ascii=False)

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

        sections = []
        styles_meta: dict = {}
        try:
            if ext == "docx":
                elements, sections, styles_meta = self._parse_docx(path)
            elif ext in ("txt", "md"):
                elements = self._parse_text(path)
            else:
                try:
                    elements = self._parse_text(path)
                except Exception:
                    elements, sections, styles_meta = self._parse_docx(path)

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
            "type": ext, "elements": elements, "element_count": len(elements),
            "sections": sections, "styles": styles_meta,
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

    def refreshDocxFields(self, docx_b64: str) -> str:
        """
        用 Word COM (PowerShell) 刷新 docx 的域/目录编号。
        回退：LibreOffice headless 重存（不刷域，但不破坏文件）。
        两者均不可用时返回 error_code=NO_OFFICE_ENGINE。
        """
        import base64 as _b64
        import subprocess
        import tempfile
        import shutil
        from pathlib import Path as _Path

        try:
            docx_bytes = _b64.b64decode(docx_b64)
        except Exception as exc:
            return json.dumps({"error": f"base64 decode failed: {exc}"})

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(docx_bytes)
                tmp_path = tmp.name

            # 尝试 Word COM（PowerShell，Windows only）
            if sys.platform == "win32":
                src_ps = tmp_path.replace("'", "''")
                ps = (
                    "$ErrorActionPreference='Stop';"
                    "$w=$null;"
                    "try{"
                    f"$w=New-Object -ComObject Word.Application;"
                    "$w.Visible=$false;"
                    f"$d=$w.Documents.Open('{src_ps}');"
                    "$d.Fields.Update();"
                    "$d.TablesOfContents|ForEach-Object{$_.Update()};"
                    "$d.Save();"
                    "$d.Close();"
                    "Write-Output 'OK'"
                    "}catch{Write-Error $_.Exception.Message}"
                    "finally{if($w){$w.Quit()}}"
                )
                try:
                    r = subprocess.run(
                        ["powershell", "-NonInteractive", "-Command", ps],
                        capture_output=True, text=True, timeout=120,
                    )
                    if r.returncode == 0 and "OK" in r.stdout:
                        with open(tmp_path, "rb") as f:
                            out_b64 = _b64.b64encode(f.read()).decode("utf-8")
                        return json.dumps({"success": True, "content": out_b64})
                    logger.warning("Word COM Fields.Update 失败: %s", r.stderr[:200])
                except subprocess.TimeoutExpired:
                    return json.dumps({"error_code": "TIMEOUT", "error": "Word COM 超时（>120s）"})
                except Exception as ps_err:
                    logger.warning("PowerShell 调用失败: %s", ps_err)

            # 尝试 LibreOffice headless（重转存，不真正刷域，但保持文件完整）
            lo_candidates = [
                "libreoffice", "soffice",
                "/usr/bin/libreoffice", "/usr/bin/soffice",
                "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
                "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            ]
            lo_cmd = None
            for cmd in lo_candidates:
                try:
                    chk = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10)
                    if chk.returncode == 0:
                        lo_cmd = cmd
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue

            if lo_cmd:
                out_dir = tempfile.mkdtemp(prefix="wc_refresh_")
                try:
                    r = subprocess.run(
                        [lo_cmd, "--headless", "--convert-to", "docx",
                         "--outdir", out_dir, tmp_path],
                        capture_output=True, text=True, timeout=120,
                    )
                    stem = _Path(tmp_path).stem
                    lo_out = os.path.join(out_dir, stem + ".docx")
                    if not os.path.isfile(lo_out):
                        for fn in os.listdir(out_dir):
                            if fn.endswith(".docx"):
                                lo_out = os.path.join(out_dir, fn)
                                break
                    if r.returncode == 0 and os.path.isfile(lo_out):
                        with open(lo_out, "rb") as f:
                            out_b64 = _b64.b64encode(f.read()).decode("utf-8")
                        return json.dumps({"success": True, "content": out_b64})
                except Exception as lo_err:
                    logger.warning("LibreOffice refresh 失败: %s", lo_err)
                finally:
                    shutil.rmtree(out_dir, ignore_errors=True)

            return json.dumps({"error_code": "NO_OFFICE_ENGINE",
                               "error": "Word COM 和 LibreOffice 均不可用，请安装其中之一"})
        except Exception as exc:
            logger.error("refreshDocxFields 异常: %s", exc)
            return json.dumps({"error_code": "ERROR", "error": str(exc)})
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

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

    @staticmethod
    def _extract_docx_format_rules(file_path: str) -> dict:
        """从 .docx 文件提取排版参数，返回与前端 _aiParsedRules 格式相同的 dict。"""
        try:
            from docx import Document
            from docx.oxml.ns import qn
            doc = Document(file_path)
        except Exception:
            return {}

        def _pt(sz):
            try:
                return round(float(sz.pt), 1)
            except Exception:
                return None

        def _cm(emu):
            try:
                return round(emu / 360000.0, 2)
            except Exception:
                return None

        def _cn_font(run):
            try:
                rpr = run._r.find(qn('w:rPr'))
                if rpr is None:
                    return None
                rf = rpr.find(qn('w:rFonts'))
                if rf is None:
                    return None
                return rf.get(qn('w:eastAsia')) or rf.get(qn('w:hAnsi'))
            except Exception:
                return None

        ALIGN = {1: '左对齐', 2: '居中', 3: '右对齐', 4: '两端对齐'}
        rules = {}

        if doc.sections:
            s = doc.sections[0]
            rules.update({
                'marginTop': _cm(s.top_margin),
                'marginBottom': _cm(s.bottom_margin),
                'marginLeft': _cm(s.left_margin),
                'marginRight': _cm(s.right_margin),
            })

        found = {k: False for k in ('h1', 'h2', 'h3', 'body')}
        for para in doc.paragraphs[:300]:
            if all(found.values()):
                break
            sname = (para.style.name or '').lower().strip()
            for lvl in (1, 2, 3):
                key = f'h{lvl}'
                if found[key]:
                    continue
                if sname in (f'heading {lvl}', f'标题 {lvl}', f'标题{lvl}', f'heading{lvl}'):
                    if para.runs:
                        run = para.runs[0]
                        rules[f'h{lvl}Font'] = _cn_font(run) or run.font.name
                        rules[f'h{lvl}Size'] = _pt(run.font.size)
                        found[key] = True
                    break
            if not found['body'] and sname in ('normal', '正文', 'body text', 'default paragraph font'):
                if para.text.strip() and para.runs:
                    run = para.runs[0]
                    cn = _cn_font(run)
                    rules['bodyFont'] = cn or run.font.name
                    rules['bodySize'] = _pt(run.font.size)
                    rules['westFont'] = run.font.name
                    pf = para.paragraph_format
                    try:
                        if pf.first_line_indent and run.font.size and run.font.size.pt > 0:
                            rules['indent'] = round(float(pf.first_line_indent / run.font.size), 1)
                    except Exception:
                        pass
                    try:
                        if pf.line_spacing is not None:
                            rules['lineHeight'] = round(float(pf.line_spacing), 2)
                    except Exception:
                        pass
                    rules['align'] = ALIGN.get(pf.alignment)
                    found['body'] = True

        return {k: v for k, v in rules.items() if v is not None}

    def uploadTemplate(self, file_path: str, name: str) -> str:
        try:
            format_rules = {}
            if file_path.lower().endswith('.docx') and os.path.exists(file_path):
                format_rules = self._extract_docx_format_rules(file_path)

            if self._supabase and self._session.get("user_id"):
                user_id = self._session["user_id"]
                file_url = self._supabase.upload_template_file(user_id, file_path, name)
                if file_url:
                    record = self._supabase.insert_template(user_id, name, file_url, "custom")
                    return json.dumps({"success": True, "template_id": record.get("id", "") if record else "", "name": name, "file_url": file_url, "format_rules": format_rules}, ensure_ascii=False)
                return json.dumps({"success": False, "error": "上传失败"})
            else:
                if not os.path.exists(file_path):
                    return json.dumps({"success": False, "error": "文件不存在"})
                return json.dumps({"success": True, "template_id": "template-new-001", "name": name, "format_rules": format_rules}, ensure_ascii=False)
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

    def runQA(self, content: str, categories_str: str = '["typo", "consistency", "logic", "format", "crossref"]') -> str:
        try:
            qa_health = self._warmup_qa_capabilities(force=False)
            if not qa_health.get("ready", False):
                # 用户刚完成依赖安装时，给一次强制重检机会，避免必须重启后端。
                qa_health = self._warmup_qa_capabilities(force=True, aggressive_retry=True)
            if not qa_health.get("ready", False):
                return json.dumps({
                    "success": False,
                    "error_code": "QA_CAPABILITY_NOT_READY",
                    "error": "QA 能力未就绪，请联系管理员完成依赖安装。",
                    "missing": qa_health.get("missing", []),
                    "capabilities": qa_health.get("capabilities", {}),
                }, ensure_ascii=False)

            from core.qa_engine import QAEngine
            from core.document_model import DocumentModel, DocElement, ElementType
            from html.parser import HTMLParser

            class _StripHTML(HTMLParser):
                def __init__(self): super().__init__(); self._parts = []
                def handle_data(self, d): self._parts.append(d)
                def get_text(self): return ''.join(self._parts)

            doc = DocumentModel(title="检查文档", source_format="html")
            # 将 HTML/纯文本 content 解析为 DocElement 列表
            if content:
                import re as _re
                raw = content if isinstance(content, str) else str(content)
                # 逐个匹配 HTML 块元素（h1-h6, p, li）以及换行纯文本
                for m in _re.finditer(
                    r'<h([1-6])[^>]*>(.*?)</h[1-6]>|<(?:p|li)[^>]*>(.*?)</(?:p|li)>|([^\n<]+)',
                    raw, _re.IGNORECASE | _re.DOTALL
                ):
                    if m.group(1):  # heading
                        p = _StripHTML(); p.feed(m.group(2)); txt = p.get_text().strip()
                        if txt:
                            doc.elements.append(DocElement(element_type=ElementType.HEADING,
                                content=txt, level=int(m.group(1))))
                    elif m.group(3) is not None:  # p / li
                        p = _StripHTML(); p.feed(m.group(3)); txt = p.get_text().strip()
                        if txt:
                            elem_type = ElementType.PARAGRAPH
                            if _re.match(r"^(图|表)\s*\d+([\-\.]\d+)?", txt):
                                elem_type = ElementType.CAPTION
                            elif _re.match(r"^\[\d+\]", txt):
                                elem_type = ElementType.REFERENCE
                            doc.elements.append(DocElement(element_type=elem_type, content=txt))
                    elif m.group(4):  # 纯文本行
                        txt = m.group(4).strip()
                        if txt:
                            elem_type = ElementType.PARAGRAPH
                            if _re.match(r"^(图|表)\s*\d+([\-\.]\d+)?", txt):
                                elem_type = ElementType.CAPTION
                            elif _re.match(r"^\[\d+\]", txt):
                                elem_type = ElementType.REFERENCE
                            doc.elements.append(DocElement(element_type=elem_type, content=txt))

            categories = json.loads(categories_str) if isinstance(categories_str, str) else categories_str
            engine = QAEngine(config=self._qa_runtime_config)
            report = engine.check(doc, categories)
            return json.dumps({
                "success": True,
                "issues": [
                    {"id": i.issue_id,
                     "category": i.category.value if hasattr(i.category, 'value') else str(i.category),
                     "severity": i.severity.value if hasattr(i.severity, 'value') else str(i.severity),
                     "title": i.title, "description": i.description,
                     "suggestion": i.suggestion, "confidence": i.confidence,
                     "location_text": (i.location_text or '').strip(),
                     "rule_id": getattr(i, "rule_id", ""),
                     "checker": getattr(i, "checker", "")}
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
            from core.document_model import DocumentModel, DocElement, ElementType
            from core.crossref_engine import TargetScanner, RefPointScanner, CrossRefMatcher
            from core.crossref_models import CrossRefStatus
            from html.parser import HTMLParser

            class _Strip(HTMLParser):
                def __init__(self): super().__init__(); self._parts = []
                def handle_data(self, d): self._parts.append(d)
                def get_text(self): return ''.join(self._parts)

            doc = DocumentModel(title="xref", source_format="html")
            for m in re.finditer(
                r'<h([1-6])[^>]*>(.*?)</h[1-6]>|<(?:p|li)[^>]*>(.*?)</(?:p|li)>',
                content, re.IGNORECASE | re.DOTALL
            ):
                if m.group(1):
                    p = _Strip(); p.feed(m.group(2)); txt = p.get_text().strip()
                    if txt:
                        doc.elements.append(DocElement(element_type=ElementType.HEADING,
                            content=txt, level=int(m.group(1))))
                elif m.group(3) is not None:
                    p = _Strip(); p.feed(m.group(3)); txt = p.get_text().strip()
                    if txt:
                        et = ElementType.PARAGRAPH
                        if re.match(r"^\s*\[\d+\]", txt):
                            et = ElementType.REFERENCE
                        doc.elements.append(DocElement(element_type=et, content=txt))

            scanner = TargetScanner()
            targets = scanner.scan(doc)
            ref_scanner = RefPointScanner()
            ref_points = ref_scanner.scan(doc)
            multi_refs = ref_scanner.scan_multi_references(doc)
            ref_points.extend(multi_refs)
            matcher = CrossRefMatcher()
            report = matcher.match(targets, ref_points)

            status_map = {
                CrossRefStatus.VALID: "valid",
                CrossRefStatus.DANGLING: "dangling",
                CrossRefStatus.UNREFERENCED: "unreferenced",
                CrossRefStatus.MISMATCH: "dangling",
            }
            targets_out = [{"type": t.target_type.value, "text": t.number, "label": t.label, "title": t.title or ""} for t in targets]
            matches_out = [{"status": status_map.get(m.status, "dangling"),
                            "reference": m.ref_point.ref_text if m.ref_point.ref_text else "—",
                            "target": m.target.label if m.target else "",
                            "message": m.message,
                            "element_index": getattr(m.ref_point, 'element_index', None)} for m in report.matches]

            return json.dumps({
                "success": True, "targets": targets_out, "matches": matches_out,
                "summary": {"total_targets": len(targets_out),
                             "valid_matches": sum(1 for m in matches_out if m["status"] == "valid"),
                             "dangling_references": sum(1 for m in matches_out if m["status"] == "dangling"),
                             "unreferenced": sum(1 for m in matches_out if m["status"] == "unreferenced")},
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
        config = {}
        if config_str:
            try:
                config = json.loads(config_str) if isinstance(config_str, str) else config_str
            except Exception:
                pass

        model = str(config.get("model", "deepseek-v4-flash")).strip()
        if (not model) or (not model.lower().startswith("deepseek-")):
            # 兼容旧前端保存的 doubao/deepseek-v3 模型名，统一回退到可用默认模型。
            model = "deepseek-v4-flash"
        temperature = config.get("temperature", 0.3)
        max_tokens = int(config.get("max_tokens", 2048))
        reasoning_effort = config.get("reasoning_effort", "high")
        api_key = (
            os.environ.get("DEEPSEEK_API_KEY")
            or ((self._qa_runtime_config.get("llm") or {}).get("deepseek") or {}).get("api_key", "")
        )
        if not api_key:
            return json.dumps({"error": "DEEPSEEK_API_KEY 未配置，已停用豆包通道。"}, ensure_ascii=False)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            req = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if model in ("deepseek-v4-flash", "deepseek-v4-pro"):
                req["reasoning_effort"] = reasoning_effort
                req["extra_body"] = {"thinking": {"type": "enabled"}}
            resp = client.chat.completions.create(**req)
            content = (resp.choices[0].message.content or "").strip()
            usage = getattr(resp, "usage", None)
            return json.dumps({"content": content, "usage": usage.model_dump() if usage else {}}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  文件解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_docx(path: str):
        """Return (elements, sections, styles).

        - elements: paragraph / table list (each paragraph carries fmt + runs for round-trip export).
        - sections: page geometry per section.
        - styles: metadata for Normal / Heading 1-3 (font name, size, bold, rFonts) so the exporter
          can rewrite ``word/styles.xml`` to match the source. python-docx auto-materialises any
          missing style, so always emitting a 4-entry dict keeps the downstream code simple.
        """
        from docx import Document
        from docx.oxml.ns import qn
        doc = Document(path)
        elements = []

        def _para_fmt(para):
            fmt = para.paragraph_format
            def _tw(length):
                if length is None:
                    return None
                try:
                    return int(length.twips)
                except Exception:
                    return None
            rule_name = str(fmt.line_spacing_rule).split()[0] if fmt.line_spacing_rule is not None else None
            line_spacing = None
            line_spacing_twips = None
            if fmt.line_spacing is not None:
                if rule_name in ("EXACTLY", "AT_LEAST"):
                    line_spacing_twips = _tw(fmt.line_spacing)
                else:
                    try:
                        line_spacing = float(fmt.line_spacing)
                    except Exception:
                        line_spacing = None
            return {
                "style": para.style.name if para.style else None,
                "alignment": str(para.alignment).split()[0] if para.alignment is not None else None,
                "first_line_indent_twips": _tw(fmt.first_line_indent),
                "left_indent_twips": _tw(fmt.left_indent),
                "right_indent_twips": _tw(fmt.right_indent),
                "space_before_twips": _tw(fmt.space_before),
                "space_after_twips": _tw(fmt.space_after),
                "line_spacing_rule": rule_name,
                "line_spacing": line_spacing,
                "line_spacing_twips": line_spacing_twips,
            }

        def _runs(para):
            out = []
            for r in para.runs:
                r_pr = getattr(r._element, "rPr", None)
                r_fonts = getattr(r_pr, "rFonts", None) if r_pr is not None else None
                out.append({
                    "text": r.text or "",
                    "font_name": r.font.name,
                    "font_size_pt": float(r.font.size.pt) if r.font.size else None,
                    "bold": bool(r.bold) if r.bold is not None else None,
                    "italic": bool(r.italic) if r.italic is not None else None,
                    "underline": bool(r.underline) if r.underline is not None else None,
                    "font_ascii": r_fonts.get(qn("w:ascii")) if r_fonts is not None else None,
                    "font_hansi": r_fonts.get(qn("w:hAnsi")) if r_fonts is not None else None,
                    "font_eastAsia": r_fonts.get(qn("w:eastAsia")) if r_fonts is not None else None,
                    "font_cs": r_fonts.get(qn("w:cs")) if r_fonts is not None else None,
                })
            return out

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                from docx.text.paragraph import Paragraph
                para = Paragraph(element, doc)
                text = para.text or ""
                text_stripped = text.strip()
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
                elif "list number" in style_name or "有序列表" in style_name:
                    elem_type = "li"
                elif re.match(r"^\[\d+\]", text_stripped):
                    elem_type = "ref"
                # Detect section break contained inside this paragraph's pPr (w:sectPr). Word
                # stores section breaks on the paragraph that ends each section except the last,
                # which is captured by the body-level sectPr.
                sect_pr = element.find(qn("w:pPr") + "/" + qn("w:sectPr")) if False else None
                try:
                    p_pr = element.find(qn("w:pPr"))
                    sect_pr = p_pr.find(qn("w:sectPr")) if p_pr is not None else None
                except Exception:
                    sect_pr = None
                section_break_type = None
                if sect_pr is not None:
                    type_el = sect_pr.find(qn("w:type"))
                    if type_el is not None:
                        section_break_type = type_el.get(qn("w:val")) or "nextPage"
                    else:
                        section_break_type = "nextPage"
                elements.append({
                    "type": elem_type,
                    "text": text,
                    "fmt": _para_fmt(para),
                    "runs": _runs(para),
                    "section_break": section_break_type,
                })

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
                    elements.append({"type": "p", "text": text, "fmt": _para_fmt(para), "runs": _runs(para)})

        sections = []
        for s in doc.sections:
            def _tw(v):
                try:
                    return int(v.twips) if v is not None else None
                except Exception:
                    return None
            sections.append({
                "page_width_twips": _tw(s.page_width),
                "page_height_twips": _tw(s.page_height),
                "left_margin_twips": _tw(s.left_margin),
                "right_margin_twips": _tw(s.right_margin),
                "top_margin_twips": _tw(s.top_margin),
                "bottom_margin_twips": _tw(s.bottom_margin),
            })

        tracked_styles = ("Normal", "Heading 1", "Heading 2", "Heading 3")
        styles_meta: dict = {}
        for style_name in tracked_styles:
            try:
                style = doc.styles[style_name]
            except (KeyError, Exception):
                continue
            r_fonts_el = None
            r_pr = style.element.find(qn("w:rPr")) if style.element is not None else None
            if r_pr is not None:
                r_fonts_el = r_pr.find(qn("w:rFonts"))
            rfonts = {
                "ascii": r_fonts_el.get(qn("w:ascii")) if r_fonts_el is not None else None,
                "hAnsi": r_fonts_el.get(qn("w:hAnsi")) if r_fonts_el is not None else None,
                "eastAsia": r_fonts_el.get(qn("w:eastAsia")) if r_fonts_el is not None else None,
                "cs": r_fonts_el.get(qn("w:cs")) if r_fonts_el is not None else None,
            }
            try:
                size_pt = float(style.font.size.pt) if style.font.size else None
            except Exception:
                size_pt = None
            styles_meta[style_name] = {
                "font_name": style.font.name,
                "font_size_pt": size_pt,
                "bold": bool(style.font.bold) if style.font.bold is not None else None,
                "italic": bool(style.font.italic) if style.font.italic is not None else None,
                "underline": bool(style.font.underline) if style.font.underline is not None else None,
                "rfonts": rfonts,
            }

        return elements, sections, styles_meta

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
