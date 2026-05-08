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


def _find_libreoffice_command() -> Optional[str]:
    libreoffice_paths = [
        "libreoffice",
        "soffice",
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
        "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for cmd in libreoffice_paths:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _detect_windows_word_binary() -> Optional[str]:
    word_paths = [
        "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
        "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
        "C:\\Program Files\\Microsoft Office\\Office16\\WINWORD.EXE",
        "C:\\Program Files (x86)\\Microsoft Office\\Office16\\WINWORD.EXE",
        "C:\\Program Files\\Microsoft Office 15\\root\\Office15\\WINWORD.EXE",
        "C:\\Program Files (x86)\\Microsoft Office 15\\root\\Office15\\WINWORD.EXE",
    ]
    for path in word_paths:
        if os.path.isfile(path):
            return path
    return None


def _run_word_com_conversion(doc_path: str, out_path: str) -> tuple[bool, str]:
    src_ps = doc_path.replace("'", "''")
    dst_ps = out_path.replace("'", "''")
    ps = (
        f"$w=New-Object -ComObject Word.Application;"
        f"$w.Visible=$false;"
        f"try{{$d=$w.Documents.Open('{src_ps}');"
        f"$d.SaveAs('{dst_ps}',16);$d.Close();Write-Output 'OK'}}"
        f"catch{{Write-Error $_.Exception.Message; exit 1}}"
        f"finally{{if($w){{$w.Quit()}}}}"
    )
    result = subprocess.run(
        ["powershell", "-NonInteractive", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=90,
    )
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout
    return result.returncode == 0 and os.path.isfile(out_path), detail


def _build_doc_conversion_error(
    libreoffice_cmd: Optional[str],
    word_binary: Optional[str],
    word_com_error: Optional[str],
) -> str:
    prefix = (
        ".doc 转换失败：当前版本会先自动转换为 .docx 再打开，但这一步没有成功。"
    )
    if libreoffice_cmd:
        libreoffice_msg = f"已检测到 LibreOffice（{libreoffice_cmd}），但转换未成功。"
    else:
        libreoffice_msg = "未检测到 LibreOffice。"

    if word_binary and word_com_error:
        lower_error = word_com_error.lower()
        if "0x80070520" in lower_error or "logon session" in lower_error:
            word_msg = (
                f"已检测到 Microsoft Word（{word_binary}），但当前运行会话无法启动 "
                f"Word COM：{word_com_error}"
            )
        else:
            word_msg = (
                f"已检测到 Microsoft Word（{word_binary}），但自动转换调用失败："
                f"{word_com_error}"
            )
    elif word_binary:
        word_msg = (
            f"已检测到 Microsoft Word（{word_binary}），但自动转换未生成输出文件。"
        )
    else:
        word_msg = "未检测到可用于自动转换的 Microsoft Word。"

    suggestion = (
        "建议优先安装 LibreOffice 作为 .doc 转换引擎，或先用本机 Office/WPS 将文件另存为 .docx 后再打开。"
    )
    return "\n".join([prefix, libreoffice_msg, word_msg, suggestion])


def _convert_doc_to_docx(doc_path: str) -> str:
    """
    将 .doc 文件转换为 .docx 格式。
    回退顺序：① 直接当 .docx 打开  ② LibreOffice  ③ Windows Word COM
    """
    import sys, shutil

    # 回退1：部分 .doc 文件实际上是 Open XML（.docx）格式
    try:
        from docx import Document as _Doc
        _Doc(doc_path)
        output_dir = tempfile.mkdtemp(prefix="wordcraft_")
        out = os.path.join(output_dir, Path(doc_path).stem + ".docx")
        shutil.copy2(doc_path, out)
        return out
    except Exception:
        pass

    # 回退2：LibreOffice
    libreoffice_cmd = _find_libreoffice_command()

    if libreoffice_cmd is not None:
        output_dir = tempfile.mkdtemp(prefix="wordcraft_")
        try:
            result = subprocess.run(
                [libreoffice_cmd, "--headless", "--convert-to", "docx",
                 "--outdir", output_dir, doc_path],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"LibreOffice 转换失败: {result.stderr}")
            base_name = Path(doc_path).stem
            docx_path = os.path.join(output_dir, f"{base_name}.docx")
            if not os.path.isfile(docx_path):
                for f in os.listdir(output_dir):
                    if f.endswith(".docx"):
                        docx_path = os.path.join(output_dir, f)
                        break
            if not os.path.isfile(docx_path):
                raise RuntimeError(f"LibreOffice 未生成输出文件: {output_dir}")
            return docx_path
        except Exception as lo_err:
            shutil.rmtree(output_dir, ignore_errors=True)
            import logging as _log
            _log.getLogger(__name__).warning("LibreOffice 转换失败，尝试下一方法: %s", lo_err)

    # 回退3：Windows Word COM（通过 PowerShell，无需 pywin32）
    word_binary = None
    word_com_error = None
    if sys.platform == "win32":
        word_binary = _detect_windows_word_binary()
        output_dir = tempfile.mkdtemp(prefix="wordcraft_")
        out_path = os.path.join(output_dir, Path(doc_path).stem + ".docx")
        try:
            ok, word_com_error = _run_word_com_conversion(doc_path, out_path)
            if ok:
                return out_path
        except Exception:
            pass
        shutil.rmtree(output_dir, ignore_errors=True)

    raise RuntimeError(
        _build_doc_conversion_error(
            libreoffice_cmd=libreoffice_cmd,
            word_binary=word_binary,
            word_com_error=word_com_error,
        )
    )


def _emf_to_png_bytes(emf_data: bytes, src_ext: str = ".emf") -> Optional[bytes]:
    """将 EMF/WMF bytes 转为 PNG bytes；失败返回 None。"""
    import sys
    import logging as _log
    _logger = _log.getLogger(__name__)

    with tempfile.NamedTemporaryFile(suffix=src_ext, delete=False) as f:
        f.write(emf_data)
        emf_path = f.name
    png_path = emf_path[: -len(src_ext)] + ".png"

    try:
        if sys.platform == "win32":
            src = emf_path.replace("'", "''")
            dst = png_path.replace("'", "''")
            # 渲染到 150 DPI 以获得更清晰输出；白底；高质量模式
            ps = (
                "Add-Type -AssemblyName System.Drawing;"
                f"$m=[System.Drawing.Imaging.Metafile]::new('{src}');"
                "$dpi=150;$scale=$dpi/$m.HorizontalResolution;"
                "$w=[int]($m.Width*$scale);$h=[int]($m.Height*$scale);"
                "if($w -le 0){$w=$m.Width;$h=$m.Height};"
                "$b=[System.Drawing.Bitmap]::new($w,$h);"
                "$b.SetResolution($dpi,$dpi);"
                "$g=[System.Drawing.Graphics]::FromImage($b);"
                "$g.Clear([System.Drawing.Color]::White);"
                "$g.SmoothingMode=[System.Drawing.Drawing2D.SmoothingMode]::HighQuality;"
                "$g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic;"
                "$g.DrawImage($m,0,0,$w,$h);"
                f"$b.Save('{dst}',[System.Drawing.Imaging.ImageFormat]::Png);"
                "$g.Dispose();$b.Dispose();$m.Dispose()"
            )
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and os.path.isfile(png_path):
                with open(png_path, "rb") as fp:
                    return fp.read()
            _logger.debug("PowerShell EMF→PNG 失败: %s", result.stderr.strip())

        # LibreOffice 兜底
        lo_cmd = _find_libreoffice_command()
        if lo_cmd:
            import shutil
            out_dir = tempfile.mkdtemp(prefix="wordcraft_emf_")
            try:
                r = subprocess.run(
                    [lo_cmd, "--headless", "--convert-to", "png",
                     "--outdir", out_dir, emf_path],
                    capture_output=True,
                    timeout=30,
                )
                png_lo = os.path.join(out_dir, Path(emf_path).stem + ".png")
                if r.returncode == 0 and os.path.isfile(png_lo):
                    with open(png_lo, "rb") as fp:
                        return fp.read()
            finally:
                shutil.rmtree(out_dir, ignore_errors=True)

    except Exception as exc:
        _logger.debug("EMF→PNG 转换异常: %s", exc)
    finally:
        try:
            os.unlink(emf_path)
        except Exception:
            pass
        try:
            os.unlink(png_path)
        except Exception:
            pass

    return None


_METAFILE_EXTS = {".emf", ".wmf"}


def convert_emf_images_in_docx(docx_bytes: bytes) -> bytes:
    """
    扫描 docx zip 内 word/media/ 下所有 EMF/WMF 图片，转为 PNG。
    按扩展名检测（.emf / .wmf），System.Drawing.Metafile 处理两种格式。
    返回修改后 docx bytes；若无 metafile 或转换全部失败，返回原始 bytes 对象。
    """
    import io
    import zipfile
    import logging as _log
    _logger = _log.getLogger(__name__)

    try:
        # 第一遍：检测并转换 EMF/WMF
        mf_to_png: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            for name in z.namelist():
                if not name.startswith("word/media/"):
                    continue
                ext = ("." + name.rsplit(".", 1)[-1]).lower() if "." in name else ""
                if ext not in _METAFILE_EXTS:
                    continue
                data = z.read(name)
                if not data:
                    continue
                png = _emf_to_png_bytes(data, ext)
                if png:
                    mf_to_png[name] = png
                    _logger.info("Metafile→PNG 成功: %s (%d B)", name, len(png))
                else:
                    _logger.warning("Metafile→PNG 失败，保留原文件: %s", name)

        if not mf_to_png:
            return docx_bytes  # 无 metafile 或全部失败，原样返回

        # 第二遍：重建 zip
        out = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zin, \
             zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:

            for item in zin.infolist():
                name = item.filename
                data = zin.read(name)

                if name in mf_to_png:
                    # EMF/WMF 条目 → 写入 PNG
                    png_name = name.rsplit(".", 1)[0] + ".png"
                    info = zipfile.ZipInfo(png_name)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    zout.writestr(info, mf_to_png[name])

                elif name.endswith(".rels"):
                    # 更新关系文件：media/imageN.emf/.wmf → media/imageN.png
                    text = data.decode("utf-8")
                    for mf_zip_path in mf_to_png:
                        media_file = mf_zip_path.split("/")[-1]         # imageN.emf
                        png_file = media_file.rsplit(".", 1)[0] + ".png"  # imageN.png
                        text = text.replace(
                            f"media/{media_file}", f"media/{png_file}"
                        )
                    zout.writestr(item, text.encode("utf-8"))

                elif name == "[Content_Types].xml":
                    text = data.decode("utf-8")
                    if "image/png" not in text:
                        text = text.replace(
                            "</Types>",
                            '<Default Extension="png" ContentType="image/png"/></Types>',
                        )
                    zout.writestr(item, text.encode("utf-8"))

                else:
                    zout.writestr(item, data)

        return out.getvalue()

    except Exception as exc:
        import logging as _log2
        _log2.getLogger(__name__).warning("EMF→PNG docx 重建失败，返回原始: %s", exc)
        return docx_bytes
