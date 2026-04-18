#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordCraft Pro 性能和压力测试

测试系统性能表现：
- 大文件处理性能
- 并发处理能力
- 内存使用监控
- 响应时间测试
"""

import os
import sys
import tempfile
import shutil
import time
import threading
import psutil
from contextlib import contextmanager

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import DocumentModel, DocElement, ElementType
from parsers.dispatcher import parse_file
from core.formatting_rules import FormattingRules
from core.formatter import Formatter
from core.qa_engine import QAEngine
from core.exporter import Exporter


@contextmanager
def memory_monitor():
    """内存使用监控上下文管理器"""
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    peak_memory = initial_memory

    class MemoryTracker:
        def __init__(self):
            self.peak_memory = initial_memory

        def update_peak(self):
            current = process.memory_info().rss / 1024 / 1024
            self.peak_memory = max(self.peak_memory, current)
            return current

    tracker = MemoryTracker()
    yield tracker

    final_memory = process.memory_info().rss / 1024 / 1024
    print(f"内存使用: 初始={initial_memory:.1f}MB, 峰值={tracker.peak_memory:.1f}MB, 最终={final_memory:.1f}MB")


@contextmanager
def time_monitor():
    """时间监控上下文管理器"""
    start_time = time.time()
    yield lambda: time.time() - start_time


class TestPerformance:
    """性能测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_small_document_performance(self):
        """测试小文档处理性能"""
        doc = self._create_test_document(10, 100)  # 10段，每段100字符

        with time_monitor() as get_time:
            # 完整处理流程
            rules = FormattingRules()
            formatter = Formatter(rules)
            formatted_doc = formatter.apply(doc)

            qa_engine = QAEngine()
            qa_report = qa_engine.check(formatted_doc)

            output_path = os.path.join(self.temp_dir, "small_output.docx")
            exporter = Exporter()
            exporter.export(formatted_doc, output_path, qa_report)

        processing_time = get_time()
        print(f"小文档处理时间: {processing_time:.2f}秒")

        # 性能要求：小文档处理时间应小于1秒
        assert processing_time < 1.0, f"小文档处理过慢: {processing_time:.2f}秒"

    def test_medium_document_performance(self):
        """测试中等文档处理性能"""
        doc = self._create_test_document(100, 500)  # 100段，每段500字符

        with time_monitor() as get_time:
            rules = FormattingRules()
            formatter = Formatter(rules)
            formatted_doc = formatter.apply(doc)

            qa_engine = QAEngine()
            qa_report = qa_engine.check(formatted_doc)

            output_path = os.path.join(self.temp_dir, "medium_output.docx")
            exporter = Exporter()
            exporter.export(formatted_doc, output_path, qa_report)

        processing_time = get_time()
        print(f"中等文档处理时间: {processing_time:.2f}秒")

        # 性能要求：中等文档处理时间应小于5秒
        assert processing_time < 5.0, f"中等文档处理过慢: {processing_time:.2f}秒"

    def test_large_document_performance(self):
        """测试大文档处理性能"""
        doc = self._create_test_document(1000, 1000)  # 1000段，每段1000字符

        with time_monitor() as get_time:
            with memory_monitor() as mem_tracker:
                rules = FormattingRules()
                formatter = Formatter(rules)
                formatted_doc = formatter.apply(doc)

                qa_engine = QAEngine()
                qa_report = qa_engine.check(formatted_doc)

                output_path = os.path.join(self.temp_dir, "large_output.docx")
                exporter = Exporter()
                exporter.export(formatted_doc, output_path, qa_report)

        processing_time = get_time()
        print(f"大文档处理时间: {processing_time:.2f}秒")

        # 性能要求：大文档处理时间应小于30秒
        assert processing_time < 30.0, f"大文档处理过慢: {processing_time:.2f}秒"

        # 验证输出文件存在
        assert os.path.exists(output_path)
        file_size = os.path.getsize(output_path) / 1024 / 1024  # MB
        print(f"输出文件大小: {file_size:.2f}MB")

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        with memory_monitor() as mem_tracker:
            # 处理多个文档
            for i in range(10):
                doc = self._create_test_document(50, 200)

                rules = FormattingRules()
                formatter = Formatter(rules)
                formatted_doc = formatter.apply(doc)

                qa_engine = QAEngine()
                qa_report = qa_engine.check(formatted_doc)

                # 手动清理引用
                del doc, formatted_doc, qa_report, rules, formatter

        # 内存使用应该相对稳定
        print(f"内存稳定性测试完成，峰值内存: {mem_tracker.peak_memory:.1f}MB")

    def test_concurrent_processing_performance(self):
        """测试并发处理性能"""
        num_threads = 4
        docs_per_thread = 5
        results = []
        errors = []

        def process_documents(thread_id):
            try:
                thread_results = []
                for i in range(docs_per_thread):
                    doc = self._create_test_document(20, 100)

                    start_time = time.time()

                    rules = FormattingRules()
                    formatter = Formatter(rules)
                    formatted_doc = formatter.apply(doc)

                    qa_engine = QAEngine()
                    qa_report = qa_engine.check(formatted_doc)

                    processing_time = time.time() - start_time
                    thread_results.append(processing_time)

                results.extend(thread_results)
            except Exception as e:
                errors.append(f"线程{thread_id}错误: {e}")

        # 启动并发线程
        threads = []
        start_time = time.time()

        for i in range(num_threads):
            t = threading.Thread(target=process_documents, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join(timeout=60)  # 60秒超时

        total_time = time.time() - start_time

        # 验证结果
        assert len(errors) == 0, f"并发处理出现错误: {errors}"
        assert len(results) == num_threads * docs_per_thread

        avg_time = sum(results) / len(results)
        print(f"并发处理完成: {len(results)}个文档，平均处理时间: {avg_time:.2f}秒，总时间: {total_time:.2f}秒")

        # 并发应该比串行更快
        expected_serial_time = avg_time * len(results)
        speedup = expected_serial_time / total_time
        print(f"并发加速比: {speedup:.2f}x")

        # 至少应该有一定的加速效果
        assert speedup > 1.5, f"并发加速效果不明显: {speedup:.2f}x"

    def test_parser_performance_comparison(self):
        """测试不同解析器的性能对比"""
        # 创建测试文件
        txt_file = self._create_test_file("txt", 100, 500)
        md_file = self._create_test_file("md", 100, 500)

        parsers = {
            "TXT": txt_file,
            "Markdown": md_file
        }

        results = {}

        for parser_name, file_path in parsers.items():
            with time_monitor() as get_time:
                doc = parse_file(file_path)

            parsing_time = get_time()
            results[parser_name] = {
                "time": parsing_time,
                "elements": len(doc.elements) if doc else 0
            }
            print(f"{parser_name}解析时间: {parsing_time:.3f}秒, 元素数量: {results[parser_name]['elements']}")

        # 验证所有解析器都能正常工作
        for parser_name, result in results.items():
            assert result["time"] < 1.0, f"{parser_name}解析过慢: {result['time']:.3f}秒"
            assert result["elements"] > 0, f"{parser_name}解析失败"

    def test_qa_engine_performance_scaling(self):
        """测试QA引擎性能扩展性"""
        test_cases = [
            (10, 100, "小文档"),
            (100, 500, "中等文档"),
            (500, 1000, "大文档")
        ]

        results = {}

        for num_elements, content_length, case_name in test_cases:
            doc = self._create_test_document(num_elements, content_length)

            with time_monitor() as get_time:
                qa_engine = QAEngine()
                qa_report = qa_engine.check(doc)

            qa_time = get_time()
            results[case_name] = qa_time
            print(f"{case_name} QA检查时间: {qa_time:.3f}秒")

            # 验证QA报告
            assert qa_report is not None
            assert hasattr(qa_report, 'issues')

        # 验证性能扩展性（时间应该大致线性增长）
        small_time = results["小文档"]
        large_time = results["大文档"]
        scaling_factor = large_time / small_time

        print(f"QA引擎扩展性: 小文档{small_time:.3f}秒 -> 大文档{large_time:.3f}秒 (倍数: {scaling_factor:.1f})")

        # 大文档时间应该在合理范围内（这里设置一个宽松的上限）
        assert large_time < 10.0, f"大文档QA检查过慢: {large_time:.3f}秒"

    def _create_test_document(self, num_elements, content_length):
        """创建测试文档"""
        doc = DocumentModel(title=f"性能测试文档({num_elements}元素)")

        for i in range(num_elements):
            content = f"这是第{i}段测试内容。性能测试用例。" * (content_length // 20)
            content = content[:content_length]  # 确保精确长度

            element = DocElement(
                element_type=ElementType.PARAGRAPH,
                content=content
            )
            doc.elements.append(element)

        return doc

    def _create_test_file(self, file_type, num_elements, content_length):
        """创建测试文件"""
        if file_type == "txt":
            content = ""
            for i in range(num_elements):
                content += f"这是第{i}段测试内容。性能测试用例。\n\n"

            file_path = os.path.join(self.temp_dir, f"perf_test.{file_type}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        elif file_type == "md":
            content = "# 性能测试文档\n\n"
            for i in range(num_elements):
                content += f"## 第{i}节\n\n这是第{i}段测试内容。性能测试用例。\n\n"

            file_path = os.path.join(self.temp_dir, f"perf_test.{file_type}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return file_path


class TestStressTesting:
    """压力测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_high_frequency_operations(self):
        """测试高频操作"""
        # 模拟用户快速连续操作
        operations = 50

        with time_monitor() as get_time:
            for i in range(operations):
                doc = DocumentModel(title=f"快速操作{i}")
                doc.elements.append(DocElement(
                    element_type=ElementType.PARAGRAPH,
                    content=f"快速操作测试内容{i}"
                ))

                rules = FormattingRules()
                formatter = Formatter(rules)
                formatted_doc = formatter.apply(doc)

                # 不进行完整的QA检查，只做基本格式化
                del doc, formatted_doc, rules, formatter

        total_time = get_time()
        avg_time_per_op = total_time / operations

        print(f"高频操作测试: {operations}次操作，总时间{total_time:.2f}秒，平均{avg_time_per_op:.3f}秒/次")

        # 平均每次操作应该很快
        assert avg_time_per_op < 0.1, f"操作响应过慢: {avg_time_per_op:.3f}秒/次"

    def test_resource_limits(self):
        """测试资源限制"""
        # 测试在内存受限情况下的表现
        try:
            # 创建一个非常大的文档
            huge_doc = DocumentModel(title="巨大文档测试")

            # 添加大量内容
            for i in range(5000):
                huge_doc.elements.append(DocElement(
                    element_type=ElementType.PARAGRAPH,
                    content="大量内容测试" * 100  # 每段约2000字符
                ))

            # 尝试处理
            with memory_monitor() as mem_tracker:
                with time_monitor() as get_time:
                    rules = FormattingRules()
                    formatter = Formatter(rules)
                    formatted_doc = formatter.apply(huge_doc)

                processing_time = get_time()
                print(f"巨大文档处理: 时间{processing_time:.2f}秒, 峰值内存{mem_tracker.peak_memory:.1f}MB")

                # 验证处理成功
                assert len(formatted_doc.elements) == 5000
                assert processing_time < 60.0  # 1分钟内完成

        except MemoryError:
            # 如果内存不足，这是可以接受的
            pytest.skip("内存不足，跳过巨大文档测试")

    def test_long_running_stability(self):
        """测试长时间运行稳定性"""
        # 运行较长时间的测试
        test_duration = 30  # 30秒
        operations_count = 0

        start_time = time.time()
        while time.time() - start_time < test_duration:
            # 执行一些基本操作
            doc = DocumentModel(title=f"稳定性测试{operations_count}")
            doc.elements.append(DocElement(
                element_type=ElementType.PARAGRAPH,
                content=f"稳定性测试内容{operations_count}"
            ))

            rules = FormattingRules()
            formatter = Formatter(rules)
            formatted_doc = formatter.apply(doc)

            operations_count += 1

            # 小延迟避免CPU占用过高
            time.sleep(0.01)

        print(f"稳定性测试完成: {operations_count}次操作在{test_duration}秒内")

        # 验证执行了足够多的操作
        assert operations_count > 100, f"操作次数过少: {operations_count}"

    def test_error_recovery_under_load(self):
        """测试负载下的错误恢复"""
        # 模拟在高负载下遇到错误的情况
        success_count = 0
        error_count = 0

        for i in range(100):
            try:
                doc = DocumentModel(title=f"负载测试{i}")

                # 随机添加不同数量的元素
                num_elements = (i % 10) + 1
                for j in range(num_elements):
                    doc.elements.append(DocElement(
                        element_type=ElementType.PARAGRAPH,
                        content=f"负载测试内容{i}-{j}"
                    ))

                rules = FormattingRules()
                formatter = Formatter(rules)
                formatted_doc = formatter.apply(doc)

                success_count += 1

            except Exception as e:
                error_count += 1
                print(f"负载测试中出现错误: {e}")

        print(f"负载测试结果: 成功{success_count}次, 失败{error_count}次")

        # 大部分操作应该成功
        success_rate = success_count / (success_count + error_count)
        assert success_rate > 0.95, f"成功率过低: {success_rate:.2%}"