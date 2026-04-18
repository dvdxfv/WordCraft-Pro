"""
模板管理器 (Template Manager)

管理预设排版模板和自定义模板的加载、保存、列表。
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Optional

from core.formatting_rules import FormattingRules


# 预设模板目录
_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")


class TemplateManager:
    """模板管理器"""

    def __init__(self, templates_dir: str = None):
        self.templates_dir = templates_dir or _TEMPLATES_DIR
        self.custom_dir = os.path.join(self.templates_dir, "custom")
        os.makedirs(self.custom_dir, exist_ok=True)

    def list_templates(self) -> list[dict]:
        """列出所有可用模板"""
        templates = []

        # 预设模板
        preset_dir = self.templates_dir
        if os.path.isdir(preset_dir):
            for f in os.listdir(preset_dir):
                if f.endswith((".yaml", ".yml")):
                    path = os.path.join(preset_dir, f)
                    try:
                        with open(path, "r", encoding="utf-8") as fh:
                            data = yaml.safe_load(fh)
                        if data and isinstance(data, dict):
                            templates.append({
                                "name": data.get("template_name", f),
                                "type": data.get("template_type", "custom"),
                                "file": f,
                                "path": path,
                                "is_custom": False,
                            })
                    except Exception:
                        continue

        # 自定义模板
        if os.path.isdir(self.custom_dir):
            for f in os.listdir(self.custom_dir):
                if f.endswith((".yaml", ".yml")):
                    path = os.path.join(self.custom_dir, f)
                    try:
                        with open(path, "r", encoding="utf-8") as fh:
                            data = yaml.safe_load(fh)
                        if data and isinstance(data, dict):
                            templates.append({
                                "name": data.get("template_name", f),
                                "type": data.get("template_type", "custom"),
                                "file": f,
                                "path": path,
                                "is_custom": True,
                            })
                    except Exception:
                        continue

        return templates

    def load_template(self, name: str) -> Optional[FormattingRules]:
        """按名称加载模板"""
        for tmpl in self.list_templates():
            if tmpl["name"] == name or tmpl["file"] == name:
                return self._load_from_file(tmpl["path"])
        return None

    def load_from_file(self, file_path: str) -> FormattingRules:
        """从文件路径加载模板"""
        return self._load_from_file(file_path)

    def save_template(self, rules: FormattingRules, name: str = None) -> str:
        """保存模板到自定义目录"""
        filename = name or rules.template_name or "custom_template"
        if not filename.endswith(".yaml"):
            filename += ".yaml"
        path = os.path.join(self.custom_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(rules.to_yaml())

        return path

    def delete_template(self, name: str) -> bool:
        """删除自定义模板"""
        for tmpl in self.list_templates():
            if tmpl["name"] == name and tmpl["is_custom"]:
                os.remove(tmpl["path"])
                return True
        return False

    def _load_from_file(self, file_path: str) -> FormattingRules:
        """从 YAML 文件加载"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return FormattingRules.from_yaml(content)
