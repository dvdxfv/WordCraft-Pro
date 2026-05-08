from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_TEST_SYSTEM = ROOT / "docs" / "TEST_SYSTEM.md"
TEST_INVENTORY = ROOT / "tests" / "TEST_INVENTORY.md"
SMOKE_MATRIX = ROOT / "tests" / "SMOKE_TEST_MATRIX.md"
AGENTS = ROOT / "AGENTS.md"
CLAUDE = ROOT / "CLAUDE.md"
PLANS_DIR = ROOT / "PLANS"

CORE_GATE_COMMANDS = [
    'tests/test_batch_regression.py -v',
    'tests/test_format_checker.py -v',
    'tests/e2e/test_batch7_e2e.py -m "e2e and no_login" -v',
]
AI_PARSE_BASELINE_COMMAND = 'tests/e2e/test_ai_parse_template_baseline.py -m "e2e and no_login" -v'

PLAN_REQUIRED_HEADING_GROUPS = [
    ("## Test Strategy", "## 测试策略"),
    ("### Core Gate", "### 核心闸门"),
    ("### New Regression Coverage", "### 新增回归覆盖"),
    ("### Smoke / Real Sample Verification", "### Smoke / 真实样本验证"),
    ("### Residual Risk", "### 残余风险"),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _find_heading(text: str, *options: str) -> str:
    for option in options:
        if option in text:
            return option
    raise AssertionError(f"missing heading, expected one of: {options}")


def test_test_system_doc_exists_and_defines_core_gate() -> None:
    text = _read(DOC_TEST_SYSTEM)

    assert any(token in text for token in ("## 分层", "## Layers"))
    assert any(token in text for token in ("### 1. 核心回归闸门", "### 1. Core regression gate"))
    for command in CORE_GATE_COMMANDS:
        assert command in text
    assert AI_PARSE_BASELINE_COMMAND in text
    assert "可直接替换" in text
    assert "解释型建议" in text
    assert "导入真实模板" in text
    assert "标准答案" in text


def test_inventory_and_smoke_docs_reference_no_login_gate() -> None:
    inventory = _read(TEST_INVENTORY)
    smoke = _read(SMOKE_MATRIX)

    assert 'tests/e2e/test_batch7_e2e.py -m "e2e and no_login"' in inventory
    assert AI_PARSE_BASELINE_COMMAND in inventory
    assert 'tests/e2e/test_batch7_e2e.py -m "e2e and no_login"' in smoke
    assert "Planning Rule" in smoke


def test_agent_rules_reference_test_strategy_requirements() -> None:
    agents = _read(AGENTS)
    claude = _read(CLAUDE)

    for text in (agents, claude):
        assert 'tests/e2e/test_batch7_e2e.py -m "e2e and no_login" -v' in text
        assert "## Test Strategy" in text
        assert "### New Regression Coverage" in text
        assert "### Smoke / Real Sample Verification" in text
        assert "### Residual Risk" in text


def test_active_plan_files_include_concrete_test_strategy() -> None:
    plan_files = [path for path in PLANS_DIR.glob("*.md") if "plan" in path.stem.lower()]
    assert plan_files, "expected at least one active plan file"

    for path in plan_files:
        text = _read(path)
        found = [_find_heading(text, *group) for group in PLAN_REQUIRED_HEADING_GROUPS]

        core_block = text.split(found[1], 1)[1].split(found[2], 1)[0]
        assert "pytest" in core_block, f"{path.name} core gate must list concrete commands"

        regression_block = text.split(found[2], 1)[1].split(found[3], 1)[0]
        assert any(token in regression_block.lower() for token in ("test_", "regression", "e2e", "integration")), (
            f"{path.name} regression coverage must name automated tests or layers"
        )
        assert any(
            token in regression_block
            for token in ("AI Parse", "ai_parse", "标准答案", "direct_replacement", "可直接替换")
        ), f"{path.name} regression coverage must state concrete acceptance criteria"

        smoke_block = text.split(found[3], 1)[1].split(found[4], 1)[0]
        assert any(token in smoke_block.lower() for token in ("sample", "smoke", "docx", "manual")), (
            f"{path.name} smoke section must state sample/smoke scope"
        )

        residual_block = text.split(found[4], 1)[1]
        assert len(residual_block.strip()) > 20, f"{path.name} residual risk section must not be empty"
