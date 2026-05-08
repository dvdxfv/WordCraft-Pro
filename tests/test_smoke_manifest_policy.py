from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "samples" / "manifest.json"
README_PATH = ROOT / "samples" / "README.md"

REQUIRED_SAMPLE_KEYS = {"id", "path", "kind", "labels", "checks"}
REQUIRED_DOC_CHECKS = {"file_exists", "open_file", "preview"}


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_smoke_manifest_files_exist() -> None:
    assert README_PATH.exists(), "samples/README.md must exist"
    assert MANIFEST_PATH.exists(), "samples/manifest.json must exist"


def test_smoke_manifest_uses_real_sample_root() -> None:
    manifest = _load_manifest()
    sample_root = Path(manifest["sample_root"])

    assert str(sample_root) == r"G:\开发项目\备份\samples"
    assert sample_root.exists() and sample_root.is_dir()


def test_smoke_manifest_entries_are_concrete() -> None:
    manifest = _load_manifest()
    samples = manifest.get("samples", [])

    assert len(samples) >= 8, "real-sample smoke manifest should track the current external corpus"

    ids: set[str] = set()
    sample_root = Path(manifest["sample_root"])

    for entry in samples:
        assert REQUIRED_SAMPLE_KEYS.issubset(entry), f"missing keys in sample entry: {entry}"
        assert entry["id"] not in ids, f"duplicate sample id: {entry['id']}"
        ids.add(entry["id"])

        sample_path = sample_root / entry["path"]
        assert sample_path.exists(), f"missing real sample: {sample_path}"
        assert entry["labels"], f"sample must have labels: {entry['id']}"
        assert entry["checks"], f"sample must have checks: {entry['id']}"

        if entry["kind"] in {"doc", "docx"}:
            assert REQUIRED_DOC_CHECKS.issubset(set(entry["checks"])), (
                f"document sample must declare base smoke checks: {entry['id']}"
            )


def test_answer_key_samples_cover_real_templates() -> None:
    manifest = _load_manifest()
    samples = manifest["samples"]

    answer_keys = [entry for entry in samples if "answer-key" in entry["labels"]]
    templates = [entry for entry in samples if "format-spec" in entry["labels"]]

    assert len(answer_keys) >= 3
    assert len(templates) >= 3
