from __future__ import annotations

import pytest

from tests.sample_smoke_support import (
    answer_key_samples,
    document_samples,
    load_manifest,
    manifest_smoke_report,
    run_sample_checks,
)


MANIFEST = load_manifest()


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.parametrize("entry", document_samples(MANIFEST), ids=lambda entry: entry["id"])
def test_real_document_samples_run_declared_smoke_checks(entry: dict) -> None:
    result = run_sample_checks(entry)

    for check_name, check_result in result["checks"].items():
        assert check_result["ok"], f"{entry['id']} failed {check_name}: {check_result}"


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.parametrize("entry", answer_key_samples(MANIFEST), ids=lambda entry: entry["id"])
def test_answer_key_samples_are_nonempty(entry: dict) -> None:
    result = run_sample_checks(entry)
    assert result["checks"]["answer_reference"]["ok"], f"answer key is empty: {entry['id']}"


@pytest.mark.smoke
@pytest.mark.integration
def test_manifest_smoke_report_has_no_failures() -> None:
    report = manifest_smoke_report()
    assert report["count"] >= 8
    assert report["failures"] == []
