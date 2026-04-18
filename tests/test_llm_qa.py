#!/usr/bin/env python3
"""
LLM 质量检测测试脚本

测试 LLM 辅助质量检测的各个模块：
1. 错别字检测
2. 语法检测
3. 逻辑检测
4. 综合检测
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.document_model import DocumentModel, DocElement, ElementType
from core.qa_engine import QAEngine
from core.llm_qa_checker import LLMQAChecker


def create_test_document() -> DocumentModel:
    """创建包含各类问题的测试文档"""
    doc = DocumentModel(title="测试文档", source_format="test")

    # 包含错别字的段落
    doc.elements.append(DocElement(
        element_type=ElementType.PARAGRAPH,
        content="这个项目的帐单需要按装新的软件系统。"
    ))

    # 包含的地得误用的段落
    # 这里故意写了错误的用法
    doc.elements.append(DocElement(
        element_type=ElementType.PARAGRAPH,
        content="他认真的学习了相关资料，快速得完成了任务。"
    ))

    # 包含语法问题的段落（成分残缺）
    doc.elements.append(DocElement(
        element_type=ElementType.PARAGRAPH,
        content="通过这次培训，使我们的业务能力得到了很大提高。"
    ))

    # 包含逻辑问题的段落（前后矛盾）
    doc.elements.append(DocElement(
        element_type=ElementType.PARAGRAPH,
        content="项目总投入100万元，其中设备采购80万元，人员费用30万元，其他费用10万元。"
    ))

    # 正常段落（不应被误报）
    doc.elements.append(DocElement(
        element_type=ElementType.PARAGRAPH,
        content="本项目的目标是提高系统性能和用户体验，通过优化算法和改进界面设计来实现。"
    ))

    # 包含成语错字的段落
    doc.elements.append(DocElement(
        element_type=ElementType.PARAGRAPH,
        content="团队穿流不息地工作，终于完成了这个艰巨的任务。"
    ))

    return doc


def test_llm_typo_check():
    """测试 LLM 错别字检测"""
    print("\n" + "="*60)
    print("测试 1: LLM 错别字检测")
    print("="*60)

    doc = create_test_document()
    checker = LLMQAChecker()
    report = checker.check_typo(doc)

    print(f"\n检测到 {report.total} 个问题:")
    for issue in report.issues:
        print(f"  [{issue.severity.value}] {issue.title}")
        print(f"    原文: {issue.location_text}")
        print(f"    建议: {issue.suggestion}")
        print(f"    原因: {issue.description}")
        print(f"    置信度: {issue.confidence}")
        print()

    return report


def test_llm_grammar_check():
    """测试 LLM 语法检测"""
    print("\n" + "="*60)
    print("测试 2: LLM 语法检测")
    print("="*60)

    doc = create_test_document()
    checker = LLMQAChecker()
    report = checker.check_grammar(doc)

    print(f"\n检测到 {report.total} 个问题:")
    for issue in report.issues:
        print(f"  [{issue.severity.value}] {issue.title}")
        print(f"    原文: {issue.location_text}")
        print(f"    建议: {issue.suggestion}")
        print(f"    原因: {issue.description}")
        print(f"    置信度: {issue.confidence}")
        print()

    return report


def test_llm_logic_check():
    """测试 LLM 逻辑检测"""
    print("\n" + "="*60)
    print("测试 3: LLM 逻辑检测")
    print("="*60)

    doc = create_test_document()
    checker = LLMQAChecker()
    report = checker.check_logic(doc)

    print(f"\n检测到 {report.total} 个问题:")
    for issue in report.issues:
        print(f"  [{issue.severity.value}] {issue.title}")
        print(f"    原文: {issue.location_text}")
        print(f"    建议: {issue.suggestion}")
        print(f"    原因: {issue.description}")
        print(f"    置信度: {issue.confidence}")
        print()

    return report


def test_llm_comprehensive_check():
    """测试 LLM 综合检测"""
    print("\n" + "="*60)
    print("测试 4: LLM 综合检测")
    print("="*60)

    doc = create_test_document()
    checker = LLMQAChecker()
    report = checker.check_comprehensive(doc)

    print(f"\n检测到 {report.total} 个问题:")
    for issue in report.issues:
        print(f"  [{issue.severity.value}] [{issue.category.value}] {issue.title}")
        print(f"    原文: {issue.location_text}")
        print(f"    建议: {issue.suggestion}")
        print(f"    原因: {issue.description}")
        print(f"    置信度: {issue.confidence}")
        print()

    return report


def test_qa_engine_with_llm():
    """测试 QA 引擎集成 LLM"""
    print("\n" + "="*60)
    print("测试 5: QA 引擎集成 LLM")
    print("="*60)

    doc = create_test_document()

    # 配置 LLM
    llm_config = {
        "enabled": True,
        "max_chunk_size": 800,
        "min_confidence": 0.6,
        "config_path": "config.yaml",
    }

    config = {
        "qa": {
            "llm_check": llm_config,
            "typo_check": {"enabled": True, "use_llm": True},
            "consistency_check": {"enabled": True},
            "logic_check": {"enabled": True},
        },
        "performance": {
            "enable_chunking": False,
        },
    }

    engine = QAEngine(config=config)
    report = engine.check(doc, categories=["typo", "grammar", "logic"])

    print(f"\n检测到 {report.total} 个问题:")
    print(f"  错误: {report.error_count}")
    print(f"  警告: {report.warning_count}")
    print(f"  提示: {report.info_count}")
    print()

    for issue in report.issues:
        print(f"  [{issue.severity.value}] [{issue.category.value}] {issue.title}")
        print(f"    原文: {issue.location_text}")
        print(f"    建议: {issue.suggestion}")
        print()

    return report


if __name__ == "__main__":
    print("WordCraft-Pro LLM 质量检测测试")
    print("="*60)

    # 运行测试
    try:
        test_llm_typo_check()
        test_llm_grammar_check()
        test_llm_logic_check()
        test_llm_comprehensive_check()
        test_qa_engine_with_llm()

        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
