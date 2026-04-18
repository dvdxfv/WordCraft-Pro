"""
交叉引用引擎 (Cross-Reference Engine)

核心流程：
1. 目标扫描：从文档中提取图/表/公式/章节的编号和标题
2. 引用点扫描：找到"如图X所示"等引用文本
3. 匹配与校验：检查引用是否有效、是否有悬空引用
"""

from __future__ import annotations

import re
from typing import Optional

from core.document_model import DocumentModel, DocElement, ElementType
from core.crossref_models import (
    RefTarget, RefPoint, CrossRefMatch, CrossRefReport,
    RefTargetType, CrossRefStatus,
)
from core.formatting_rules import CrossRefRules


# ============================================================
# 目标扫描器
# ============================================================

class TargetScanner:
    """目标扫描器 — 从文档中提取可被引用的实体"""

    # 图题模式：图X-Y 标题文字 / 图X.Y 标题文字
    FIGURE_PATTERNS = [
        re.compile(r"图\s*(\d+)[\-\.](\d+)\s*(.*)"),
        re.compile(r"图\s*(\d+)\s*(.*)"),  # 简单编号：图1 标题
    ]

    # 表题模式
    TABLE_PATTERNS = [
        re.compile(r"表\s*(\d+)[\-\.](\d+)\s*(.*)"),
        re.compile(r"表\s*(\d+)\s*(.*)"),
    ]

    # 公式模式：(X-Y) 或 (X.Y) 在行尾
    EQUATION_PATTERNS = [
        re.compile(r"[(（]\s*(\d+)[\-\.](\d+)\s*[)）]\s*$"),
        re.compile(r"[(（]\s*(\d+)\s*[)）]\s*$"),
    ]

    # 章节标题模式
    CHAPTER_PATTERNS = [
        re.compile(r"第([一二三四五六七八九十百\d]+)章\s*(.*)"),
        re.compile(r"(\d+)\s*[\.、]\s*(.*)"),  # "1 标题" 或 "1、标题"
    ]

    # 参考文献模式
    REFERENCE_PATTERN = re.compile(r"^\s*\[(\d+)\]\s*(.*)")

    def scan(self, doc: DocumentModel) -> list[RefTarget]:
        """扫描文档，提取所有引用目标"""
        targets: list[RefTarget] = []

        current_chapter = 0

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue

            # 检测章节标题
            chapter = self._try_match_chapter(elem)
            if chapter:
                current_chapter = chapter.chapter_num
                targets.append(chapter)
                continue

            # 检测图题
            fig = self._try_match_figure(elem, idx, current_chapter)
            if fig:
                targets.append(fig)
                continue

            # 检测表题
            tbl = self._try_match_table(elem, idx, current_chapter)
            if tbl:
                targets.append(tbl)
                continue

            # 检测公式编号（在段落末尾）
            eq = self._try_match_equation(elem, idx, current_chapter)
            if eq:
                targets.append(eq)
                continue

            # 检测参考文献
            ref = self._try_match_reference(elem, idx)
            if ref:
                targets.append(ref)

        return targets

    def _try_match_chapter(self, elem: DocElement) -> Optional[RefTarget]:
        """尝试匹配章节标题"""
        if elem.element_type != ElementType.HEADING:
            return None

        for pattern in self.CHAPTER_PATTERNS:
            m = pattern.match(elem.content.strip())
            if not m:
                continue

            raw_num = m.group(1)
            title = m.group(2).strip() if m.lastindex >= 2 else ""

            # 中文数字转阿拉伯数字
            chapter_num = self._cn_num_to_int(raw_num)
            if chapter_num <= 0:
                try:
                    chapter_num = int(raw_num)
                except ValueError:
                    continue

            if chapter_num <= 0:
                continue

            label = "第" + self._int_to_cn_num(chapter_num) + "章"
            if title:
                label += " " + title

            return RefTarget(
                target_type=RefTargetType.CHAPTER,
                number=str(chapter_num),
                label=label,
                title=title,
                element_index=elem.metadata.get("_original_index", -1),
                chapter_num=chapter_num,
                seq_num=0,
                bookmark_name=f"_chapter_{chapter_num}",
            )

        return None

    def _try_match_figure(self, elem: DocElement, idx: int,
                          chapter: int) -> Optional[RefTarget]:
        """尝试匹配图题"""
        if elem.element_type not in (ElementType.CAPTION, ElementType.PARAGRAPH):
            return None

        text = elem.content.strip()
        for pattern in self.FIGURE_PATTERNS:
            m = pattern.match(text)
            if not m:
                continue

            if m.lastindex >= 2:
                try:
                    ch = int(m.group(1))
                    seq = int(m.group(2))
                    title = m.group(3).strip() if m.lastindex >= 3 else ""
                    number = f"{ch}-{seq}"
                    label = f"图{number}"
                    if title:
                        label += " " + title
                    return RefTarget(
                        target_type=RefTargetType.FIGURE,
                        number=number,
                        label=label,
                        title=title,
                        element_index=idx,
                        chapter_num=ch,
                        seq_num=seq,
                        bookmark_name=f"_fig_{ch}_{seq}",
                    )
                except (ValueError, IndexError):
                    continue

        return None

    def _try_match_table(self, elem: DocElement, idx: int,
                         chapter: int) -> Optional[RefTarget]:
        """尝试匹配表题"""
        if elem.element_type not in (ElementType.CAPTION, ElementType.PARAGRAPH):
            return None

        text = elem.content.strip()
        for pattern in self.TABLE_PATTERNS:
            m = pattern.match(text)
            if not m:
                continue

            if m.lastindex >= 2:
                try:
                    ch = int(m.group(1))
                    seq = int(m.group(2))
                    title = m.group(3).strip() if m.lastindex >= 3 else ""
                    number = f"{ch}-{seq}"
                    label = f"表{number}"
                    if title:
                        label += " " + title
                    return RefTarget(
                        target_type=RefTargetType.TABLE,
                        number=number,
                        label=label,
                        title=title,
                        element_index=idx,
                        chapter_num=ch,
                        seq_num=seq,
                        bookmark_name=f"_tbl_{ch}_{seq}",
                    )
                except (ValueError, IndexError):
                    continue

        return None

    def _try_match_equation(self, elem: DocElement, idx: int,
                            chapter: int) -> Optional[RefTarget]:
        """尝试匹配公式编号"""
        if elem.element_type != ElementType.PARAGRAPH:
            return None

        text = elem.content.strip()
        for pattern in self.EQUATION_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue

            if m.lastindex >= 2:
                try:
                    ch = int(m.group(1))
                    seq = int(m.group(2))
                    number = f"{ch}-{seq}"
                    label = f"({number})"
                    return RefTarget(
                        target_type=RefTargetType.EQUATION,
                        number=number,
                        label=label,
                        title=text[:m.start()].strip(),
                        element_index=idx,
                        chapter_num=ch,
                        seq_num=seq,
                        bookmark_name=f"_eq_{ch}_{seq}",
                    )
                except (ValueError, IndexError):
                    continue

        return None

    def _try_match_reference(self, elem: DocElement, idx: int) -> Optional[RefTarget]:
        """尝试匹配参考文献条目"""
        if elem.element_type != ElementType.REFERENCE:
            return None

        text = elem.content.strip()
        m = self.REFERENCE_PATTERN.match(text)
        if not m:
            return None

        try:
            seq = int(m.group(1))
            title = m.group(2).strip()
            number = str(seq)
            label = f"[{number}]"
            return RefTarget(
                target_type=RefTargetType.REFERENCE,
                number=number,
                label=label,
                title=title,
                element_index=idx,
                seq_num=seq,
                bookmark_name=f"_ref_{seq}",
            )
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _cn_num_to_int(cn: str) -> int:
        """中文数字转整数"""
        cn_map = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
            "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
        }
        return cn_map.get(cn, 0)

    @staticmethod
    def _int_to_cn_num(n: int) -> str:
        """整数转中文数字"""
        cn_map = {
            1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
            6: "六", 7: "七", 8: "八", 9: "九", 10: "十",
            11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五",
            16: "十六", 17: "十七", 18: "十八", 19: "十九", 20: "二十",
        }
        return cn_map.get(n, str(n))


# ============================================================
# 引用点扫描器
# ============================================================

class RefPointScanner:
    """引用点扫描器 — 找到文中引用某目标的位置"""

    # 引用模式：类型关键词 + 编号
    REF_PATTERNS = [
        # 图引用（复合编号优先）
        (RefTargetType.FIGURE, re.compile(
            r"图\s*(\d+)[\-\.](\d+)"
        )),
        # 图引用（简单编号，排除后面跟着 - 或 . 的情况）
        (RefTargetType.FIGURE, re.compile(
            r"图\s*(\d+)(?![\-\.])"
        )),
        # 表引用（复合编号优先）
        (RefTargetType.TABLE, re.compile(
            r"表\s*(\d+)[\-\.](\d+)"
        )),
        # 表引用（简单编号）
        (RefTargetType.TABLE, re.compile(
            r"表\s*(\d+)(?![\-\.])"
        )),
        # 公式引用
        (RefTargetType.EQUATION, re.compile(
            r"[（(]\s*(\d+)[\-\.](\d+)\s*[）)]"
        )),
        (RefTargetType.EQUATION, re.compile(
            r"式\s*(\d+)[\-\.](\d+)"
        )),
        (RefTargetType.EQUATION, re.compile(
            r"公式\s*(\d+)[\-\.](\d+)"
        )),
        # 章节引用
        (RefTargetType.CHAPTER, re.compile(
            r"第([一二三四五六七八九十百\d]+)章"
        )),
        (RefTargetType.CHAPTER, re.compile(
            r"(\d+)\.[\d\.]*\s*节"
        )),
        # 参考文献引用
        (RefTargetType.REFERENCE, re.compile(
            r"\[(\d+(?:\s*[,，;；]\s*\d+)*)\]"
        )),
    ]

    def scan(self, doc: DocumentModel) -> list[RefPoint]:
        """扫描文档，提取所有引用点"""
        ref_points: list[RefPoint] = []

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue

            # 跳过标题本身（标题不是引用点）
            if elem.element_type == ElementType.HEADING:
                continue

            # 跳过题注本身（题注是目标，不是引用点）
            if elem.element_type == ElementType.CAPTION:
                # 但需要检查题注中是否引用了其他目标（罕见但可能）
                pass

            text = elem.content
            for target_type, pattern in self.REF_PATTERNS:
                for match in pattern.finditer(text):
                    ref_point = self._create_ref_point(
                        match, target_type, text, idx
                    )
                    if ref_point:
                        ref_points.append(ref_point)

        return ref_points

    def _create_ref_point(self, match: re.Match, target_type: RefTargetType,
                          context: str, element_index: int) -> Optional[RefPoint]:
        """从正则匹配创建引用点"""
        ref_text = match.group(0)

        if target_type == RefTargetType.FIGURE:
            if match.lastindex >= 2:
                try:
                    ch, seq = int(match.group(1)), int(match.group(2))
                    number = f"{ch}-{seq}"
                except ValueError:
                    return None
            else:
                try:
                    number = str(int(match.group(1)))
                except ValueError:
                    return None

        elif target_type == RefTargetType.TABLE:
            if match.lastindex >= 2:
                try:
                    ch, seq = int(match.group(1)), int(match.group(2))
                    number = f"{ch}-{seq}"
                except ValueError:
                    return None
            else:
                try:
                    number = str(int(match.group(1)))
                except ValueError:
                    return None

        elif target_type == RefTargetType.EQUATION:
            try:
                ch, seq = int(match.group(1)), int(match.group(2))
                number = f"{ch}-{seq}"
            except (ValueError, IndexError):
                return None

        elif target_type == RefTargetType.CHAPTER:
            raw = match.group(1)
            cn_map = {
                "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
                "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
                "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
            }
            number = str(cn_map.get(raw, 0))
            if number == "0":
                try:
                    number = str(int(raw))
                except ValueError:
                    return None

        elif target_type == RefTargetType.REFERENCE:
            # 参考文献可能一次引用多个：[1,3,5]
            refs_str = match.group(1)
            numbers = re.findall(r"\d+", refs_str)
            if len(numbers) == 1:
                number = numbers[0]
            else:
                # 多个引用，为每个创建单独的引用点
                # 这里先返回 None，在 scan 中特殊处理
                return None  # 由下面的多引用处理逻辑接管

        else:
            return None

        return RefPoint(
            ref_text=ref_text,
            target_type=target_type,
            target_number=number,
            context=context,
            element_index=element_index,
            start_pos=match.start(),
            end_pos=match.end(),
        )

    def scan_multi_references(self, doc: DocumentModel) -> list[RefPoint]:
        """扫描文档中的多参考文献引用（如 [1,3,5]）"""
        ref_points: list[RefPoint] = []
        multi_pattern = re.compile(r"\[(\d+(?:\s*[,，;；]\s*\d+)*)\]")

        for idx, elem in enumerate(doc.elements):
            if not elem.content or elem.element_type == ElementType.HEADING:
                continue

            for match in multi_pattern.finditer(elem.content):
                refs_str = match.group(1)
                numbers = re.findall(r"\d+", refs_str)
                for num in numbers:
                    ref_points.append(RefPoint(
                        ref_text=f"[{num}]",
                        target_type=RefTargetType.REFERENCE,
                        target_number=num,
                        context=elem.content,
                        element_index=idx,
                        start_pos=match.start(),
                        end_pos=match.end(),
                    ))

        return ref_points


# ============================================================
# 匹配与校验器
# ============================================================

class CrossRefMatcher:
    """匹配与校验器 — 检查引用是否有效"""

    def match(self, targets: list[RefTarget],
              ref_points: list[RefPoint]) -> CrossRefReport:
        """执行匹配，生成报告"""
        report = CrossRefReport(targets=targets, ref_points=ref_points)

        # 构建目标索引：按 (类型, 编号) 快速查找
        target_index: dict[tuple[str, str], RefTarget] = {}
        for t in targets:
            key = (t.target_type.value, t.number)
            if key not in target_index:
                target_index[key] = t

        # 匹配每个引用点
        for rp in ref_points:
            key = (rp.target_type.value, rp.target_number)
            target = target_index.get(key)

            if target is None:
                # 悬空引用
                match = CrossRefMatch(
                    ref_point=rp,
                    target=RefTarget(
                        target_type=rp.target_type,
                        number=rp.target_number,
                        label=f"未知{rp.target_type.value}",
                    ),
                    status=CrossRefStatus.DANGLING,
                    message='找不到目标："' + rp.ref_text + '"',
                )
            else:
                rp.matched_target = target
                match = CrossRefMatch(
                    ref_point=rp,
                    target=target,
                    status=CrossRefStatus.VALID,
                )

            report.matches.append(match)

        # 检查未被引用的目标
        referenced_targets: set[tuple[str, str]] = set()
        for rp in ref_points:
            referenced_targets.add((rp.target_type.value, rp.target_number))

        for t in targets:
            key = (t.target_type.value, t.number)
            if key not in referenced_targets:
                report.matches.append(CrossRefMatch(
                    ref_point=RefPoint(ref_text="", target_type=t.target_type,
                                       target_number=t.number),
                    target=t,
                    status=CrossRefStatus.UNREFERENCED,
                    message='目标未被引用："' + t.label + '"',
                ))

        # 检查重复编号
        seen: dict[tuple[str, str], list[RefTarget]] = {}
        for t in targets:
            key = (t.target_type.value, t.number)
            if key not in seen:
                seen[key] = []
            seen[key].append(t)

        for key, group in seen.items():
            if len(group) > 1:
                for t in group[1:]:
                    report.matches.append(CrossRefMatch(
                        ref_point=RefPoint(ref_text="", target_type=t.target_type,
                                           target_number=t.number),
                        target=t,
                        status=CrossRefStatus.DUPLICATE,
                        message='重复编号："' + t.label + '"',
                    ))

        return report


# ============================================================
# 交叉引用引擎（统一入口）
# ============================================================

class CrossRefEngine:
    """交叉引用引擎 — 统一入口"""

    def __init__(self, rules: Optional[CrossRefRules] = None):
        self.rules = rules or CrossRefRules()
        self.target_scanner = TargetScanner()
        self.ref_scanner = RefPointScanner()
        self.matcher = CrossRefMatcher()

    def check(self, doc: DocumentModel) -> CrossRefReport:
        """执行完整的交叉引用检查"""
        if not self.rules.enabled:
            return CrossRefReport()

        # 1. 扫描目标
        targets = self.target_scanner.scan(doc)

        # 2. 扫描引用点
        ref_points = self.ref_scanner.scan(doc)

        # 2.5 扫描多参考文献引用
        multi_refs = self.ref_scanner.scan_multi_references(doc)
        ref_points.extend(multi_refs)

        # 3. 匹配与校验
        report = self.matcher.match(targets, ref_points)

        return report

    def get_interactive_suggestions(self, report: CrossRefReport) -> list[dict]:
        """获取需要用户确认的交互建议

        用于 UI 层展示，让用户确认是否执行自动修复。
        返回格式：[{"type": "dangling", "ref": "...", "suggestion": "..."}, ...]
        """
        suggestions = []

        for m in report.matches:
            if m.status == CrossRefStatus.DANGLING:
                suggestions.append({
                    "type": "dangling",
                    "ref": m.ref_point.ref_text,
                    "context": m.ref_point.context,
                    "message": m.message,
                    "suggestion": '请检查引用"' + m.ref_point.ref_text + '"是否正确',
                })
            elif m.status == CrossRefStatus.UNREFERENCED:
                suggestions.append({
                    "type": "unreferenced",
                    "target": m.target.label,
                    "message": m.message,
                    "suggestion": '目标"' + m.target.label + '"未被引用，是否需要添加引用？',
                })
            elif m.status == CrossRefStatus.DUPLICATE:
                suggestions.append({
                    "type": "duplicate",
                    "target": m.target.label,
                    "message": m.message,
                    "suggestion": '存在重复编号"' + m.target.label + '"，请检查',
                })

        return suggestions
