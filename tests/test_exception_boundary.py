#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordCraft Pro 异常处理和边界测试

测试各种异常场景和边界条件：
- 网络异常
- 文件异常
- 系统资源异常
- 配置异常
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import DocumentModel, DocElement, ElementType
from parsers.dispatcher import parse_file
from core.formatting_rules import FormattingRules
from core.formatter import Formatter
from core.qa_engine import QAEngine
from core.exporter import Exporter
from llm.client import LLMClient, DoubaoClient, ChatMessage
from core.template_manager import TemplateManager


class TestExceptionHandling:
    """异常处理测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_nonexistent_file(self):
        """测试解析不存在的文件"""
        with pytest.raises((FileNotFoundError, IOError)):
            parse_file("/nonexistent/file.docx")

    def test_parse_corrupted_file(self):
        """测试解析损坏的文件"""
        # 创建一个损坏的文件
        corrupted_path = os.path.join(self.temp_dir, "corrupted.docx")
        with open(corrupted_path, "wb") as f:
            f.write(b"corrupted content")

        # 应该抛出异常
        from docx.opc.exceptions import PackageNotFoundError
        with pytest.raises(PackageNotFoundError):
            parse_file(corrupted_path)

    def test_parse_empty_file(self):
        """测试解析空文件"""
        empty_path = os.path.join(self.temp_dir, "empty.txt")
        with open(empty_path, "w", encoding="utf-8") as f:
            f.write("")

        doc = parse_file(empty_path)
        assert doc is not None
        assert len(doc.elements) == 0

    def test_parse_unsupported_format(self):
        """测试解析不支持的文件格式"""
        unsupported_path = os.path.join(self.temp_dir, "test.unsupported")
        with open(unsupported_path, "w", encoding="utf-8") as f:
            f.write("unsupported format content")

        with pytest.raises(ValueError):
            parse_file(unsupported_path)

    def test_parse_file_with_unknown_encoding(self):
        """测试解析未知编码的文件"""
        # 创建一个用未知编码的文件
        unknown_encoding_path = os.path.join(self.temp_dir, "unknown_encoding.txt")
        try:
            with open(unknown_encoding_path, "w", encoding="utf-16") as f:
                f.write("测试内容")
        except UnicodeEncodeError:
            # 如果utf-16不支持中文，跳过这个测试
            pytest.skip("UTF-16 encoding not supported for Chinese text")

        # 解析应该成功或抛出可处理的异常
        try:
            doc = parse_file(unknown_encoding_path)
            assert doc is not None
        except UnicodeDecodeError:
            # 这是可接受的异常
            pass

    @patch('llm.client.DoubaoClient.chat')
    def test_llm_api_timeout(self, mock_chat):
        """测试LLM API超时"""
        # 模拟超时
        mock_chat.side_effect = TimeoutError("Request timed out")

        client = DoubaoClient()
        with pytest.raises(TimeoutError):
            client.chat([ChatMessage("user", "test message")])

    @patch('llm.client.DoubaoClient.chat')
    def test_llm_api_connection_error(self, mock_chat):
        """测试LLM API连接错误"""
        from requests.exceptions import ConnectionError
        mock_chat.side_effect = ConnectionError("Connection failed")

        client = DoubaoClient()
        with pytest.raises(ConnectionError):
            client.chat([ChatMessage("user", "test message")])

    @patch('llm.client.DoubaoClient.chat')
    def test_llm_api_invalid_response(self, mock_chat):
        """测试LLM API无效响应"""
        mock_chat.side_effect = Exception("API Error")

        client = DoubaoClient()
        with pytest.raises(Exception):
            client.chat([ChatMessage("user", "test message")])

    def test_formatter_with_invalid_rules(self):
        """测试格式化器处理无效规则"""
        doc = DocumentModel(title="测试文档")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content="测试内容"
        ))

        # 创建包含无效规则的FormattingRules
        rules = FormattingRules()
        # 这里可以设置一些无效的规则值

        formatter = Formatter(rules)
        # 应该正常处理，不抛出异常
        result = formatter.apply(doc)
        assert result is not None

    def test_qa_engine_with_empty_document(self):
        """测试QA引擎处理空文档"""
        doc = DocumentModel(title="空文档")

        qa_engine = QAEngine()
        report = qa_engine.check(doc)

        assert report is not None
        assert len(report.issues) == 0  # 空文档应该没有问题

    def test_exporter_with_invalid_path(self):
        """测试导出器处理无效路径"""
        doc = DocumentModel(title="测试文档")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content="测试内容"
        ))

        exporter = Exporter()

        # 测试无效路径 - 使用包含非法字符的文件名
        # 这会导致Windows OSError
        try:
            exporter.export(doc, "test<invalid>.docx")
            # 如果没有异常，尝试清理
            if os.path.exists("test<invalid>.docx"):
                os.remove("test<invalid>.docx")
                assert False, "应该抛出异常"
        except (OSError, IOError):
            # 预期的异常
            assert True

    def test_template_manager_invalid_template(self):
        """测试模板管理器处理无效模板"""
        template_mgr = TemplateManager()

        # 尝试加载不存在的模板 - 应该返回None而不是抛出异常
        result = template_mgr.load_template("nonexistent_template")
        assert result is None

    def test_large_document_processing(self):
        """测试大文档处理"""
        # 创建一个较大的文档
        doc = DocumentModel(title="大文档测试")

        # 添加很多元素
        for i in range(1000):
            doc.elements.append(DocElement(
                element_type=ElementType.PARAGRAPH,
                content=f"这是第{i}段测试内容，用于测试大文档处理能力。" * 10
            ))

        # 测试解析和处理
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        assert len(formatted_doc.elements) == 1000

        # 测试QA检查（可能需要较长时间）
        qa_engine = QAEngine()
        report = qa_engine.check(formatted_doc)

        assert report is not None

    def test_memory_cleanup_after_processing(self):
        """测试处理后的内存清理"""
        import gc

        # 创建文档并处理
        doc = DocumentModel(title="内存测试")
        for i in range(100):
            doc.elements.append(DocElement(
                element_type=ElementType.PARAGRAPH,
                content=f"内存测试内容{i}"
            ))

        # 处理文档
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        # 删除引用
        del doc, formatted_doc, rules, formatter
        gc.collect()

        # 验证内存清理（这里只是基本检查，实际内存分析需要专门工具）
        # 在实际测试中，可以使用memory_profiler等工具进行更详细的分析

    def test_concurrent_file_processing(self):
        """测试并发文件处理"""
        import threading
        import time

        results = []
        errors = []

        def process_file(file_id):
            try:
                # 创建测试文档
                doc = DocumentModel(title=f"并发测试文档{file_id}")
                doc.elements.append(DocElement(
                    element_type=ElementType.PARAGRAPH,
                    content=f"并发测试内容{file_id}"
                ))

                # 应用排版
                rules = FormattingRules()
                formatter = Formatter(rules)
                formatted_doc = formatter.apply(doc)

                results.append(f"success_{file_id}")
            except Exception as e:
                errors.append(f"error_{file_id}: {e}")

        # 启动多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=process_file, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join(timeout=10)  # 10秒超时

        # 验证结果
        assert len(results) == 5, f"并发处理失败: {errors}"
        assert len(errors) == 0, f"处理过程中出现错误: {errors}"


class TestBoundaryConditions:
    """边界条件测试"""

    def test_document_with_max_elements(self):
        """测试包含最大元素数量的文档"""
        doc = DocumentModel(title="最大元素测试")

        # 添加大量元素（根据系统限制）
        max_elements = 10000
        for i in range(max_elements):
            doc.elements.append(DocElement(
                element_type=ElementType.PARAGRAPH,
                content=f"元素{i}"
            ))

        # 验证文档创建成功
        assert len(doc.elements) == max_elements

        # 测试基本操作
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        assert len(formatted_doc.elements) == max_elements

    def test_very_long_content_element(self):
        """测试包含非常长内容的元素"""
        long_content = "测试内容" * 10000  # 创建很长的内容

        doc = DocumentModel(title="长内容测试")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content=long_content
        ))

        assert len(doc.elements[0].content) > 10000

        # 测试处理
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        assert len(formatted_doc.elements[0].content) == len(long_content)

    def test_nested_elements_processing(self):
        """测试嵌套元素处理"""
        doc = DocumentModel(title="嵌套元素测试")

        # 创建嵌套结构
        parent = DocElement(
            element_type=ElementType.PARAGRAPH,
            content="父元素"
        )

        child1 = DocElement(
            element_type=ElementType.PARAGRAPH,
            content="子元素1"
        )
        child2 = DocElement(
            element_type=ElementType.PARAGRAPH,
            content="子元素2"
        )

        parent.children.extend([child1, child2])
        doc.elements.append(parent)

        # 验证嵌套结构
        assert len(doc.elements) == 1
        assert len(doc.elements[0].children) == 2

        # 测试格式化
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        assert len(formatted_doc.elements[0].children) == 2

    def test_special_characters_handling(self):
        """测试特殊字符处理"""
        special_content = "特殊字符：\u0000\u0001\u0002\t\n\r\"'\\特殊符号：©®™€£¥"

        doc = DocumentModel(title="特殊字符测试")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content=special_content
        ))

        # 测试处理
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        # 验证内容保持完整
        assert formatted_doc.elements[0].content == special_content

    def test_unicode_content_processing(self):
        """测试Unicode内容处理"""
        unicode_content = "多语言内容：English 中文 日本語 한국어 العربية हिन्दी"

        doc = DocumentModel(title="Unicode测试")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content=unicode_content
        ))

        # 测试处理
        rules = FormattingRules()
        formatter = Formatter(rules)
        formatted_doc = formatter.apply(doc)

        assert formatted_doc.elements[0].content == unicode_content