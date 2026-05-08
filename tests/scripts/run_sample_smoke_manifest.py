from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "samples" / "manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sample_root = Path(manifest["sample_root"])
    rows = []

    for entry in manifest["samples"]:
        sample_path = sample_root / entry["path"]
        rows.append(
            {
                "id": entry["id"],
                "kind": entry["kind"],
                "exists": sample_path.exists(),
                "labels": entry["labels"],
                "checks": entry["checks"],
                "path": str(sample_path),
            }
        )

    report = {
        "sample_root": str(sample_root),
        "count": len(rows),
        "missing": [row["id"] for row in rows if not row["exists"]],
        "samples": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["missing"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
