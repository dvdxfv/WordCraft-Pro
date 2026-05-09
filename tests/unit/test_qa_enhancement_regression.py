#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA 能力增强回归测试（规则层 + 交叉引用层）。"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import Api
from core.document_model import DocElement, DocumentModel, ElementType
from core.qa_engine import QAEngine
from core.qa_models import QAIssue, QAReport, IssueCategory, IssueSeverity


def _build_doc(lines: list[str]) -> DocumentModel:
    doc = DocumentModel(title="qa-regression", source_format="txt")
    for line in lines:
        doc.elements.append(DocElement(element_type=ElementType.PARAGRAPH, content=line))
    return doc


def test_typo_checker_catches_project_known_typos():
    doc = _build_doc([
        "他门还发现CPUE较高的海域主要分布在北纬10°-11°。",
        "但波浪条件改变可能对捕捞量立生影响。",
    ])
    report = QAEngine().check(doc, ["typo"])
    texts = [i.location_text for i in report.issues]
    assert "他门" in texts
    assert "立生" in texts


def test_format_checker_catches_sentence_gap_and_unit_norm():
    # 注意：单空格触发 sentence_gap；多于1个空格被豁免（排版对齐）
    doc = _build_doc([
        "包括海流速度和涡旋的发生 研究表明，资源分布受影响。",
        "Chl-a高于0.18 ug/L。",
        "SST范围主要在27–28 °C之间。",
    ])
    report = QAEngine().check(doc, ["format"])
    rules = {i.rule_id for i in report.issues}
    assert "format.sentence_gap" in rules
    assert "format.unit.ug_per_l" in rules
    assert "format.unit.celsius_spacing" in rules


def test_crossref_checker_reports_dangling_reference():
    doc = DocumentModel(title="xref", source_format="txt")
    doc.elements.append(DocElement(element_type=ElementType.PARAGRAPH, content="如图2-1所示，温度变化明显。"))
    report = QAEngine().check(doc, ["crossref"])
    assert any(i.category.value == "reference" for i in report.issues)
    assert any("悬空引用" in i.title for i in report.issues)


def test_app_runqa_default_includes_crossref_and_schema_fields():
    api = Api(supabase_enabled=False)
    api._qa_health = {"ready": True, "missing": [], "capabilities": {}}
    api._qa_runtime_config = {}
    content = "<p>如图3-2所示，结果如下。</p>"
    data = json.loads(api.runQA(content))
    assert data["success"] is True
    assert any(i.get("category") == "reference" for i in data["issues"])
    # 统一 schema 字段回传
    for issue in data["issues"]:
        assert "rule_id" in issue
        assert "checker" in issue


def test_consistency_and_logic_emit_rule_metadata():
    # logic 检查依赖 LLM，单元测试环境不验证其具体 rule_id；仅验证 consistency 层
    doc = _build_doc([
        "本年度营收为1,000万元。",
        "上文同一数据在附录写作1000万元。",
    ])
    report = QAEngine().check(doc, ["consistency"])
    assert any(i.rule_id == "consistency.number_format" for i in report.issues)
    assert all(i.checker for i in report.issues)


def test_qa_engine_supports_ignore_rules():
    doc = _build_doc(["Chl-a高于0.18 ug/L。"])
    engine = QAEngine(config={"qa": {"ignore_rule_ids": ["format.unit.ug_per_l"]}})
    report = engine.check(doc, ["format"])
    assert all(i.rule_id != "format.unit.ug_per_l" for i in report.issues)


def test_qa_engine_merges_autocorrect_layer():
    doc = _build_doc(["你好Hello世界"])
    engine = QAEngine(config={"qa": {"punctuation_check": {"enabled": False}}})

    def _fake_autocorrect(_doc):
        r = QAReport()
        r.add_issue(QAIssue(
            category=IssueCategory.FORMAT,
            severity=IssueSeverity.WARNING,
            title="AutoCorrect 文案规范问题",
            description="space-word",
            suggestion="你好 Hello 世界",
            rule_id="autocorrect.lint",
            checker="autocorrect_checker",
            location_text="好H",
            confidence=0.85,
        ))
        return r

    engine.autocorrect_checker.enabled = True
    engine.autocorrect_checker.check = _fake_autocorrect
    report = engine.check(doc, ["format"])
    assert any(i.rule_id == "autocorrect.lint" for i in report.issues)


def test_api_qa_health_reports_capabilities():
    api = Api(supabase_enabled=False)
    data = json.loads(api.getQAHealth())
    assert data["success"] is True
    assert "ready" in data
    assert "capabilities" in data
    assert "autocorrect" in data["capabilities"]


def test_runqa_hard_fails_when_qa_not_ready():
    api = Api(supabase_enabled=False)
    # monkey-patch 探测函数，使 autocorrect 始终返回不可用，触发硬门禁。
    api._probe_autocorrect = lambda: {
        "enabled": True, "available": False,
        "detail": "exec failed: test-sentinel", "command": "none",
    }
    # 同时禁用自动安装，避免安装逻辑干扰测试。
    orig_auto_fix = api._auto_fix_qa_dependencies
    api._auto_fix_qa_dependencies = lambda ac, **kw: {"attempted": False, "actions": []}
    api._qa_health = {}  # 清空缓存，强制重探测
    result = json.loads(api.runQA("<p>测试内容</p>"))
    api._auto_fix_qa_dependencies = orig_auto_fix  # 恢复
    assert result["success"] is False
    assert result["error_code"] == "QA_CAPABILITY_NOT_READY"
