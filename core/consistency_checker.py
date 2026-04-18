"""
数据一致性检查器 (Consistency Checker)

检查文档中数字、日期、专有名词等前后是否一致。
"""

from __future__ import annotations

import re
from typing import Optional
from collections import defaultdict

from core.document_model import DocumentModel, DocElement, ElementType
from core.qa_models import QAIssue, QAReport, IssueCategory, IssueSeverity


class ConsistencyChecker:
    """数据一致性检查器
    
    功能：
    1. 数字一致性检查（百分比、金额、统计数据）
    2. 日期时间一致性（日期格式、时间顺序）
    3. 专有名词一致性（机构名、人名、地名）
    4. 术语一致性（专业术语、缩写）
    5. 计量单位一致性（单位统一性）
    """

    def __init__(self):
        self.enabled = True
        self.check_numbers = True
        self.check_dates = True
        self.check_names = True
        self.check_terms = True  # 术语检查
        self.check_units = True  # 单位检查

    def check(self, doc: DocumentModel) -> QAReport:
        """对文档执行一致性检查"""
        report = QAReport()

        if self.check_numbers:
            self._check_numbers(doc, report)

        if self.check_dates:
            self._check_dates(doc, report)

        if self.check_names:
            self._check_proper_nouns(doc, report)

        if self.check_terms:
            self._check_terms(doc, report)

        if self.check_units:
            self._check_units(doc, report)

        return report

    def _check_numbers(self, doc: DocumentModel, report: QAReport):
        """检查数字一致性"""
        # 提取所有数字（含千位分隔符）
        number_pattern = re.compile(r"(\d[\d,，]*\d|\d)(?:\.\d+)?")

        # 按数值分组
        number_occurrences: dict[str, list[tuple[int, int, str]]] = defaultdict(list)

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            for match in number_pattern.finditer(elem.content):
                raw = match.group(1)
                # 标准化：去除千位分隔符
                normalized = raw.replace(",", "").replace("，", "")
                number_occurrences[normalized].append(
                    (idx, match.start(), raw)
                )

        # 检查同一数字的不同表示（如 "1,000" vs "1000"）
        for normalized, occurrences in number_occurrences.items():
            if len(occurrences) < 2:
                continue

            raw_values = set(raw for _, _, raw in occurrences)
            if len(raw_values) > 1:
                # 同一数值有不同格式
                for elem_idx, pos, raw in occurrences:
                    if raw != list(raw_values)[0]:
                        issue = QAIssue(
                            category=IssueCategory.INCONSISTENCY,
                            severity=IssueSeverity.INFO,
                            title=f"数字格式不一致：{raw}",
                            description=f"数值 {normalized} 在文档中存在多种格式表示：{', '.join(raw_values)}",
                            suggestion=f"统一使用格式：{list(raw_values)[0]}",
                            element_index=elem_idx,
                            element_type="paragraph",
                            location_text=raw,
                            confidence=0.7,
                        )
                        report.add_issue(issue)

    def _check_dates(self, doc: DocumentModel, report: QAReport):
        """检查日期一致性"""
        # 匹配各种日期格式
        date_patterns = [
            r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",  # 2024年3月15日
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",              # 2024-03-15
            r"(\d{4})\.(\d{1,2})\.(\d{1,2})",                   # 2024.03.15
        ]

        date_occurrences: dict[str, list[tuple[int, str]]] = defaultdict(list)

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            for pattern in date_patterns:
                for match in re.finditer(pattern, elem.content):
                    raw = match.group(0)
                    # 标准化为 YYYY-MM-DD
                    year, month, day = match.group(1), match.group(2), match.group(3)
                    normalized = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    date_occurrences[normalized].append((idx, raw))

        # 检查同一日期的不同格式
        for normalized, occurrences in date_occurrences.items():
            if len(occurrences) < 2:
                continue
            raw_values = set(raw for _, raw in occurrences)
            if len(raw_values) > 1:
                for elem_idx, raw in occurrences:
                    if raw != list(raw_values)[0]:
                        issue = QAIssue(
                            category=IssueCategory.INCONSISTENCY,
                            severity=IssueSeverity.WARNING,
                            title=f"日期格式不一致：{raw}",
                            description=f"日期 {normalized} 存在多种格式：{', '.join(raw_values)}",
                            suggestion=f"统一使用格式：{list(raw_values)[0]}",
                            element_index=elem_idx,
                            element_type="paragraph",
                            location_text=raw,
                            confidence=0.8,
                        )
                        report.add_issue(issue)

    def _check_proper_nouns(self, doc: DocumentModel, report: QAReport):
        """检查专有名词一致性

        两轮检查：
        1. 提取所有机构名称（后缀匹配），比较名称间相似度
        2. 对每个已提取名称，在全文中模糊搜索相似子串（捕获拼写错误）
        """
        # 提取可能的专有名词（机构名称）
        # 限制前缀 2-4 字符，避免贪婪匹配到前面的动词/介词
        org_pattern = re.compile(
            r"([\u4e00-\u9fff]{2,4}(?:公司|集团|大学|学院|研究院|研究所|医院|政府|部门|委员会|中心))"
        )

        # 收集所有提取到的机构名称
        found_names: dict[str, list[tuple[int, str]]] = defaultdict(list)

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            for match in org_pattern.finditer(elem.content):
                name = match.group(1)
                found_names[name].append((idx, match.group(0)))

        # 已检查过的名称对（避免重复报告）
        checked_pairs: set[tuple[str, str]] = set()

        # 第一轮：检查提取到的名称之间的相似性
        names = list(found_names.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a, name_b = names[i], names[j]
                if self._edit_distance(name_a, name_b) <= 2:
                    pair = tuple(sorted([name_a, name_b]))
                    if pair in checked_pairs:
                        continue
                    checked_pairs.add(pair)
                    for elem_idx, raw in found_names[name_b]:
                        issue = QAIssue(
                            category=IssueCategory.INCONSISTENCY,
                            severity=IssueSeverity.WARNING,
                            title='专有名词疑似不一致："' + raw + '"',
                            description='文档中同时出现"' + name_a + '"和"' + name_b + '"，可能是笔误',
                            suggestion='请确认是否应统一为"' + name_a + '"或"' + name_b + '"',
                            element_index=elem_idx,
                            element_type="paragraph",
                            location_text=raw,
                            related_text=name_a,
                            confidence=0.6,
                        )
                        report.add_issue(issue)

        # 第二轮：对每个已提取的名称，在文档中搜索相似字符串
        # 用于捕获拼写错误的机构名称（错误名称可能不含标准后缀）
        for name in names:
            name_len = len(name)
            for idx, elem in enumerate(doc.elements):
                if not elem.content:
                    continue
                text = elem.content
                # 滑动窗口：只检查长度相近的子串（±1字符）
                for start in range(len(text)):
                    for length in range(max(2, name_len - 1), name_len + 1):
                        end = start + length
                        if end > len(text):
                            break
                        candidate = text[start:end]
                        # 跳过完全相同的名称
                        if candidate == name:
                            continue
                        # 跳过子串关系（避免部分匹配误报）
                        if candidate in name or name in candidate:
                            continue
                        # 快速预检：至少一半字符相同才计算编辑距离
                        common = sum(1 for a, b in zip(name, candidate) if a == b)
                        if common < max(2, len(name) * 0.5):
                            continue
                        if self._edit_distance(name, candidate) <= 2:
                            pair = tuple(sorted([name, candidate]))
                            if pair in checked_pairs:
                                continue
                            checked_pairs.add(pair)
                            issue = QAIssue(
                                category=IssueCategory.INCONSISTENCY,
                                severity=IssueSeverity.WARNING,
                                title='专有名词疑似不一致："' + candidate + '"',
                                description='文档中同时出现"' + name + '"和"' + candidate + '"，可能是笔误',
                                suggestion='请确认是否应统一为"' + name + '"或"' + candidate + '"',
                                element_index=idx,
                                element_type="paragraph",
                                location_text=candidate,
                                related_text=name,
                                confidence=0.5,
                            )
                            report.add_issue(issue)

    @staticmethod
    def _edit_distance(s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            return ConsistencyChecker._edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        prev_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row

        return prev_row[-1]

    def _check_terms(self, doc: DocumentModel, report: QAReport):
        """检查术语一致性
        
        检查常见术语的不同表达方式，如：
        - 人工智能 vs AI
        - 机器学习 vs ML
        - 深度学习 vs DL
        """
        # 常见术语对照表：{标准术语：[别名，缩写]}
        term_mapping = {
            "人工智能": ["AI", "artificial intelligence"],
            "机器学习": ["ML", "machine learning"],
            "深度学习": ["DL", "deep learning"],
            "神经网络": ["NN", "neural network"],
            "卷积神经网络": ["CNN", "convolutional neural network"],
            "循环神经网络": ["RNN", "recurrent neural network"],
            "自然语言处理": ["NLP", "natural language processing"],
            "计算机视觉": ["CV", "computer vision"],
            "强化学习": ["RL", "reinforcement learning"],
            "生成对抗网络": ["GAN", "generative adversarial network"],
            "支持向量机": ["SVM", "support vector machine"],
            "主成分分析": ["PCA", "principal component analysis"],
            "逻辑回归": ["LR", "logistic regression"],
            "决策树": ["DT", "decision tree"],
            "随机森林": ["RF", "random forest"],
            "梯度提升": ["GBDT", "gradient boosting decision tree"],
            "长短期记忆": ["LSTM", "long short-term memory"],
            "Transformer": ["transformer", "注意力机制"],
            "大语言模型": ["LLM", "large language model"],
            "预训练模型": ["pre-trained model", "基础模型"],
        }
        
        # 收集文档中出现的术语
        found_terms: dict[str, list[tuple[int, str]]] = defaultdict(list)
        
        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            text = elem.content
            
            # 检查每个术语及其别名
            for standard_term, aliases in term_mapping.items():
                # 检查标准术语
                if standard_term in text:
                    found_terms[standard_term].append((idx, standard_term))
                
                # 检查别名
                for alias in aliases:
                    if alias in text:
                        found_terms[standard_term].append((idx, alias))
        
        # 检查同一术语的不同表达
        for standard_term, occurrences in found_terms.items():
            if len(occurrences) < 2:
                continue
            
            used_forms = set(form for _, form in occurrences)
            if len(used_forms) > 1:
                # 同一术语有多种表达
                aliases = [form for form in used_forms if form != standard_term]
                if aliases:
                    for elem_idx, form in occurrences:
                        if form != standard_term:
                            issue = QAIssue(
                                category=IssueCategory.INCONSISTENCY,
                                severity=IssueSeverity.INFO,
                                title=f"术语不统一：{form}",
                                description=f"术语'{standard_term}'在文档中有多种表达：{', '.join(used_forms)}",
                                suggestion=f"建议统一使用标准术语：{standard_term}",
                                element_index=elem_idx,
                                element_type="paragraph",
                                location_text=form,
                                related_text=standard_term,
                                confidence=0.6,
                            )
                            report.add_issue(issue)

    def _check_units(self, doc: DocumentModel, report: QAReport):
        """检查计量单位一致性
        
        检查同一物理量的不同单位表示，如：
        - km vs 公里
        - kg vs 千克
        - m vs 米
        """
        # 单位对照表：{标准单位：[同义单位，缩写]}
        unit_mapping = {
            "米": ["m", "meter", "meters"],
            "千米": ["km", "kilometer", "kilometers", "公里"],
            "厘米": ["cm", "centimeter", "centimeters"],
            "毫米": ["mm", "millimeter", "millimeters"],
            "千克": ["kg", "kilogram", "kilograms", "公斤"],
            "克": ["g", "gram", "grams"],
            "吨": ["t", "ton", "tons"],
            "升": ["L", "l", "liter", "liters"],
            "毫升": ["mL", "ml", "milliliter", "milliliters"],
            "平方米": ["m²", "m2", "square meter"],
            "立方米": ["m³", "m3", "cubic meter"],
            "秒": ["s", "second", "seconds"],
            "分钟": ["min", "minute", "minutes"],
            "小时": ["h", "hour", "hours"],
            "天": ["d", "day", "days"],
            "年": ["y", "year", "years"],
            "摄氏度": ["°C", "℃", "Celsius"],
            "华氏度": ["°F", "Fahrenheit"],
            "开尔文": ["K", "Kelvin"],
            "帕斯卡": ["Pa", "pascal"],
            "牛顿": ["N", "newton"],
            "焦耳": ["J", "joule"],
            "瓦特": ["W", "watt"],
            "伏特": ["V", "volt"],
            "安培": ["A", "ampere"],
            "欧姆": ["Ω", "ohm"],
            "赫兹": ["Hz", "hertz"],
            "字节": ["B", "byte", "bytes"],
            "千字节": ["KB", "kB", "kilobyte"],
            "兆字节": ["MB", "megabyte"],
            "吉字节": ["GB", "gigabyte"],
            "太字节": ["TB", "terabyte"],
        }
        
        # 收集文档中出现的单位
        found_units: dict[str, list[tuple[int, str]]] = defaultdict(list)
        
        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            text = elem.content
            
            # 检查每个单位及其同义词
            for standard_unit, synonyms in unit_mapping.items():
                # 检查标准单位
                if standard_unit in text:
                    found_units[standard_unit].append((idx, standard_unit))
                
                # 检查同义词
                for synonym in synonyms:
                    if synonym in text:
                        found_units[standard_unit].append((idx, synonym))
        
        # 检查同一物理量的不同单位
        for standard_unit, occurrences in found_units.items():
            if len(occurrences) < 2:
                continue
            
            used_forms = set(form for _, form in occurrences)
            if len(used_forms) > 1:
                # 同一单位有多种表达
                variants = [form for form in used_forms if form != standard_unit]
                if variants:
                    for elem_idx, form in occurrences:
                        if form != standard_unit:
                            issue = QAIssue(
                                category=IssueCategory.INCONSISTENCY,
                                severity=IssueSeverity.INFO,
                                title=f"单位不统一：{form}",
                                description=f"单位'{standard_unit}'在文档中有多种表达：{', '.join(used_forms)}",
                                suggestion=f"建议统一使用标准单位：{standard_unit}",
                                element_index=elem_idx,
                                element_type="paragraph",
                                location_text=form,
                                related_text=standard_unit,
                                confidence=0.6,
                            )
                            report.add_issue(issue)
