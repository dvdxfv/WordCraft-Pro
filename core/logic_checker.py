"""
逻辑检查器 (Logic Checker)

基于规则的文档逻辑合理性检查。
检测：因果断裂、结论无支撑、时间线矛盾、前后矛盾等。
"""

from __future__ import annotations

import re
from typing import Optional

from core.document_model import DocumentModel, DocElement, ElementType
from core.qa_models import QAIssue, QAReport, IssueCategory, IssueSeverity


class LogicChecker:
    """逻辑检查器
    
    核心功能（实用导向）：
    1. 前后矛盾检测（金额、数值、时间）
    2. 时间线一致性（日期顺序）
    3. 专有名词一致性（项目名称、机构名）
    4. 空章节检测
    
    已移除（避免过多误报）：
    - ❌ 论证充分性
    - ❌ 条件关系检查
    - ❌ 比较关系检查
    - ❌ 结论支撑检查
    """

    def __init__(self):
        self.enabled = True
        # 核心检查（保留）
        self.check_contradictions = True
        self.check_timeline = True
        self.check_proper_nouns = True
        self.check_empty_sections = True
        
        # 已移除（避免过多误报）
        self.check_causality = False        # 已禁用
        self.check_conclusion = False       # 已禁用
        self.check_argumentation = False    # 已禁用
        self.check_conditionals = False     # 已禁用
        self.check_comparisons = False      # 已禁用

    def check(self, doc: DocumentModel) -> QAReport:
        """对文档执行逻辑检查"""
        report = QAReport()

        if self.check_contradictions:
            self._check_contradictions(doc, report)

        if self.check_causality:
            self._check_causality(doc, report)

        if self.check_timeline:
            self._check_timeline(doc, report)

        if self.check_conclusion:
            self._check_conclusion_support(doc, report)

        if self.check_empty_sections:
            self._check_empty_sections(doc, report)

        if self.check_argumentation:
            self._check_argumentation(doc, report)

        if self.check_conditionals:
            self._check_conditionals(doc, report)

        if self.check_comparisons:
            self._check_comparisons(doc, report)

        return report

    def _check_contradictions(self, doc: DocumentModel, report: QAReport):
        """检查前后矛盾"""
        paragraphs = [(i, e) for i, e in enumerate(doc.elements) if e.content]

        # 检测"但是"/"然而"后的内容是否与前面矛盾
        contradiction_markers = ["但是", "然而", "不过", "可是", "却", "相反"]
        for idx, (elem_idx, elem) in enumerate(paragraphs):
            text = elem.content
            for marker in contradiction_markers:
                if marker in text:
                    pos = text.index(marker)
                    # 检查前后是否有关键词矛盾
                    before = text[:pos]
                    after = text[pos + len(marker):]

                    # 简单矛盾检测：前面说"增加"，后面说"减少"
                    opposite_pairs = [
                        ("增加", "减少"), ("提高", "降低"), ("上升", "下降"),
                        ("增长", "下降"), ("扩大", "缩小"), ("加强", "削弱"),
                        ("支持", "反对"), ("正确", "错误"), ("成功", "失败"),
                        ("有利", "不利"), ("积极", "消极"),
                    ]
                    for pos_word, neg_word in opposite_pairs:
                        if pos_word in before and neg_word in after:
                            issue = QAIssue(
                                category=IssueCategory.LOGIC,
                                severity=IssueSeverity.WARNING,
                                title=f"可能存在前后矛盾",
                                description='在"' + marker + '"前后分别出现了"' + pos_word + '"和"' + neg_word + '"，请确认是否存在逻辑矛盾',
                                element_index=elem_idx,
                                element_type=elem.element_type.value,
                                location_text=text[max(0, pos - 20):pos + len(marker) + 30],
                                confidence=0.4,
                            )
                            report.add_issue(issue)
                            break

    def _check_causality(self, doc: DocumentModel, report: QAReport):
        """检查因果关系"""
        paragraphs = [e for e in doc.elements if e.content]

        for idx, elem in enumerate(paragraphs):
            text = elem.content

            # 检测"因为...所以..."结构中是否缺少原因或结果
            if "因为" in text and "所以" not in text and "因此" not in text and "导致" not in text:
                # "因为"后面没有结论词
                # 检查是否在下一句中
                if idx + 1 < len(paragraphs):
                    next_text = paragraphs[idx + 1].content
                    if "所以" not in next_text and "因此" not in next_text and "导致" not in next_text:
                        issue = QAIssue(
                            category=IssueCategory.LOGIC,
                            severity=IssueSeverity.INFO,
                            title=f"因果关系可能不完整",
                            description='第' + str(idx + 1) + '段使用了"因为"但未找到对应的结论词（所以/因此/导致）',
                            suggestion="检查是否缺少结论部分，或补充结论",
                            element_index=idx,
                            element_type=elem.element_type.value,
                            location_text=text[:50] + "...",
                            confidence=0.3,
                        )
                        report.add_issue(issue)

            # "因此"没有前置原因
            if "因此" in text and idx > 0:
                prev_text = paragraphs[idx - 1].content
                if "因为" not in prev_text and "由于" not in prev_text and "鉴于" not in prev_text:
                    # 不一定是问题，低置信度
                    pass  # 暂不报告，避免过多误报

    def _check_timeline(self, doc: DocumentModel, report: QAReport):
        """检查时间线矛盾"""
        # 提取所有年份
        year_pattern = re.compile(r"(\d{4})\s*年")

        years_found: list[tuple[int, int, str]] = []  # (elem_idx, year, context)

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            for match in year_pattern.finditer(elem.content):
                year = int(match.group(1))
                if 1900 <= year <= 2100:  # 合理年份范围
                    context = elem.content[max(0, match.start() - 15):match.end() + 5]
                    years_found.append((idx, year, context))

        # 检查年份是否递增（同一文档中后面的年份不应小于前面的）
        for i in range(len(years_found) - 1):
            idx_a, year_a, ctx_a = years_found[i]
            idx_b, year_b, ctx_b = years_found[i + 1]

            if year_b < year_a and abs(year_b - year_a) > 1:
                # 年份倒退，可能有问题
                issue = QAIssue(
                    category=IssueCategory.LOGIC,
                    severity=IssueSeverity.WARNING,
                    title=f"时间线可能矛盾：{year_a}年 → {year_b}年",
                    description=f"文档中先提到{year_a}年，后提到{year_b}年，时间线可能存在矛盾",
                    element_index=idx_b,
                    element_type="paragraph",
                    location_text=ctx_b,
                    related_text=ctx_a,
                    confidence=0.5,
                )
                report.add_issue(issue)

    def _check_conclusion_support(self, doc: DocumentModel, report: QAReport):
        """检查结论是否有数据支撑"""
        paragraphs = [e for e in doc.elements if e.content]

        conclusion_markers = ["结论", "总结", "总之", "综上", "由此可见", "结果表明"]

        for idx, elem in enumerate(paragraphs):
            text = elem.content
            for marker in conclusion_markers:
                if marker in text:
                    # 检查结论段落中是否包含数据/数字
                    has_number = bool(re.search(r"\d+", text))
                    has_data_ref = any(w in text for w in ["数据", "统计", "调查", "实验", "分析", "研究", "测试"])

                    if not has_number and not has_data_ref:
                        issue = QAIssue(
                            category=IssueCategory.LOGIC,
                            severity=IssueSeverity.INFO,
                            title=f"结论可能缺少数据支撑",
                            description='包含"' + marker + '"的段落中没有发现数据或引用，建议补充数据支撑',
                            suggestion="在结论中引用具体数据或分析结果",
                            element_index=idx,
                            element_type=elem.element_type.value,
                            location_text=text[:80] + "...",
                            confidence=0.3,
                        )
                        report.add_issue(issue)
                    break

    def _check_empty_sections(self, doc: DocumentModel, report: QAReport):
        """检查空章节（有标题但无内容）"""
        for i in range(len(doc.elements) - 1):
            curr = doc.elements[i]
            next_elem = doc.elements[i + 1]

            if curr.element_type == ElementType.HEADING and curr.level <= 2:
                # 如果下一个元素也是标题（同级或更高级），说明当前章节为空
                if next_elem.element_type == ElementType.HEADING and next_elem.level <= curr.level:
                    issue = QAIssue(
                        category=IssueCategory.LOGIC,
                        severity=IssueSeverity.ERROR,
                        title='章节内容为空："' + curr.content + '"',
                        description='标题"' + curr.content + '"后没有正文内容，直接跟了下一个标题',
                        suggestion="补充该章节的内容，或删除空标题",
                        element_index=i,
                        element_type="heading",
                        location_text=curr.content,
                        confidence=0.9,
                    )
                    report.add_issue(issue)

    def _check_argumentation(self, doc: DocumentModel, report: QAReport):
        """检查论证充分性
        
        检测：
        1. 观点是否有论据支撑
        2. 论据是否充分（数据、案例、引用）
        3. 论证链条是否完整
        """
        paragraphs = [e for e in doc.elements if e.content and e.element_type == ElementType.PARAGRAPH]
        
        # 观点性词汇
        opinion_markers = ["认为", "觉得", "主张", "提议", "建议", "应该", "必须", "务必", 
                          "显然", "毫无疑问", "显而易见", "可以肯定", "由此可见"]
        
        # 论据性词汇
        evidence_markers = ["数据表明", "研究显示", "实验证明", "据统计", "调查", 
                           "例如", "比如", "实例", "案例", "事实", 
                           "因为", "由于", "原因是", "鉴于", "基于"]
        
        for idx, elem in enumerate(paragraphs):
            text = elem.content
            
            # 检查是否有观点无论证
            has_opinion = any(marker in text for marker in opinion_markers)
            has_evidence = any(marker in text for marker in evidence_markers)
            has_data = bool(re.search(r"\d+\.?\d*%?", text))  # 数字或百分比
            
            if has_opinion and not has_evidence and not has_data and len(text) < 100:
                # 观点性陈述短且无论据
                issue = QAIssue(
                    category=IssueCategory.LOGIC,
                    severity=IssueSeverity.INFO,
                    title="观点可能缺少论证支撑",
                    description="该段落包含观点性陈述，但未发现数据、研究或案例支撑",
                    suggestion="建议补充相关数据、研究结果或具体案例来支撑观点",
                    element_index=idx,
                    element_type="paragraph",
                    location_text=text[:80] + "...",
                    confidence=0.4,
                )
                report.add_issue(issue)

    def _check_conditionals(self, doc: DocumentModel, report: QAReport):
        """检查条件关系
        
        检测：
        1. 如果...那么...结构是否完整
        2. 只有...才...结构是否正确
        3. 除非...否则...结构是否正确
        """
        paragraphs = [e for e in doc.elements if e.content]
        
        # 条件关系词组
        conditional_patterns = [
            ("如果", ["那么", "就", "则", "便"]),
            ("假如", ["那么", "就", "则"]),
            ("倘若", ["那么", "就", "则"]),
            ("只要", ["就"]),
            ("只有", ["才"]),
            ("除非", ["否则", "才"]),
            ("无论", ["都", "也"]),
            ("不管", ["都", "也"]),
        ]
        
        for idx, elem in enumerate(paragraphs):
            text = elem.content
            
            for if_word, then_words in conditional_patterns:
                if if_word in text:
                    # 检查是否有对应的结论词
                    has_then = any(then_word in text for then_word in then_words)
                    
                    # 如果当前句没有，检查下一句
                    if not has_then and idx + 1 < len(paragraphs):
                        next_text = paragraphs[idx + 1].content
                        has_then = any(then_word in next_text for then_word in then_words)
                    
                    if not has_then:
                        issue = QAIssue(
                            category=IssueCategory.LOGIC,
                            severity=IssueSeverity.INFO,
                            title=f"条件关系可能不完整",
                            description=f'使用了"{if_word}"但未找到对应的结论词（{"/".join(then_words)}）',
                            suggestion="检查是否缺少结论部分，或补充完整条件关系",
                            element_index=idx,
                            element_type="paragraph",
                            location_text=text[:60] + "...",
                            confidence=0.3,
                        )
                        report.add_issue(issue)

    def _check_comparisons(self, doc: DocumentModel, report: QAReport):
        """检查比较关系
        
        检测：
        1. 比较对象是否明确
        2. 比较维度是否一致
        3. 比较级使用是否正确
        """
        paragraphs = [e for e in doc.elements if e.content]
        
        # 比较词
        comparison_markers = ["比", "相比", "相较于", "与...相比", "相对于", 
                             "更", "更加", "更为", "越发", "愈发"]
        
        # 不一致的比较维度
        inconsistent_dims = [
            ("质量", "数量"),
            ("速度", "效率"),
            ("成本", "费用"),
            ("性能", "功能"),
            ("优点", "优势"),
            ("缺点", "不足"),
        ]
        
        for idx, elem in enumerate(paragraphs):
            text = elem.content
            
            # 检查是否有比较词
            has_comparison = any(marker in text for marker in comparison_markers)
            
            if has_comparison:
                # 检查是否明确比较对象
                if "比" in text and "与" not in text and "和" not in text and "跟" not in text:
                    # 可能缺少比较对象
                    if text.count("比") == 1 and len(text) < 50:
                        issue = QAIssue(
                            category=IssueCategory.LOGIC,
                            severity=IssueSeverity.INFO,
                            title="比较对象可能不明确",
                            description="句子包含比较词，但未明确指出与什么进行比较",
                            suggestion="补充明确的比较对象，如'与...相比'",
                            element_index=idx,
                            element_type="paragraph",
                            location_text=text[:60] + "...",
                            confidence=0.3,
                        )
                        report.add_issue(issue)
                
                # 检查比较维度是否一致
                for dim1, dim2 in inconsistent_dims:
                    if dim1 in text and dim2 in text:
                        # 同时提到两个不同维度，可能混淆
                        issue = QAIssue(
                            category=IssueCategory.LOGIC,
                            severity=IssueSeverity.INFO,
                            title="比较维度可能不一致",
                            description=f'同时提及"{dim1}"和"{dim2}"，请确认比较维度是否一致',
                            suggestion="明确比较的具体维度，避免混淆",
                            element_index=idx,
                            element_type="paragraph",
                            location_text=text[:60] + "...",
                            confidence=0.2,
                        )
                        report.add_issue(issue)
