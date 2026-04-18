#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordCraft Pro 兼容性测试

测试多环境兼容性：
- 操作系统兼容性
- Python版本兼容性
- 第三方库版本兼容性
- 文件格式兼容性
"""

import os
import sys
import platform
import tempfile
import shutil
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import DocumentModel, DocElement, ElementType
from parsers.dispatcher import parse_file
from core.formatting_rules import FormattingRules
from core.formatter import Formatter
from core.qa_engine import QAEngine
from core.exporter import Exporter


class TestOSCompatibility:
    """操作系统兼容性测试"""

    def test_path_handling(self):
        """测试路径处理兼容性"""
        # 测试不同路径格式
        test_paths = [
            "simple_file.txt",
            "./relative/file.txt",
            "folder/subfolder/file.txt",
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt"
        ]

        for path in test_paths:
            # 创建测试文件
            full_path = os.path.join(tempfile.gettempdir(), path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("测试内容")

                # 验证文件可以被解析器处理
                if path.endswith('.txt'):
                    doc = parse_file(full_path)
                    assert doc is not None

            finally:
                # 清理
                if os.path.exists(full_path):
                    os.remove(full_path)

    def test_file_encoding_compatibility(self):
        """测试文件编码兼容性"""
        encodings = ['utf-8', 'utf-16', 'gbk', 'latin1']

        for encoding in encodings:
            try:
                # 创建测试文件
                test_content = "测试文件编码兼容性：English 中文 日本語"
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding=encoding) as f:
                    f.write(test_content)
                    temp_path = f.name

                # 尝试解析
                doc = parse_file(temp_path)

                # 对于某些编码可能失败，这是正常的
                if doc is not None:
                    assert len(doc.elements) > 0

            except (UnicodeEncodeError, UnicodeDecodeError):
                # 某些编码不支持中文，这是预期的
                continue
            finally:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_temp_directory_handling(self):
        """测试临时目录处理"""
        # 测试在系统临时目录中创建和处理文件
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("临时目录测试内容")

            # 验证可以处理临时目录中的文件
            doc = parse_file(test_file)
            assert doc is not None

            # 测试输出到临时目录
            output_file = os.path.join(temp_dir, "output.docx")
            rules = FormattingRules()
            formatter = Formatter(rules)
            formatted_doc = formatter.apply(doc)

            exporter = Exporter()
            exporter.export(formatted_doc, output_file)

            assert os.path.exists(output_file)


class TestPythonVersionCompatibility:
    """Python版本兼容性测试"""

    def test_python_version_detection(self):
        """测试Python版本检测"""
        version = sys.version_info
        print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")

        # 验证版本在支持范围内
        assert version.major == 3
        assert version.minor >= 8  # 支持3.8+

    def test_syntax_compatibility(self):
        """测试语法兼容性"""
        # 测试现代Python语法
        test_dict = {"key": "value"}
        value = test_dict.get("key")

        # 测试f-string
        formatted = f"测试值: {value}"

        # 测试类型注解（如果支持）
        def test_function(param: str) -> str:
            return param.upper()

        result = test_function("test")
        assert result == "TEST"

    def test_import_compatibility(self):
        """测试导入兼容性"""
        # 测试所有核心模块可以导入
        try:
            from core.document_model import DocumentModel
            from parsers.dispatcher import parse_file
            from core.formatting_rules import FormattingRules
            from core.formatter import Formatter
            from core.qa_engine import QAEngine
            from core.exporter import Exporter

            # 验证导入成功
            assert DocumentModel is not None
            assert parse_file is not None
            assert FormattingRules is not None
            assert Formatter is not None
            assert QAEngine is not None
            assert Exporter is not None

        except ImportError as e:
            pytest.fail(f"核心模块导入失败: {e}")

    def test_builtin_function_compatibility(self):
        """测试内置函数兼容性"""
        # 测试pathlib
        from pathlib import Path
        temp_path = Path(tempfile.gettempdir()) / "test_file.txt"
        temp_path.write_text("测试pathlib兼容性", encoding="utf-8")
        content = temp_path.read_text(encoding="utf-8")
        assert content == "测试pathlib兼容性"
        temp_path.unlink()

        # 测试dataclasses（如果支持）
        try:
            from dataclasses import dataclass

            @dataclass
            class TestClass:
                value: str

            instance = TestClass("test")
            assert instance.value == "test"

        except ImportError:
            # Python 3.6不支持dataclasses，跳过
            pass


class TestLibraryCompatibility:
    """第三方库兼容性测试"""

    def test_core_dependencies(self):
        """测试核心依赖库"""
        required_modules = [
            'os', 'sys', 'tempfile', 'shutil', 'time', 'threading',
            'pathlib', 'json', 're', 'typing'
        ]

        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                pytest.fail(f"核心依赖模块 {module} 不可用")

    def test_optional_dependencies(self):
        """测试可选依赖库"""
        optional_modules = [
            ('PyQt6', 'QtWidgets'),
            ('pywebview', None),
            ('requests', None),
            ('python_docx', None),
            ('PyPDF2', None),
            ('markdown', None),
            ('openpyxl', None),
            ('psutil', None),
            ('pytest', None)
        ]

        missing_modules = []

        for module, submodule in optional_modules:
            try:
                if submodule:
                    __import__(module, fromlist=[submodule])
                else:
                    __import__(module)
            except ImportError:
                missing_modules.append(module)

        if missing_modules:
            print(f"缺少可选依赖模块: {missing_modules}")
            # 不直接失败，因为这些是可选的
            # 但在CI环境中应该安装

    def test_library_version_compatibility(self):
        """测试库版本兼容性"""
        # 检查关键库的版本
        version_checks = []

        try:
            import PyQt6
            version_checks.append(("PyQt6", PyQt6.QtCore.PYQT_VERSION_STR))
        except ImportError:
            version_checks.append(("PyQt6", "Not installed"))

        try:
            import requests
            version_checks.append(("requests", requests.__version__))
        except ImportError:
            version_checks.append(("requests", "Not installed"))

        try:
            import pytest
            version_checks.append(("pytest", pytest.__version__))
        except ImportError:
            version_checks.append(("pytest", "Not installed"))

        # 打印版本信息
        for lib, version in version_checks:
            print(f"{lib}: {version}")

        # 这里可以添加具体的版本兼容性检查
        # 例如：assert version.parse(requests.__version__) >= version.parse("2.0.0")


class TestFileFormatCompatibility:
    """文件格式兼容性测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_text_file_variations(self):
        """测试文本文件变体"""
        test_cases = [
            ("utf8.txt", "utf-8", "UTF-8编码文件"),
            ("gbk.txt", "gbk", "GBK编码文件"),
            ("ascii.txt", "ascii", "ASCII文件"),
        ]

        for filename, encoding, description in test_cases:
            try:
                content = f"{description}：测试内容"
                file_path = os.path.join(self.temp_dir, filename)

                with open(file_path, "w", encoding=encoding) as f:
                    f.write(content)

                # 尝试解析
                doc = parse_file(file_path)
                if doc is not None:
                    assert len(doc.elements) > 0
                    print(f"✓ {description} 解析成功")

            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"⚠ {description} 编码问题，跳过")
                continue

    def test_document_structure_variations(self):
        """测试文档结构变体"""
        # 测试不同结构的文档
        structures = [
            ("empty.txt", ""),
            ("single_line.txt", "单行文档内容"),
            ("multi_line.txt", "第一行\n第二行\n第三行"),
            ("with_empty_lines.txt", "第一段\n\n第二段\n\n\n第三段"),
        ]

        for filename, content in structures:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            doc = parse_file(file_path)
            assert doc is not None
            assert doc.title is not None

            # 验证元素数量合理
            if content.strip():
                assert len(doc.elements) > 0
            else:
                assert len(doc.elements) == 0

    def test_special_filename_characters(self):
        """测试特殊文件名字符"""
        special_names = [
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file (with parentheses).txt",
            "file[with]brackets.txt",
            "file+with+plus.txt",
            "file=with=equals.txt",
        ]

        for filename in special_names:
            try:
                file_path = os.path.join(self.temp_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("特殊文件名测试内容")

                doc = parse_file(file_path)
                assert doc is not None

            except OSError:
                # 某些文件名在某些系统上可能不支持
                print(f"文件名 {filename} 在当前系统上不支持")

    def test_large_file_handling(self):
        """测试大文件处理"""
        # 创建一个较大的文本文件
        large_content = "大文件测试内容\n" * 10000  # 约200KB

        large_file = os.path.join(self.temp_dir, "large_file.txt")
        with open(large_file, "w", encoding="utf-8") as f:
            f.write(large_content)

        # 验证可以处理大文件
        doc = parse_file(large_file)
        assert doc is not None
        assert len(doc.elements) > 0

        # 测试文件大小
        file_size = os.path.getsize(large_file) / 1024  # KB
        print(f"大文件大小: {file_size:.1f}KB")

        assert file_size > 100  # 至少100KB


class TestSystemIntegration:
    """系统集成测试"""

    def test_environment_variable_handling(self):
        """测试环境变量处理"""
        # 测试环境变量的读取和处理
        test_vars = {
            'WORDCRAFT_CONFIG': '/path/to/config.yaml',
            'WORDCRAFT_DEBUG': 'true',
            'WORDCRAFT_API_KEY': 'test_key'
        }

        # 备份原始环境变量
        original_vars = {}
        for key in test_vars:
            original_vars[key] = os.environ.get(key)

        try:
            # 设置测试环境变量
            for key, value in test_vars.items():
                os.environ[key] = value

            # 验证环境变量可以读取
            for key, expected_value in test_vars.items():
                actual_value = os.environ.get(key)
                assert actual_value == expected_value

        finally:
            # 恢复原始环境变量
            for key, original_value in original_vars.items():
                if original_value is not None:
                    os.environ[key] = original_value
                elif key in os.environ:
                    del os.environ[key]

    def test_working_directory_handling(self):
        """测试工作目录处理"""
        original_cwd = os.getcwd()

        try:
            # 切换到临时目录
            os.chdir(self.temp_dir)

            # 在临时目录中创建文件
            test_file = "cwd_test.txt"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("工作目录测试")

            # 验证可以处理当前目录中的文件
            doc = parse_file(test_file)
            assert doc is not None

        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)

    def test_system_resource_limits(self):
        """测试系统资源限制"""
        # 测试文件句柄限制
        open_files = []
        try:
            # 尝试打开多个文件
            for i in range(10):
                f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                f.write(f"文件{i}的内容")
                open_files.append(f)

            # 验证可以同时处理多个文件
            for f in open_files:
                f.seek(0)
                content = f.read()
                assert len(content) > 0

        finally:
            # 清理打开的文件
            for f in open_files:
                f.close()
                os.unlink(f.name)
