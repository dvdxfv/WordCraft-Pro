"""
AutoCorrect 增强检查器（空格/标点规范）。

调用 `autocorrect --lint --format json` 作为规范层：
- 安装了 autocorrect CLI 时生效；
- 未安装时自动降级，不影响主流程。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any

from core.document_model import DocumentModel
from core.qa_models import QAIssue, QAReport, IssueCategory, IssueSeverity


class AutoCorrectChecker:
    """基于 autocorrect CLI 的规范检查器。"""

    def __init__(self):
        self.enabled = True
        self.min_confidence = 0.7
        self.command = "autocorrect"
        self._available = None

    def check(self, doc: DocumentModel) -> QAReport:
        report = QAReport()
        if not self.enabled:
            return report
        if not self._ensure_available():
            return report

        lines = [(elem.content or "") for elem in doc.elements]
        if not any(line.strip() for line in lines):
            return report

        diagnostics = self._run_lint(lines)
        for d in diagnostics:
            issue = self._diag_to_issue(d, lines)
            if issue is None:
                continue
            if issue.confidence < self.min_confidence:
                continue
            report.add_issue(issue)

        return report

    def _ensure_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            proc = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            self._available = proc.returncode == 0
        except Exception:
            self._available = False
        return self._available

    def _run_lint(self, lines: list[str]) -> list[dict[str, Any]]:
        text = "\n".join(lines)
        fd, temp_path = tempfile.mkstemp(
            prefix="wc_autocorrect_",
            suffix=".txt",
            dir=os.getcwd(),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)

            proc = subprocess.run(
                [self.command, "--lint", "--format", "json", temp_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
            # lint 发现问题时可能返回非 0，仍尽量解析 stdout
            payload = proc.stdout.strip() or proc.stderr.strip()
            if not payload:
                return []
            parsed = json.loads(payload)
            return self._extract_diagnostics(parsed)
        except Exception:
            return []
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _extract_diagnostics(self, payload: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        def walk(node: Any):
            if isinstance(node, dict):
                # autocorrect 原生 JSON: {"messages":[{"filepath":"..","lines":[{"l":1,"c":1,"old":"..","new":"..","severity":1}]}]}
                if "lines" in node and isinstance(node["lines"], list):
                    for line_entry in node["lines"]:
                        if isinstance(line_entry, dict):
                            merged = dict(line_entry)
                            merged["filepath"] = node.get("filepath", "")
                            out.append(merged)
                has_line = any(k in node for k in ("line", "start_line", "row"))
                has_msg = any(k in node for k in ("message", "detail", "title"))
                if has_line and has_msg:
                    out.append(node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(payload)
        return out

    def _diag_to_issue(self, d: dict[str, Any], lines: list[str]) -> QAIssue | None:
        line = int(d.get("line") or d.get("start_line") or d.get("row") or d.get("l") or 1)
        col = int(d.get("column") or d.get("start_col") or d.get("col") or d.get("c") or 1)
        raw_sev = d.get("severity") or d.get("level") or "warning"
        if isinstance(raw_sev, int):
            sev = "error" if raw_sev == 1 else "warning"
        else:
            sev = str(raw_sev).lower()
        old_text = str(d.get("old") or "")
        new_text = str(d.get("new") or "")
        message = str(d.get("message") or d.get("detail") or d.get("title") or "AutoCorrect lint issue")
        if old_text or new_text:
            message = f'建议规范化："{old_text}" -> "{new_text}"'
        replace_with = str(
            d.get("replacement")
            or d.get("replace")
            or d.get("new")
            or d.get("suggestion")
            or ""
        )

        # 过滤：跳过中英文/数字间的空格建议（项目规范：中英文/数字间都不加空格）
        import re
        if old_text and new_text:
            # 跳过"数字+空格+中文"的建议（如"204.94 万吨" → "204.94万吨"）
            if re.search(r'[\d.]+\s+[一-鿿]', new_text) and re.search(r'[\d.]+[一-鿿]', old_text):
                return None
            # 跳过"中文+空格+数字"的建议（如"年份 2022" → "年份2022"）
            if re.search(r'[一-鿿]\s+[\d.]', new_text) and re.search(r'[一-鿿][\d.]', old_text):
                return None
            # 跳过"中文+空格+英文"的建议
            if re.search(r'[一-鿿]\s+[a-zA-Z]', new_text) and re.search(r'[一-鿿][a-zA-Z]', old_text):
                return None
            # 跳过"英文+空格+中文"的建议
            if re.search(r'[a-zA-Z]\s+[一-鿿]', new_text) and re.search(r'[a-zA-Z][一-鿿]', old_text):
                return None

        element_index = max(0, min(len(lines) - 1, line - 1))
        line_text = lines[element_index] if lines else ""
        snippet = old_text.strip() or line_text[max(0, col - 1): max(0, col + 9)].strip() or line_text[:20].strip()

        severity = IssueSeverity.WARNING if sev in ("error", "warning") else IssueSeverity.INFO

        # 根据具体内容识别问题分类
        problem_type = self._classify_problem(old_text, new_text, message)

        if old_text and new_text:
            title = f'建议规范化（{problem_type}）："{old_text[:16]}"'
        else:
            title = f"文案{problem_type}"

        return QAIssue(
            category=IssueCategory.FORMAT,
            severity=severity,
            title=title,
            description=message,
            suggestion=replace_with,
            rule_id="autocorrect.lint",
            checker="autocorrect_checker",
            element_index=element_index,
            element_type="paragraph",
            location_text=snippet,
            start_pos=max(0, col - 1),
            end_pos=max(0, col),
            confidence=0.82,
        )

    def _classify_problem(self, old_text: str, new_text: str, message: str) -> str:
        """识别具体的规范问题类型"""
        import re

        # 中英文间空格问题
        if re.search(r'[a-zA-Z\d]\s+[一-鿿]|[一-鿿]\s+[a-zA-Z\d]', new_text):
            return "中英文空格规范"

        # 标点混用：英文标点 vs 中文标点
        en_punct = set(',.!?;:\'"')
        cn_punct = set('，。！？；：''""')
        if any(p in new_text for p in en_punct) or any(p in new_text for p in cn_punct):
            return "标点规范"

        # 重复空格
        if '  ' in new_text or '   ' in old_text:
            return "空格规范"

        # 大小写规范
        if old_text.lower() != new_text.lower():
            return "大小写规范"

        # 默认
        return "文案规范"
