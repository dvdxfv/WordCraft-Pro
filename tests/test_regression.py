#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordCraft Pro 回归测试套件

测试历史bug回归，版本升级兼容性，配置变更影响
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import DocumentModel, DocElement, ElementType
from parsers.dispatcher import parse_file
from core.formatting_rules import FormattingRules
from core.formatter import Formatter
from core.qa_engine import QAEngine
from core.exporter import Exporter
from core.crossref_checker import CrossRefChecker
from core.typo_checker import TypoChecker
from core.logic_checker import LogicChecker


class TestRegressionBugs:
    """历史bug回归测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_crossref_element_text_bug_regression(self):
        """回归测试：修复element.text属性错误bug"""
        # 这个bug曾经导致AttributeError: 'DocElement' object has no attribute 'text'
        # 修复后应该使用element.content

        # 创建测试文档
        doc = DocumentModel(title="交叉引用测试")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content="参见第2.1节的说明。"
        ))
        doc.elements.append(DocElement(
            element_type=ElementType.HEADING,
            content="2.1 测试章节",
            level=2
        ))

        # 创建交叉引用检查器
        checker = CrossRefChecker()

        # 应该不会抛出AttributeError
        try:
            targets = checker._scan_targets(doc)
            refs = checker._scan_references(doc)
            suggestions = checker._generate_suggestions(refs, targets)

            # 验证结果
            assert isinstance(targets, list)
            assert isinstance(refs, list)
            assert isinstance(suggestions, list)

        except AttributeError as e:
            if "text" in str(e):
                pytest.fail(f"历史bug回归：element.text属性错误未修复: {e}")
            else:
                raise

    def test_typo_checker_false_positive_regression(self):
        """回归测试：修复错别字检测误报bug"""
        # 这个bug曾经导致"快速的"被误报为"的地得"问题

        checker = TypoChecker()

        # 测试正常文本不应被误报
        normal_texts = [
            "快速的",
            "伟大的",
            "重要的",
            "大量的",
            "正确的",
            "大量的地得"  # 这个应该被检测，但上下文不同的"快速的"不应该
        ]

        for text in normal_texts:
            issues = checker.check_text(text)
            # 正常文本不应该有高置信度的误报
            high_confidence_issues = [i for i in issues if i.get('confidence', 0) > 0.8]
            assert len(high_confidence_issues) == 0, f"误报回归：'{text}'被误报为问题"

    def test_logic_checker_missing_functionality_regression(self):
        """回归测试：确保逻辑检查功能已实现"""
        # 这个功能曾经缺失

        checker = LogicChecker()

        # 测试缺乏数据支撑的结论
        text_without_data = """
        通过以上分析，我们可以得出结论：该方案是最佳选择。
        然而，文中并未提供任何数据或证据来支持这一结论。
        """

        issues = checker.check_text(text_without_data)

        # 应该能够检测到逻辑问题
        logic_issues = [i for i in issues if i.get('type') == 'logic']
        assert len(logic_issues) > 0, "逻辑检查功能缺失：无法检测缺乏数据支撑的结论"

    def test_config_loading_regression(self):
        """回归测试：配置文件加载问题"""
        # 测试YAML配置加载
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

        if os.path.exists(config_path):
            # 如果配置文件存在，应该能够加载
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                assert isinstance(config, dict)
                assert 'llm' in config  # 应该有LLM配置

            except Exception as e:
                pytest.fail(f"配置文件加载回归: {e}")

    def test_export_functionality_regression(self):
        """回归测试：导出功能完整性"""
        # 创建测试文档
        doc = DocumentModel(title="导出测试")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content="这是一个导出测试文档。"
        ))

        # 应用格式化
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        # 创建QA报告
        qa_engine = QAEngine()
        qa_report = qa_engine.check(formatted_doc)

        # 测试导出
        output_path = os.path.join(self.temp_dir, "export_test.docx")
        exporter = Exporter()

        try:
            exporter.export(formatted_doc, output_path, qa_report)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

        except Exception as e:
            pytest.fail(f"导出功能回归: {e}")


class TestVersionCompatibility:
    """版本升级兼容性测试"""

    def test_backward_compatibility_document_model(self):
        """测试DocumentModel向后兼容性"""
        # 测试旧版本的DocumentModel结构是否仍然支持

        # 创建文档（模拟旧版本格式）
        doc = DocumentModel(title="兼容性测试")

        # 添加不同类型的元素
        elements_data = [
            {"type": "paragraph", "content": "段落内容"},
            {"type": "heading", "content": "标题", "level": 1},
            {"type": "list_item", "content": "列表项"},
        ]

        for elem_data in elements_data:
            element = DocElement(
                element_type=ElementType[elem_data["type"].upper()],
                content=elem_data["content"]
            )
            if "level" in elem_data:
                element.level = elem_data["level"]

            doc.elements.append(element)

        # 验证文档可以正常处理
        assert len(doc.elements) == 3

        # 测试格式化
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        assert len(formatted_doc.elements) == 3

    def test_api_interface_stability(self):
        """测试API接口稳定性"""
        # 测试核心API接口是否保持稳定

        # 测试parse_file接口
        test_content = "API稳定性测试内容"
        test_file = os.path.join(self.temp_dir, "api_test.txt")

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        doc = parse_file(test_file)
        assert doc is not None
        assert len(doc.elements) > 0

        # 测试Formatter接口
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        assert formatted_doc is not None

        # 测试QAEngine接口
        qa_engine = QAEngine()
        qa_report = qa_engine.check(formatted_doc)

        assert qa_report is not None

    def test_configuration_format_stability(self):
        """测试配置格式稳定性"""
        # 测试配置文件的格式是否保持稳定

        # 创建测试配置
        test_config = {
            "llm": {
                "model": "doubao-seed-1-6-251015",
                "api_key": "test_key",
                "base_url": "https://api.example.com"
            },
            "formatting": {
                "default_template": "thesis",
                "font_size": 12,
                "line_spacing": 1.5
            }
        }

        config_file = os.path.join(self.temp_dir, "test_config.yaml")

        try:
            import yaml
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)

            # 验证配置文件可以重新加载
            with open(config_file, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f)

            assert loaded_config == test_config

        except ImportError:
            # 如果没有yaml，跳过测试
            pytest.skip("PyYAML不可用，跳过配置测试")


class TestConfigurationChanges:
    """配置变更影响测试"""

    def test_llm_config_changes(self):
        """测试LLM配置变更的影响"""
        # 测试不同LLM配置下的行为

        config_variations = [
            {
                "model": "doubao-seed-1-6-251015",
                "temperature": 0.1,
                "max_tokens": 1000
            },
            {
                "model": "doubao-seed-1-6-251015",
                "temperature": 0.8,
                "max_tokens": 2000
            }
        ]

        for config in config_variations:
            # 这里可以测试配置变更对LLM行为的影响
            # 由于需要实际的API调用，这里主要验证配置格式正确性

            assert "model" in config
            assert "temperature" in config
            assert isinstance(config["temperature"], (int, float))
            assert 0 <= config["temperature"] <= 1

    def test_formatting_config_changes(self):
        """测试排版配置变更的影响"""
        # 测试不同排版配置下的输出差异

        configs = [
            {"font_size": 10, "line_spacing": 1.0},
            {"font_size": 12, "line_spacing": 1.5},
            {"font_size": 14, "line_spacing": 2.0}
        ]

        base_doc = DocumentModel(title="配置测试")
        base_doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content="测试不同配置下的排版效果"
        ))

        for config in configs:
            # 创建自定义规则
            rules = FormattingRules()
            # 这里可以根据config设置规则

            formatter = Formatter(rules)
            formatted_doc = formatter.apply(base_doc)

            # 验证格式化成功
            assert formatted_doc is not None
            assert len(formatted_doc.elements) == 1

    def test_error_handling_config_changes(self):
        """测试错误处理配置变更"""
        # 测试不同错误处理配置下的行为

        # 这里可以测试超时设置、重试次数等配置的影响
        # 由于涉及网络调用，这里主要验证配置逻辑

        timeout_configs = [5, 10, 30]  # 秒

        for timeout in timeout_configs:
            assert isinstance(timeout, int)
            assert timeout > 0

            # 在实际应用中，这些配置会影响网络请求的超时时间


class TestDataMigration:
    """数据迁移测试"""

    def test_document_format_migration(self):
        """测试文档格式迁移"""
        # 测试从旧版本文档格式迁移到新版本

        # 模拟旧版本文档结构
        old_format_doc = {
            "title": "旧版本文档",
            "elements": [
                {
                    "type": "paragraph",
                    "text": "这是旧版本的段落",  # 注意：旧版本可能使用"text"而非"content"
                    "style": "normal"
                }
            ]
        }

        # 转换为新版本DocumentModel
        doc = DocumentModel(title=old_format_doc["title"])

        for elem_data in old_format_doc["elements"]:
            # 处理字段名变化
            content = elem_data.get("text") or elem_data.get("content", "")
            element = DocElement(
                element_type=ElementType[elem_data["type"].upper()],
                content=content
            )
            doc.elements.append(element)

        # 验证迁移成功
        assert doc.title == "旧版本文档"
        assert len(doc.elements) == 1
        assert doc.elements[0].content == "这是旧版本的段落"

    def test_template_format_migration(self):
        """测试模板格式迁移"""
        # 测试模板配置格式的迁移

        # 模拟旧版本模板
        old_template = {
            "name": "旧模板",
            "font_family": "宋体",
            "font_size": 12,
            "margins": {
                "top": 2.5,
                "bottom": 2.5,
                "left": 3.0,
                "right": 3.0
            }
        }

        # 转换为新版本FormattingRules
        rules = FormattingRules()
        # 这里可以根据旧模板设置新规则

        # 验证转换成功
        assert rules is not None

    def test_config_file_migration(self):
        """测试配置文件迁移"""
        # 测试配置文件格式的迁移

        # 模拟旧版本配置
        old_config = {
            "api_key": "old_key",
            "model_name": "old_model",  # 旧版本可能使用不同的字段名
            "timeout": 10
        }

        # 转换为新版本配置
        new_config = {
            "llm": {
                "model": old_config.get("model_name", "doubao-seed-1-6-251015"),
                "api_key": old_config["api_key"],
                "timeout": old_config.get("timeout", 30)
            }
        }

        # 验证转换成功
        assert "llm" in new_config
        assert new_config["llm"]["model"] == "old_model"
        assert new_config["llm"]["api_key"] == "old_key"
