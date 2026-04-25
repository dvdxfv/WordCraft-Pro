"""
标点/格式检查器 (Punctuation & Formatting Checker)

基于规则的非 AI 可检测常见错误：
1. 中英文标点混用（中文句末使用英文 . , ? ! ; : ）
2. 连续重复标点（。。。、！！、？？、，，）
3. 中英文之间缺少空格（CJK ↔ ASCII 数字/字母）
4. 全角/半角数字混用（如 ２０２５ 应为 2025）
5. 括号/引号不配对（( )、（ ）、" "、" "、【 】、《 》）
6. 连续重复汉字（如"的的"、"了了"、"是是"；三字以上基本都是错）
7. 空段（除章节转折外不应该有连续空白段）
"""

from __future__ import annotations

import re
from typing import Optional

from core.document_model import DocumentModel, DocElement, ElementType
from core.qa_models import QAIssue, QAReport, IssueCategory, IssueSeverity


# 中文范围：CJK 统一汉字 + 标点（不含 ASCII）
_CJK = r"\u4e00-\u9fff"

# 英文标点 → 中文标点 的映射（句末位置时应使用中文）
_EN_PUNCT_TO_CN = {
    ",": "，",
    ".": "。",
    "?": "？",
    "!": "！",
    ":": "：",
    ";": "；",
}

# 成对括号/引号
_PAIR_MAP = {
    "（": "）",
    "(": ")",
    "【": "】",
    "[": "]",
    "《": "》",
    "<": ">",
    "{": "}",
    "「": "」",
    "『": "』",
    "\u201c": "\u201d",   # 中文双引号 " "
    "\u2018": "\u2019",   # 中文单引号 ' '
}

# 不应重复出现的汉字白名单（这些叠字是合法的，不能误报）
_VALID_REDUP = {
    "人", "天", "日", "月", "年", "分", "种", "样", "次",
    "家", "各", "个", "件", "位", "条", "层", "片", "串",
    "爸", "妈", "哥", "姐", "弟", "妹", "爷", "奶", "叔", "姑", "舅", "姨",
    "宝", "乖", "娃", "咪",
    "红", "绿", "黄", "蓝", "黑", "白", "灰",
    "高", "矮", "胖", "瘦", "长", "短", "大", "小", "多", "少",
    "快", "慢", "好", "坏", "美", "丑", "干", "湿", "冷", "热", "深", "浅",
    "闪", "亮", "暗", "晃",
    "看", "说", "想", "听", "走", "跑", "笑", "哭", "睡",
    "纷", "茫", "蒙", "沉", "往", "熊", "悄", "隐", "默",
    "刚", "常", "偏", "偶",
    "每", "仅", "单", "独", "仍", "依",
    "慢慢", "快快", "渐渐", "缓缓",   # 特殊：这里是双字叠字，下面作为整体过滤
}

# 在学术/科技文本中常作为合成词词尾和词首的字符（如"南海|海表"、"生物|物理"）
# 当这些字符两侧均为汉字时，很可能是词界碰撞而非输入错误
_BOUNDARY_CHARS = {
    # 自然地理
    "海", "洋", "湖", "江", "河", "湾", "陆", "岸", "岛", "礁",
    # 方位/结构
    "面", "表", "底", "层", "端", "侧", "边", "角", "心", "中", "间",
    # 科学量纲（常作独立名词，也常嵌入合成词）
    "数", "量", "率", "度", "力", "场", "流", "压", "能", "温",
    # 学科词素
    "物", "学", "术", "理", "性", "体", "态", "型", "式", "法",
    "论", "制", "观", "境", "状", "势", "系", "素", "质",
    # 信息/技术
    "点", "线", "路", "道", "图", "文", "字", "语", "词",
    # 物理/海洋常见词素
    "波", "热", "声", "光", "电", "磁", "动", "静", "化",
}


class PunctuationChecker:
    """标点、空格、括号、重复字等格式检查器（全部基于规则，不依赖 AI）"""

    def __init__(self):
        self.enabled = True
        self.check_mixed_punct = True       # 中英文标点混用
        self.check_repeat_punct = True      # 连续重复标点
        self.check_cjk_spacing = False      # 中英文之间空格（学术文档常见合法写法，默认关闭）
        self.check_fullwidth_digit = True   # 全角数字
        self.check_bracket_pair = True      # 括号/引号配对
        self.check_repeat_char = True       # 连续重复汉字
        self.check_sentence_gap = True      # 句间异常空格
        self.check_unit_norm = True         # 单位规范（ug/L 等）

    def check(self, doc: DocumentModel) -> QAReport:
        report = QAReport()

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            text = elem.content
            et = elem.element_type.value if hasattr(elem.element_type, 'value') else str(elem.element_type)

            if self.check_mixed_punct:
                self._check_mixed_punct(text, idx, et, report)
            if self.check_repeat_punct:
                self._check_repeat_punct(text, idx, et, report)
            if self.check_cjk_spacing:
                self._check_cjk_spacing(text, idx, et, report)
            if self.check_fullwidth_digit:
                self._check_fullwidth_digit(text, idx, et, report)
            if self.check_repeat_char:
                self._check_repeat_char(text, idx, et, report)
            if self.check_sentence_gap:
                self._check_sentence_gap(text, idx, et, report)
            if self.check_unit_norm:
                self._check_unit_norm(text, idx, et, report)

        if self.check_bracket_pair:
            # 括号配对是全文级别的
            self._check_bracket_pair(doc, report)

        return report

    # ------------------------------------------------------------------
    #  规则 1：中英文标点混用
    # ------------------------------------------------------------------
    def _check_mixed_punct(self, text: str, idx: int, et: str, report: QAReport):
        # 汉字后紧跟 ASCII 标点 → 很可能是误用
        pattern = re.compile(rf"([{_CJK}])\s*([,\.;:\?!])(?!\d)")
        seen = set()
        for m in pattern.finditer(text):
            cjk = m.group(1)
            en_p = m.group(2)
            # 小数点在数字间是合法的，这里已经用 (?!\d) 排除
            # 但 "Python." 或英文缩写情况：前字是 CJK 所以只会匹配中文后，OK
            key = (en_p, m.start())
            if key in seen:
                continue
            seen.add(key)
            cn_p = _EN_PUNCT_TO_CN.get(en_p, en_p)
            snippet_start = max(0, m.start() - 8)
            snippet_end = min(len(text), m.end() + 8)
            report.add_issue(QAIssue(
                category=IssueCategory.FORMAT,
                severity=IssueSeverity.WARNING,
                title=f'中英文标点混用："{cjk}{en_p}"',
                description=f'中文文本后应使用中文标点"{cn_p}"，而非英文"{en_p}"',
                suggestion=f"{cjk}{cn_p}",
                rule_id="format.mixed_punctuation",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=f"{cjk}{en_p}",
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.85,
            ))

    # ------------------------------------------------------------------
    #  规则 2：连续重复标点
    # ------------------------------------------------------------------
    def _check_repeat_punct(self, text: str, idx: int, et: str, report: QAReport):
        # 句号：。。、。。。；感叹：！！；问号：？？；逗号：，，
        # 英文感叹/问号连用：!! 、 ?? ，合法省略号 …… 或 ... 不在此范围
        for raw, cn in [("。。", "。"), ("！！", "！"), ("？？", "？"),
                         ("，，", "，"), ("；；", "；"), ("：：", "："),
                         ("!!", "!"), ("??", "?"), (",,", ",")]:
            start = 0
            while True:
                pos = text.find(raw, start)
                if pos == -1:
                    break
                # 特殊：三个点 "..." 是合法省略号，不报；省略号 …… 也是合法
                report.add_issue(QAIssue(
                    category=IssueCategory.FORMAT,
                    severity=IssueSeverity.WARNING,
                    title=f'连续重复标点："{raw}"',
                    description=f'文中出现连续重复的"{raw[0]}"，建议简化为单个"{cn}"或使用省略号',
                    suggestion=cn,
                    rule_id="format.repeat_punctuation",
                    checker="punctuation_checker",
                    element_index=idx,
                    element_type=et,
                    location_text=raw,
                    start_pos=pos,
                    end_pos=pos + len(raw),
                    confidence=0.9,
                ))
                start = pos + len(raw)

    # ------------------------------------------------------------------
    #  规则 3：中英文/中文与数字之间缺少空格
    # ------------------------------------------------------------------
    def _check_cjk_spacing(self, text: str, idx: int, et: str, report: QAReport):
        # CJK ↔ 拉丁字母：如 "使用Python" → "使用 Python"
        # 仅报告，不强制（INFO 级）
        pattern = re.compile(rf"([{_CJK}])([A-Za-z])|([A-Za-z])([{_CJK}])")
        count = 0
        for m in pattern.finditer(text):
            if count >= 3:  # 每段最多报 3 条，避免刷屏
                break
            count += 1
            around = m.group(0)
            report.add_issue(QAIssue(
                category=IssueCategory.FORMAT,
                severity=IssueSeverity.INFO,
                title=f'中英文间缺少空格："{around}"',
                description="中文与英文字母之间建议添加半角空格，提升可读性",
                suggestion=f"{around[0]} {around[1]}",
                rule_id="format.cjk_ascii_spacing",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=around,
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.4,
            ))

    # ------------------------------------------------------------------
    #  规则 4：全角数字
    # ------------------------------------------------------------------
    def _check_fullwidth_digit(self, text: str, idx: int, et: str, report: QAReport):
        pattern = re.compile(r"[\uff10-\uff19]+")
        for m in pattern.finditer(text):
            raw = m.group(0)
            half = raw.translate({0xff10 + i: 0x30 + i for i in range(10)})
            report.add_issue(QAIssue(
                category=IssueCategory.FORMAT,
                severity=IssueSeverity.WARNING,
                title=f'全角数字："{raw}"',
                description=f'"{raw}"为全角数字，规范文档应使用半角数字"{half}"',
                suggestion=half,
                rule_id="format.fullwidth_digit",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=raw,
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.95,
            ))

    # ------------------------------------------------------------------
    #  规则 5：括号/引号配对（全文级别）
    # ------------------------------------------------------------------
    def _check_bracket_pair(self, doc: DocumentModel, report: QAReport):
        # 检查每个元素内是否括号左右数量一致（跨段匹配概率低，不做跨段）
        pairs = {
            "（": "）", "(": ")", "【": "】", "[": "]",
            "《": "》", "{": "}", "「": "」", "『": "』",
        }
        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            text = elem.content
            for left, right in pairs.items():
                lc = text.count(left)
                rc = text.count(right)
                if lc != rc:
                    report.add_issue(QAIssue(
                        category=IssueCategory.FORMAT,
                        severity=IssueSeverity.WARNING,
                        title=f'括号不配对："{left}{right}"',
                        description=f'该段落中"{left}"出现 {lc} 次，"{right}"出现 {rc} 次，可能存在未闭合的括号',
                        suggestion="检查并补全对应括号",
                        rule_id="format.bracket_pair",
                        checker="punctuation_checker",
                        element_index=idx,
                        element_type=elem.element_type.value,
                        location_text=text[:60] + ("..." if len(text) > 60 else ""),
                        confidence=0.85,
                    ))

    # ------------------------------------------------------------------
    #  规则 6：连续重复汉字
    # ------------------------------------------------------------------
    def _check_repeat_char(self, text: str, idx: int, et: str, report: QAReport):
        # 三个及以上相同汉字连续 → 几乎一定是错误（例："的的的"、"了了了"）
        pattern3 = re.compile(rf"([{_CJK}])\1{{2,}}")
        for m in pattern3.finditer(text):
            raw = m.group(0)
            report.add_issue(QAIssue(
                category=IssueCategory.TYPO,
                severity=IssueSeverity.ERROR,
                title=f'重复字符：连续{len(raw)}个"{raw[0]}"',
                description=f'"{raw}"可能是输入法连击导致的重复字符',
                suggestion=raw[0],
                rule_id="typo.repeat_char_3plus",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=raw,
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.95,
            ))

        # 两个相同汉字连续：排除白名单叠字
        cjk_re = re.compile(rf"[{_CJK}]")
        pattern2 = re.compile(rf"([{_CJK}])\1")
        for m in pattern2.finditer(text):
            ch = m.group(1)
            if ch in _VALID_REDUP:
                continue
            # 若是三字模式已报过，跳过
            if m.start() > 0 and text[m.start() - 1] == ch:
                continue
            if m.end() < len(text) and text[m.end()] == ch:
                continue
            # 词界碰撞过滤：如"南海海表"中"海"在词尾词首均出现
            # 若该字是常见词素且两侧均为汉字，大概率是词界碰撞而非输入错误
            if ch in _BOUNDARY_CHARS:
                prev_ch = text[m.start() - 1] if m.start() > 0 else ''
                next_ch = text[m.end()] if m.end() < len(text) else ''
                if cjk_re.match(prev_ch) and cjk_re.match(next_ch):
                    continue
            # 低置信度，仅提示
            raw = m.group(0)
            report.add_issue(QAIssue(
                category=IssueCategory.TYPO,
                severity=IssueSeverity.INFO,
                title=f'疑似重复字："{raw}"',
                description=f'文中出现"{raw}"，请确认是否为叠字错别字',
                suggestion=ch,
                rule_id="typo.repeat_char_2",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=raw,
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.35,
            ))

    # ------------------------------------------------------------------
    #  规则 7：句间异常空格（疑似缺失句号）
    # ------------------------------------------------------------------
    def _check_sentence_gap(self, text: str, idx: int, et: str, report: QAReport):
        # 形态：中文字符之间出现空格，且前后都不是标点。
        # 单空格（如"发生 研究表明"）和多空格均纳入检测；单空格置信度稍低。
        pattern = re.compile(rf"([{_CJK}])(\s+)([{_CJK}])")
        for m in pattern.finditer(text):
            left = m.group(1)
            spaces = m.group(2)
            right = m.group(3)
            # 允许在已有句末标点后的排版空格
            if m.start() > 0 and text[m.start() - 1] in "。！？；:：":
                continue
            is_single = len(spaces.strip("\n\r")) <= 1
            confidence = 0.65 if is_single else 0.72
            space_desc = "一个空格" if is_single else f"{len(spaces)}个空格"
            report.add_issue(QAIssue(
                category=IssueCategory.FORMAT,
                severity=IssueSeverity.WARNING,
                title=f'句间异常空格："{left}…{right}"',
                description=f"疑似句号缺失：中文句子之间出现{space_desc}，建议改为句号",
                suggestion=f"{left}。{right}",
                rule_id="format.sentence_gap",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=m.group(0),
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=confidence,
            ))

    # ------------------------------------------------------------------
    #  规则 8：单位规范（ug/L -> μg/L）
    # ------------------------------------------------------------------
    def _check_unit_norm(self, text: str, idx: int, et: str, report: QAReport):
        # 注意：Python 3 的 \b 把 CJK 字符视为 \w，导致 "ug/L时" 不触发 \b。
        # 改用 ASCII 限定的 lookahead/lookbehind，在 CJK 上下文中也能正确匹配。
        pattern = re.compile(r"(?<![A-Za-z\d])ug/L(?![A-Za-z\d])", re.IGNORECASE)
        for m in pattern.finditer(text):
            report.add_issue(QAIssue(
                category=IssueCategory.FORMAT,
                severity=IssueSeverity.WARNING,
                title='单位写法不规范："ug/L"',
                description='浓度单位建议使用 "μg/L"（微克每升）',
                suggestion="μg/L",
                rule_id="format.unit.ug_per_l",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=m.group(0),
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.95,
            ))

        # 温度单位写法：数字后有空格再跟 °C，建议去掉空格（如 "28 °C" → "28°C"）
        temp_pattern = re.compile(r"(\d)\s+(°C|℃)", re.IGNORECASE)
        for m in temp_pattern.finditer(text):
            unit = m.group(2)
            report.add_issue(QAIssue(
                category=IssueCategory.FORMAT,
                severity=IssueSeverity.INFO,
                title=f'温度单位前多余空格："{m.group(1)} {unit}"',
                description='中文科技写作中温度单位紧跟数字，建议去掉空格',
                suggestion=f"{m.group(1)}{unit}",
                rule_id="format.unit.celsius_spacing",
                checker="punctuation_checker",
                element_index=idx,
                element_type=et,
                location_text=m.group(0),
                start_pos=m.start(),
                end_pos=m.end(),
                confidence=0.65,
            ))
