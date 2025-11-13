#!/usr/bin/env python3
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    print("Missing dependency: pyyaml is required (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

MARKER_NAMES = {"unit", "integration", "security", "contract", "admin", "slow"}


def extract_markers_from_file(py_file: Path) -> set[str]:
    text = py_file.read_text(encoding="utf-8", errors="ignore")
    found: set[str] = set()
    # Find @pytest.mark.<marker>
    for m in re.findall(r"@pytest\.mark\.([A-Za-z_][A-Za-z0-9_]*)", text):
        if m in MARKER_NAMES:
            found.add(m)
    # Find pytestmark = [pytest.mark.x, pytest.mark.y]
    for m in re.findall(r"pytestmark\s*=\s*\[(.*?)\]", text, flags=re.DOTALL):
        for inner in re.findall(r"pytest\.mark\.([A-Za-z_][A-Za-z0-9_]*)", m):
            if inner in MARKER_NAMES:
                found.add(inner)
    return found


def main():
    repo_root = Path(__file__).resolve().parents[1]
    backend_catalog_dir = repo_root / "docs" / "testing" / "catalog" / "backend"
    catalogs = sorted(backend_catalog_dir.glob("*.yaml"))
    if not catalogs:
        print("No backend catalogs found.", file=sys.stderr)
        sys.exit(1)

    changed = 0
    for cat_path in catalogs:
        data = yaml.safe_load(cat_path.read_text(encoding="utf-8")) or {}
        items = data.get("items") or []
        modified = False
        for it in items:
            tests = it.get("tests") or []
            if not tests:
                continue
            detected: set[str] = set()
            for t in tests:
                if not isinstance(t, str):
                    continue
                file_part = t.split("::", 1)[0]
                py_path = repo_root / file_part
                if not py_path.exists():
                    continue
                detected |= extract_markers_from_file(py_path)
            # Sync markers if we found any; keep unique, sorted for stability
            if detected:
                cur = set(it.get("markers") or [])
                # Replace with detected to match code, not union (ensures accuracy)
                new_markers = sorted(detected)
                if cur != set(new_markers):
                    it["markers"] = new_markers
                    modified = True
        if modified:
            cat_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            changed += 1

    print(f"Synchronized markers in {changed} catalog file(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
