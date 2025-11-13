#!/usr/bin/env python3
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    print("Missing dependency: pyyaml is required (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "docs" / "testing" / "catalog" / "backend"
    catalogs = []
    for path in sorted(backend_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f) or {}
            except Exception as exc:
                print(f"YAML parse error in {path}: {exc}", file=sys.stderr)
                sys.exit(1)
            catalogs.append(data)
    referenced = set()
    for c in catalogs:
        for it in c.get("items") or []:
            for t in it.get("tests") or []:
                if not isinstance(t, str):
                    continue
                p = t.split("::", 1)[0]
                if p.endswith(".py"):
                    referenced.add(Path(p).as_posix())
    tests_root = repo_root / "backend" / "tests"
    missing = []
    for p in tests_root.rglob("*.py"):
        if p.name in ("conftest.py", "__init__.py"):
            continue
        rel = p.relative_to(repo_root).as_posix()
        if rel not in referenced:
            missing.append(rel)
    if missing:
        print(
            "The following backend test files are not referenced in any catalog YAML:",
            file=sys.stderr,
        )
        for m in sorted(missing):
            print(f"- {m}", file=sys.stderr)
        print("\nAdd these to a catalog under docs/testing/catalog/backend/.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
