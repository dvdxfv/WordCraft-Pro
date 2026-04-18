#!/usr/bin/env python3
"""
WordCraft Pro - 智能Word排版桌面应用
使用 pywebview 加载网页版 UI，提供原生文件对话框和系统集成。
"""

import json
import logging
import os
import re
import sys
import time
from functools import wraps

import webview

logger = logging.getLogger(__name__)

APP_TITLE = "WordCraft Pro"
APP_VERSION = "1.0.0"


# ============================================================
# 性能优化：响应缓存装饰器
# ============================================================

def cached_response(ttl_seconds: int = 300):
    """缓存 API 响应装饰器（TTL: 生存时间）✅ 优化"""
    def decorator(func):
        cache = {}
        cache_time = {}

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"

            # 检查缓存是否有效
            now = time.time()
            if cache_key in cache and (now - cache_time.get(cache_key, 0)) < ttl_seconds:
                logger.debug(f"✅ 缓存命中: {func.__name__}")
                return cache[cache_key]

            # 执行原函数并缓存结果
            result = func(self, *args, **kwargs)
            cache[cache_key] = result
            cache_time[cache_key] = now
            return result

        return wrapper
    return decorator


class Api:
    """暴露给网页版 JavaScript 的 Python API。

    网页版通过 window.pywebview.api.xxx() 调用这些方法。
    """

    def __init__(self, supabase_enabled: bool = True) -> None:
        self._window = None
        self._session = {}  # 存储当前用户会话
        self._supabase = None  # Supabase 客户端
        self._supabase_enabled = supabase_enabled
        self._supabase_initialized = False
        # ✅ 优化: 延迟初始化 Supabase（不阻塞启动）

    def _ensure_supabase_initialized(self):
        """确保 Supabase 已初始化（延迟初始化）"""
        if not self._supabase_initialized and self._supabase_enabled:
            self._init_supabase()
            self._supabase_initialized = True

    def _init_supabase(self):
        """初始化 Supabase 客户端"""
        try:
            from core.supabase_client import SupabaseClient
            self._supabase = SupabaseClient()
            logger.info("Supabase 客户端初始化成功")
        except Exception as e:
            logger.warning("Supabase 客户端初始化失败，使用本地模式: %s", e)
            self._supabase = None

    def set_window(self, window) -> None:
        self._window = window

    # ------------------------------------------------------------------
    #  文件操作
    # ------------------------------------------------------------------

    def openFile(self) -> str:
        """弹出原生文件对话框，返回 JSON 字符串。"""
        if not self._window:
            logger.warning("openFile: 没有窗口对象")
            return json.dumps({"cancelled": True})

        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=(
                "Word Document (*.docx)",
                "Text File (*.txt;*.md)",
                "All Files (*.*)",
            ),
        )
        if not result:
            logger.info("openFile: 用户取消选择")
            return json.dumps({"cancelled": True})

        path = result[0]
        name = os.path.basename(path)

        # 检查文件是否存在
        if not os.path.exists(path):
            logger.error(f"openFile: 文件不存在 {path}")
            return json.dumps({"success": False, "error": f"文件不存在: {path}"})

        try:
            size = os.path.getsize(path)
        except Exception as e:
            logger.error(f"openFile: 无法获取文件大小 {path}: {e}")
            return json.dumps({"success": False, "error": f"无法获取文件大小: {str(e)}"})

        ext = name.rsplit(".", 1)[-1].lower()
        logger.info(f"openFile: 打开文件 {name} (大小: {size}, 类型: {ext})")

        try:
            if ext == "docx":
                elements = self._parse_docx(path)
            elif ext in ("txt", "md"):
                elements = self._parse_text(path)
            else:
                elements = self._parse_text(path)

            logger.info(f"openFile: 成功解析 {len(elements)} 个元素")
        except Exception as exc:
            logger.error(f"openFile: 解析文件失败 {path}: {exc}", exc_info=True)
            return json.dumps({
                "success": False,
                "error": f"文件解析失败: {str(exc)}"
            })

        return json.dumps({
            "success": True,
            "name": name,
            "size": size,
            "type": ext,
            "elements": elements,
            "element_count": len(elements)
        }, ensure_ascii=False)

    def saveFile(self, content: str) -> str:
        """保存 HTML 到本地文件。"""
        if not self._window:
            return json.dumps({"cancelled": True})

        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="document.html",
            file_types=("HTML File (*.html)",),
        )
        if not result:
            return json.dumps({"cancelled": True})

        with open(result, "w", encoding="utf-8") as fh:
            fh.write(content)
        return json.dumps({"success": True, "path": result}, ensure_ascii=False)

    def exportDocx(self, content: str, format_params: str = "{}") -> str:
        """导出为 Word 文档。"""
        if not self._window:
            return json.dumps({"cancelled": True})

        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="document.docx",
            file_types=("Word Document (*.docx)",),
        )
        if not result:
            return json.dumps({"cancelled": True})

        try:
            params = json.loads(format_params) if format_params else {}
            self._write_docx(result, content, params)
            return json.dumps({"success": True, "path": result}, ensure_ascii=False)
        except Exception as exc:
            logger.error("导出失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    @cached_response(ttl_seconds=600)  # ✅ 优化: 10分钟缓存
    def getSystemInfo(self) -> str:
        """返回系统信息。"""
        return json.dumps({
            "version": APP_VERSION,
            "platform": sys.platform,
            "python": sys.version.split()[0],
        })

    # ------------------------------------------------------------------
    #  用户认证（Mock 版本，待对接 Supabase Auth）
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> str:
        """用户登录（对接 Supabase Auth）。"""
        try:
            self._ensure_supabase_initialized()  # ✅ 优化: 延迟初始化
            if self._supabase:
                result = self._supabase.sign_in(email, password)
                if result.get("success"):
                    # 获取用户档案
                    profile = self._supabase.get_profile(result["user_id"])
                    user_info = {
                        "id": result["user_id"],
                        "email": result["email"],
                        "nickname": profile.get("nickname", email.split("@")[0]) if profile else email.split("@")[0],
                        "avatar_url": profile.get("avatar_url", "") if profile else "",
                        "token_quota": profile.get("token_quota", 100000) if profile else 100000,
                        "token_used": profile.get("token_used", 0) if profile else 0,
                    }
                    # 保存会话
                    self._session = {
                        "user_id": result["user_id"],
                        "access_token": result.get("access_token"),
                        "user_info": user_info,
                    }
                    return json.dumps({
                        "success": True,
                        "user": user_info,
                        "token": result.get("access_token"),
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "success": False,
                        "error": result.get("error", "登录失败"),
                    }, ensure_ascii=False)
            else:
                # 本地 Mock 模式
                mock_user = {
                    "id": "mock-user-001",
                    "email": email,
                    "nickname": email.split("@")[0],
                    "avatar_url": "",
                    "token_quota": 100000,
                    "token_used": 12345,
                }
                self._session = {"user_id": "mock-user-001", "user_info": mock_user}
                return json.dumps({
                    "success": True,
                    "user": mock_user,
                    "token": "mock-jwt-token",
                }, ensure_ascii=False)
        except Exception as exc:
            logger.error("登录失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def logout(self) -> str:
        """用户登出。"""
        try:
            self._ensure_supabase_initialized()  # ✅ 优化: 延迟初始化
            if self._supabase and self._session.get("access_token"):
                self._supabase.sign_out(self._session.get("access_token"))
            self._session = {}
            return json.dumps({"success": True})
        except Exception as exc:
            logger.error("登出失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  Token 管理（Mock 版本，待对接 Supabase 数据库）
    # ------------------------------------------------------------------

    def getTokenUsage(self) -> str:
        """获取 Token 用量（对接 Supabase 数据库）。"""
        try:
            if self._supabase and self._session.get("user_id"):
                usage = self._supabase.get_token_usage(self._session["user_id"])
                return json.dumps(usage, ensure_ascii=False)
            else:
                # 本地 Mock 模式
                from core.token_tracker import TokenTracker
                tracker = TokenTracker()
                usage = tracker.get_quota()
                return json.dumps({
                    "token_quota": usage.get('quota', 100000),
                    "token_used": usage.get('used', 0),
                    "token_remaining": usage.get('remaining', 100000),
                    "usage_percentage": usage.get('usage_percentage', 0),
                    "today_usage": 0,
                    "month_usage": usage.get('used', 0),
                }, ensure_ascii=False)
        except Exception as exc:
            logger.error("获取 Token 用量失败: %s", exc)
            return json.dumps({
                "token_quota": 100000,
                "token_used": 0,
                "token_remaining": 100000,
                "usage_percentage": 0,
                "today_usage": 0,
                "month_usage": 0,
            }, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  模板管理（Mock 版本，待对接 Supabase Storage）
    # ------------------------------------------------------------------

    @cached_response(ttl_seconds=300)  # ✅ 优化: 5分钟缓存
    def getUserTemplates(self) -> str:
        """获取用户模板列表（对接 Supabase Storage）。"""
        try:
            if self._supabase and self._session.get("user_id"):
                templates = self._supabase.get_user_templates(self._session["user_id"])
                return json.dumps({
                    "success": True,
                    "templates": templates,
                }, ensure_ascii=False)
            else:
                # 本地 Mock 模式
                mock_templates = [
                    {"id": "template-001", "name": "广东海洋大学毕业论文", "category": "thesis", "file_url": "", "created_at": "2026-04-15"},
                    {"id": "template-002", "name": "尖草坪区绩效评价报告", "category": "gov", "file_url": "", "created_at": "2026-04-16"},
                ]
                return json.dumps({"success": True, "templates": mock_templates}, ensure_ascii=False)
        except Exception as exc:
            logger.error("获取模板列表失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def uploadTemplate(self, file_path: str, name: str) -> str:
        """上传模板文件（对接 Supabase Storage）。"""
        try:
            if self._supabase and self._session.get("user_id"):
                user_id = self._session["user_id"]
                file_url = self._supabase.upload_template_file(user_id, file_path, name)
                if file_url:
                    # 保存到数据库
                    template_entry = {
                        "user_id": user_id,
                        "name": name,
                        "file_url": file_url,
                        "category": "custom",
                    }
                    # 需要添加插入模板的逻辑
                    return json.dumps({
                        "success": True,
                        "template_id": "new-template",
                        "name": name,
                        "file_url": file_url,
                    }, ensure_ascii=False)
                else:
                    return json.dumps({"success": False, "error": "上传失败"})
            else:
                # 本地 Mock 模式
                if not os.path.exists(file_path):
                    return json.dumps({"success": False, "error": "文件不存在"})
                return json.dumps({
                    "success": True,
                    "template_id": "template-new-001",
                    "name": name,
                }, ensure_ascii=False)
        except Exception as exc:
            logger.error("上传模板失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def deleteTemplate(self, template_id: str) -> str:
        """删除模板（对接 Supabase）。"""
        try:
            if self._supabase and self._session.get("user_id"):
                success = self._supabase.delete_template(template_id, self._session["user_id"])
                return json.dumps({"success": success})
            else:
                return json.dumps({"success": True})
        except Exception as exc:
            logger.error("删除模板失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  质量检查（调用后端 QA 引擎）
    # ------------------------------------------------------------------

    def runQA(self, content: str, categories_str: str = '["typo", "consistency", "logic"]') -> str:
        """运行质量检查。"""
        try:
            from core.qa_engine import QAEngine
            from core.document_model import DocumentModel

            # 解析内容（简化版，实际应从前端传入 DocumentModel）
            doc = DocumentModel(
                title="检查文档",
                source_format="html",
            )
            # TODO: 将 HTML content 转换为 DocumentModel

            categories = json.loads(categories_str)
            engine = QAEngine()
            report = engine.check(doc, categories)

            return json.dumps({
                "success": True,
                "issues": [
                    {
                        "id": issue.id,
                        "category": issue.category.value if hasattr(issue.category, 'value') else str(issue.category),
                        "severity": issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
                        "title": issue.title,
                        "description": issue.description,
                        "suggestion": issue.suggestion,
                        "confidence": issue.confidence,
                    }
                    for issue in report.issues
                ],
                "stats": {
                    "total": len(report.issues),
                    "errors": len([i for i in report.issues if i.severity.value == "error"]),
                    "warnings": len([i for i in report.issues if i.severity.value == "warning"]),
                    "infos": len([i for i in report.issues if i.severity.value == "info"]),
                },
            }, ensure_ascii=False)
        except Exception as exc:
            logger.error("QA 检查失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)})

    def acceptSuggestion(self, content: str, issue_id: str, original_text: str, suggested_text: str) -> str:
        """接受单个建议，仅替换错误部分。✅ 改进: 精确替换"""
        try:
            logger.info(f"acceptSuggestion: 接受建议 - '{original_text}' -> '{suggested_text}'")

            # 使用精确替换而不是整行替换
            # 只替换原文本第一次出现的地方
            corrected = content.replace(original_text, suggested_text, 1)

            if corrected == content:
                logger.warning(f"acceptSuggestion: 未找到待替换文本 '{original_text}'")
                return json.dumps({
                    "success": False,
                    "error": f"未找到待替换文本: {original_text}"
                })

            logger.info(f"acceptSuggestion: 成功替换")
            return json.dumps({
                "success": True,
                "corrected_content": corrected,
                "message": f"已将 '{original_text}' 改为 '{suggested_text}'"
            }, ensure_ascii=False)

        except Exception as exc:
            logger.error(f"acceptSuggestion 失败: {exc}", exc_info=True)
            return json.dumps({"success": False, "error": str(exc)})

    # ------------------------------------------------------------------
    #  交叉引用（调用后端交叉引用引擎）
    # ------------------------------------------------------------------

    def runXRef(self, content: str) -> str:
        """运行交叉引用检查。✅ 改进: 从 HTML 提取目标和引用"""
        try:
            from core.crossref_engine import CrossRefEngine
            from core.document_model import DocumentModel, DocElement, ElementType
            import re

            logger.info("runXRef: 开始交叉引用检查")

            # 从 HTML content 中提取文本和结构
            # 查找所有 <h1>...<h3>, 表题, 图题等
            targets_found = []
            references_found = []

            # 提取标题（作为章节目标）
            for match in re.finditer(r'<h([1-3])>([^<]+)</h\1>', content):
                level = int(match.group(1))
                text = match.group(2)
                targets_found.append({
                    "type": f"heading_{level}",
                    "text": text,
                    "label": text
                })
                logger.info(f"  发现目标: H{level} '{text}'")

            # 提取表题（表X-Y 或 表X）
            for match in re.finditer(r'表\s*(\d+)[\-\.]?(\d*)\s*([^<\n]*)', content):
                table_num = match.group(1)
                table_sub = match.group(2) or ""
                title = match.group(3).strip()
                label = f"表{table_num}" + (f"-{table_sub}" if table_sub else "")
                targets_found.append({
                    "type": "table",
                    "text": label,
                    "label": f"{label} {title}".strip()
                })
                logger.info(f"  发现目标: {label}")

            # 提取图题（图X-Y 或 图X）
            for match in re.finditer(r'图\s*(\d+)[\-\.]?(\d*)\s*([^<\n]*)', content):
                fig_num = match.group(1)
                fig_sub = match.group(2) or ""
                title = match.group(3).strip()
                label = f"图{fig_num}" + (f"-{fig_sub}" if fig_sub else "")
                targets_found.append({
                    "type": "figure",
                    "text": label,
                    "label": f"{label} {title}".strip()
                })
                logger.info(f"  发现目标: {label}")

            # 提取引用（"如图X-Y所示", "见表X-Y", 等）
            for match in re.finditer(r'(如图|见表|查看图|参见表|图|表)\s*(\d+)[\-\.]?(\d*)', content):
                ref_type = match.group(1)
                num = match.group(2)
                sub_num = match.group(3) or ""
                ref_text = f"{num}" + (f"-{sub_num}" if sub_num else "")
                references_found.append({
                    "type": "图" if "图" in ref_type else "表",
                    "text": ref_text,
                    "full_text": match.group(0),
                    "location": match.start()
                })
                logger.info(f"  发现引用: {ref_type}{ref_text}")

            # 匹配引用与目标
            matches = []
            for ref in references_found:
                found = False
                for target in targets_found:
                    # 修复匹配逻辑：检查类型和编号是否匹配
                    target_type = target["type"]
                    # 检查图表类型匹配
                    if ref["type"] == "图" and "figure" in target_type:
                        # 图的匹配
                        if ref["text"] in target["label"]:
                            matches.append({
                                "status": "valid",
                                "reference": ref["full_text"],
                                "target": target["label"],
                                "message": "匹配成功"
                            })
                            found = True
                            break
                    elif ref["type"] == "表" and "table" in target_type:
                        # 表的匹配
                        if ref["text"] in target["label"]:
                            matches.append({
                                "status": "valid",
                                "reference": ref["full_text"],
                                "target": target["label"],
                                "message": "匹配成功"
                            })
                            found = True
                            break

                if not found:
                    # 只有当真的找不到目标时才报告悬空
                    matches.append({
                        "status": "dangling",
                        "reference": ref["full_text"],
                        "message": f"找不到{ref['type']}{ref['text']}的定义"
                    })

            logger.info(f"runXRef: 检查完成 - 发现 {len(targets_found)} 个目标, {len(references_found)} 个引用")

            return json.dumps({
                "success": True,
                "targets": targets_found,
                "references": references_found,
                "matches": matches,
                "summary": {
                    "total_targets": len(targets_found),
                    "total_references": len(references_found),
                    "valid_matches": len([m for m in matches if m["status"] == "valid"]),
                    "dangling_references": len([m for m in matches if m["status"] == "dangling"]),
                }
            }, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"交叉引用检查失败: {exc}", exc_info=True)
            return json.dumps({"success": False, "error": str(exc)})

    # ------------------------------------------------------------------
    #  排版引擎（调用后端排版引擎）
    # ------------------------------------------------------------------

    def applyFormat(self, content: str, rules_str: str = "{}") -> str:
        """应用排版规则。✅ 改进: 实际应用规则到内容"""
        try:
            rules = json.loads(rules_str) if rules_str else {}

            # 解析规则
            heading1_font = rules.get("heading1_font", "宋体")
            heading1_size = rules.get("heading1_size", "16")
            heading2_font = rules.get("heading2_font", "宋体")
            heading2_size = rules.get("heading2_size", "14")
            heading3_font = rules.get("heading3_font", "宋体")
            heading3_size = rules.get("heading3_size", "12")
            body_font = rules.get("body_font", "宋体")
            body_size = rules.get("body_size", "10.5")
            line_height = rules.get("line_height", "1.5")

            logger.info(f"applyFormat: 应用排版规则 - 标题字体:{heading1_font}, 正文字体:{body_font}")

            # 应用 CSS 样式到 HTML 内容
            styled_content = self._apply_css_styles(
                content,
                {
                    "h1": {"font-family": heading1_font, "font-size": f"{heading1_size}pt", "line-height": line_height},
                    "h2": {"font-family": heading2_font, "font-size": f"{heading2_size}pt", "line-height": line_height},
                    "h3": {"font-family": heading3_font, "font-size": f"{heading3_size}pt", "line-height": line_height},
                    "p": {"font-family": body_font, "font-size": f"{body_size}pt", "line-height": line_height},
                    "body": {"font-family": body_font, "line-height": line_height},
                }
            )

            return json.dumps({
                "success": True,
                "message": "排版规则已应用",
                "rules_applied": len(rules),
                "formatted_content": styled_content,
            }, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"排版失败: {exc}", exc_info=True)
            return json.dumps({"success": False, "error": str(exc)})

    def _apply_css_styles(self, html_content: str, styles: dict) -> str:
        """应用 CSS 样式到 HTML 内容。✅ 改进: 支持样式应用"""
        import re

        result = html_content

        # 对每个标签应用样式
        for tag, tag_styles in styles.items():
            # 构建 style 字符串
            style_str = "; ".join(f"{k}: {v}" for k, v in tag_styles.items())

            # 查找所有该标签并添加样式
            pattern = f"<{tag}([^>]*)>"
            replacement = f'<{tag}\\1 style="{style_str}">'

            # 如果标签已有 style，则合并
            def merge_styles(match):
                existing = match.group(1)
                if 'style=' in existing:
                    # 已有 style，在其后追加新样式
                    existing = re.sub(
                        r'style="([^"]*)"',
                        f'style="\\1; {style_str}"',
                        existing
                    )
                    return f"<{tag}{existing}>"
                else:
                    return f'<{tag}{existing} style="{style_str}">'

            result = re.sub(pattern, merge_styles, result, flags=re.IGNORECASE)

        return result

    # ------------------------------------------------------------------
    #  文档管理（Mock 版本，待对接 Supabase 数据库）
    # ------------------------------------------------------------------

    def saveDocument(self, content: str, title: str = "未命名文档") -> str:
        """保存文档（对接 Supabase 数据库）。"""
        try:
            if self._supabase and self._session.get("user_id"):
                doc_id = self._supabase.save_document(
                    self._session["user_id"],
                    title,
                    {"html_content": content}
                )
                if doc_id:
                    return json.dumps({
                        "success": True,
                        "message": "文档已保存到云端",
                        "doc_id": doc_id,
                    }, ensure_ascii=False)
                else:
                    return json.dumps({"success": False, "error": "保存失败"})
            else:
                # 本地缓存模式
                import tempfile
                from core.user_data_manager import UserDataManager
                manager = UserDataManager()
                cache_dir = os.path.join(tempfile.gettempdir(), "wordcraft-cache")
                os.makedirs(cache_dir, exist_ok=True)
                
                doc_file = os.path.join(cache_dir, "current_doc.json")
                with open(doc_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "title": title,
                        "content": content,
                        "saved_at": "now",
                    }, f, ensure_ascii=False)
                
                return json.dumps({
                    "success": True,
                    "message": "文档已保存到本地",
                    "path": doc_file,
                }, ensure_ascii=False)
        except Exception as exc:
            logger.error("保存文档失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def loadDocument(self, doc_id: str = "current") -> str:
        """加载文档（对接 Supabase 数据库）。"""
        try:
            if self._supabase and self._session.get("user_id"):
                doc = self._supabase.load_document(doc_id, self._session["user_id"])
                if doc:
                    return json.dumps({
                        "success": True,
                        "document": doc,
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "success": False,
                        "error": "未找到文档",
                    }, ensure_ascii=False)
            else:
                # 本地缓存模式
                import tempfile
                cache_dir = os.path.join(tempfile.gettempdir(), "wordcraft-cache")
                doc_file = os.path.join(cache_dir, "current_doc.json")
                
                if os.path.exists(doc_file):
                    with open(doc_file, "r", encoding="utf-8") as f:
                        doc_data = json.load(f)
                    return json.dumps({
                        "success": True,
                        "document": doc_data,
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "success": False,
                        "error": "未找到保存的文档",
                    }, ensure_ascii=False)
        except Exception as exc:
            logger.error("加载文档失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    def getDocumentList(self) -> str:
        """获取文档列表（对接 Supabase 数据库）。"""
        try:
            if self._supabase and self._session.get("user_id"):
                docs = self._supabase.get_user_documents(self._session["user_id"])
                return json.dumps({
                    "success": True,
                    "documents": docs,
                }, ensure_ascii=False)
            else:
                # 本地 Mock 模式
                mock_documents = [
                    {
                        "id": "doc-001",
                        "title": "益海嘉里项目综合效益评价",
                        "updated_at": "2026-04-18 10:30",
                        "word_count": 5678,
                    },
                ]
                return json.dumps({
                    "success": True,
                    "documents": mock_documents,
                }, ensure_ascii=False)
        except Exception as exc:
            logger.error("获取文档列表失败: %s", exc)
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  AI 代理（解决浏览器 CORS 限制）
    # ------------------------------------------------------------------

    def callAI(self, system_prompt: str, user_message: str, config_str: str = "{}") -> str:
        """通过 Supabase Edge Function 代理调用豆包 API，失败时回退直接调用。"""
        import urllib.request
        import urllib.error

        config = json.loads(config_str) if config_str else {}
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
            # 通道2: 直接调用豆包 API（回退）
            print(f"[AI] Supabase proxy failed ({proxy_err}), falling back to direct API")
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
                    err_data = json.loads(body)
                    msg = err_data.get("error", {}).get("message", f"HTTP {e.code}")
                except Exception:
                    msg = f"HTTP {e.code}: {body[:200]}"
                return json.dumps({"error": msg}, ensure_ascii=False)
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    #  文件解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_docx(path: str) -> list[dict[str, str]]:
        """解析 .docx 文件。"""
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(path)
        elements: list[dict[str, str]] = []

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                from docx.text.paragraph import Paragraph
                para = Paragraph(element, doc)
                text = para.text.strip()
                if not text:
                    continue
                style_name = ((para.style.name if para.style else "") or "").lower()
                if any(k in style_name for k in ("heading 1", "标题 1", "title", "toc 1")):
                    elements.append({"type": "h1", "text": text})
                elif any(k in style_name for k in ("heading 2", "标题 2", "toc 2")):
                    elements.append({"type": "h2", "text": text})
                elif any(k in style_name for k in ("heading 3", "标题 3", "toc 3", "heading 4", "标题 4")):
                    elements.append({"type": "h3", "text": text})
                elif any(k in style_name for k in ("caption", "题注")):
                    elements.append({"type": "caption", "text": text})
                elif any(k in style_name for k in ("list bullet", "无序列表")):
                    elements.append({"type": "li", "text": "• " + text})
                elif any(k in style_name for k in ("list number", "有序列表")):
                    elements.append({"type": "li", "text": text})
                elif re.match(r"^\[\d+\]", text):
                    elements.append({"type": "ref", "text": text})
                else:
                    elements.append({"type": "p", "text": text})

            elif tag == "tbl":
                from docx.table import Table
                try:
                    table = Table(element, doc)
                    rows = []
                    for row in table.rows:
                        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        rows.append(cells)
                    if rows:
                        html_parts = ["<table>"]
                        for i, row in enumerate(rows):
                            t = "th" if i == 0 else "td"
                            html_parts.append(
                                "<tr>" + "".join(f"<{t}>{c}</{t}>" for c in row) + "</tr>"
                            )
                        html_parts.append("</table>")
                        elements.append({"type": "table", "text": "".join(html_parts)})
                except Exception:
                    pass

        if not elements:
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    elements.append({"type": "p", "text": text})

        return elements

    @staticmethod
    def _parse_text(path: str) -> list[dict[str, str]]:
        """解析 .txt / .md 文件。"""
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

        elements: list[dict[str, str]] = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if line.startswith("#### "):
                elements.append({"type": "h3", "text": line[5:].strip()})
            elif line.startswith("### "):
                elements.append({"type": "h3", "text": line[4:].strip()})
            elif line.startswith("## "):
                elements.append({"type": "h2", "text": line[3:].strip()})
            elif line.startswith("# "):
                elements.append({"type": "h1", "text": line[2:].strip()})
            elif re.match(r"^[\-\*]\s+", line):
                elements.append({"type": "li", "text": "• " + re.sub(r"^[\-\*]\s+", "", line)})
            elif re.match(r"^\d+\.\s+", line):
                elements.append({"type": "li", "text": line})
            elif line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+$", lines[i + 1].strip()):
                table_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    if not lines[i].strip().startswith("|---"):
                        table_lines.append(lines[i].strip())
                    i += 1
                rows = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.split("|")[1:-1]]
                    if cells:
                        rows.append(cells)
                if rows:
                    html_parts = ["<table>"]
                    for ri, row in enumerate(rows):
                        t = "th" if ri == 0 else "td"
                        html_parts.append(
                            "<tr>" + "".join(f"<{t}>{c}</{t}>" for c in row) + "</tr>"
                        )
                    html_parts.append("</table>")
                    elements.append({"type": "table", "text": "".join(html_parts)})
                continue
            elif re.match(r"^\[\d+\]", line):
                elements.append({"type": "ref", "text": line})
            elif re.match(r"^(图|表|Figure|Table)\s*\d", line):
                elements.append({"type": "caption", "text": line})
            else:
                elements.append({"type": "p", "text": line})
            i += 1
        return elements

    # ------------------------------------------------------------------
    #  Word 导出
    # ------------------------------------------------------------------

    @staticmethod
    def _write_docx(path: str, html_content: str, format_params: dict | None = None) -> None:
        """将 HTML 内容写入 .docx 文件。"""
        from docx import Document
        from docx.shared import Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn

        # 默认排版参数
        fp = format_params or {}
        h1_font = fp.get("h1Font", "黑体")
        h1_size = fp.get("h1Size", 16)
        h2_font = fp.get("h2Font", "黑体")
        h2_size = fp.get("h2Size", 14)
        h3_font = fp.get("h3Font", "黑体")
        h3_size = fp.get("h3Size", 12)
        body_font = fp.get("bodyFont", "宋体")
        west_font = fp.get("westFont", "Times New Roman")
        body_size = fp.get("bodySize", 12)
        indent_chars = fp.get("indent", 2)
        line_height = fp.get("lineHeight", 1.5)
        align = fp.get("align", "justify")
        margin_top = fp.get("marginTop", 2.5)
        margin_bottom = fp.get("marginBottom", 2.5)
        margin_left = fp.get("marginLeft", 3.0)
        margin_right = fp.get("marginRight", 2.5)

        doc = Document()
        section = doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(margin_top)
        section.bottom_margin = Cm(margin_bottom)
        section.left_margin = Cm(margin_left)
        section.right_margin = Cm(margin_right)

        elements = Api._html_to_elements(html_content)
        for elem in elements:
            t = elem["type"]
            text = elem["text"]
            if t in ("h1", "h2", "h3"):
                level = int(t[1])
                p = doc.add_heading(text, level=level)
                for run in p.runs:
                    run.font.name = west_font
                    run._element.rPr.rFonts.set(qn("w:eastAsia"), h1_font if t == "h1" else (h2_font if t == "h2" else h3_font))
                    run.font.size = Pt(h1_size if t == "h1" else (h2_size if t == "h2" else h3_size))
            elif t == "table":
                # Parse HTML table
                from html.parser import HTMLParser
                class TableParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.rows = []
                        self._current_row = []
                        self._in_cell = False
                        self._cell_text = ""
                    def handle_starttag(self, tag, attrs):
                        if tag in ("th", "td"):
                            self._in_cell = True
                            self._cell_text = ""
                    def handle_endtag(self, tag):
                        if tag in ("th", "td"):
                            self._in_cell = False
                            self._current_row.append(self._cell_text)
                        elif tag == "tr":
                            if self._current_row:
                                self.rows.append(self._current_row)
                            self._current_row = []
                    def handle_data(self, data):
                        if self._in_cell:
                            self._cell_text += data
                tp = TableParser()
                tp.feed(text)
                if tp.rows:
                    table = doc.add_table(rows=len(tp.rows), cols=len(tp.rows[0]))
                    table.style = "Table Grid"
                    for ri, row_data in enumerate(tp.rows):
                        for ci, cell_text in enumerate(row_data):
                            if ci < len(table.rows[ri].cells):
                                table.rows[ri].cells[ci].text = cell_text
            elif t == "ref":
                p = doc.add_paragraph(text)
                for run in p.runs:
                    run.font.name = west_font
                    run.font.size = Pt(10.5)
                    run._element.rPr.rFonts.set(qn("w:eastAsia"), body_font)
            elif t == "caption":
                p = doc.add_paragraph(text)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = west_font
                    run.font.size = Pt(10.5)
                    run._element.rPr.rFonts.set(qn("w:eastAsia"), h3_font)
            elif t == "li":
                p = doc.add_paragraph(text, style="List Bullet")
                for run in p.runs:
                    run.font.name = west_font
                    run.font.size = Pt(body_size)
                    run._element.rPr.rFonts.set(qn("w:eastAsia"), body_font)
                p.paragraph_format.line_spacing = line_height
            else:
                p = doc.add_paragraph(text)
                p.paragraph_format.first_line_indent = Cm(indent_chars * 0.35 * body_size / 12)
                p.paragraph_format.line_spacing = line_height
                if align == "justify":
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                elif align == "left":
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                elif align == "center":
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif align == "right":
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                for run in p.runs:
                    run.font.name = west_font
                    run.font.size = Pt(body_size)
                    run._element.rPr.rFonts.set(qn("w:eastAsia"), body_font)

        doc.save(path)

    @staticmethod
    def _html_to_elements(html: str) -> list[dict[str, str]]:
        """将 HTML 字符串解析为元素列表。"""
        cleaned = re.sub(r"<br\s*/?>", "\n", html)
        pattern = re.compile(
            r"<(h[1-6]|p|div|caption|li)[^>]*>(.*?)</\1>|(<table>.*?</table>)",
            re.DOTALL | re.IGNORECASE,
        )
        elements = []
        for match in pattern.finditer(cleaned):
            tag = match.group(1)
            html_block = match.group(3)
            if html_block:
                elements.append({"type": "table", "text": html_block})
                continue
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if not text:
                continue
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                elements.append({"type": tag, "text": text})
            elif tag == "caption":
                elements.append({"type": "caption", "text": text})
            elif tag == "li":
                elements.append({"type": "li", "text": text})
            else:
                elements.append({"type": "p", "text": text})
        return elements


# ======================================================================
#  网页版 JS 桥接注入（仅在 pywebview 环境下覆盖网页版的模拟函数）
# ======================================================================

BRIDGE_JS = """
// 等待 pywebview API 就绪后，覆盖网页版的文件操作函数
function waitForPywebview() {
    if (window.pywebview && window.pywebview.api) {
        console.log('pywebview API ready');

        // 覆盖 openFile：使用原生文件对话框
        window.openFile = async function() {
            try {
                const result = await window.pywebview.api.openFile();
                const data = JSON.parse(result);
                if (data.cancelled || data.error) {
                    if (data.error) showToast('打开失败: ' + data.error);
                    return;
                }
                // 注入到网页版数据结构
                _addFile(data.name, data.size, data.type, data.elements);
                showToast('已打开: ' + data.name);
            } catch(e) {
                console.error('openFile error:', e);
                showToast('打开文件失败');
            }
        };

        // 覆盖 saveFile：使用原生保存对话框
        window.saveFile = async function() {
            if (activeTabIdx < 0) { showToast('没有打开的文件'); return; }
            try {
                const page = document.getElementById('docPage');
                const result = await window.pywebview.api.saveFile(page.innerHTML);
                const data = JSON.parse(result);
                if (data.success) showToast('已保存: ' + data.path);
            } catch(e) {
                console.error('saveFile error:', e);
            }
        };

        // 覆盖 exportDoc：使用原生导出对话框 + python-docx
        window.exportDoc = async function() {
            if (activeTabIdx < 0) { showToast('没有打开的文件'); return; }
            try {
                const tab = openTabs[activeTabIdx];
                const html = document.getElementById('docPage').innerHTML;
                // 读取排版面板参数
                const formatParams = JSON.stringify({
                    h1Font: (document.getElementById('fH1Font')?.value || '黑体'),
                    h1Size: parseFloat(document.getElementById('fH1Size')?.value || 16),
                    h2Font: (document.getElementById('fH2Font')?.value || '黑体'),
                    h2Size: parseFloat(document.getElementById('fH2Size')?.value || 14),
                    h3Font: (document.getElementById('fH3Font')?.value || '黑体'),
                    h3Size: parseFloat(document.getElementById('fH3Size')?.value || 12),
                    bodyFont: (document.getElementById('fBFont')?.value || '宋体'),
                    westFont: (document.getElementById('fWFont')?.value || 'Times New Roman'),
                    bodySize: parseFloat(document.getElementById('fBSize')?.value || 12),
                    indent: parseFloat(document.getElementById('fIndent')?.value || 2),
                    lineHeight: parseFloat(document.getElementById('fLH')?.value || 1.5),
                    align: (document.getElementById('fAlign')?.value || 'justify'),
                    marginTop: parseFloat(document.getElementById('fMT')?.value || 2.5),
                    marginBottom: parseFloat(document.getElementById('fMB')?.value || 2.5),
                    marginLeft: parseFloat(document.getElementById('fML')?.value || 3.0),
                    marginRight: parseFloat(document.getElementById('fMR')?.value || 2.5),
                });
                const result = await window.pywebview.api.exportDocx(html, formatParams);
                const data = JSON.parse(result);
                if (data.success) showToast('已导出: ' + data.path + '（已应用排版参数）');
                else if (data.error) showToast('导出失败: ' + data.error);
            } catch(e) {
                console.error('exportDoc error:', e);
                showToast('导出失败');
            }
        };

        // 覆盖 callDoubao：使用 Python 代理通过 Supabase Edge Function
        window.callDoubao = async function(systemPrompt, userMessage, temperature) {
            try {
                const config = JSON.parse(localStorage.getItem('wc_ai_config') || '{}');
                const configStr = JSON.stringify({
                    model: config.model || 'doubao-seed-1-6-251015',
                    temperature: temperature || 0.3
                });
                const result = await window.pywebview.api.callAI(systemPrompt, userMessage, configStr);
                const data = JSON.parse(result);
                if (data.error) throw new Error(data.error);
                return data.content || '';
            } catch(e) {
                console.error('callDoubao bridge error:', e);
                throw e;
            }
        };

        // 新增：用户登录
        window.appLogin = async function(email, password) {
            try {
                const result = await window.pywebview.api.login(email, password);
                return JSON.parse(result);
            } catch(e) {
                console.error('login error:', e);
                return { success: false, error: '登录失败' };
            }
        };

        // 新增：用户登出
        window.appLogout = async function() {
            try {
                const result = await window.pywebview.api.logout();
                return JSON.parse(result);
            } catch(e) {
                console.error('logout error:', e);
                return { success: false, error: '登出失败' };
            }
        };

        // 新增：获取 Token 用量
        window.getTokenUsage = async function() {
            try {
                const result = await window.pywebview.api.getTokenUsage();
                return JSON.parse(result);
            } catch(e) {
                console.error('getTokenUsage error:', e);
                return { token_quota: 0, token_used: 0, token_remaining: 0 };
            }
        };

        // 新增：获取用户模板列表
        window.getUserTemplates = async function() {
            try {
                const result = await window.pywebview.api.getUserTemplates();
                return JSON.parse(result);
            } catch(e) {
                console.error('getUserTemplates error:', e);
                return { success: false, templates: [] };
            }
        };

        // 新增：运行质量检查
        window.appRunQA = async function(content, categories) {
            try {
                const cats = categories || ['typo', 'consistency', 'logic'];
                const result = await window.pywebview.api.runQA(content, JSON.stringify(cats));
                return JSON.parse(result);
            } catch(e) {
                console.error('runQA error:', e);
                return { success: false, error: 'QA 检查失败' };
            }
        };

        // 新增：运行交叉引用检查
        window.appRunXRef = async function(content) {
            try {
                const result = await window.pywebview.api.runXRef(content);
                return JSON.parse(result);
            } catch(e) {
                console.error('runXRef error:', e);
                return { success: false, error: '交叉引用检查失败' };
            }
        };

        // 新增：应用排版规则
        window.appApplyFormat = async function(content, rules) {
            try {
                const rulesStr = JSON.stringify(rules || {});
                const result = await window.pywebview.api.applyFormat(content, rulesStr);
                return JSON.parse(result);
            } catch(e) {
                console.error('applyFormat error:', e);
                return { success: false, error: '排版失败' };
            }
        };

        // 新增：保存文档
        window.appSaveDocument = async function(content, title) {
            try {
                const result = await window.pywebview.api.saveDocument(content, title || '未命名文档');
                return JSON.parse(result);
            } catch(e) {
                console.error('saveDocument error:', e);
                return { success: false, error: '保存失败' };
            }
        };

        // 新增：加载文档
        window.appLoadDocument = async function(docId) {
            try {
                const result = await window.pywebview.api.loadDocument(docId || 'current');
                return JSON.parse(result);
            } catch(e) {
                console.error('loadDocument error:', e);
                return { success: false, error: '加载失败' };
            }
        };

        // 新增：获取文档列表
        window.appGetDocumentList = async function() {
            try {
                const result = await window.pywebview.api.getDocumentList();
                return JSON.parse(result);
            } catch(e) {
                console.error('getDocumentList error:', e);
                return { success: false, documents: [] };
            }
        };

        console.log('Bridge functions overridden');
    } else {
        setTimeout(waitForPywebview, 100);
    }
}
waitForPywebview();
"""


def _get_resource_path(relative_path: str) -> str:
    """获取资源文件路径，兼容 PyInstaller 打包。"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def main() -> None:
    """应用入口。"""
    import webview

    api = Api()
    html_path = _get_resource_path(os.path.join("web", "index.html"))

    if not os.path.exists(html_path):
        print(f"错误: 找不到 {html_path}")
        sys.exit(1)

    window = webview.create_window(
        APP_TITLE,
        html_path,
        js_api=api,
        width=1440,
        height=900,
        min_size=(1024, 700),
    )
    api.set_window(window)

    # 页面加载完成后注入桥接 JS
    def on_loaded():
        window.evaluate_js(BRIDGE_JS)

    window.events.loaded += on_loaded

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("WordCraft Pro 启动 (pywebview)")

    webview.start(debug=False)


if __name__ == "__main__":
    main()
