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

    # 参考文献节标题检测（匹配常见中英文写法）
    REF_SECTION_PATTERN = re.compile(
        r"参考文献|references?\b|bibliography", re.IGNORECASE
    )

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
        re.compile(r"^第([一二三四五六七八九十百零〇\d]+)章\s*(.*)$"),
        re.compile(r"^(\d+)\s*[\.、]\s*(.*)$"),  # "1 标题" 或 "1、标题"
    ]

    # 参考文献模式
    REFERENCE_PATTERN = re.compile(r"^\s*\[(\d+)\]\s*(.*)")

    def scan(self, doc: DocumentModel) -> list[RefTarget]:
        """扫描文档，提取所有引用目标"""
        targets: list[RefTarget] = []
        current_chapter = 0
        in_ref_section = False
        ref_seq = 0  # sequential counter for un-numbered bibliography entries

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue

            # 第十八批：目录条目 / 封面 不作为交叉引用目标，避免把目录里的"第3章 ......15"当真章节
            if isinstance(elem.metadata, dict) and elem.metadata.get("exclude_from_xref_targets"):
                continue

            text = elem.content.strip()

            # ── 标题：判断是否进入/退出参考文献节（标题本身不作为交叉引用目标）──
            if elem.element_type == ElementType.HEADING:
                if self.REF_SECTION_PATTERN.search(text):
                    in_ref_section = True
                    ref_seq = 0
                    continue

                in_ref_section = False
                chapter = self._try_match_chapter(elem, idx)
                if chapter:
                    current_chapter = chapter.chapter_num
                    targets.append(chapter)
                continue

            # ── 参考文献节内部：按位置顺序编号 ──
            if in_ref_section:
                if elem.element_type in (ElementType.PARAGRAPH, ElementType.REFERENCE) and text:
                    m = self.REFERENCE_PATTERN.match(text)
                    if m:
                        # 显式 [N] 前缀（如 Word 导出时有编号）
                        seq_num = int(m.group(1))
                        title = m.group(2).strip()
                    else:
                        # 无显式编号：按出现顺序分配
                        ref_seq += 1
                        seq_num = ref_seq
                        title = text
                    targets.append(RefTarget(
                        target_type=RefTargetType.REFERENCE,
                        number=str(seq_num),
                        label=f"[{seq_num}]",
                        title=title[:120],
                        element_index=idx,
                        seq_num=seq_num,
                        bookmark_name=f"_ref_{seq_num}",
                    ))
                continue

            # ── 参考文献节之外：现有检测逻辑 ──
            fig = self._try_match_figure(elem, idx, current_chapter)
            if fig:
                targets.append(fig)
                continue

            tbl = self._try_match_table(elem, idx, current_chapter)
            if tbl:
                targets.append(tbl)
                continue

            eq = self._try_match_equation(elem, idx, current_chapter)
            if eq:
                targets.append(eq)
                continue

            # ElementType.REFERENCE 带显式 [N] 前缀（非参考文献节场景兜底）
            ref = self._try_match_reference(elem, idx)
            if ref:
                targets.append(ref)

        return targets

    def _try_match_chapter(self, elem: DocElement, idx: int) -> Optional[RefTarget]:
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
                element_index=idx,
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
        """单遍扫描，按文档阅读顺序分配全局递增 scan_index。

        核心不变量：输出序列 = 文档从前到后扫描到的引用 token 序列（保真映射）。
        - 段内按 match.start() 排序后统一分配 scan_index，再合并到全局列表。
        - 多引用（如 [2,3,6,7]）在同一 span 内展开，展开顺序即为 findall 顺序。
        - 不允许任何按 reference/target_label 的重排。
        """
        ref_points: list[RefPoint] = []
        scan_index = 0

        for elem_idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            if elem.element_type in (ElementType.HEADING, ElementType.REFERENCE):
                continue

            text = elem.content
            para_hits: list[tuple[int, list[RefPoint]]] = []
            seen_spans: set[tuple[int, int]] = set()

            for target_type, pattern in self.REF_PATTERNS:
                for match in pattern.finditer(text):
                    span = (match.start(), match.end())
                    if span in seen_spans:
                        continue
                    rps = self._expand_match(match, target_type, text, elem_idx)
                    if rps:
                        seen_spans.add(span)
                        para_hits.append((match.start(), rps))

            para_hits.sort(key=lambda x: x[0])

            for _, rps in para_hits:
                for rp in rps:
                    rp.scan_index = scan_index
                    scan_index += 1
                    ref_points.append(rp)

        return ref_points

    def _expand_match(self, match: re.Match, target_type: RefTargetType,
                      context: str, element_index: int) -> list[RefPoint]:
        """将正则匹配展开为一个或多个 RefPoint。

        REFERENCE 多引用（如 [1,3,5]）展开为多个 RefPoint；其余类型最多产生一个。
        """
        ref_text = match.group(0)

        if target_type == RefTargetType.FIGURE:
            if match.lastindex >= 2:
                try:
                    ch, seq = int(match.group(1)), int(match.group(2))
                    number = f"{ch}-{seq}"
                except ValueError:
                    return []
            else:
                try:
                    number = str(int(match.group(1)))
                except ValueError:
                    return []
            return [RefPoint(ref_text=ref_text, target_type=target_type,
                             target_number=number, context=context,
                             element_index=element_index,
                             start_pos=match.start(), end_pos=match.end())]

        elif target_type == RefTargetType.TABLE:
            if match.lastindex >= 2:
                try:
                    ch, seq = int(match.group(1)), int(match.group(2))
                    number = f"{ch}-{seq}"
                except ValueError:
                    return []
            else:
                try:
                    number = str(int(match.group(1)))
                except ValueError:
                    return []
            return [RefPoint(ref_text=ref_text, target_type=target_type,
                             target_number=number, context=context,
                             element_index=element_index,
                             start_pos=match.start(), end_pos=match.end())]

        elif target_type == RefTargetType.EQUATION:
            try:
                ch, seq = int(match.group(1)), int(match.group(2))
                number = f"{ch}-{seq}"
            except (ValueError, IndexError):
                return []
            return [RefPoint(ref_text=ref_text, target_type=target_type,
                             target_number=number, context=context,
                             element_index=element_index,
                             start_pos=match.start(), end_pos=match.end())]

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
                    return []
            return [RefPoint(ref_text=ref_text, target_type=target_type,
                             target_number=number, context=context,
                             element_index=element_index,
                             start_pos=match.start(), end_pos=match.end())]

        elif target_type == RefTargetType.REFERENCE:
            refs_str = match.group(1)
            numbers = re.findall(r"\d+", refs_str)
            if not numbers:
                return []
            return [RefPoint(
                ref_text=f"[{num}]",
                target_type=target_type,
                target_number=num,
                context=context,
                element_index=element_index,
                start_pos=match.start(),
                end_pos=match.end(),
            ) for num in numbers]

        return []

    def scan_multi_references(self, doc: DocumentModel) -> list[RefPoint]:
        """已废弃：功能已合并至 scan()。保留方法签名供向后兼容，始终返回空列表。"""
        return []


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

        # 2. 扫描引用点（单遍，含多引用展开，scan_index 已赋值）
        ref_points = self.ref_scanner.scan(doc)

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
