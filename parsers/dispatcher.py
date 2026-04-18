"""
解析器调度器 (Parser Dispatcher)

根据文件扩展名自动选择对应的解析器，统一调用入口。
支持 .doc 旧格式自动转换为 .docx 后解析。
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from parsers.base import BaseParser
from parsers.docx_parser import DocxParser
from parsers.txt_parser import TxtParser
from parsers.md_parser import MdParser
from parsers.xlsx_parser import XlsxParser
from parsers.pdf_parser import PdfParser
from core.document_model import DocumentModel


# 注册所有解析器
_PARSERS: list[BaseParser] = [
    DocxParser(),
    TxtParser(),
    MdParser(),
    XlsxParser(),
    PdfParser(),
]

# 扩展名 → 解析器映射
_EXT_MAP: dict[str, BaseParser] = {}
for parser in _PARSERS:
    for ext in parser.supported_extensions:
        _EXT_MAP[ext] = parser


def parse_file(file_path: str, **kwargs) -> DocumentModel:
    """
    解析文件，自动选择解析器。

    Args:
        file_path: 文件路径
        **kwargs: 传递给解析器的额外参数

    Returns:
        DocumentModel: 统一文档模型

    Raises:
        ValueError: 不支持的文件格式
        FileNotFoundError: 文件不存在
    """
    abs_path = os.path.abspath(file_path)
    ext = Path(abs_path).suffix.lower()

    # .doc 旧格式：先转换为 .docx
    if ext == ".doc":
        docx_path = _convert_doc_to_docx(abs_path)
        return DocxParser().parse(docx_path, **kwargs)

    # 查找对应的解析器
    parser = _EXT_MAP.get(ext)
    if parser is None:
        supported = ", ".join(sorted(_EXT_MAP.keys()))
        raise ValueError(f"不支持的文件格式: {ext}（支持: {supported}）")

    try:
        return parser.parse(abs_path, **kwargs)
    except Exception as e:
        # 捕获所有解析异常并重新抛出为通用异常
        # 这确保异常处理的一致性
        raise


def get_supported_formats() -> list[str]:
    """获取所有支持的文件格式"""
    formats = list(_EXT_MAP.keys())
    formats.append(".doc")  # 通过转换支持
    return sorted(formats)


def get_parser_for_file(file_path: str) -> Optional[BaseParser]:
    """获取文件对应的解析器（不执行解析）"""
    ext = Path(file_path).suffix.lower()
    if ext == ".doc":
        return DocxParser()
    return _EXT_MAP.get(ext)


def _convert_doc_to_docx(doc_path: str) -> str:
    """
    将 .doc 文件转换为 .docx 格式。
    使用 LibreOffice 进行转换。

    Returns:
        str: 转换后的 .docx 文件路径
    """
    # 检查 LibreOffice 是否可用
    libreoffice_paths = [
        "libreoffice",
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]

    libreoffice_cmd = None
    for cmd in libreoffice_paths:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                libreoffice_cmd = cmd
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    if libreoffice_cmd is None:
        raise RuntimeError(
            "无法找到 LibreOffice，.doc 格式转换需要 LibreOffice。\n"
            "请安装 LibreOffice: https://www.libreoffice.org/"
        )

    # 转换到临时目录
    output_dir = tempfile.mkdtemp(prefix="wordcraft_")
    try:
        result = subprocess.run(
            [
                libreoffice_cmd,
                "--headless",
                "--convert-to", "docx",
                "--outdir", output_dir,
                doc_path,
            ],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice 转换失败: {result.stderr}")

        # 查找转换后的文件
        base_name = Path(doc_path).stem
        docx_path = os.path.join(output_dir, f"{base_name}.docx")
        if not os.path.isfile(docx_path):
            # 尝试查找目录中任何 .docx 文件
            for f in os.listdir(output_dir):
                if f.endswith(".docx"):
                    docx_path = os.path.join(output_dir, f)
                    break

        if not os.path.isfile(docx_path):
            raise RuntimeError(f"转换后的文件未找到: {docx_path}")

        return docx_path

    except Exception:
        # 清理临时目录
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
