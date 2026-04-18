"""
基础解析器接口 (Base Parser)

所有文件解析器的抽象基类，定义统一的解析接口。
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from core.document_model import DocumentModel


class BaseParser(ABC):
    """文件解析器抽象基类"""

    # 子类需定义支持的文件扩展名
    supported_extensions: list[str] = []

    @abstractmethod
    def parse(self, file_path: str, **kwargs) -> DocumentModel:
        """
        解析文件，返回统一文档模型。

        Args:
            file_path: 文件路径
            **kwargs: 额外参数（如编码、引擎选择等）

        Returns:
            DocumentModel: 统一文档模型

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或内容无效
            Exception: 解析过程中的其他错误
        """
        ...

    def supports(self, file_path: str) -> bool:
        """判断是否支持该文件类型"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    @staticmethod
    def _validate_file(file_path: str) -> str:
        """验证文件存在性，返回绝对路径"""
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        return abs_path

    @staticmethod
    def _detect_encoding(file_path: str) -> str:
        """检测文件编码"""
        try:
            import chardet
            with open(file_path, "rb") as f:
                raw = f.read(10240)  # 读取前10KB
            result = chardet.detect(raw)
            return result.get("encoding", "utf-8") or "utf-8"
        except ImportError:
            return "utf-8"

    @staticmethod
    def _read_text_file(file_path: str, encoding: Optional[str] = None) -> str:
        """读取文本文件，自动检测编码"""
        if encoding is None:
            encoding = BaseParser._detect_encoding(file_path)
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试常见编码
            for enc in ("gbk", "gb2312", "gb18030", "latin-1"):
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"无法解码文件: {file_path}")
