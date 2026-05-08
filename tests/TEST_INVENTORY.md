# Test Inventory (Refactor Baseline)

This file records the status of the legacy test suite before the layered refactor.

## Classification Rules

- **unit**: Pure module/function logic, no browser, no external runtime dependency.
- **integration**: Multi-module pipeline in Python process, no browser.
- **e2e**: Real browser workflow (login/upload/check/export/download).
- **script**: Diagnostic/manual scripts, not for default CI gate.

## Current File Mapping

| File | Current Type | Runtime Status | Action |
| --- | --- | --- | --- |
| `test_phase1.py` | unit | usable | keep (legacy core) |
| `test_phase2.py` | unit/integration | partial (contains absolute-path skips) | keep + progressively fixture-ize |
| `test_phase3.py` | unit/integration | partial (contains absolute-path skips) | keep + progressively fixture-ize |
| `test_phase4.py` | unit/integration | usable | keep |
| `test_phase5.py` | unit/integration | usable | keep |
| `test_phase6.py` | unit/integration | usable | keep |
| `test_phase7.py` | unit/integration | usable | keep |
| `test_core_functions.py` | unit | usable | keep |
| `test_bridge_api.py` | unit | usable | keep |
| `test_compatibility.py` | integration | usable | keep (slow gate) |
| `test_exception_boundary.py` | unit | usable | keep |
| `test_regression.py` | integration | usable | keep |
| `test_performance.py` | slow/script-like | partial | mark slow |
| `test_performance_stress.py` | slow | partial | mark slow |
| `test_ui_state_management.py` | integration (backend API mock) | usable | keep |
| `test_llm_integration_real.py` | integration/real API | flaky (network/key dependent) | keep, mark integration + external |
| `test_webapp.py` | pseudo-e2e script | stale (hardcoded 8080/Linux path) | split into pytest e2e files |
| `test_e2e_integration.py` | integration (misnamed e2e) | usable | migrate to `tests/integration/` |
| `e2e/test_export_docx_regression.py` | real e2e | usable baseline | keep |
| `test_startup.py` | script | not CI-suitable | relocate to `tests/scripts/` |
| `test_llm_simple.py` | script | not CI-suitable | relocate to `tests/scripts/` |
| `test_llm_qa.py` | script | not CI-suitable | relocate to `tests/scripts/` |

## Migration Snapshot

- `test_e2e_integration.py` -> `integration/test_pipeline_integration.py`
- `e2e/test_export_docx_regression.py` (phase5 export e2e) -> kept as the canonical path
- `test_webapp.py` -> `e2e/test_auth_login_flow.py`, `e2e/test_upload_preview_flow.py`, `e2e/test_xref_flow.py`
- `test_startup.py` -> `scripts/startup_benchmark.py`
- `test_llm_simple.py` + `test_llm_qa.py` -> `scripts/llm_manual_probe.py` + `scripts/llm_qa_manual_probe.py`

## Refactor Exit Criteria

1. New layered directories exist: `unit/ integration/ e2e/ scripts/ fixtures/ artifacts/`.
2. Browser workflows are tested by pytest+playwright files under `tests/e2e/`.
3. Script-like diagnostics are excluded from default pytest collection.
4. E2E fixtures include service bootstrap, login helper, upload helper, download capture.
5. Export regression test writes machine-readable comparison report.

## Current Repository Gates

The repository now treats the following as the minimum cross-layer gate after
normal product changes:

```bash
python -m pytest tests/test_batch_regression.py -v
python -m pytest tests/test_format_checker.py -v
python -m pytest tests/e2e/test_batch7_e2e.py -m "e2e and no_login" -v
```

Interpretation:

- `test_batch_regression.py` protects historical backend regression points
- `test_format_checker.py` protects format-checking core logic
- `test_batch7_e2e.py -m "e2e and no_login"` protects critical frontend JS
  behavior without needing a real Supabase login

## Smoke corpus source

The current real-sample smoke corpus is external to the repo:

- sample root: `G:\开发项目\备份\samples`
- manifest: `samples/manifest.json`
- manifest audit script: `tests/scripts/run_sample_smoke_manifest.py`
- executable smoke pytest: `python -m pytest tests/test_real_sample_smoke.py -m smoke -v`
- executable smoke report: `python tests/scripts/run_real_sample_smoke.py`
- AI parse baseline: `python -m pytest tests/e2e/test_ai_parse_template_baseline.py -m "e2e and no_login" -v`

