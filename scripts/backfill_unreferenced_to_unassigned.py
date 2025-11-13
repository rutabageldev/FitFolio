#!/usr/bin/env python3
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    print("Missing dependency: pyyaml is required to run this script.", file=sys.stderr)
    sys.exit(2)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "docs" / "testing" / "catalog" / "backend"
    report_file = backend_dir / "report.json"
    if not report_file.exists():
        print("Report not found. Run scripts/build_catalog_report.py first.", file=sys.stderr)
        sys.exit(1)
    report = json.loads(report_file.read_text(encoding="utf-8"))
    unref = report.get("unreferenced_test_files", [])
    items = []
    for idx, path in enumerate(sorted(unref), start=1):
        items.append(
            {
                "id": f"UNASSIGNED-{idx:03d}",
                "title": f"Unassigned test file {path}",
                "level": "integration",
                "markers": [],
                "risk": "medium",
                "status": "implemented",
                "tests": [path],
                "last_verified": None,
            }
        )
    out = {
        "schema": 1,
        "area": "unassigned",
        "updated": "auto",
        "owners": ["backend", "qa"],
        "items": items,
    }
    out_file = backend_dir / "unassigned.yaml"
    out_file.write_text(yaml.safe_dump(out, sort_keys=False), encoding="utf-8")
    print(f"Wrote {out_file} with {len(items)} items.")


if __name__ == "__main__":
    main()
