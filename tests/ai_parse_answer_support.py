from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from app import Api


SIZE_ALIASES_PT = {
    "初号": 42.0,
    "小初": 36.0,
    "一号": 26.0,
    "小一": 24.0,
    "二号": 22.0,
    "小二": 18.0,
    "三号": 16.0,
    "小三": 15.0,
    "四号": 14.0,
    "小四": 12.0,
    "五号": 10.5,
    "小五": 9.0,
    "六号": 7.5,
    "小六": 6.5,
}

HEADING_RE = re.compile(r"^(#+)\s+(.*)$")
BULLET_RE = re.compile(r"^\s*-\s+([^：:]+)[：:]\s*(.+?)\s*$")


def _clean_heading(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^[0-9]+(?:\.[0-9]+)*\s*", "", text)
    return text.strip()


def _clean_value(raw: str) -> str:
    return raw.replace("`", "").strip()


def _parse_size_pt(value: str) -> float | None:
    clean = _clean_value(value)
    for alias, pt in SIZE_ALIASES_PT.items():
        if alias in clean:
            return pt
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*pt", clean, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _parse_line_spacing(value: str) -> dict[str, float | str] | None:
    clean = _clean_value(value)
    match = re.search(r"固定值\s*([0-9]+(?:\.[0-9]+)?)\s*磅", clean)
    if match:
        return {"lineSpacingMode": "exact", "lineSpacingValue": float(match.group(1))}
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*倍", clean)
    if match:
        return {"lineSpacingMode": "multiple", "lineSpacingValue": float(match.group(1))}
    if "单倍行距" in clean:
        return {"lineSpacingMode": "multiple", "lineSpacingValue": 1.0}
    return None


def _parse_margin_cm(value: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*cm", _clean_value(value), re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def parse_ai_parse_answer(answer_path: Path) -> dict[str, object]:
    headings: list[str] = []
    rules: dict[str, object] = {}

    for raw_line in answer_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = _clean_heading(heading_match.group(2))
            while len(headings) >= level:
                headings.pop()
            headings.append(title)
            continue

        bullet_match = BULLET_RE.match(line)
        if not bullet_match:
            continue

        label = _clean_heading(bullet_match.group(1))
        value = _clean_value(bullet_match.group(2))
        current = headings[-1] if headings else ""

        if current == "主标题":
            if label == "对齐":
                rules["titleAlign"] = value
            elif label == "字体":
                rules["titleFont"] = value
            elif label == "字号":
                pt = _parse_size_pt(value)
                if pt is not None:
                    rules["titleSize"] = pt

        if current in {"一级标题", "二级标题", "三级标题", "四级标题"}:
            prefix = {"一级标题": "h1", "二级标题": "h2", "三级标题": "h3", "四级标题": "h4"}[current]
            if label in {"中文字体", "字体"}:
                rules[f"{prefix}Font"] = value
            elif label == "西文字体":
                rules["westFont"] = value
            elif label == "字号":
                pt = _parse_size_pt(value)
                if pt is not None:
                    rules[f"{prefix}Size"] = pt
            elif label == "行距":
                spacing = _parse_line_spacing(value)
                if spacing:
                    rules.update(spacing)

        if current == "正文":
            if label in {"字体", "正文字体"}:
                rules["bodyFont"] = value
            elif label in {"字号", "正文字号"}:
                pt = _parse_size_pt(value)
                if pt is not None:
                    rules["bodySize"] = pt
            elif label == "行距":
                spacing = _parse_line_spacing(value)
                if spacing:
                    rules.update(spacing)

        if current == "页边距":
            margin_key = {"上": "marginTop", "下": "marginBottom", "左": "marginLeft", "右": "marginRight"}.get(label)
            if margin_key:
                cm = _parse_margin_cm(value)
                if cm is not None:
                    rules[margin_key] = cm

    return rules


def build_ai_parse_pairs(manifest: dict) -> list[dict]:
    answers_by_id = {entry["id"]: entry for entry in manifest["samples"] if entry["kind"] == "markdown"}
    pairs: list[dict] = []
    sample_root = Path(manifest["sample_root"])
    for entry in manifest["samples"]:
        if "ai-parse" not in entry.get("labels", []):
            continue
        answer_id = entry["id"].replace("-docx", "-answer-md")
        answer_entry = answers_by_id.get(answer_id)
        if not answer_entry:
            continue
        pairs.append(
            {
                "id": entry["id"],
                "doc_path": sample_root / entry["path"],
                "answer_path": sample_root / answer_entry["path"],
            }
        )
    return pairs


def upload_template_payload(doc_path: Path) -> tuple[str, str]:
    b64 = base64.b64encode(doc_path.read_bytes()).decode("ascii")
    return b64, doc_path.name


def extract_template_text(doc_path: Path) -> str:
    return Api._extract_docx_text(str(doc_path))


def expected_rules_json(answer_path: Path) -> str:
    return json.dumps(parse_ai_parse_answer(answer_path), ensure_ascii=False)
