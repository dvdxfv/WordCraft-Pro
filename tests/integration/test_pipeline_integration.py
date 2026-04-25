# -*- coding: utf-8 -*-
"""Integration pipeline tests (non-browser)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.document_model import ElementType
from core.exporter import Exporter
from core.formatter import Formatter
from core.formatting_rules import FormattingRules
from core.qa_engine import QAEngine
from core.template_manager import TemplateManager
from parsers.dispatcher import parse_file


@pytest.mark.integration
class TestPipelineIntegration:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.template_mgr = TemplateManager()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_pipeline_with_txt(self):
        doc_path = self._create_test_txt()
        doc = parse_file(doc_path)
        assert doc is not None
        assert len(doc.elements) > 0

        formatter = Formatter(FormattingRules())
        formatted_doc = formatter.apply(doc)

        qa_report = QAEngine().check(formatted_doc)
        output_path = os.path.join(self.temp_dir, "output_from_txt.docx")
        Exporter().export(formatted_doc, output_path, qa_report)

        assert os.path.exists(output_path)

    def test_full_pipeline_with_md(self):
        doc_path = self._create_test_md()
        doc = parse_file(doc_path)
        assert doc is not None
        headings = [e for e in doc.elements if e.element_type == ElementType.HEADING]
        assert len(headings) > 0

        formatter = Formatter(FormattingRules())
        formatted_doc = formatter.apply(doc)
        qa_report = QAEngine().check(formatted_doc)

        output_path = os.path.join(self.temp_dir, "output_from_md.docx")
        Exporter().export(formatted_doc, output_path, qa_report)
        assert os.path.exists(output_path)

    def test_template_application_pipeline(self):
        doc_path = self._create_test_txt()
        doc = parse_file(doc_path)
        templates = ["thesis", "gov", "report"]
        results = {}

        for template_name in templates:
            try:
                rules = self.template_mgr.load_template(template_name)
                formatted_doc = Formatter(rules).apply(doc)
                assert formatted_doc.page_setup.paper_size is not None
                results[template_name] = True
            except Exception:
                results[template_name] = False

        assert any(results.values()), f"all templates failed: {results}"

    def _create_test_txt(self):
        content = """# 测试文档

这是一个测试文档，用于端到端集成测试。

## 第一章 引言

项目背景介绍。
"""
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def _create_test_md(self):
        content = """# 测试文档

这是一个测试Markdown文档。

## 第一章

### 1.1 节标题
"""
        file_path = os.path.join(self.temp_dir, "test.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

