#!/usr/bin/env python3
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    print("Missing dependency: pyyaml is required to run this script.", file=sys.stderr)
    sys.exit(2)


def load_catalogs(root: Path):
    catalogs = []
    for path in sorted(root.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            data["_filepath"] = str(path)
            catalogs.append(data)
    return catalogs


def compute_report(catalogs):
    id_to_files = {}
    per_area = {}
    totals = {
        "areas": 0,
        "items_total": 0,
        "items_implemented": 0,
        "items_planned": 0,
        "items_deprecated": 0,
    }

    for c in catalogs:
        area = c.get("area", "unknown")
        items = c.get("items", []) or []
        impl = sum(1 for it in items if (it.get("status") or "").lower() == "implemented")
        planned = sum(1 for it in items if (it.get("status") or "").lower() == "planned")
        deprecated = sum(1 for it in items if (it.get("status") or "").lower() == "deprecated")
        total = len(items)
        rate = (impl / total) if total else 0.0
        per_area[area] = {
            "file": c.get("_filepath"),
            "total": total,
            "implemented": impl,
            "planned": planned,
            "deprecated": deprecated,
            "implementation_rate": round(rate, 4),
        }
        totals["areas"] += 1
        totals["items_total"] += total
        totals["items_implemented"] += impl
        totals["items_planned"] += planned
        totals["items_deprecated"] += deprecated

        # collect ids for duplicate detection
        for it in items:
            tid = it.get("id")
            if not tid:
                continue
            id_to_files.setdefault(tid, set()).add(c.get("_filepath"))

    duplicates = {i: sorted(list(paths)) for i, paths in id_to_files.items() if len(paths) > 1}
    overall_rate = (
        (totals["items_implemented"] / totals["items_total"]) if totals["items_total"] else 0.0
    )

    return {
        "per_area": per_area,
        "totals": {**totals, "overall_implementation_rate": round(overall_rate, 4)},
        "duplicate_ids": duplicates,
    }


def main():
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "docs" / "testing" / "catalog" / "backend"
    out_file = backend_dir / "report.json"
    catalogs = load_catalogs(backend_dir)
    report = compute_report(catalogs)
    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote report to {out_file}")


if __name__ == "__main__":
    main()
