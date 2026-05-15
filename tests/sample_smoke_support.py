from __future__ import annotations

import base64
import io
import json
import zipfile
from pathlib import Path

from app import Api
from tests.ai_parse_answer_support import build_ai_parse_pairs, parse_ai_parse_answer


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "samples" / "manifest.json"


class SampleAssetsUnavailable(RuntimeError):
    """Raised when local-only real sample assets are unavailable."""


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def sample_root_from_manifest(manifest: dict) -> Path:
    return Path(manifest["sample_root"])


def ensure_sample_assets_available() -> tuple[dict, Path]:
    if not MANIFEST_PATH.exists():
        raise SampleAssetsUnavailable(
            f"real sample manifest is unavailable: {MANIFEST_PATH}"
        )

    manifest = load_manifest()
    sample_root = sample_root_from_manifest(manifest)
    if not sample_root.exists():
        raise SampleAssetsUnavailable(
            f"real sample root is unavailable: {sample_root}"
        )
    if not sample_root.is_dir():
        raise SampleAssetsUnavailable(
            f"real sample root is not a directory: {sample_root}"
        )
    return manifest, sample_root


def document_samples(manifest: dict) -> list[dict]:
    return [entry for entry in manifest["samples"] if entry["kind"] in {"doc", "docx"}]


def answer_key_samples(manifest: dict) -> list[dict]:
    return [entry for entry in manifest["samples"] if entry["kind"] == "markdown"]


def sample_path(sample_root: Path, entry: dict) -> Path:
    return sample_root / entry["path"]


def build_api() -> Api:
    api = Api(supabase_enabled=False)
    api._qa_health = {"ready": True, "missing": [], "capabilities": {}}
    api._qa_runtime_config = {}
    return api


def open_document(api: Api, path: Path) -> dict:
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return json.loads(api.openFile(payload, path.name))


def build_html_from_elements(elements: list[dict], limit: int = 40) -> str:
    chunks: list[str] = []
    for element in elements[:limit]:
        text = (element.get("text") or "").strip()
        if not text:
            continue
        element_type = (element.get("type") or "p").lower()
        if element_type in {"h1", "h2", "h3"}:
            chunks.append(f"<{element_type}>{text}</{element_type}>")
        else:
            chunks.append(f"<p>{text}</p>")
    return "".join(chunks)


def trusted_format_rules_for(path: Path) -> dict | None:
    if path.suffix.lower() != ".docx":
        return None
    rules = Api._extract_docx_format_rules(str(path))
    if not isinstance(rules, dict) or not rules:
        return None
    trusted = dict(rules)
    trusted["savedByUser"] = True
    trusted["saveSource"] = "manual"
    return trusted


def run_sample_checks(entry: dict) -> dict:
    manifest, sample_root = ensure_sample_assets_available()
    path = sample_path(sample_root, entry)
    ai_pairs = ai_parse_answer_pairs(manifest)
    api = build_api()

    result: dict = {
        "id": entry["id"],
        "path": str(path),
        "checks": {},
    }

    if "answer_reference" in entry["checks"]:
        text = path.read_text(encoding="utf-8")
        result["checks"]["answer_reference"] = {
            "ok": bool(text.strip()),
            "length": len(text),
        }
        return result

    opened = open_document(api, path)
    result["checks"]["open_file"] = {
        "ok": bool(opened.get("success")),
        "type": opened.get("type"),
        "element_count": opened.get("element_count", 0),
        "error": opened.get("error"),
    }
    if not opened.get("success"):
        return result

    elements = opened.get("elements") or []
    result["checks"]["preview"] = {
        "ok": bool(elements),
        "element_count": len(elements),
    }

    elements_json = json.dumps(elements, ensure_ascii=False)

    if "ai_parse" in entry["checks"]:
        pair = ai_pairs.get(entry["id"])
        answer_rules = parse_ai_parse_answer(pair["answer_path"]) if pair else {}
        upload = json.loads(api.uploadTemplate(str(path), path.stem))
        result["checks"]["ai_parse"] = {
            "ok": bool(upload.get("success")) and bool((upload.get("doc_text") or "").strip()) and bool(answer_rules),
            "doc_text_len": len((upload.get("doc_text") or "").strip()),
            "expected_rule_count": len(answer_rules),
            "error": upload.get("error"),
        }

    if "format_qa" in entry["checks"]:
        format_rules = trusted_format_rules_for(path)
        qa = json.loads(
            api.runQA(
                "",
                categories_str='["format"]',
                elements_json=elements_json,
                format_rules_json=json.dumps(format_rules, ensure_ascii=False) if format_rules else None,
            )
        )
        result["checks"]["format_qa"] = {
            "ok": bool(qa.get("success")),
            "issue_count": len(qa.get("issues", [])),
            "error": qa.get("error"),
        }

    if "xref" in entry["checks"]:
        xref = json.loads(api.runXRef("", opened.get("fielded_refs", []), elements_json=elements_json))
        result["checks"]["xref"] = {
            "ok": bool(xref.get("success")),
            "target_count": len(xref.get("targets", [])),
            "match_count": len(xref.get("matches", [])),
            "error": xref.get("error"),
        }

    if "export" in entry["checks"]:
        html = build_html_from_elements(elements)
        exported = json.loads(api.exportDocx(html, file_name=f"{path.stem}-smoke.docx"))
        ok = False
        if exported.get("success") and exported.get("content"):
            try:
                docx_bytes = base64.b64decode(exported["content"])
                with zipfile.ZipFile(io.BytesIO(docx_bytes), "r") as zf:
                    ok = "[Content_Types].xml" in zf.namelist()
            except Exception:
                ok = False
        result["checks"]["export"] = {
            "ok": ok,
            "error": exported.get("error"),
        }

    return result


def manifest_smoke_report() -> dict:
    manifest, sample_root = ensure_sample_assets_available()
    rows = [run_sample_checks(entry) for entry in manifest["samples"]]
    failures = []
    for row in rows:
        for check_name, check_result in row["checks"].items():
            if not check_result.get("ok", False):
                failures.append({"id": row["id"], "check": check_name, "path": row["path"]})

    return {
        "sample_root": str(sample_root),
        "count": len(rows),
        "failures": failures,
        "samples": rows,
    }


def ai_parse_answer_pairs(manifest: dict) -> dict[str, dict]:
    return {pair["id"]: pair for pair in build_ai_parse_pairs(manifest)}
