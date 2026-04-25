#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manual QAEngine + LLM probe script."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from core.document_model import DocElement, DocumentModel, ElementType
from core.qa_engine import QAEngine


def _doc() -> DocumentModel:
    doc = DocumentModel(title="测试文档", source_format="test")
    doc.elements.append(DocElement(element_type=ElementType.PARAGRAPH, content="这个项目的帐单需要按装新的软件系统。"))
    doc.elements.append(DocElement(element_type=ElementType.PARAGRAPH, content="他认真的学习了相关资料，快速得完成了任务。"))
    return doc


def main() -> int:
    cfg = {
        "qa": {
            "llm_check": {"enabled": True, "max_chunk_size": 800, "min_confidence": 0.6, "config_path": "config.yaml"},
            "typo_check": {"enabled": True, "use_llm": True},
            "consistency_check": {"enabled": True},
            "logic_check": {"enabled": True},
        },
        "performance": {"enable_chunking": False},
    }
    report = QAEngine(config=cfg).check(_doc(), categories=["typo", "grammar", "logic"])
    print(f"total={report.total} error={report.error_count} warn={report.warning_count} info={report.info_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

