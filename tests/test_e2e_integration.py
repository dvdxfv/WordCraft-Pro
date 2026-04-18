#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordCraft Pro 端到端集成测试

测试完整业务流程：文件上传 → 解析 → 排版 → QA检查 → 导出
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import DocumentModel, DocElement, ElementType
from parsers.dispatcher import parse_file
from core.formatting_rules import FormattingRules
from core.formatter import Formatter
from core.qa_engine import QAEngine
from core.exporter import Exporter
from core.template_manager import TemplateManager


class TestEndToEndIntegration:
    """端到端集成测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.template_mgr = TemplateManager()

    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_pipeline_with_docx(self):
        """测试完整的DOCX文件处理流程"""
        # 1. 创建测试文档
        doc_path = self._create_test_docx()

        # 2. 解析文档
        doc = parse_file(doc_path)
        assert doc is not None
        assert len(doc.elements) > 0
        assert doc.title == "测试文档"

        # 3. 应用排版规则
        rules = self.template_mgr.load_template("thesis")
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        # 验证排版应用
        assert formatted_doc.page_setup.paper_size is not None

        # 4. 运行QA检查
        qa_engine = QAEngine()
        qa_report = qa_engine.check(formatted_doc)

        # 验证QA报告
        assert qa_report is not None
        assert hasattr(qa_report, 'issues')
        assert hasattr(qa_report, 'summary')

        # 5. 导出文档
        output_path = os.path.join(self.temp_dir, "output.docx")
        exporter = Exporter()
        exporter.export(formatted_doc, output_path, qa_report)

        # 验证导出文件
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        # 6. 验证导出的文档可以重新解析
        re_parsed_doc = parse_file(output_path)
        assert re_parsed_doc is not None
        assert len(re_parsed_doc.elements) > 0

    def test_full_pipeline_with_txt(self):
        """测试完整的TXT文件处理流程"""
        # 1. 创建测试文档
        doc_path = self._create_test_txt()

        # 2. 解析文档
        doc = parse_file(doc_path)
        assert doc is not None
        assert len(doc.elements) > 0

        # 3. 应用排版规则
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        # 4. 运行QA检查
        qa_engine = QAEngine()
        qa_report = qa_engine.check(formatted_doc)

        # 5. 导出文档
        output_path = os.path.join(self.temp_dir, "output_from_txt.docx")
        exporter = Exporter()
        exporter.export(formatted_doc, output_path, qa_report)

        # 验证导出文件
        assert os.path.exists(output_path)

    def test_full_pipeline_with_md(self):
        """测试完整的Markdown文件处理流程"""
        # 1. 创建测试文档
        doc_path = self._create_test_md()

        # 2. 解析文档
        doc = parse_file(doc_path)
        assert doc is not None
        assert len(doc.elements) > 0

        # 验证Markdown解析结果
        headings = [e for e in doc.elements if e.element_type == ElementType.HEADING]
        assert len(headings) > 0

        # 3. 应用排版规则并导出
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        qa_engine = QAEngine()
        qa_report = qa_engine.check(formatted_doc)

        output_path = os.path.join(self.temp_dir, "output_from_md.docx")
        exporter = Exporter()
        exporter.export(formatted_doc, output_path, qa_report)

        assert os.path.exists(output_path)

    def test_batch_processing_workflow(self):
        """测试批量文件处理工作流"""
        # 创建多个测试文件
        file_paths = []
        for i in range(3):
            doc_path = self._create_test_docx(f"batch_test_{i}.docx")
            file_paths.append(doc_path)

        # 批量处理
        processed_docs = []
        for path in file_paths:
            doc = parse_file(path)
            assert doc is not None

            # 应用统一排版规则
            rules = FormattingRules()
            formatter = Formatter(rules)
            formatted_doc = formatter.apply(doc)

            processed_docs.append(formatted_doc)

        # 验证批量处理结果
        assert len(processed_docs) == 3
        for doc in processed_docs:
            assert len(doc.elements) > 0

    def test_template_application_pipeline(self):
        """测试模板应用完整流程"""
        # 1. 创建测试文档
        doc_path = self._create_test_docx()

        # 2. 解析文档
        doc = parse_file(doc_path)

        # 3. 加载并应用不同模板
        templates = ["thesis", "gov", "report"]
        results = {}

        for template_name in templates:
            try:
                rules = self.template_mgr.load_template(template_name)
                formatter = Formatter(rules)
                formatted_doc = formatter.apply(doc)

                # 验证模板应用效果
                assert formatted_doc.page_setup.paper_size is not None

                results[template_name] = True
            except Exception as e:
                results[template_name] = False
                print(f"模板 {template_name} 应用失败: {e}")

        # 至少一个模板应该成功应用
        assert any(results.values()), f"所有模板应用都失败: {results}"

    def _create_test_docx(self, filename="test.docx"):
        """创建测试DOCX文件"""
        # 这里简化创建，使用现有的测试文件或创建临时文件
        # 实际实现中可能需要使用python-docx创建测试文档
        test_file = os.path.join(os.path.dirname(__file__), "test_files", "sample.docx")
        if os.path.exists(test_file):
            target_path = os.path.join(self.temp_dir, filename)
            shutil.copy(test_file, target_path)
            return target_path

        # 如果没有测试文件，创建一个简单的文本文件作为替代
        txt_path = self._create_test_txt()
        # 将txt转换为docx的逻辑可以在这里实现
        return txt_path

    def _create_test_txt(self):
        """创建测试TXT文件"""
        content = """# 测试文档

这是一个测试文档，用于端到端集成测试。

## 第一章 引言

项目背景介绍。

### 1.1 项目目标

- 实现文档智能排版
- 提供质量检查功能
- 支持多种文件格式

## 第二章 系统设计

系统架构设计说明。

### 2.1 总体架构

系统采用分层架构设计。

## 结论

项目实施完成后，将能够有效提高文档处理效率。
"""

        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def _create_test_md(self):
        """创建测试Markdown文件"""
        content = """# 测试文档

这是一个测试Markdown文档。

## 第一章

### 1.1 节标题

内容段落。

## 第二章

- 列表项1
- 列表项2

| 表头1 | 表头2 |
|-------|-------|
| 数据1 | 数据2 |

> 引用内容

**粗体文本** 和 *斜体文本*。

## 结论

测试文档结束。
"""

        file_path = os.path.join(self.temp_dir, "test.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path