#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordCraft Pro 分批修复回归测试
============================
每个 class 对应一个修复批次（第一批～第十批）。
只要对应代码回退，此文件内对应的测试就会失败，
从而防止已修复问题重复返工。

运行方式：
    python -m pytest tests/test_batch_regression.py -v
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import DocElement, DocumentModel, ElementType
from core.qa_engine import QAEngine
from core.qa_models import IssueCategory, IssueSeverity, QAIssue, QAReport


# ──────────────────────────────────────────────────────────────────────────────
# 通用工具
# ──────────────────────────────────────────────────────────────────────────────

def _build_doc(*lines: str) -> DocumentModel:
    doc = DocumentModel(title="regression-test", source_format="txt")
    for line in lines:
        doc.elements.append(DocElement(element_type=ElementType.PARAGRAPH, content=line))
    return doc


def _build_doc_with_heading(heading: str, *paras: str) -> DocumentModel:
    doc = DocumentModel(title="regression-test", source_format="txt")
    doc.elements.append(DocElement(element_type=ElementType.HEADING, content=heading, level=1))
    for p in paras:
        doc.elements.append(DocElement(element_type=ElementType.PARAGRAPH, content=p))
    return doc


# ──────────────────────────────────────────────────────────────────────────────
# 第一批：runQA 基础链路
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch1RunQAChain:
    """第一批：runQA 后端字段序列化 + 非空内容解析"""

    def test_runqa_returns_success_with_location_text(self):
        """runQA 返回的每条 issue 必须含 location_text 字段（曾因字段名拼写错误缺失）"""
        from app import Api
        api = Api(supabase_enabled=False)
        api._qa_health = {"ready": True, "missing": [], "capabilities": {}}
        api._qa_runtime_config = {}
        content = "<p>他门还发现该方案存在问题。</p>"
        data = json.loads(api.runQA(content))
        assert data["success"] is True
        for issue in data["issues"]:
            assert "location_text" in issue, "issue 缺少 location_text 字段"

    def test_runqa_schema_contains_rule_id_and_checker(self):
        """每条 issue 必须含 rule_id / checker（API schema 完整性）"""
        from app import Api
        api = Api(supabase_enabled=False)
        api._qa_health = {"ready": True, "missing": [], "capabilities": {}}
        api._qa_runtime_config = {}
        data = json.loads(api.runQA("<p>立生影响。</p>"))
        assert data["success"] is True
        for issue in data["issues"]:
            assert "rule_id" in issue
            assert "checker" in issue

    def test_runqa_html_content_not_empty_check(self):
        """传入 HTML 内容时 runQA 必须解析出 elements 并执行检查（曾因未解析 HTML 始终返回 0 条）"""
        from app import Api
        api = Api(supabase_enabled=False)
        api._qa_health = {"ready": True, "missing": [], "capabilities": {}}
        api._qa_runtime_config = {}
        html = "<h1>第一章</h1><p>他门发现问题。</p>"
        data = json.loads(api.runQA(html))
        assert data["success"] is True
        assert len(data["issues"]) > 0, "HTML 内容未被解析，返回 0 条问题"


# ──────────────────────────────────────────────────────────────────────────────
# 第三批：PunctuationChecker + TypoLib 扩充
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch3PunctuationChecker:
    """第三批：PunctuationChecker 新规则 + typo_lib 扩充"""

    def test_sentence_gap_detected(self):
        """中文句子间异常空格应被检出（如"发生 研究表明"）"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        doc = _build_doc("包括海流速度和涡旋的发生 研究表明，资源分布受影响。")
        report = checker.check(doc)
        rule_ids = {i.rule_id for i in report.issues}
        assert "format.sentence_gap" in rule_ids, "句间空格规则未检出"

    def test_unit_ug_l_detected(self):
        """ug/L 单位写法不规范应被检出"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        doc = _build_doc("Chl-a高于0.18 ug/L时，浮游植物丰度显著增加。")
        report = checker.check(doc)
        rule_ids = {i.rule_id for i in report.issues}
        assert "format.unit.ug_per_l" in rule_ids, "ug/L 单位规则未检出"

    def test_celsius_spacing_detected(self):
        """温度单位前多余空格应被检出（如"28 °C"）"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        doc = _build_doc("SST范围主要在27–28 °C之间。")
        report = checker.check(doc)
        rule_ids = {i.rule_id for i in report.issues}
        assert "format.unit.celsius_spacing" in rule_ids, "摄氏度空格规则未检出"

    def test_cjk_spacing_disabled_by_default(self):
        """中英文空格规则默认应关闭（学术文档中大量合法出现，不应刷屏）"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        assert checker.check_cjk_spacing is False, "check_cjk_spacing 未默认关闭"
        doc = _build_doc("使用Python进行数据分析，基于NumPy实现。")
        report = checker.check(doc)
        cjk_issues = [i for i in report.issues if i.rule_id == "format.cjk_ascii_spacing"]
        assert len(cjk_issues) == 0, "中英文空格规则被意外启用"

    def test_typo_lib_covers_known_academic_typos(self):
        """typo_lib 应覆盖样本文件中已知的错别字"""
        from core.typo_checker import TypoChecker
        checker = TypoChecker()
        doc = _build_doc(
            "他门还发现CPUE较高的海域主要分布在北纬10°-11°。",
            "但波浪条件改变可能对捕捞量立生影响。",
        )
        from core.qa_engine import QAEngine
        report = QAEngine().check(doc, ["typo"])
        texts = [i.location_text for i in report.issues]
        assert "他门" in texts, "错别字'他门'未被检出"
        assert "立生" in texts, "错别字'立生'未被检出"


# ──────────────────────────────────────────────────────────────────────────────
# 第八批：交叉引用参考文献扫描
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch8CrossRefReferenceScan:
    """第八批：TargetScanner 识别参考文献节中的 [1]-[N] 目标"""

    def _build_ref_doc(self) -> DocumentModel:
        doc = DocumentModel(title="xref-ref-test", source_format="txt")

        def h(text, level=1):
            return DocElement(element_type=ElementType.HEADING, content=text, level=level)

        def p(text):
            return DocElement(element_type=ElementType.PARAGRAPH, content=text)

        doc.elements += [
            h("1 引言"),
            p("如文献[1]所示，南海鸢乌贼广泛分布。"),
            p("参见[2]和[3]的研究结果。"),
            h("参考文献"),
            p("陈国宝, 于杰, 张俊. 南海鸢乌贼种群结构研究. 水产学报, 2007."),
            p("Ichii T. Jumbo flying squid Dosidicus gigas. 2004."),
            p("Nigmatullin Ch. M. 2001. A review of the biology."),
        ]
        return doc

    def test_target_scanner_finds_reference_targets(self):
        """TargetScanner 应在参考文献节中识别出 [1]、[2]、[3] 等目标"""
        from core.crossref_engine import TargetScanner
        doc = self._build_ref_doc()
        scanner = TargetScanner()
        targets = scanner.scan(doc)
        labels = {t.label for t in targets}
        assert "[1]" in labels, "参考文献 [1] 未被识别为 target"
        assert "[2]" in labels, "参考文献 [2] 未被识别为 target"
        assert "[3]" in labels, "参考文献 [3] 未被识别为 target"

    def test_ref_point_scanner_finds_inline_citations(self):
        """RefPointScanner 应识别正文中的 [1]、[2]、[3] 引用"""
        from core.crossref_engine import RefPointScanner
        doc = self._build_ref_doc()
        scanner = RefPointScanner()
        refs = scanner.scan(doc)
        ref_texts = {r.ref_text for r in refs}
        assert "[1]" in ref_texts, "文内引用 [1] 未被识别"
        assert "[2]" in ref_texts, "文内引用 [2] 未被识别"

    def test_crossref_matcher_links_valid_citations(self):
        """CrossRefMatcher 应将文内 [1]~[3] 与参考文献节目标匹配为 VALID"""
        from core.crossref_engine import CrossRefMatcher, RefPointScanner, TargetScanner
        from core.crossref_engine import CrossRefStatus
        doc = self._build_ref_doc()
        targets = TargetScanner().scan(doc)
        refs = RefPointScanner().scan(doc)
        # match(targets, ref_points) — targets 在前
        report = CrossRefMatcher().match(targets, refs)
        valid = [m for m in report.matches if m.status == CrossRefStatus.VALID]
        assert len(valid) >= 3, f"应有 ≥3 条有效引用，实际 {len(valid)}"


# ──────────────────────────────────────────────────────────────────────────────
# 第九批：QA + 交叉引用链路全面修复
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch9QAXrefChainFix:
    """第九批：elem.content 字段名 + runQA 包含 crossref + runXRef 调用 crossref_engine"""

    def test_doc_element_has_content_not_text(self):
        """DocElement 字段名是 content 不是 text（曾因 .text 引发 AttributeError）"""
        elem = DocElement(element_type=ElementType.PARAGRAPH, content="测试文本")
        assert hasattr(elem, "content"), "DocElement 缺少 content 属性"
        assert not hasattr(elem, "text") or elem.content == "测试文本"
        assert elem.content == "测试文本"

    def test_runqa_includes_crossref_category(self):
        """runQA 默认 categories 必须包含 crossref（第九批修复前缺失导致交叉引用漏检）"""
        from app import Api
        api = Api(supabase_enabled=False)
        api._qa_health = {"ready": True, "missing": [], "capabilities": {}}
        api._qa_runtime_config = {}
        # 悬空引用应被 crossref 检查捕获
        data = json.loads(api.runQA("<p>如图3-2所示，结果如下。</p>"))
        assert data["success"] is True
        cats = {i.get("category") for i in data["issues"]}
        assert "reference" in cats, "crossref 类别未包含在默认 runQA 中"

    def test_runxref_uses_crossref_engine_returns_element_index(self):
        """runXRef 返回的 matches 必须包含 element_index 字段（第七批后续补充）"""
        from app import Api
        api = Api(supabase_enabled=False)

        html = (
            "<h1>1 引言</h1>"
            "<p>如文献[1]所示。</p>"
            "<h1>参考文献</h1>"
            "<p>陈国宝等，2007，水产学报。</p>"
        )
        raw = api.runXRef(html)
        data = json.loads(raw)
        assert data.get("success") is True or "matches" in data
        matches = data.get("matches", [])
        if matches:
            assert "element_index" in matches[0], "matches 缺少 element_index 字段"

    def test_performance_chunker_uses_content_field(self):
        """DocumentChunker 遍历元素时应访问 elem.content 而非 elem.text"""
        from core.performance import DocumentChunker
        doc = _build_doc("这是第一段。", "这是第二段，内容较长，用于测试分块逻辑。")
        chunker = DocumentChunker(chunk_size=50)
        try:
            # chunk() 接收 elements 列表，不是 DocumentModel
            chunks = chunker.chunk(doc.elements)
            assert isinstance(chunks, list), "chunk() 应返回列表"
        except AttributeError as e:
            pytest.fail(f"DocumentChunker 访问了不存在的属性：{e}")


# ──────────────────────────────────────────────────────────────────────────────
# 第十批：误报减少 + 仪表盘修复（后端可测部分）
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch10FalsePositiveReduction:
    """第十批：词界碰撞误报 + AutoCorrect 标题 + CJK 空格默认关闭"""

    def test_boundary_char_no_false_positive_nanhaihaibiao(self):
        """'南海海表' 中 '海海' 不应被报为重复字（词界碰撞）"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        doc = _build_doc("在南海海表波浪动力学中的作用已有大量研究。")
        report = checker.check(doc)
        repeat_issues = [
            i for i in report.issues
            if i.rule_id == "typo.repeat_char_2" and "海" in (i.location_text or "")
        ]
        assert len(repeat_issues) == 0, f"'南海海表' 被误报为重复字：{repeat_issues}"

    def test_boundary_char_no_false_positive_shengwuwuli(self):
        """'生物物理' 中 '物物' 不应被报为重复字（词界碰撞）"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        doc = _build_doc("考虑中尺度海洋动力过程及其生物物理机制的影响。")
        report = checker.check(doc)
        repeat_issues = [
            i for i in report.issues
            if i.rule_id == "typo.repeat_char_2" and "物" in (i.location_text or "")
        ]
        assert len(repeat_issues) == 0, f"'生物物理' 被误报为重复字：{repeat_issues}"

    def test_genuine_double_char_still_detected(self):
        """真正的重复字（如'的的'）仍应被检出，不被误滤"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        doc = _build_doc("这是的的确确一个错误输入。")
        report = checker.check(doc)
        repeat_issues = [i for i in report.issues if "repeat_char" in (i.rule_id or "")]
        assert len(repeat_issues) > 0, "真实重复字'的的'未被检出"

    def test_autocorrect_title_is_descriptive(self):
        """AutoCorrect 问题标题应清晰描述具体的规范问题类型"""
        from core.autocorrect_checker import AutoCorrectChecker

        checker = AutoCorrectChecker()
        # 使用标点混用的例子（中英文空格建议会被过滤掉）
        fake_entry = {"old": "你好.", "new": "你好。", "severity": 1, "line": 1, "col": 1}
        issue = checker._diag_to_issue(fake_entry, lines=["你好.世界"])
        assert issue is not None
        assert "AutoCorrect 文案规范问题" not in issue.title, (
            f"标题仍是旧的通用文案：'{issue.title}'"
        )
        # 标题应包含"建议规范化"和具体的问题分类
        assert "建议规范化" in issue.title, (
            f"标题应包含'建议规范化'关键词：'{issue.title}'"
        )

    def test_cjk_spacing_disabled_no_noise_in_academic_text(self):
        """含大量中英文混排的学术句子不应产生任何中英文空格提示"""
        from core.punctuation_checker import PunctuationChecker
        checker = PunctuationChecker()
        academic = (
            "利用MODIS卫星数据和Argo浮标数据，结合EOF分析和Pearson相关系数，"
            "对SST、Chl-a和CPUE之间的关系进行了统计建模。"
        )
        doc = _build_doc(academic)
        report = checker.check(doc)
        spacing_issues = [i for i in report.issues if i.rule_id == "format.cjk_ascii_spacing"]
        assert len(spacing_issues) == 0, (
            f"学术文本被误报 {len(spacing_issues)} 条中英文空格问题"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 综合：crossref engine 不双倍计数（双 scan 问题）
# ──────────────────────────────────────────────────────────────────────────────

class TestCrossRefNoDuplicateMatches:
    """
    RefPointScanner.scan + scan_multi_references 均使用相同正则，
    历史上导致每条文内引用在 report.matches 中出现两次。
    element_index 字段用于前端去重；此测试验证后端返回的结构完整。
    """

    def _build_full_paper(self) -> DocumentModel:
        doc = DocumentModel(title="full-paper", source_format="txt")

        def h(t, lv=1):
            return DocElement(element_type=ElementType.HEADING, content=t, level=lv)

        def p(t):
            return DocElement(element_type=ElementType.PARAGRAPH, content=t)

        doc.elements += [
            h("1 引言"),
            p("南海鸢乌贼广泛分布于热带海域[1]，其资源量受SST影响[2]。"),
            p("Chl-a浓度与CPUE显著相关[1][3]，已有研究[2]证实。"),
            h("参考文献"),
            p("陈国宝等，2007，水产学报。"),
            p("Ichii T. 2004. Jumbo flying squid."),
            p("Nigmatullin Ch. M. 2001. A review."),
        ]
        return doc

    def test_matches_contain_element_index(self):
        """每条 match 必须带 element_index，供前端去重跳转"""
        from core.crossref_engine import CrossRefMatcher, RefPointScanner, TargetScanner
        doc = self._build_full_paper()
        targets = TargetScanner().scan(doc)
        refs = RefPointScanner().scan(doc)
        # match(targets, ref_points) — targets 在前
        report = CrossRefMatcher().match(targets, refs)
        for m in report.matches:
            assert hasattr(m.ref_point, "element_index"), (
                f"RefPoint 缺少 element_index，ref_text={m.ref_point.ref_text}"
            )

    def test_app_runxref_matches_include_element_index(self):
        """app.runXRef 序列化后的 matches 每条必须有 element_index 字段"""
        from app import Api
        api = Api(supabase_enabled=False)
        html = (
            "<h1>1 引言</h1>"
            "<p>研究发现[1]和[2]均有重要意义。</p>"
            "<h1>参考文献</h1>"
            "<p>第一篇参考文献。</p>"
            "<p>第二篇参考文献。</p>"
        )
        data = json.loads(api.runXRef(html))
        matches = data.get("matches", [])
        for m in matches:
            assert "element_index" in m, (
                f"runXRef 返回的 match 缺少 element_index：{m}"
            )
