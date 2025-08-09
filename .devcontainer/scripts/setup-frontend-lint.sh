#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# 0) Ensure Node is available in the devcontainer (for hooks)
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "❌ Node/npm not found in devcontainer."
  echo "➡️  Adding Node 20 feature to .devcontainer/devcontainer.json ..."
  python - <<'PY'
import json, pathlib
p = pathlib.Path(".devcontainer/devcontainer.json")
data = json.loads(p.read_text())
feat = data.setdefault("features", {})
feat["ghcr.io/devcontainers/features/node:1"] = {"version":"20"}
p.write_text(json.dumps(data, indent=2) + "\n")
print("Updated", p)
PY
  echo "Please: Dev Containers → Rebuild and Reopen in Container, then re-run this script."
  exit 1
fi

# 1) Frontend project scaffold (idempotent)
mkdir -p frontend
cd frontend
[ -f package.json ] || npm init -y >/dev/null

# 2) Install ESLint + Prettier toolchain (React/TS friendly; OK for plain TS too)
npm i -D \
  eslint @eslint/js typescript typescript-eslint \
  eslint-plugin-react eslint-plugin-react-hooks \
  eslint-plugin-import eslint-plugin-jsx-a11y \
  prettier eslint-config-prettier >/dev/null

# 3) Write configs if missing
[ -f .eslintrc.cjs ] || cat > .eslintrc.cjs <<'CFG'
/* eslint-env node */
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint","react","react-hooks","import","jsx-a11y"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:import/recommended",
    "plugin:import/typescript",
    "plugin:jsx-a11y/recommended",
    "prettier"
  ],
  settings: { react: { version: "detect" } },
  ignorePatterns: ["dist","build","node_modules"],
};
CFG

[ -f .prettierrc ] || cat > .prettierrc <<'CFG'
{ "printWidth": 100, "singleQuote": true, "trailingComma": "all" }
CFG

[ -f .prettierignore ] || cat > .prettierignore <<'IGNORE'
dist
build
node_modules
IGNORE

# 4) Ensure npm scripts exist
node - <<'JS'
const fs = require('fs');
const p = 'package.json';
const pkg = JSON.parse(fs.readFileSync(p, 'utf8'));
pkg.scripts ||= {};
pkg.scripts.lint ||= "eslint . --ext .ts,.tsx,.js,.jsx";
pkg.scripts.format ||= "prettier -w .";
pkg.scripts["format:check"] ||= "prettier -c .";
fs.writeFileSync(p, JSON.stringify(pkg, null, 2) + "\n");
console.log("Updated frontend/package.json scripts.");
JS

cd "$ROOT"

# 5) Add pre-commit hooks (idempotent append)
PC='.pre-commit-config.yaml'
if ! grep -q "frontend eslint" "$PC" 2>/dev/null; then
  cat >> "$PC" <<'YAML'

- repo: local
  hooks:
    - id: eslint
      name: frontend eslint
      language: system
      types_or: [javascript, ts, tsx]
      entry: bash -lc "npm --prefix frontend run lint"
    - id: prettier
      name: frontend prettier check
      language: system
      types_or: [javascript, ts, tsx, json, css, scss, md, yaml, yml]
      entry: bash -lc "npm --prefix frontend run format:check"
YAML
  echo "Appended ESLint/Prettier hooks to .pre-commit-config.yaml"
fi

# 6) Ignore node_modules in git (if not already)
grep -qxF 'frontend/node_modules' .gitignore || echo 'frontend/node_modules' >> .gitignore

# 7) Install/refresh hooks and run once
pip install -q pre-commit >/dev/null || true
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
echo "▶ Running pre-commit across repo (first run may take a bit)..."
pre-commit run --all-files || true

echo "✅ ESLint + Prettier configured for frontend and wired to pre-commit."
echo "   Lint:   npm --prefix frontend run lint"
echo "   Format: npm --prefix frontend run format"
BASH
