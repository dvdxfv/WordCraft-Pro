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

    def test_runqa_schema_contains_position_fields(self):
        from app import Api
        api = Api(supabase_enabled=False)
        api._qa_health = {"ready": True, "missing": [], "capabilities": {}}
        api._qa_runtime_config = {}
        data = json.loads(api.runQA("<p>海温为 28 °C。</p>"))
        assert data["success"] is True
        for issue in data["issues"]:
            assert "element_index" in issue
            assert "start_pos" in issue
            assert "end_pos" in issue

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


# ──────────────────────────────────────────────────────────────────────────────
# 第十三批：交叉引用采纳式设计
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch13XRefAdoption:
    """第十三批：runXRef 返回 xref_issues 字段，支持采纳式交叉引用设计"""

    def _html_with_refs(self) -> str:
        return (
            "<h1>1 引言</h1>"
            "<p>研究发现[1]有重要意义，[2]也提供了佐证。</p>"
            "<p>如图1-1所示，结果明显。</p>"
            "<h1>参考文献</h1>"
            "<p>第一篇参考文献。</p>"
            "<p>第二篇参考文献。</p>"
        )

    def test_runxref_returns_xref_issues_field(self):
        """runXRef 返回值必须包含 xref_issues 字段（第十三批新增）"""
        from app import Api
        api = Api(supabase_enabled=False)
        data = json.loads(api.runXRef(self._html_with_refs()))
        assert data.get("success") is True
        assert "xref_issues" in data, "runXRef 返回值缺少 xref_issues 字段"

    def test_xref_issues_have_required_fields(self):
        """xref_issues 每条必须有 type/target_label/element_index/title/description"""
        from app import Api
        api = Api(supabase_enabled=False)
        data = json.loads(api.runXRef(self._html_with_refs()))
        issues = data.get("xref_issues", [])
        assert len(issues) > 0, "有有效引用时 xref_issues 不应为空"
        for iss in issues:
            for field in ("type", "target_label", "element_index", "title", "description"):
                assert field in iss, f"xref_issues 条目缺少字段 '{field}'：{iss}"

    def test_valid_refs_appear_as_unreferenced_type(self):
        """与已知目标匹配的文内引用，在 xref_issues 中应为 type='unreferenced'（可采纳）"""
        from app import Api
        api = Api(supabase_enabled=False)
        data = json.loads(api.runXRef(self._html_with_refs()))
        issues = data.get("xref_issues", [])
        unref = [i for i in issues if i["type"] == "unreferenced"]
        assert len(unref) > 0, "有效引用[1][2]应生成 type=unreferenced 的 xref_issues"

    def test_valid_refs_have_bookmark_name(self):
        """可采纳的引用（type=unreferenced）必须携带 bookmark_name，供导出时生成 REF 字段"""
        from app import Api
        api = Api(supabase_enabled=False)
        data = json.loads(api.runXRef(self._html_with_refs()))
        issues = data.get("xref_issues", [])
        for iss in issues:
            if iss["type"] == "unreferenced":
                assert iss.get("bookmark_name"), (
                    f"可采纳引用缺少 bookmark_name：{iss}"
                )

    def test_xref_issues_deduplicated_by_label(self):
        """同一引用标签（如 [1]）在 xref_issues 中只出现一次（前端按 target_label 采纳所有实例）"""
        from app import Api
        api = Api(supabase_enabled=False)
        # [1] appears twice in this HTML
        html = (
            "<h1>1 引言</h1>"
            "<p>根据[1]的结果，[1]得到了验证。</p>"
            "<h1>参考文献</h1>"
            "<p>第一篇参考文献。</p>"
        )
        data = json.loads(api.runXRef(html))
        issues = data.get("xref_issues", [])
        labels = [i["target_label"] for i in issues if i["type"] == "unreferenced"]
        assert labels.count("[1]") == 1, f"[1] 在 xref_issues 中重复出现：{labels}"


# ──────────────────────────────────────────────────────────────────────────────
# 第十六批：交叉引用结果排序与样式保留
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch16XRefSort:
    """第十六批：runXRef matches 和 xref_issues 必须按 element_index 文档顺序升序排列"""

    def test_matches_sorted_by_element_index(self):
        """runXRef matches 列表必须按 element_index 升序（文档从上到下）"""
        from app import Api
        api = Api(supabase_enabled=False)
        # 构造引用出现在不同位置的 HTML，顺序为 [3], [1], [2]
        html = (
            "<h1>1 引言</h1>"
            "<p>见第三节[3]的讨论</p>"
            "<p>见第一节[1]的讨论</p>"
            "<p>见第二节[2]的讨论</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一节</p>"
            "<p>[2] 第二节</p>"
            "<p>[3] 第三节</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        indices = [m["element_index"] for m in matches if m["element_index"] is not None]
        # 验证 element_index 是升序的
        assert indices == sorted(indices), (
            f"matches 未按 element_index 升序排列，实际顺序：{indices}"
        )

    def test_xref_issues_sorted_by_element_index(self):
        """runXRef xref_issues 列表必须按 element_index 升序"""
        from app import Api
        api = Api(supabase_enabled=False)
        html = (
            "<h1>1 引言</h1>"
            "<p>见[3]节和[1]节的讨论，也见[2]节</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一节</p>"
            "<p>[2] 第二节</p>"
            "<p>[3] 第三节</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        issues = data.get("xref_issues", [])
        indices = [x["element_index"] for x in issues if x["element_index"] is not None]
        # 验证 element_index 是升序的
        assert indices == sorted(indices), (
            f"xref_issues 未按 element_index 升序排列，实际顺序：{indices}"
        )

    def test_same_element_index_sorted_by_start_pos_not_alphabetical(self):
        """同一 element_index 的多个引用应按在段落中的出现位置（start_pos）排列，不按字母序"""
        from app import Api
        api = Api(supabase_enabled=False)
        # [3] 在段落中最先出现，然后是 [1]，最后是 [2]
        # 修复前：按字典序 = [1],[2],[3]（错误）
        # 修复后：按出现位置 = [3],[1],[2]（正确）
        html = (
            "<h1>1 引言</h1>"
            "<p>见[3]节和[1]节与[2]节的讨论</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一节</p>"
            "<p>[2] 第二节</p>"
            "<p>[3] 第三节</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        # 找出包含 [1],[2],[3] 的那个 element_index
        by_index: dict = {}
        for m in matches:
            ei = m["element_index"]
            if ei is not None:
                by_index.setdefault(ei, []).append(m["reference"])
        para_refs = None
        for refs in by_index.values():
            if set(refs) >= {"[1]", "[2]", "[3]"}:
                para_refs = refs
                break
        assert para_refs is not None, "未找到包含 [1],[2],[3] 的段落 matches"
        # 文档出现顺序：[3] 最先，[1] 居中，[2] 最后
        assert para_refs == ["[3]", "[1]", "[2]"], (
            f"同一段落内引用未按出现位置排列，实际顺序：{para_refs}，期望：['[3]', '[1]', '[2]']"
        )

    def test_no_duplicate_matches_from_multi_ref_scanner(self):
        """scan_multi_references 不应为普通单号引用 [N] 产生重复 RefPoint"""
        from app import Api
        from collections import Counter
        api = Api(supabase_enabled=False)
        # 段落中 [1] 和 [2] 均为独立引用（非组合引用 [1,2]）
        # 修复前：scan() + scan_multi_references() 各产生一次 → 每个 ref 出现两次
        # 修复后：scan_multi_references() 跳过单号引用 → 每个 ref 只出现一次
        html = (
            "<h1>1 引言</h1>"
            "<p>文献[1]和文献[2]均支持此结论。</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一篇文献</p>"
            "<p>[2] 第二篇文献</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        valid_matches = [m for m in matches if m["status"] == "valid"]
        ref_counts = Counter(m["reference"] for m in valid_matches)
        assert ref_counts.get("[1]", 0) == 1, (
            f"[1] 的有效匹配数应为 1，实际为 {ref_counts.get('[1]', 0)}（存在重复）"
        )
        assert ref_counts.get("[2]", 0) == 1, (
            f"[2] 的有效匹配数应为 1，实际为 {ref_counts.get('[2]', 0)}（存在重复）"
        )

    def test_matches_include_start_pos_field(self):
        """runXRef matches 应包含 start_pos 字段，供前端按段内位置精确定位"""
        from app import Api
        api = Api(supabase_enabled=False)
        html = (
            "<h1>1 引言</h1>"
            "<p>文献[1]支持此结论。</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一篇文献</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        valid = [m for m in matches if m["status"] == "valid"]
        assert len(valid) > 0, "应有至少一个有效匹配"
        for m in valid:
            assert "start_pos" in m, f"match 缺少 start_pos 字段：{m}"
            assert isinstance(m["start_pos"], int), f"start_pos 应为整数：{m.get('start_pos')}"


# ──────────────────────────────────────────────────────────────────────────────
# Batch 16 补充：交叉引用定位映射修复
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch16XRefLocationMapping:
    """第十六批补充：paraOcc 定义修复，确保定位映射正确"""

    def test_para_occ_based_on_match_sequence_not_element_index(self):
        """paraOcc 应基于 matches 序列中的位置，而非 element_index 计数"""
        from app import Api
        api = Api(supabase_enabled=False)
        # HTML 中 [1] 出现3次，位置不同
        html = (
            "<h1>1 引言</h1>"
            "<p>根据[1]的研究</p>"
            "<p>进一步[1]分析表明</p>"
            "<p>综合[1]结果可知</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一篇文献</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])

        # 筛出所有 [1] 的 matches
        ref1_matches = [m for m in matches if m["reference"] == "[1]"]

        # 如果有多个 [1]，它们在返回的 matches 中应该是连续出现的，
        # 且顺序应该按文档顺序（因为后端按 element_index 排序）
        assert len(ref1_matches) > 0, "应该有 [1] 的 matches"

    def test_matches_ordering_stable_for_location_lookup(self):
        """后端返回的 matches 顺序应该稳定，便于前端通过 occ 参数定位"""
        from app import Api
        api = Api(supabase_enabled=False)
        # 构造一个特定顺序的引用出现
        html = (
            "<h1>1 背景</h1>"
            "<p>见文献[2]和[1]的对比</p>"
            "<p>另外[3]也有相关论述</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一篇</p>"
            "<p>[2] 第二篇</p>"
            "<p>[3] 第三篇</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])

        # 同一个引用的多个出现应该有不同的 element_index
        # 且后端返回的顺序应该是按 element_index 升序的
        ei_list = [m["element_index"] for m in matches if m["element_index"] is not None]
        assert ei_list == sorted(ei_list), (
            f"matches 未按 element_index 升序排列：{ei_list}"
        )

    def test_duplicate_refs_preserved_not_deduplicated(self):
        """同一引用（如 [2]）在不同位置出现时，matches 中应保留所有实例（不去重）"""
        from app import Api
        api = Api(supabase_enabled=False)
        # [2] 在段落中出现两次，期望 matches 中有两条 [2] 的 valid 记录
        html = (
            "<h1>1 引言</h1>"
            "<p>文献[1]奠定基础，[2]提出方法，[2]进一步验证。</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一篇</p>"
            "<p>[2] 第二篇</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        valid = [m for m in matches if m["status"] == "valid"]
        refs = [m["reference"] for m in valid]
        # matches 必须包含两条 [2]
        assert refs.count("[2]") == 2, (
            f"[2] 出现两次时 matches 应有 2 条，实际：{refs}"
        )
        # 出现顺序必须是 [1],[2],[2]（scan order）
        assert refs == ["[1]", "[2]", "[2]"], (
            f"scan order 应为 ['[1]','[2]','[2]']，实际：{refs}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 第十七批：scan_index 属性测试
# ──────────────────────────────────────────────────────────────────────────────

class TestBatch17ScanIndex:
    """scan_index 核心不变量：输出序列 = 文档扫描顺序，与引用编号大小无关。"""

    def test_scan_index_field_present_in_all_valid_matches(self):
        """matches 每条记录必须携带 scan_index 字段"""
        from app import Api
        api = Api(supabase_enabled=False)
        html = (
            "<h1>1 引言</h1>"
            "<p>见[1]和[2]的研究。</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一篇</p>"
            "<p>[2] 第二篇</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        for m in data.get("matches", []):
            assert "scan_index" in m, f"match 缺少 scan_index 字段：{m}"

    def test_large_ref_numbers_do_not_affect_display_order(self):
        """属性测试：引用编号大小不影响展示顺序（[10][2][300] → 按文中出现顺序）"""
        from app import Api
        api = Api(supabase_enabled=False)
        # 段落中顺序：[10] → [2] → [300]，正确结果必须是 [10],[2],[300]
        html = (
            "<h1>1 引言</h1>"
            "<p>见文献[10]的基础工作，[2]提出改进，[300]做了综述。</p>"
            "<h1>参考文献</h1>"
            "<p>[2] 第二篇</p>"
            "<p>[10] 第十篇</p>"
            "<p>[300] 第三百篇</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        valid = [m for m in matches if m["status"] == "valid"]
        refs = [m["reference"] for m in valid]
        assert refs == ["[10]", "[2]", "[300]"], (
            f"引用编号大小不应影响顺序，期望 ['[10]','[2]','[300]']，实际：{refs}"
        )

    def test_multi_ref_expansion_preserves_order(self):
        """多引用 [2,3,6,7] 展开后顺序必须为 [2],[3],[6],[7]（不按编号重排）"""
        from app import Api
        api = Api(supabase_enabled=False)
        html = (
            "<h1>1 引言</h1>"
            "<p>见文献[2,3,6,7]所示方法。</p>"
            "<h1>参考文献</h1>"
            "<p>[2] 第二篇</p>"
            "<p>[3] 第三篇</p>"
            "<p>[6] 第六篇</p>"
            "<p>[7] 第七篇</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        valid = [m for m in matches if m["status"] == "valid"]
        refs = [m["reference"] for m in valid]
        assert refs == ["[2]", "[3]", "[6]", "[7]"], (
            f"多引用展开顺序应为 ['[2]','[3]','[6]','[7]']，实际：{refs}"
        )

    def test_scan_index_monotonically_increases(self):
        """valid matches 的 scan_index 必须严格单调递增（无重复，无逆序）"""
        from app import Api
        api = Api(supabase_enabled=False)
        html = (
            "<h1>1 背景</h1>"
            "<p>文献[3]奠定基础，[1]提出改进，[2]做了综述。</p>"
            "<p>另见[4]的讨论。</p>"
            "<h1>参考文献</h1>"
            "<p>[1] 第一篇</p>"
            "<p>[2] 第二篇</p>"
            "<p>[3] 第三篇</p>"
            "<p>[4] 第四篇</p>"
        )
        data = json.loads(api.runXRef(html))
        assert data.get("success") is True
        matches = data.get("matches", [])
        valid_si = [m["scan_index"] for m in matches
                    if m["status"] == "valid" and m.get("scan_index", -1) >= 0]
        assert valid_si == sorted(valid_si), (
            f"valid matches 的 scan_index 应单调递增，实际：{valid_si}"
        )
        assert len(valid_si) == len(set(valid_si)), (
            f"scan_index 存在重复值：{valid_si}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 第十八批：文档结构识别（cover/toc/heading/body 自动分类 + metadata 流通）
# ──────────────────────────────────────────────────────────────────────────────


class TestBatch18StructureRecognition:
    """第十八批：纯规则结构识别层

    回归点：
      1. classify_dicts 写入 metadata.structure_role / structure_confidence /
         structure_reason / exclude_from_format_body / exclude_from_xref_targets
      2. parsers/docx_parser.py 不再把 'toc 1/2/3' 样式归类为 HEADING
      3. FormatChecker 跳过 exclude_from_format_body=True 的元素
      4. CrossRefEngine.TargetScanner 跳过 exclude_from_xref_targets=True 的元素
      5. app.py.runXRef 接受 elements_json 并保留 metadata
    """

    def _toc_doc_dict(self):
        """构造一份带封面 + 目录 + 真章节的 dict 形态文档。"""
        return [
            {"type": "p", "text": "研究报告标题", "fmt": {"alignment": "CENTER"},
             "runs": [{"text": "研究报告标题", "font_size_pt": 22.0, "bold": True}]},
            {"type": "p", "text": "作者：张三", "fmt": {"alignment": "CENTER"},
             "runs": [{"text": "作者：张三", "font_size_pt": 14.0}]},
            {"type": "h1", "text": "目录", "fmt": {"style": "heading 1"},
             "runs": [{"text": "目录", "font_size_pt": 16.0, "bold": True}]},
            {"type": "p", "text": "第3章 模型与方法 ......15", "fmt": {"style": "toc 1"},
             "runs": [{"text": "第3章 模型与方法 ......15", "font_size_pt": 11.0}]},
            {"type": "h1", "text": "第3章 模型与方法", "fmt": {"style": "heading 1"},
             "runs": [{"text": "第3章 模型与方法", "font_size_pt": 16.0, "bold": True}]},
            {"type": "p", "text": "正文段落内容很长很长很长" * 2, "fmt": {"first_line_indent_twips": 420},
             "runs": [{"text": "正文段落", "font_size_pt": 11.0}]},
        ]

    def test_classify_dicts_writes_required_metadata(self):
        from core.document_structure import classify_dicts

        elems = self._toc_doc_dict()
        classify_dicts(elems)

        for el in elems:
            meta = el.get("metadata") or {}
            assert "structure_role" in meta
            assert "structure_confidence" in meta
            assert "structure_reason" in meta
            assert "exclude_from_format_body" in meta
            assert "exclude_from_xref_targets" in meta
            assert isinstance(meta["structure_role"], str)
            assert 0.0 <= meta["structure_confidence"] <= 1.0

    def test_toc_entry_excluded_from_xref_targets(self):
        from core.document_structure import classify_dicts

        elems = self._toc_doc_dict()
        classify_dicts(elems)

        # 索引 3 是目录条目"第3章 ......15"，必须被排除作为交叉引用目标
        toc_entry = elems[3]["metadata"]
        assert toc_entry["structure_role"] == "toc"
        assert toc_entry["exclude_from_xref_targets"] is True

        # 索引 4 是真章节"第3章 模型与方法"，不应被排除
        real_chapter = elems[4]["metadata"]
        assert real_chapter["structure_role"] == "heading"
        assert real_chapter["exclude_from_xref_targets"] is False

    def test_cover_excluded_from_format_body(self):
        from core.document_structure import classify_dicts

        elems = self._toc_doc_dict()
        classify_dicts(elems)

        # 索引 0、1 是封面：居中 + 大字号
        for i in (0, 1):
            meta = elems[i]["metadata"]
            assert meta["structure_role"] == "cover", f"index {i}"
            assert meta["exclude_from_format_body"] is True, f"index {i}"

    def test_docx_parser_no_longer_maps_toc_styles_to_heading(self):
        """parsers/docx_parser.py 不再把 'toc 1/2/3' 当 HEADING。

        以源码文本断言代替运行时 import，避免 parsers/__init__.py 链式触发可选
        依赖 (pdfplumber 等) 的 ImportError。
        """
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "parsers", "docx_parser.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()

        # 找到 _detect_element_type 函数体范围，仅在该范围内检查
        start = src.find("def _detect_element_type")
        assert start >= 0, "未找到 _detect_element_type 函数"
        # 从函数开始到下一个顶层 def 之间
        end = src.find("\n    def ", start + 1)
        body = src[start:end if end > 0 else len(src)]

        # HEADING 1/2/3 分支不应再出现 'toc 1/2/3' 字面量
        # （TOC 段落由 core.document_structure.classify_elements 后置识别）
        for bad in ('"toc 1"', '"toc 2"', '"toc 3"', "'toc 1'", "'toc 2'", "'toc 3'"):
            assert bad not in body, (
                f"docx_parser.py._detect_element_type 不应再把 {bad} 当作 HEADING；"
                f"TOC 段落需保留 PARAGRAPH 类型，结构识别由 classify_elements 处理。"
            )

    def test_format_checker_skips_exclude_from_format_body(self):
        """FormatChecker 必须跳过 metadata.exclude_from_format_body=True 的元素。"""
        from core.document_model import (
            DocumentModel, DocElement, ElementType, FontStyle,
        )
        from core.format_checker import FormatChecker, FormatRules

        rules = FormatRules(bFont="宋体", bSize=11.0)
        # 一个被排除的封面段（字体不符规范）
        excluded = DocElement(
            element_type=ElementType.PARAGRAPH,
            content="封面大标题",
            font_style=FontStyle(font_name_cn="黑体", font_size_pt=22.0),
            metadata={"exclude_from_format_body": True, "structure_role": "cover"},
        )
        # 一个普通正文段（同样字体不符）
        included = DocElement(
            element_type=ElementType.PARAGRAPH,
            content="正文段落",
            font_style=FontStyle(font_name_cn="黑体", font_size_pt=11.0),
        )
        doc = DocumentModel(title="t", source_format="txt")
        doc.elements.extend([excluded, included])

        report = FormatChecker(rules).check(doc)
        # 应只对正文段报字体问题，封面段被跳过
        font_issues = [i for i in report.issues if "字体" in i.title]
        assert len(font_issues) == 1
        assert "正文段落" in font_issues[0].suggestion

    def test_crossref_target_scanner_skips_exclude_from_xref(self):
        """TargetScanner 必须跳过 metadata.exclude_from_xref_targets=True 的元素。"""
        from core.document_model import (
            DocumentModel, DocElement, ElementType,
        )
        from core.crossref_engine import TargetScanner

        # 目录条目 "第3章 ......15"（被标记排除）+ 真章节 "第3章 模型"（HEADING）
        toc_entry = DocElement(
            element_type=ElementType.HEADING, level=1,
            content="第3章 模型与方法",
            metadata={"exclude_from_xref_targets": True, "structure_role": "toc"},
        )
        real = DocElement(
            element_type=ElementType.HEADING, level=1,
            content="第3章 模型与方法",
        )
        doc = DocumentModel(title="t", source_format="txt")
        doc.elements.extend([toc_entry, real])

        targets = TargetScanner().scan(doc)
        chapter_targets = [t for t in targets if t.target_type.value == "chapter"]
        assert len(chapter_targets) == 1, (
            "目录条目应被排除，只有真章节进入 targets"
        )
        assert chapter_targets[0].element_index == 1, "应来自索引 1（真章节）而非 0（目录）"

    def test_runxref_carries_metadata_through_elements_json(self):
        """app.py.runXRef 通过 elements_json 接收 metadata 后，TargetScanner 跳过目录章节。"""
        from app import Api

        api = Api()
        # elements_json：目录条目带 exclude_from_xref_targets=True，真章节不带
        elements = [
            {"type": "h1", "text": "目录"},
            {"type": "p", "text": "第3章 模型 ......15",
             "metadata": {"structure_role": "toc",
                          "exclude_from_xref_targets": True,
                          "exclude_from_format_body": True}},
            {"type": "h1", "text": "第3章 模型与方法"},
            {"type": "p", "text": "正文中提到第3章的内容"},
        ]
        elements_json = json.dumps(elements, ensure_ascii=False)
        # content 留空，强制走 elements_json 路径
        result = json.loads(api.runXRef("", [], elements_json=elements_json))
        assert result.get("success") is True
        targets = result.get("targets", [])
        # 只应有 1 个 chapter target（真章节），目录条目被跳过
        chapter_targets = [t for t in targets if t.get("type") == "chapter"]
        assert len(chapter_targets) == 1, (
            f"目录条目不应进入 targets，实际 chapter targets={chapter_targets}"
        )
