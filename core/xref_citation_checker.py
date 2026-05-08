"""
参考文献引用规范性检查器

检测正文中是否按标准方式引用参考文献。
当前实现基于 DocumentModel 纯文字层：检测手动打的 [n] 文字引用（未使用 Word 交叉引用功能）。
REF 域 / 上标 / 超链接层的检测需要 DOCX XML 字节访问，由更高层（docx 解析器 + API 层）负责。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from core.document_model import DocumentModel, ElementType
from core.qa_models import QAIssue, IssueCategory, IssueSeverity, QAReport


# 正文中疑似手动引用的正则：[1], [1,2], [1-3], [1，2] 等
_CITATION_PATTERN = re.compile(
    r'\[(\d+(?:[,，\-–]\d+)*)\]'
)

# 参考文献节标题检测
_REF_SECTION_HEADING = re.compile(
    r'参考文献|references?\b|bibliography', re.IGNORECASE
)

# 参考文献条目格式：[n] 开头
_REF_ENTRY_PATTERN = re.compile(r'^\s*\[(\d+)\]')

# 页眉/页脚元素类型集合（不扫描这些区域）
_SKIP_TYPES = {ElementType.HEADER, ElementType.FOOTER}


@dataclass
class CandidateCitation:
    """正文中检测到的疑似引用"""
    para_idx: int
    start_pos: int
    end_pos: int
    citation_text: str      # 原文片段，如 "[1]"
    numbers: list[int]      # 解析出的引用编号列表
    para_content: str       # 所在段落全文（前 80 字）


class XRefCitationStyleChecker:
    """
    参考文献引用规范性检查器。

    扫描范围：参考文献节之前的正文段落。
    当前能力：检测手动输入的 [n] 纯文字引用（未使用 Word 交叉引用功能）。
    """

    def __init__(self):
        self.enabled = True

    def check(self, doc: DocumentModel) -> QAReport:
        """对文档执行参考文献引用规范性检查。"""
        report = QAReport()
        if not self.enabled:
            return report

        ref_map, ref_section_start, warning = self._build_ref_map(doc)
        if warning:
            report.metadata["xref_citation_warning"] = warning

        if ref_section_start == -1 and not ref_map:
            return report

        issues = self._scan_body_citations(doc, ref_section_start, ref_map)
        for issue in issues:
            report.add_issue(issue)
        return report

    # ── 内部方法 ──────────────────────────────────────────────

    def _build_ref_map(
        self, doc: DocumentModel
    ) -> tuple[dict[int, int], int, Optional[str]]:
        """
        构建 {引用编号 → 参考文献节 element_index} 映射。

        返回 (ref_map, ref_section_start, warning_or_None)
        ref_section_start = 参考文献节第一个条目的 element_index（-1 表示未找到）
        """
        ref_section_idx = -1
        ref_map: dict[int, int] = {}

        for idx, elem in enumerate(doc.elements):
            if elem.element_type == ElementType.HEADING:
                text = (elem.content or "").strip()
                if _REF_SECTION_HEADING.search(text):
                    ref_section_idx = idx
                    break

        if ref_section_idx == -1:
            return {}, -1, "未找到参考文献节，跳过引用规范性检查"

        for idx in range(ref_section_idx + 1, len(doc.elements)):
            elem = doc.elements[idx]
            content = (elem.content or "").strip()
            m = _REF_ENTRY_PATTERN.match(content)
            if m:
                ref_map[int(m.group(1))] = idx

        return ref_map, ref_section_idx, None

    def _scan_body_citations(
        self,
        doc: DocumentModel,
        ref_section_start: int,
        ref_map: dict[int, int],
    ) -> list[QAIssue]:
        """扫描参考文献节之前的正文段落，收集手动 [n] 引用。"""
        issues: list[QAIssue] = []
        end_idx = ref_section_start if ref_section_start >= 0 else len(doc.elements)

        for para_idx in range(end_idx):
            elem = doc.elements[para_idx]
            if elem.element_type in _SKIP_TYPES:
                continue
            content = elem.content or ""
            for m in _CITATION_PATTERN.finditer(content):
                numbers = _parse_citation_numbers(m.group(1))
                citation_text = m.group(0)
                # 尝试匹配第一个引用编号，判断是否能找到对应条目
                can_fix = any(n in ref_map for n in numbers) if ref_map else False

                issues.append(QAIssue(
                    category=IssueCategory.REFERENCE,
                    severity=IssueSeverity.WARNING,
                    title=f'手动引用 {citation_text} 未使用交叉引用功能',
                    description=(
                        f'正文中手动输入了 {citation_text}，应通过 Word "引用→交叉引用" 插入标准 REF 域并设置上标格式'
                    ),
                    suggestion=f'将 {citation_text} 替换为 Word 交叉引用（REF 域 + 上标）',
                    location_text=content[max(0, m.start() - 10): m.end() + 10].strip(),
                    element_index=para_idx,
                    start_pos=m.start(),
                    end_pos=m.end(),
                    rule_id="xref.plain_text_citation",
                    checker="xref_citation_checker",
                    confidence=0.85,
                    fixable=can_fix,
                    fix_type="xref" if can_fix else None,
                    fix_payload={
                        "type": "xref",
                        "para_idx": para_idx,
                        "para_fingerprint": content[:40].strip(),
                        "citation_text": citation_text,
                        "ref_numbers": numbers,
                        "ref_element_indices": [ref_map[n] for n in numbers if n in ref_map],
                    } if can_fix else None,
                ))

        return issues


def _parse_citation_numbers(num_str: str) -> list[int]:
    """将 "1,2,3" 或 "1-3" 等格式解析为数字列表。"""
    result: list[int] = []
    parts = re.split(r'[,，]', num_str)
    for part in parts:
        part = part.strip()
        range_match = re.match(r'(\d+)[–\-](\d+)', part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            result.extend(range(start, end + 1))
        elif part.isdigit():
            result.append(int(part))
    return result
